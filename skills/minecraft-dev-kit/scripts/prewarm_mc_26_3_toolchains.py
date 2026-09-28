#!/usr/bin/env python3
"""Download and checksum-verify the Minecraft 26.3 Java/Gradle toolchain cache on a networked machine."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / "references" / "minecraft-26.3-toolchain-lock.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path) -> None:
    part = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "Minecraft-Dev-Kit/26.3-toolchain-prewarm"})
    with urllib.request.urlopen(req, timeout=120) as resp, part.open("wb") as out:
        shutil.copyfileobj(resp, out, length=1024 * 1024)
    part.replace(dest)


def remote_checksum(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Minecraft-Dev-Kit/26.3-toolchain-prewarm"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        text = resp.read(4096).decode("utf-8", errors="replace")
    token = text.strip().split()[0].lower()
    if len(token) != 64 or any(c not in "0123456789abcdef" for c in token):
        raise RuntimeError(f"invalid SHA-256 response from {url}: {text[:200]!r}")
    return token


def ensure(url: str, dest: Path, expected: str | None = None, checksum_url: str | None = None) -> dict:
    if expected is None and checksum_url:
        expected = remote_checksum(checksum_url)
    if dest.exists() and expected and sha256(dest) == expected:
        return {"path": str(dest), "sha256": expected, "status": "reused"}
    download(url, dest)
    actual = sha256(dest)
    if expected and actual != expected:
        dest.unlink(missing_ok=True)
        raise RuntimeError(f"checksum mismatch for {url}: expected {expected}, got {actual}")
    return {"path": str(dest), "sha256": actual, "status": "downloaded"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("output", type=Path)
    ap.add_argument("--platform", choices=["linux", "windows", "both"], default="both")
    ap.add_argument("--skip-gradle", action="store_true")
    args = ap.parse_args()
    cfg = json.loads(LOCK.read_text(encoding="utf-8"))
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    results = []

    platforms = ["linux", "windows"] if args.platform == "both" else [args.platform]
    for platform in platforms:
        entry = cfg["java"][f"{platform}_x64"]
        filename = Path(entry["url"]).name
        results.append(ensure(entry["url"], out / filename, checksum_url=entry["checksum_url"]))

    if not args.skip_gradle:
        for loader in ("fabric", "neoforge"):
            entry = cfg["gradle"][loader]
            results.append(ensure(entry["url"], out / Path(entry["url"]).name, expected=entry.get("sha256"), checksum_url=entry.get("checksum_url")))

    manifest = {"schema_version": 1, "lock_snapshot": cfg["snapshot_date"], "artifacts": results}
    (out / "MC-26.3-TOOLCHAIN-CACHE-MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
