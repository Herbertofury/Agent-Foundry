#!/usr/bin/env python3
"""Create a SHA-256 manifest and deterministic ZIP for a visual QA showcase."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import zipfile


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("showcase", type=Path)
    ap.add_argument("--zip", dest="zip_path", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    args = ap.parse_args()

    root = args.showcase.resolve()
    if not root.is_dir():
        ap.error(f"showcase directory does not exist: {root}")

    zip_path = args.zip_path.resolve()
    manifest = args.manifest.resolve()
    excluded = {zip_path, manifest}

    files = sorted(
        (p for p in root.rglob("*") if p.is_file() and p.resolve() not in excluded),
        key=lambda p: p.relative_to(root).as_posix(),
    )

    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        "".join(f"{sha256(p)}  {p.relative_to(root).as_posix()}\n" for p in files),
        encoding="utf-8",
    )

    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in files:
            rel = p.relative_to(root).as_posix()
            info = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o644 & 0xFFFF) << 16
            zf.writestr(info, p.read_bytes())

    print(f"files: {len(files)}")
    print(f"manifest: {manifest}")
    print(f"zip: {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
