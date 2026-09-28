#!/usr/bin/env python3
"""Audit GitHub Actions references without requiring GitHub Dependency Graph."""
from __future__ import annotations
import re
from pathlib import Path

USES_RE = re.compile(r"^\s*-?\s*uses:\s*([^#\s]+)", re.M)
UNSAFE_REFS = {"main", "master", "head", "latest", "develop", "dev", "trunk"}

def main() -> int:
    errors = []
    refs = []
    for wf in sorted(Path(".github/workflows").glob("*.y*ml")):
        text = wf.read_text(encoding="utf-8")
        for match in USES_RE.finditer(text):
            spec = match.group(1).strip().strip('"\'')
            if spec.startswith("./"):
                continue
            if "@" not in spec:
                errors.append(f"{wf}: action reference has no ref: {spec}")
                continue
            action, ref = spec.rsplit("@", 1)
            refs.append((action, ref))
            if ref.lower() in UNSAFE_REFS:
                errors.append(f"{wf}: floating action ref forbidden: {spec}")
    if errors:
        for e in errors:
            print("FAIL", e)
        return 1
    print(f"PASS workflow action refs: {len(refs)} external uses, no forbidden floating branches")
    for action, ref in refs:
        print(f"  {action}@{ref}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
