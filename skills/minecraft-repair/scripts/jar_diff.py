#!/usr/bin/env python3
"""Compare JAR/ZIP entry contents and metadata at a useful repair level."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def index_jar(path: Path) -> dict:
    with zipfile.ZipFile(path, "r") as zf:
        out = {}
        for info in zf.infolist():
            out[info.filename] = {
                "sha256": digest(zf.read(info)),
                "size": info.file_size,
                "compress_type": info.compress_type,
                "external_attr": info.external_attr,
                "date_time": info.date_time,
            }
        return out


def compare(a: Path, b: Path) -> dict:
    ia, ib = index_jar(a), index_jar(b)
    a_names, b_names = set(ia), set(ib)
    added = sorted(b_names - a_names)
    removed = sorted(a_names - b_names)
    changed = []
    metadata_only = []
    for name in sorted(a_names & b_names):
        if ia[name]["sha256"] != ib[name]["sha256"]:
            changed.append({"entry": name, "before": ia[name], "after": ib[name]})
        elif ia[name] != ib[name]:
            metadata_only.append({"entry": name, "before": ia[name], "after": ib[name]})
    return {
        "a": str(a),
        "b": str(b),
        "added": added,
        "removed": removed,
        "content_changed": changed,
        "metadata_only_changed": metadata_only,
        "unchanged_content_count": len(a_names & b_names) - len(changed),
        "same_entry_set": not added and not removed,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("a", type=Path)
    ap.add_argument("b", type=Path)
    ap.add_argument("--pretty", action="store_true")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    data = compare(args.a, args.b)
    out = json.dumps(data, indent=2 if args.pretty else None, ensure_ascii=False)
    if args.output:
        args.output.write_text(out + "\n", encoding="utf-8")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
