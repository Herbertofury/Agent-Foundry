#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import artifact_publisher as ap


class FakeResponse:
    def __init__(self, status: int, payload: dict):
        self.status = status
        self._data = json.dumps(payload).encode()

    def read(self) -> bytes:
        return self._data


class FakeHTTPSConnection:
    instances = []
    response_payload = {}

    def __init__(self, host: str, timeout: int = 0):
        self.host = host
        self.timeout = timeout
        self.headers = {}
        self.sent = bytearray()
        self.method = None
        self.path = None
        type(self).instances.append(self)

    def putrequest(self, method: str, path: str):
        self.method = method
        self.path = path

    def putheader(self, key: str, value: str):
        self.headers[key] = value

    def endheaders(self):
        return None

    def send(self, data: bytes):
        self.sent.extend(data)

    def getresponse(self):
        return FakeResponse(201, type(self).response_payload)

    def close(self):
        return None


class PublisherTests(unittest.TestCase):
    def test_prepare_split_verify_and_reassemble(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.bin"
            source.write_bytes((b"gamesync" * 200_000) + os.urandom(2048))
            out = root / "prepared"
            manifest_path = ap.prepare_artifact(source, out, None, chunk_mib=1)
            manifest = ap.load_json(manifest_path)
            self.assertGreater(len(manifest["parts"]), 1)
            ap.verify_manifest(manifest_path, reassemble=True)
            expected = ap.digest_file(out / source.name)
            self.assertEqual(expected.sha256, manifest["artifact"]["sha256"])
            self.assertTrue((out / "REASSEMBLE-WINDOWS.cmd").is_file())
            self.assertTrue((out / "reassemble-unix.sh").is_file())

    def test_deterministic_zip(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "tree"
            source.mkdir()
            (source / "a.txt").write_text("alpha", encoding="utf-8")
            (source / "nested").mkdir()
            (source / "nested" / "b.bin").write_bytes(b"beta" * 1024)
            first = root / "first.zip"
            second = root / "second.zip"
            ap.deterministic_zip(source, first)
            ap.deterministic_zip(source, second)
            self.assertEqual(ap.digest_file(first).sha256, ap.digest_file(second).sha256)

    def test_tamper_detection(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.bin"
            source.write_bytes(b"x" * (2 * 1024 * 1024))
            manifest_path = ap.prepare_artifact(source, root / "out", None, chunk_mib=1)
            manifest = ap.load_json(manifest_path)
            part = manifest_path.parent / manifest["parts"][0]["name"]
            with part.open("r+b") as handle:
                handle.seek(10)
                handle.write(b"BAD")
            with self.assertRaises(ap.PublisherError):
                ap.verify_manifest(manifest_path, reassemble=True)

    def test_github_binary_stream_and_digest_verification(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "asset.zip"
            payload = os.urandom(512 * 1024)
            path.write_bytes(payload)
            local = ap.digest_file(path)
            asset = {
                "id": 123,
                "name": path.name,
                "state": "uploaded",
                "size": local.size,
                "digest": f"sha256:{local.sha256}",
                "url": "https://api.github.invalid/asset/123",
                "browser_download_url": "https://github.invalid/download/asset.zip",
            }
            FakeHTTPSConnection.instances.clear()
            FakeHTTPSConnection.response_payload = asset
            publisher = ap.GitHubPublisher("secret", "owner/repo")
            publisher.cleanup_named_asset = lambda release_id, digest: None  # type: ignore[method-assign]
            with mock.patch.object(ap.http.client, "HTTPSConnection", FakeHTTPSConnection):
                result = publisher.upload_asset(1, local, retries=0)
            self.assertEqual(result["digest"], f"sha256:{local.sha256}")
            self.assertEqual(bytes(FakeHTTPSConnection.instances[-1].sent), payload)
            self.assertEqual(FakeHTTPSConnection.instances[-1].headers["Content-Length"], str(len(payload)))

    def test_google_drive_resumable_contract(self):
        class FakeDrive(ap.GoogleDrivePublisher):
            def __init__(self):
                super().__init__("secret")
                self.uploaded = bytearray()
                self.local = None

            def start_session(self, local, parent_id):
                self.local = local
                return "https://upload.invalid/session"

            def query_offset(self, session_url, total):
                return 0, None

            def upload_chunk(self, session_url, block, start, total):
                self.uploaded.extend(block)
                end = start + len(block)
                if end < total:
                    return end, None
                return 200, {"id": "file123"}

            def get_metadata(self, file_id):
                return {
                    "id": file_id,
                    "size": str(self.local.size),
                    "md5Checksum": self.local.md5,
                    "webViewLink": "https://drive.invalid/file123",
                }

            def create_permission(self, file_id, email, anyone):
                return None

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / "large.bin"
            payload = os.urandom(700 * 1024)
            path.write_bytes(payload)
            publisher = FakeDrive()
            result = publisher.upload_file(path, None, None, False, root / "state", chunk_size=256 * 1024)
            self.assertEqual(bytes(publisher.uploaded), payload)
            self.assertEqual(result["sha256"], hashlib.sha256(payload).hexdigest())
            self.assertFalse(any((root / "state").glob("*.json")))

    def test_helpers(self):
        self.assertEqual(ap.safe_filename(" ../Bad name?.zip "), "Bad-name-.zip")
        self.assertEqual(ap.nested_json_value({"a": [{"b": "ok"}]}, "a.0.b"), "ok")
        local = ap.FileDigest(Path("x"), 10, "a" * 64, "b" * 32)
        publisher = ap.GitHubPublisher("secret", "owner/repo")
        self.assertTrue(publisher.asset_shape_matches({"state": "uploaded", "size": 10, "digest": "sha256:" + "a" * 64}, local))
        self.assertFalse(publisher.asset_shape_matches({"state": "starter", "size": 10}, local))


if __name__ == "__main__":
    unittest.main(verbosity=2)
