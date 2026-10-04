#!/usr/bin/env python3
"""Generate or verify a deterministic manifest for mirrored Agent Foundry Skill sources."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "evidence"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}
MANIFEST = "SOURCE_MANIFEST.json"


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def skill_record(skill: Path) -> dict:
    files = []
    tree = hashlib.sha256()
    total = 0
    for path in sorted((p for p in skill.rglob("*") if p.is_file()),
                       key=lambda p: p.relative_to(skill).as_posix()):
        rel = path.relative_to(skill)
        if any(part in EXCLUDED_PARTS for part in rel.parts) or path.suffix in EXCLUDED_SUFFIXES:
            continue
        data = path.read_bytes()
        sha = digest_bytes(data)
        rels = rel.as_posix()
        total += len(data)
        files.append({"path": rels, "sha256": sha, "sizeBytes": len(data)})
        tree.update(rels.encode("utf-8"))
        tree.update(b"\0")
        tree.update(sha.encode("ascii"))
        tree.update(b"\n")
    return {
        "fileCount": len(files),
        "sizeBytes": total,
        "treeDigest": tree.hexdigest(),
        "files": files,
    }


def build(root: Path) -> dict:
    skills = {}
    for skill in sorted(p for p in root.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()):
        skills[skill.name] = skill_record(skill)
    return {
        "schemaVersion": 1,
        "sourceRoot": root.as_posix(),
        "skillCount": len(skills),
        "fileCount": sum(v["fileCount"] for v in skills.values()),
        "sizeBytes": sum(v["sizeBytes"] for v in skills.values()),
        "skills": skills,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("skills"))
    ap.add_argument("--manifest", type=Path, default=Path(MANIFEST))
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = ap.parse_args()

    data = build(args.root)
    rendered = json.dumps(data, indent=2, sort_keys=True) + "\n"
    if args.write:
        args.manifest.write_text(rendered, encoding="utf-8", newline="\n")
        print(f"WROTE {args.manifest}: {data['skillCount']} skills, {data['fileCount']} files, {data['sizeBytes']} bytes")
        return 0

    if not args.manifest.is_file():
        print(f"FAIL missing manifest: {args.manifest}")
        return 1
    current = args.manifest.read_text(encoding="utf-8")
    if current != rendered:
        print(f"FAIL stale source manifest: {args.manifest}")
        return 1
    print(f"PASS source manifest: {data['skillCount']} skills, {data['fileCount']} files, {data['sizeBytes']} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
