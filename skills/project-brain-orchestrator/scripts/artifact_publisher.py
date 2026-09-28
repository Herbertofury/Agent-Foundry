#!/usr/bin/env python3
"""Reliable artifact preparation and publication.

Standard-library-only CLI for:
- deterministic ZIP creation
- upload-safe multipart splitting and reassembly helpers
- local SHA-256/MD5 verification
- transactional GitHub Release uploads
- resumable Google Drive uploads
- configurable raw or multipart HTTP uploads

Secrets are accepted only from environment variables or existing authenticated CLIs.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import dataclasses
import datetime as dt
import getpass
import hashlib
import http.client
import json
import mimetypes
import os
from pathlib import Path
import random
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from typing import Any, BinaryIO, Iterable, Iterator, Mapping, Sequence
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile


SCHEMA_VERSION = 1
DEFAULT_CHUNK_MIB = 85
IO_CHUNK = 4 * 1024 * 1024
DRIVE_CHUNK = 8 * 1024 * 1024
TRANSIENT_HTTP = {408, 409, 425, 429, 500, 502, 503, 504}
GITHUB_API_VERSION = "2022-11-28"
API_TIMEOUT = 60
UPLOAD_TIMEOUT = 120
DEFAULT_API_RETRIES = 2
DEFAULT_UPLOAD_RETRIES = 2
DRIVE_CHUNK_RETRIES = 3
MAX_RETRY_DELAY = 30.0


class PublisherError(RuntimeError):
    """Expected user-facing failure."""


@dataclasses.dataclass(frozen=True)
class FileDigest:
    path: Path
    size: int
    sha256: str
    md5: str

    def to_json(self, base: Path | None = None) -> dict[str, Any]:
        name = self.path.name if base is None else self.path.relative_to(base).as_posix()
        return {"name": name, "size": self.size, "sha256": self.sha256, "md5": self.md5}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def eprint(*args: object, **kwargs: Any) -> None:
    kwargs.setdefault("file", sys.stderr)
    kwargs.setdefault("flush", True)
    print(*args, **kwargs)


def human_bytes(value: int) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.2f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{value} B"


def digest_file(path: Path, chunk_size: int = IO_CHUNK) -> FileDigest:
    sha = hashlib.sha256()
    md5 = hashlib.md5(usedforsecurity=False)
    size = 0
    with path.open("rb") as handle:
        while True:
            block = handle.read(chunk_size)
            if not block:
                break
            size += len(block)
            sha.update(block)
            md5.update(block)
    return FileDigest(path=path, size=size, sha256=sha.hexdigest(), md5=md5.hexdigest())


def atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise PublisherError(f"Expected a JSON object in {path}")
    return value


def safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._+-]+", "-", name).strip(".-")
    return cleaned or "artifact.bin"


def hardlink_or_copy(source: Path, destination: Path) -> None:
    if source.resolve() == destination.resolve():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(OSError):
        os.link(source, destination)
        return
    shutil.copy2(source, destination)


def deterministic_zip(source_dir: Path, output_file: Path) -> None:
    """Create a stable ZIP without following directory symlinks."""
    source_dir = source_dir.resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    temp = output_file.with_name(f".{output_file.name}.{uuid.uuid4().hex}.tmp")
    fixed_time = (1980, 1, 1, 0, 0, 0)

    paths = sorted(source_dir.rglob("*"), key=lambda p: p.relative_to(source_dir).as_posix())
    with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9, allowZip64=True) as archive:
        for path in paths:
            relative = path.relative_to(source_dir).as_posix()
            if not relative:
                continue
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                info = zipfile.ZipInfo(relative, fixed_time)
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(info, os.readlink(path).encode("utf-8"))
            elif path.is_dir():
                info = zipfile.ZipInfo(relative.rstrip("/") + "/", fixed_time)
                info.create_system = 3
                info.external_attr = (stat.S_IFDIR | 0o755) << 16
                archive.writestr(info, b"")
            elif path.is_file():
                info = zipfile.ZipInfo(relative, fixed_time)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | (mode & 0o777 or 0o644)) << 16
                with path.open("rb") as handle, archive.open(info, "w", force_zip64=True) as target:
                    while True:
                        block = handle.read(IO_CHUNK)
                        if not block:
                            break
                        target.write(block)
    os.replace(temp, output_file)


def split_file(path: Path, output_dir: Path, chunk_bytes: int) -> list[FileDigest]:
    if chunk_bytes <= 0:
        return []
    output_dir.mkdir(parents=True, exist_ok=True)
    parts: list[FileDigest] = []
    with path.open("rb") as source:
        index = 0
        while True:
            first = source.read(min(IO_CHUNK, chunk_bytes))
            if not first:
                break
            part_path = output_dir / f"{path.name}.part{index:03d}"
            sha = hashlib.sha256()
            md5 = hashlib.md5(usedforsecurity=False)
            written = 0
            with part_path.open("wb") as target:
                block = first
                while block:
                    target.write(block)
                    sha.update(block)
                    md5.update(block)
                    written += len(block)
                    if written >= chunk_bytes:
                        break
                    block = source.read(min(IO_CHUNK, chunk_bytes - written))
                target.flush()
                os.fsync(target.fileno())
            parts.append(FileDigest(part_path, written, sha.hexdigest(), md5.hexdigest()))
            index += 1
    return parts


def write_reassembly_helpers(output_dir: Path, artifact: FileDigest, parts: Sequence[FileDigest]) -> None:
    if not parts:
        return
    windows = output_dir / "REASSEMBLE-WINDOWS.cmd"
    unix = output_dir / "reassemble-unix.sh"
    quoted_parts = "+".join(f'"{part.path.name}"' for part in parts)
    windows.write_text(
        "@echo off\r\n"
        "setlocal EnableExtensions\r\n"
        "cd /d \"%~dp0\"\r\n"
        f"copy /b {quoted_parts} \"{artifact.path.name}\" >nul || exit /b 1\r\n"
        f"powershell -NoProfile -ExecutionPolicy Bypass -Command \"$h=(Get-FileHash -Algorithm SHA256 -LiteralPath '{artifact.path.name}').Hash.ToLower(); if($h -ne '{artifact.sha256}'){{Write-Error ('SHA-256 mismatch: '+$h); exit 2}} else {{Write-Host 'Verified {artifact.path.name}: '+$h}}\"\r\n"
        "exit /b %errorlevel%\r\n",
        encoding="utf-8",
        newline="",
    )
    unix.write_text(
        "#!/bin/sh\nset -eu\ncd \"$(dirname \"$0\")\"\n"
        f"cat {' '.join(repr(part.path.name) for part in parts)} > {artifact.path.name!r}\n"
        f"actual=$(sha256sum {artifact.path.name!r} | awk '{{print $1}}')\n"
        f"[ \"$actual\" = \"{artifact.sha256}\" ] || {{ echo \"SHA-256 mismatch: $actual\" >&2; exit 2; }}\n"
        f"echo \"Verified {artifact.path.name}: $actual\"\n",
        encoding="utf-8",
        newline="\n",
    )
    unix.chmod(0o755)


def write_checksums(output_dir: Path, artifact: FileDigest, parts: Sequence[FileDigest]) -> Path:
    checksums = output_dir / "SHA256SUMS.txt"
    rows = [f"{artifact.sha256} *{artifact.path.name}"]
    rows.extend(f"{part.sha256} *{part.path.name}" for part in parts)
    checksums.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    return checksums


def prepare_artifact(source: Path, output_dir: Path, name: str | None, chunk_mib: int) -> Path:
    source = source.resolve()
    if not source.exists():
        raise PublisherError(f"Source does not exist: {source}")
    output_dir.mkdir(parents=True, exist_ok=True)

    if source.is_dir():
        artifact_name = safe_filename(name or f"{source.name}.zip")
        if not artifact_name.lower().endswith(".zip"):
            artifact_name += ".zip"
        artifact_path = output_dir / artifact_name
        eprint(f"Creating deterministic ZIP: {artifact_path}")
        deterministic_zip(source, artifact_path)
    elif source.is_file():
        artifact_name = safe_filename(name or source.name)
        artifact_path = output_dir / artifact_name
        eprint(f"Staging artifact: {artifact_path}")
        hardlink_or_copy(source, artifact_path)
    else:
        raise PublisherError(f"Unsupported source type: {source}")

    artifact = digest_file(artifact_path)
    eprint(f"Artifact: {artifact.path.name} ({human_bytes(artifact.size)})")
    eprint(f"SHA-256: {artifact.sha256}")

    chunk_bytes = chunk_mib * 1024 * 1024 if chunk_mib > 0 and artifact.size > chunk_mib * 1024 * 1024 else 0
    parts = split_file(artifact_path, output_dir, chunk_bytes) if chunk_bytes else []
    if parts:
        eprint(f"Created {len(parts)} part(s), maximum {chunk_mib} MiB each")

    checksums = write_checksums(output_dir, artifact, parts)
    write_reassembly_helpers(output_dir, artifact, parts)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "created_utc": utc_now(),
        "artifact": artifact.to_json(output_dir),
        "parts": [part.to_json(output_dir) for part in parts],
        "sidecars": [checksums.name]
        + (["REASSEMBLE-WINDOWS.cmd", "reassemble-unix.sh"] if parts else []),
    }
    manifest_path = output_dir / "UPLOAD-MANIFEST.json"
    atomic_json(manifest_path, manifest)
    verify_manifest(manifest_path, reassemble=False)
    eprint(f"Manifest: {manifest_path}")
    return manifest_path


def digest_from_manifest(base: Path, entry: Mapping[str, Any]) -> FileDigest:
    try:
        name = str(entry["name"])
        size = int(entry["size"])
        sha256 = str(entry["sha256"]).lower()
        md5 = str(entry.get("md5", "")).lower()
    except (KeyError, TypeError, ValueError) as exc:
        raise PublisherError(f"Malformed manifest entry: {entry}") from exc
    return FileDigest(base / name, size, sha256, md5)


def verify_digest(expected: FileDigest) -> None:
    if not expected.path.is_file():
        raise PublisherError(f"Missing file: {expected.path}")
    actual = digest_file(expected.path)
    if actual.size != expected.size:
        raise PublisherError(f"Size mismatch for {expected.path.name}: {actual.size} != {expected.size}")
    if actual.sha256 != expected.sha256:
        raise PublisherError(f"SHA-256 mismatch for {expected.path.name}: {actual.sha256} != {expected.sha256}")
    if expected.md5 and actual.md5 != expected.md5:
        raise PublisherError(f"MD5 mismatch for {expected.path.name}: {actual.md5} != {expected.md5}")


def verify_manifest(manifest_path: Path, reassemble: bool = False) -> None:
    manifest_path = manifest_path.resolve()
    manifest = load_json(manifest_path)
    base = manifest_path.parent
    artifact = digest_from_manifest(base, manifest["artifact"])
    parts = [digest_from_manifest(base, item) for item in manifest.get("parts", [])]

    if parts:
        for part in parts:
            verify_digest(part)
        if reassemble:
            temp = base / f".{artifact.path.name}.{uuid.uuid4().hex}.verify"
            sha = hashlib.sha256()
            md5 = hashlib.md5(usedforsecurity=False)
            size = 0
            try:
                with temp.open("wb") as out:
                    for part in parts:
                        with part.path.open("rb") as handle:
                            while True:
                                block = handle.read(IO_CHUNK)
                                if not block:
                                    break
                                out.write(block)
                                sha.update(block)
                                md5.update(block)
                                size += len(block)
                if size != artifact.size or sha.hexdigest() != artifact.sha256:
                    raise PublisherError("Reassembled artifact does not match the manifest")
                if artifact.md5 and md5.hexdigest() != artifact.md5:
                    raise PublisherError("Reassembled artifact MD5 does not match the manifest")
            finally:
                temp.unlink(missing_ok=True)
    else:
        verify_digest(artifact)
    eprint(f"Verified manifest: {manifest_path}")


def manifest_upload_files(manifest_path: Path) -> list[Path]:
    manifest = load_json(manifest_path)
    base = manifest_path.resolve().parent
    parts = [base / str(item["name"]) for item in manifest.get("parts", [])]
    artifact = base / str(manifest["artifact"]["name"])
    files = parts if parts else [artifact]
    files.append(manifest_path.resolve())
    for sidecar in manifest.get("sidecars", []):
        candidate = base / str(sidecar)
        if candidate.exists():
            files.append(candidate)
    # Stable de-duplication.
    seen: set[Path] = set()
    result: list[Path] = []
    for item in files:
        resolved = item.resolve()
        if resolved not in seen:
            seen.add(resolved)
            result.append(resolved)
    return result


def token_from_environment(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value.strip()
    return None


def command_output(command: Sequence[str]) -> str | None:
    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=20)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() or None


def retry_delay(attempt: int, retry_after: str | None = None) -> float:
    if retry_after:
        with contextlib.suppress(ValueError):
            return min(float(retry_after), MAX_RETRY_DELAY)
    return min(2 ** attempt + random.random(), MAX_RETRY_DELAY)


class JsonApi:
    def __init__(self, token: str, base_url: str, auth_scheme: str = "Bearer") -> None:
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.auth_scheme = auth_scheme

    def request(
        self,
        method: str,
        path_or_url: str,
        payload: Any | None = None,
        expected: Iterable[int] = (200,),
        extra_headers: Mapping[str, str] | None = None,
        retries: int = DEFAULT_API_RETRIES,
    ) -> tuple[int, Mapping[str, str], Any]:
        url = path_or_url if path_or_url.startswith("http") else self.base_url + path_or_url
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {
            "Accept": "application/json",
            "Authorization": f"{self.auth_scheme} {self.token}",
            "User-Agent": "reliable-artifact-publisher/1",
        }
        if body is not None:
            headers["Content-Type"] = "application/json; charset=utf-8"
        if extra_headers:
            headers.update(extra_headers)
        expected_set = set(expected)
        last_error = "unknown error"
        for attempt in range(retries + 1):
            request = urllib.request.Request(url, data=body, method=method, headers=headers)
            try:
                with urllib.request.urlopen(request, timeout=API_TIMEOUT) as response:
                    raw = response.read()
                    parsed = json.loads(raw) if raw else None
                    if response.status not in expected_set:
                        raise PublisherError(f"Unexpected HTTP {response.status} from {url}")
                    return response.status, dict(response.headers.items()), parsed
            except urllib.error.HTTPError as exc:
                raw = exc.read()
                detail = raw.decode("utf-8", errors="replace")[:2000]
                last_error = f"HTTP {exc.code}: {detail}"
                if exc.code not in TRANSIENT_HTTP or attempt >= retries:
                    raise PublisherError(f"{method} {url} failed: {last_error}") from exc
                time.sleep(retry_delay(attempt, exc.headers.get("Retry-After")))
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = str(exc)
                if attempt >= retries:
                    raise PublisherError(f"{method} {url} failed after retries: {last_error}") from exc
                time.sleep(retry_delay(attempt))
        raise PublisherError(f"{method} {url} failed: {last_error}")


class GitHubPublisher:
    def __init__(self, token: str, repo: str) -> None:
        if not re.fullmatch(r"[^/\s]+/[^/\s]+", repo):
            raise PublisherError("GitHub repo must be OWNER/REPO")
        self.token = token
        self.repo = repo
        self.api = JsonApi(token, "https://api.github.com")
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
        }

    @staticmethod
    def resolve_token() -> str:
        token = token_from_environment("GH_TOKEN", "GITHUB_TOKEN")
        if token:
            return token
        token = command_output(["gh", "auth", "token"])
        if token:
            return token
        raise PublisherError(
            "GitHub authentication is required. Connect GitHub, run 'gh auth login', or set GH_TOKEN/GITHUB_TOKEN. "
            "Use a fine-grained token with Contents: write for the target repository."
        )

    def get_repo(self) -> dict[str, Any]:
        _, _, repo = self.api.request("GET", f"/repos/{self.repo}", expected=(200,), extra_headers=self.headers)
        return dict(repo)

    def ensure_repo(self, private: bool = True) -> dict[str, Any]:
        try:
            return self.get_repo()
        except PublisherError as exc:
            if "HTTP 404" not in str(exc):
                raise
        owner, name = self.repo.split("/", 1)
        _, _, user = self.api.request("GET", "/user", expected=(200,), extra_headers=self.headers)
        login = str(user.get("login", ""))
        payload = {"name": name, "private": private, "auto_init": True, "description": "Artifact publication repository"}
        endpoint = "/user/repos" if login.lower() == owner.lower() else f"/orgs/{owner}/repos"
        _, _, repo = self.api.request("POST", endpoint, payload, expected=(201,), extra_headers=self.headers)
        return dict(repo)

    def get_release_by_tag(self, tag: str) -> dict[str, Any] | None:
        try:
            _, _, release = self.api.request(
                "GET", f"/repos/{self.repo}/releases/tags/{urllib.parse.quote(tag, safe='')}",
                expected=(200,), extra_headers=self.headers,
            )
            return dict(release)
        except PublisherError as exc:
            if "HTTP 404" in str(exc):
                return None
            raise

    def create_release(self, tag: str, title: str, body: str, target: str | None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "tag_name": tag,
            "name": title,
            "body": body,
            "draft": True,
            "prerelease": False,
        }
        if target:
            payload["target_commitish"] = target
        _, _, release = self.api.request(
            "POST", f"/repos/{self.repo}/releases", payload, expected=(201,), extra_headers=self.headers
        )
        return dict(release)

    def list_assets(self, release_id: int) -> list[dict[str, Any]]:
        _, _, assets = self.api.request(
            "GET", f"/repos/{self.repo}/releases/{release_id}/assets?per_page=100",
            expected=(200,), extra_headers=self.headers,
        )
        return [dict(item) for item in assets]

    def delete_asset(self, asset_id: int) -> None:
        self.api.request(
            "DELETE", f"/repos/{self.repo}/releases/assets/{asset_id}",
            expected=(204,), extra_headers=self.headers,
        )

    def asset_shape_matches(self, asset: Mapping[str, Any], local: FileDigest) -> bool:
        if asset.get("state") != "uploaded" or int(asset.get("size", -1)) != local.size:
            return False
        digest = str(asset.get("digest") or "")
        return not digest or digest.lower() == f"sha256:{local.sha256}"

    def verify_asset(self, asset: Mapping[str, Any], local: FileDigest) -> bool:
        if not self.asset_shape_matches(asset, local):
            return False
        digest = str(asset.get("digest") or "")
        if digest:
            return digest.lower() == f"sha256:{local.sha256}"
        # Older GitHub responses may omit digest. In that case, fully download
        # through the authenticated asset API and verify every byte.
        asset_url = str(asset.get("url") or "")
        if not asset_url:
            return False
        request = urllib.request.Request(
            asset_url,
            method="GET",
            headers={
                "Accept": "application/octet-stream",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": GITHUB_API_VERSION,
                "User-Agent": "reliable-artifact-publisher/1",
            },
        )
        sha = hashlib.sha256()
        size = 0
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                while True:
                    block = response.read(IO_CHUNK)
                    if not block:
                        break
                    size += len(block)
                    sha.update(block)
        except (urllib.error.URLError, OSError, TimeoutError):
            return False
        return size == local.size and sha.hexdigest() == local.sha256

    def cleanup_named_asset(self, release_id: int, local: FileDigest) -> dict[str, Any] | None:
        matches = [asset for asset in self.list_assets(release_id) if str(asset.get("name")) == local.path.name]
        for asset in matches:
            if self.verify_asset(asset, local):
                return asset
            eprint(f"Deleting mismatched/stuck GitHub asset: {local.path.name}")
            self.delete_asset(int(asset["id"]))
        return None

    def upload_asset(self, release_id: int, local: FileDigest, retries: int = DEFAULT_UPLOAD_RETRIES) -> dict[str, Any]:
        existing = self.cleanup_named_asset(release_id, local)
        if existing:
            eprint(f"GitHub asset already verified: {local.path.name}")
            return existing

        mime = mimetypes.guess_type(local.path.name)[0] or "application/octet-stream"
        query = urllib.parse.urlencode({"name": local.path.name})
        path = f"/repos/{self.repo}/releases/{release_id}/assets?{query}"
        last_error = "unknown error"
        for attempt in range(retries + 1):
            connection = http.client.HTTPSConnection("uploads.github.com", timeout=UPLOAD_TIMEOUT)
            try:
                connection.putrequest("POST", path)
                connection.putheader("Accept", "application/vnd.github+json")
                connection.putheader("Authorization", f"Bearer {self.token}")
                connection.putheader("X-GitHub-Api-Version", GITHUB_API_VERSION)
                connection.putheader("User-Agent", "reliable-artifact-publisher/1")
                connection.putheader("Content-Type", mime)
                connection.putheader("Content-Length", str(local.size))
                connection.endheaders()
                sent = 0
                with local.path.open("rb") as handle:
                    while True:
                        block = handle.read(IO_CHUNK)
                        if not block:
                            break
                        connection.send(block)
                        sent += len(block)
                        eprint(f"Uploading {local.path.name}: {sent * 100 // local.size}%", end="\r")
                response = connection.getresponse()
                raw = response.read()
                eprint(" " * 100, end="\r")
                if response.status == 201:
                    asset = json.loads(raw)
                    if not self.verify_asset(asset, local):
                        raise PublisherError(f"GitHub returned an unverified asset for {local.path.name}: {asset}")
                    eprint(f"GitHub verified: {local.path.name} ({human_bytes(local.size)})")
                    return dict(asset)
                detail = raw.decode("utf-8", errors="replace")[:2000]
                last_error = f"HTTP {response.status}: {detail}"
                if response.status not in TRANSIENT_HTTP or attempt >= retries:
                    raise PublisherError(f"GitHub upload failed: {last_error}")
            except (OSError, TimeoutError, http.client.HTTPException, PublisherError) as exc:
                last_error = str(exc)
                # GitHub may leave a zero-byte starter asset after a 502.
                with contextlib.suppress(Exception):
                    self.cleanup_named_asset(release_id, local)
                if attempt >= retries:
                    raise PublisherError(f"GitHub upload failed after retries: {last_error}") from exc
                time.sleep(retry_delay(attempt))
            finally:
                connection.close()
        raise PublisherError(last_error)

    def publish_release(self, release_id: int) -> dict[str, Any]:
        _, _, release = self.api.request(
            "PATCH", f"/repos/{self.repo}/releases/{release_id}", {"draft": False},
            expected=(200,), extra_headers=self.headers,
        )
        return dict(release)

    def upload_release(
        self,
        files: Sequence[Path],
        tag: str,
        title: str,
        body: str,
        target: str | None,
        create_repo: bool,
        private_repo: bool,
        keep_draft: bool,
        receipt_path: Path,
    ) -> dict[str, Any]:
        repo = self.ensure_repo(private=private_repo) if create_repo else self.get_repo()
        if not target:
            target = str(repo.get("default_branch") or "main")
        release = self.get_release_by_tag(tag) or self.create_release(tag, title, body, target)
        release_id = int(release["id"])
        local_digests = [digest_file(path.resolve()) for path in files]
        for digest in local_digests:
            self.upload_asset(release_id, digest)

        # Re-list before publication; never trust only the upload response.
        remote_by_name = {str(asset.get("name")): asset for asset in self.list_assets(release_id)}
        for local in local_digests:
            remote = remote_by_name.get(local.path.name)
            if not remote or not self.verify_asset(remote, local):
                raise PublisherError(f"Final GitHub verification failed for {local.path.name}")
        if not keep_draft:
            release = self.publish_release(release_id)
        else:
            release = self.get_release_by_tag(tag) or release

        receipt = {
            "schema_version": SCHEMA_VERSION,
            "provider": "github-release",
            "verified_utc": utc_now(),
            "repository": self.repo,
            "tag": tag,
            "release_url": release.get("html_url"),
            "draft": bool(release.get("draft")),
            "assets": [
                {
                    "name": local.path.name,
                    "size": local.size,
                    "sha256": local.sha256,
                    "url": remote_by_name[local.path.name].get("browser_download_url"),
                    "remote_digest": remote_by_name[local.path.name].get("digest"),
                }
                for local in local_digests
            ],
        }
        atomic_json(receipt_path, receipt)
        return receipt


class GoogleDrivePublisher:
    def __init__(self, token: str) -> None:
        self.token = token
        self.api = JsonApi(token, "https://www.googleapis.com")

    @staticmethod
    def resolve_token() -> str:
        token = token_from_environment("GOOGLE_DRIVE_ACCESS_TOKEN", "GOOGLE_OAUTH_ACCESS_TOKEN")
        if token:
            return token
        token = command_output(["gcloud", "auth", "print-access-token"])
        if token:
            return token
        raise PublisherError(
            "Google Drive authentication is required. Use the connected Google Drive tool, or set "
            "GOOGLE_DRIVE_ACCESS_TOKEN / authenticate gcloud. Tokens are never written to disk."
        )

    def start_session(self, local: FileDigest, parent_id: str | None) -> str:
        metadata: dict[str, Any] = {"name": local.path.name}
        if parent_id:
            metadata["parents"] = [parent_id]
        url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&fields=id,name,size,md5Checksum,webViewLink,webContentLink"
        body = json.dumps(metadata).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json; charset=UTF-8",
            "Content-Length": str(len(body)),
            "X-Upload-Content-Type": mimetypes.guess_type(local.path.name)[0] or "application/octet-stream",
            "X-Upload-Content-Length": str(local.size),
            "User-Agent": "reliable-artifact-publisher/1",
        }
        request = urllib.request.Request(url, data=body, method="POST", headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=API_TIMEOUT) as response:
                location = response.headers.get("Location")
                if response.status != 200 or not location:
                    raise PublisherError("Google Drive did not return a resumable session URL")
                return location
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:2000]
            raise PublisherError(f"Could not start Google Drive upload: HTTP {exc.code}: {detail}") from exc

    def query_offset(self, session_url: str, total: int) -> tuple[int, dict[str, Any] | None]:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Length": "0",
            "Content-Range": f"bytes */{total}",
            "User-Agent": "reliable-artifact-publisher/1",
        }
        request = urllib.request.Request(session_url, data=b"", method="PUT", headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=API_TIMEOUT) as response:
                raw = response.read()
                return total, json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            if exc.code == 308:
                range_header = exc.headers.get("Range")
                if not range_header:
                    return 0, None
                match = re.search(r"bytes=0-(\d+)", range_header)
                return (int(match.group(1)) + 1 if match else 0), None
            if exc.code == 404:
                return -1, None
            detail = exc.read().decode("utf-8", errors="replace")[:2000]
            raise PublisherError(f"Google Drive status query failed: HTTP {exc.code}: {detail}") from exc

    def upload_chunk(self, session_url: str, block: bytes, start: int, total: int) -> tuple[int, dict[str, Any] | None]:
        end = start + len(block) - 1
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Length": str(len(block)),
            "Content-Range": f"bytes {start}-{end}/{total}",
            "Content-Type": "application/octet-stream",
            "User-Agent": "reliable-artifact-publisher/1",
        }
        request = urllib.request.Request(session_url, data=block, method="PUT", headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=UPLOAD_TIMEOUT) as response:
                raw = response.read()
                return response.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            if exc.code == 308:
                range_header = exc.headers.get("Range")
                match = re.search(r"bytes=0-(\d+)", range_header or "")
                return int(match.group(1)) + 1 if match else start + len(block), None
            detail = exc.read().decode("utf-8", errors="replace")[:2000]
            if exc.code in TRANSIENT_HTTP:
                raise OSError(f"Transient HTTP {exc.code}: {detail}") from exc
            raise PublisherError(f"Google Drive upload failed: HTTP {exc.code}: {detail}") from exc

    def get_metadata(self, file_id: str) -> dict[str, Any]:
        fields = urllib.parse.quote("id,name,size,md5Checksum,webViewLink,webContentLink", safe=",")
        _, _, metadata = self.api.request(
            "GET", f"/drive/v3/files/{file_id}?fields={fields}", expected=(200,)
        )
        return dict(metadata)

    def create_permission(self, file_id: str, email: str | None, anyone: bool) -> None:
        if anyone:
            payload = {"type": "anyone", "role": "reader"}
        elif email:
            payload = {"type": "user", "role": "reader", "emailAddress": email}
        else:
            return
        self.api.request(
            "POST", f"/drive/v3/files/{file_id}/permissions?sendNotificationEmail={'true' if email else 'false'}",
            payload, expected=(200,),
        )

    def upload_file(
        self,
        path: Path,
        parent_id: str | None,
        share_email: str | None,
        share_anyone: bool,
        state_dir: Path,
        chunk_size: int = DRIVE_CHUNK,
    ) -> dict[str, Any]:
        if chunk_size % (256 * 1024) != 0:
            raise PublisherError("Google Drive chunk size must be a multiple of 256 KiB")
        local = digest_file(path.resolve())
        state_dir.mkdir(parents=True, exist_ok=True)
        state_path = state_dir / f".{safe_filename(path.name)}.drive-upload.json"
        state = load_json(state_path) if state_path.exists() else {}
        session_url = str(state.get("session_url") or "")
        if state and (
            int(state.get("size", -1)) != local.size
            or str(state.get("sha256", "")) != local.sha256
            or str(state.get("parent_id") or "") != str(parent_id or "")
        ):
            state = {}
            session_url = ""
        if session_url:
            offset, completed = self.query_offset(session_url, local.size)
            if offset == -1:
                session_url = ""
            elif completed:
                metadata = completed
                offset = local.size
        if not session_url:
            session_url = self.start_session(local, parent_id)
            offset = 0
            atomic_json(state_path, {
                "session_url": session_url,
                "name": local.path.name,
                "size": local.size,
                "sha256": local.sha256,
                "parent_id": parent_id,
                "created_utc": utc_now(),
            })

        metadata: dict[str, Any] | None = None
        with local.path.open("rb") as handle:
            handle.seek(offset)
            while offset < local.size:
                block = handle.read(min(chunk_size, local.size - offset))
                if not block:
                    raise PublisherError("Unexpected EOF during Google Drive upload")
                for attempt in range(DRIVE_CHUNK_RETRIES):
                    try:
                        result, metadata = self.upload_chunk(session_url, block, offset, local.size)
                        if result in (200, 201):
                            offset = local.size
                        else:
                            offset = int(result)
                            # A resumable server may acknowledge only part of a
                            # submitted block. Reposition to the exact confirmed
                            # byte rather than assuming the entire block landed.
                            handle.seek(offset)
                        break
                    except OSError:
                        if attempt >= DRIVE_CHUNK_RETRIES - 1:
                            raise
                        time.sleep(retry_delay(attempt))
                        offset, completed = self.query_offset(session_url, local.size)
                        if completed:
                            metadata = completed
                            offset = local.size
                            break
                        handle.seek(offset)
                        block = handle.read(min(chunk_size, local.size - offset))
                eprint(f"Uploading {local.path.name} to Drive: {offset * 100 // local.size}%", end="\r")
        eprint(" " * 100, end="\r")
        if not metadata or not metadata.get("id"):
            _, metadata = self.query_offset(session_url, local.size)
        if not metadata or not metadata.get("id"):
            raise PublisherError("Google Drive upload completed without file metadata")
        remote = self.get_metadata(str(metadata["id"]))
        if int(remote.get("size", -1)) != local.size:
            raise PublisherError(f"Google Drive size verification failed for {local.path.name}")
        remote_md5 = str(remote.get("md5Checksum") or "").lower()
        if remote_md5 and remote_md5 != local.md5:
            raise PublisherError(f"Google Drive MD5 verification failed for {local.path.name}")
        self.create_permission(str(remote["id"]), share_email, share_anyone)
        state_path.unlink(missing_ok=True)
        eprint(f"Google Drive verified: {local.path.name} ({human_bytes(local.size)})")
        return {
            "name": local.path.name,
            "size": local.size,
            "sha256": local.sha256,
            "md5": local.md5,
            "file_id": remote["id"],
            "url": remote.get("webViewLink"),
            "download_url": remote.get("webContentLink"),
            "remote_md5": remote_md5 or None,
        }

    def upload_files(
        self,
        files: Sequence[Path],
        parent_id: str | None,
        share_email: str | None,
        share_anyone: bool,
        state_dir: Path,
        receipt_path: Path,
    ) -> dict[str, Any]:
        assets = [self.upload_file(path, parent_id, share_email, share_anyone, state_dir) for path in files]
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "provider": "google-drive",
            "verified_utc": utc_now(),
            "assets": assets,
        }
        atomic_json(receipt_path, receipt)
        return receipt


def parse_header_env(values: Sequence[str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise PublisherError("--header-env must be HEADER=ENV_VARIABLE")
        header, env_name = value.split("=", 1)
        secret = os.environ.get(env_name)
        if secret is None:
            raise PublisherError(f"Missing environment variable: {env_name}")
        headers[header.strip()] = secret
    return headers


def nested_json_value(data: Any, path: str) -> Any:
    current = data
    for piece in path.split("."):
        if isinstance(current, list):
            current = current[int(piece)]
        elif isinstance(current, dict):
            current = current[piece]
        else:
            raise KeyError(path)
    return current


def verify_download(url: str, expected: FileDigest, headers: Mapping[str, str], deep: bool) -> None:
    request = urllib.request.Request(url, method="HEAD", headers=dict(headers))
    size: int | None = None
    with contextlib.suppress(Exception):
        with urllib.request.urlopen(request, timeout=120) as response:
            if response.headers.get("Content-Length"):
                size = int(response.headers["Content-Length"])
    if size is not None and size != expected.size:
        raise PublisherError(f"Remote size mismatch: {size} != {expected.size}")
    if not deep:
        if size is None:
            raise PublisherError("Remote host did not expose Content-Length; use --deep-verify")
        return
    sha = hashlib.sha256()
    total = 0
    request = urllib.request.Request(url, method="GET", headers=dict(headers))
    with urllib.request.urlopen(request, timeout=180) as response:
        while True:
            block = response.read(IO_CHUNK)
            if not block:
                break
            total += len(block)
            sha.update(block)
    if total != expected.size or sha.hexdigest() != expected.sha256:
        raise PublisherError("Remote deep verification failed")


def http_stream_upload(
    url: str,
    path: Path,
    method: str,
    mode: str,
    field_name: str,
    headers: Mapping[str, str],
    response_json_path: str | None,
    response_regex: str | None,
    deep_verify: bool,
    receipt_path: Path,
) -> dict[str, Any]:
    local = digest_file(path.resolve())
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https":
        raise PublisherError("Generic uploads require HTTPS")
    connection = http.client.HTTPSConnection(parsed.hostname, parsed.port or 443, timeout=180)
    request_path = urllib.parse.urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
    request_headers = {"User-Agent": "reliable-artifact-publisher/1", **headers}
    if mode == "raw":
        preamble = b""
        closing = b""
        request_headers.setdefault("Content-Type", mimetypes.guess_type(local.path.name)[0] or "application/octet-stream")
    else:
        boundary = f"----artifact-{uuid.uuid4().hex}"
        filename = local.path.name.replace('"', "")
        preamble = (
            f"--{boundary}\r\n"
            f"Content-Disposition: form-data; name=\"{field_name}\"; filename=\"{filename}\"\r\n"
            f"Content-Type: {mimetypes.guess_type(filename)[0] or 'application/octet-stream'}\r\n\r\n"
        ).encode("utf-8")
        closing = f"\r\n--{boundary}--\r\n".encode("ascii")
        request_headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    request_headers["Content-Length"] = str(len(preamble) + local.size + len(closing))

    try:
        connection.putrequest(method.upper(), request_path)
        for key, value in request_headers.items():
            connection.putheader(key, value)
        connection.endheaders()
        if preamble:
            connection.send(preamble)
        sent = 0
        with local.path.open("rb") as handle:
            while True:
                block = handle.read(IO_CHUNK)
                if not block:
                    break
                connection.send(block)
                sent += len(block)
                eprint(f"Uploading {local.path.name}: {sent * 100 // local.size}%", end="\r")
        if closing:
            connection.send(closing)
        response = connection.getresponse()
        raw = response.read()
        eprint(" " * 100, end="\r")
        if response.status < 200 or response.status >= 300:
            raise PublisherError(f"Upload failed with HTTP {response.status}: {raw[:2000]!r}")
    finally:
        connection.close()

    text = raw.decode("utf-8", errors="replace").strip()
    upload_url: str | None = None
    if response_json_path:
        try:
            upload_url = str(nested_json_value(json.loads(text), response_json_path))
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise PublisherError(f"Could not extract URL at JSON path {response_json_path}") from exc
    elif response_regex:
        match = re.search(response_regex, text)
        if not match:
            raise PublisherError("Could not extract URL using the response regex")
        upload_url = match.group(1) if match.groups() else match.group(0)
    elif re.fullmatch(r"https://\S+", text):
        upload_url = text
    if not upload_url:
        raise PublisherError("Upload returned no verifiable download URL")
    verification_headers = {
        key: value for key, value in headers.items()
        if key.lower() not in {"content-type", "content-length"}
    }
    verify_download(upload_url, local, headers=verification_headers, deep=deep_verify)
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "provider": "generic-http",
        "verified_utc": utc_now(),
        "name": local.path.name,
        "size": local.size,
        "sha256": local.sha256,
        "url": upload_url,
        "deep_verified": deep_verify,
    }
    atomic_json(receipt_path, receipt)
    return receipt


def print_receipt(receipt: Mapping[str, Any]) -> None:
    print(json.dumps(receipt, indent=2, sort_keys=True))


def resolve_files(args: argparse.Namespace) -> list[Path]:
    if getattr(args, "manifest", None):
        manifest_path = Path(args.manifest).resolve()
        verify_manifest(manifest_path, reassemble=True)
        return manifest_upload_files(manifest_path)
    files = [Path(item).resolve() for item in getattr(args, "file", [])]
    if not files:
        raise PublisherError("Provide --manifest or at least one --file")
    for path in files:
        if not path.is_file():
            raise PublisherError(f"File does not exist: {path}")
    return files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare and publish artifacts with byte-level verification")
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="Archive, hash, split, and generate reassembly helpers")
    prepare.add_argument("source")
    prepare.add_argument("--output-dir", required=True)
    prepare.add_argument("--name")
    prepare.add_argument("--chunk-mib", type=int, default=DEFAULT_CHUNK_MIB)

    verify = sub.add_parser("verify", help="Verify a prepared upload manifest")
    verify.add_argument("manifest")
    verify.add_argument("--reassemble", action="store_true")

    github = sub.add_parser("github-release", help="Upload verified files to a transactional GitHub Release")
    github.add_argument("--repo", required=True, help="OWNER/REPO")
    github.add_argument("--tag", required=True)
    github.add_argument("--title")
    github.add_argument("--body", default="Verified artifact publication")
    github.add_argument("--target")
    github.add_argument("--manifest")
    github.add_argument("--file", action="append", default=[])
    github.add_argument("--create-repo", action="store_true")
    github.add_argument("--public-repo", action="store_true")
    github.add_argument("--keep-draft", action="store_true")
    github.add_argument("--receipt", default="GITHUB-UPLOAD-RECEIPT.json")

    drive = sub.add_parser("drive-upload", help="Resumably upload verified files to Google Drive")
    drive.add_argument("--manifest")
    drive.add_argument("--file", action="append", default=[])
    drive.add_argument("--parent-id")
    drive.add_argument("--share-email")
    drive.add_argument("--share-anyone", action="store_true")
    drive.add_argument("--state-dir", default=".upload-state")
    drive.add_argument("--receipt", default="DRIVE-UPLOAD-RECEIPT.json")

    http = sub.add_parser("http-upload", help="Upload to an authenticated HTTPS endpoint")
    http.add_argument("--url", required=True)
    http.add_argument("--file", required=True)
    http.add_argument("--method", default="POST")
    http.add_argument("--mode", choices=("raw", "multipart"), default="multipart")
    http.add_argument("--field-name", default="file")
    http.add_argument("--header-env", action="append", default=[], help="HEADER=ENV_VARIABLE")
    http.add_argument("--bearer-env")
    http.add_argument("--basic-user-env")
    http.add_argument("--basic-password-env")
    http.add_argument("--cookie-env")
    http.add_argument("--response-json-path")
    http.add_argument("--response-regex")
    http.add_argument("--deep-verify", action="store_true")
    http.add_argument("--receipt", default="HTTP-UPLOAD-RECEIPT.json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            manifest = prepare_artifact(Path(args.source), Path(args.output_dir).resolve(), args.name, args.chunk_mib)
            print(manifest)
        elif args.command == "verify":
            verify_manifest(Path(args.manifest), reassemble=args.reassemble)
        elif args.command == "github-release":
            files = resolve_files(args)
            token = GitHubPublisher.resolve_token()
            publisher = GitHubPublisher(token, args.repo)
            receipt = publisher.upload_release(
                files=files,
                tag=args.tag,
                title=args.title or args.tag,
                body=args.body,
                target=args.target,
                create_repo=args.create_repo,
                private_repo=not args.public_repo,
                keep_draft=args.keep_draft,
                receipt_path=Path(args.receipt).resolve(),
            )
            print_receipt(receipt)
        elif args.command == "drive-upload":
            files = resolve_files(args)
            token = GoogleDrivePublisher.resolve_token()
            publisher = GoogleDrivePublisher(token)
            receipt = publisher.upload_files(
                files=files,
                parent_id=args.parent_id,
                share_email=args.share_email,
                share_anyone=args.share_anyone,
                state_dir=Path(args.state_dir).resolve(),
                receipt_path=Path(args.receipt).resolve(),
            )
            print_receipt(receipt)
        elif args.command == "http-upload":
            headers = parse_header_env(args.header_env)
            if args.bearer_env:
                token = os.environ.get(args.bearer_env)
                if not token:
                    raise PublisherError(f"Missing environment variable: {args.bearer_env}")
                headers["Authorization"] = f"Bearer {token}"
            if args.basic_user_env or args.basic_password_env:
                if not args.basic_user_env or not args.basic_password_env:
                    raise PublisherError("Both --basic-user-env and --basic-password-env are required")
                user = os.environ.get(args.basic_user_env)
                password = os.environ.get(args.basic_password_env)
                if user is None or password is None:
                    raise PublisherError("Missing basic-auth environment variable")
                headers["Authorization"] = "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()
            if args.cookie_env:
                cookie = os.environ.get(args.cookie_env)
                if not cookie:
                    raise PublisherError(f"Missing environment variable: {args.cookie_env}")
                headers["Cookie"] = cookie
            receipt = http_stream_upload(
                url=args.url,
                path=Path(args.file),
                method=args.method,
                mode=args.mode,
                field_name=args.field_name,
                headers=headers,
                response_json_path=args.response_json_path,
                response_regex=args.response_regex,
                deep_verify=args.deep_verify,
                receipt_path=Path(args.receipt).resolve(),
            )
            print_receipt(receipt)
        return 0
    except PublisherError as exc:
        eprint(f"ERROR: {exc}")
        return 2
    except KeyboardInterrupt:
        eprint("ERROR: interrupted")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
