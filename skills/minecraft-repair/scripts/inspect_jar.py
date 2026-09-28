#!/usr/bin/env python3
"""Inspect a Minecraft mod JAR without executing it."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from collections import Counter
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def class_major(data: bytes):
    if len(data) >= 8 and data[:4] == b"\xca\xfe\xba\xbe":
        return int.from_bytes(data[6:8], "big")
    return None


def safe_text(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def extract_forge_mods_toml(text: str) -> dict:
    result: dict[str, object] = {}
    mods = []
    for block in re.split(r"(?=\[\[mods\]\])", text):
        if "[[mods]]" not in block:
            continue
        item = {}
        for key in ("modId", "version", "displayName", "displayURL"):
            m = re.search(rf'^\s*{re.escape(key)}\s*=\s*["\']([^"\']+)["\']', block, re.M)
            if m:
                item[key] = m.group(1)
        if item:
            mods.append(item)
    deps = []
    dep_re = re.compile(r"\[\[dependencies\.([^\]]+)\]\]([\s\S]*?)(?=\[\[dependencies\.|\[\[mods\]\]|\Z)")
    for owner, block in dep_re.findall(text):
        item = {"owner": owner}
        for key in ("modId", "mandatory", "versionRange", "ordering", "side"):
            m = re.search(rf'^\s*{re.escape(key)}\s*=\s*(?:["\']([^"\']+)["\']|([^\s#]+))', block, re.M)
            if m:
                item[key] = (m.group(1) or m.group(2)).strip()
        deps.append(item)
    result["mods"] = mods
    result["dependencies"] = deps
    return result


def inspect(path: Path, search_terms: list[str]) -> dict:
    result = {
        "path": str(path),
        "sha256": sha256_file(path),
        "size": path.stat().st_size,
        "valid_zip": False,
        "entry_count": 0,
        "class_count": 0,
        "class_major_versions": {},
        "metadata": {},
        "signature_files": [],
        "search_hits": {},
    }
    with zipfile.ZipFile(path, "r") as zf:
        bad = zf.testzip()
        result["valid_zip"] = bad is None
        result["first_bad_entry"] = bad
        infos = zf.infolist()
        result["entry_count"] = len(infos)
        class_versions = Counter()
        search_hits = {term: [] for term in search_terms}
        for info in infos:
            name = info.filename
            upper = name.upper()
            if upper.startswith("META-INF/") and upper.endswith((".SF", ".RSA", ".DSA", ".EC")):
                result["signature_files"].append(name)
            data = zf.read(info)
            if name.endswith(".class"):
                result["class_count"] += 1
                major = class_major(data)
                if major is not None:
                    class_versions[major] += 1
            for term in search_terms:
                raw = term.encode("utf-8")
                count = data.count(raw)
                if count:
                    search_hits[term].append({"entry": name, "count": count})
        result["class_major_versions"] = {str(k): v for k, v in sorted(class_versions.items())}
        result["search_hits"] = search_hits
        for candidate in ("META-INF/mods.toml", "META-INF/neoforge.mods.toml"):
            if candidate in zf.namelist():
                text = safe_text(zf.read(candidate))
                result["metadata"][candidate] = {
                    "parsed": extract_forge_mods_toml(text),
                    "text": text,
                }
        for candidate in ("fabric.mod.json", "quilt.mod.json"):
            if candidate in zf.namelist():
                text = safe_text(zf.read(candidate))
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    parsed = None
                result["metadata"][candidate] = {"parsed": parsed, "text": text}
        if "META-INF/MANIFEST.MF" in zf.namelist():
            result["metadata"]["META-INF/MANIFEST.MF"] = safe_text(zf.read("META-INF/MANIFEST.MF"))
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("jar", type=Path)
    ap.add_argument("--search", action="append", default=[])
    ap.add_argument("--pretty", action="store_true")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    data = inspect(args.jar, args.search)
    out = json.dumps(data, indent=2 if args.pretty else None, ensure_ascii=False)
    if args.output:
        args.output.write_text(out + "\n", encoding="utf-8")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
