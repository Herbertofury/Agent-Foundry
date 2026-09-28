#!/usr/bin/env python3
"""Audit personal skill packages for the Zero-Loss composition bridge."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys


def skill_dirs(root: Path):
    root = root.resolve()
    if (root / "SKILL.md").is_file():
        yield root
        return
    found: dict[str, Path] = {}
    for marker in root.rglob("SKILL.md"):
        d = marker.parent
        if d.name not in found or len(d.parts) < len(found[d.name].parts):
            found[d.name] = d
    for name in sorted(found):
        yield found[name]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path, help="Skill directory or parent tree containing skills")
    ap.add_argument("--ignore", action="append", default=[], help="Skill directory name to ignore (repeatable)")
    args = ap.parse_args()
    ignore = set(args.ignore)
    failures = []
    checked = 0
    constitution_marker = "UAG_EXECUTION_CONSTITUTION:v0.3.2"
    for d in skill_dirs(args.root):
        if d.name in ignore:
            continue
        checked += 1
        text = (d / "SKILL.md").read_text(encoding="utf-8")
        front = text.split("---", 2)[1] if text.startswith("---") and text.count("---") >= 2 else ""
        if d.name == "zero-loss-chat-accelerator":
            required = ["## Cross-skill continuity", "continuity capsule", "overlay rather than a replacement", "still-applicable domain constraint"]
            missing = [x for x in required if x not in text]
        else:
            required_body = ["## Zero-Loss composition", "zero-loss-chat-accelerator", "exact next action"]
            missing = [x for x in required_body if x.lower() not in text.lower()]
            if "zero-loss-chat-accelerator" not in front:
                missing.append("frontmatter composition sentence")
        if constitution_marker not in text:
            missing.append("shared execution constitution marker")
        if missing:
            failures.append((d.name, missing))
        else:
            print(f"PASS {d.name}")
    if checked == 0:
        print("FAIL no skills found", file=sys.stderr)
        return 2
    if failures:
        for name, missing in failures:
            print(f"FAIL {name}: missing {', '.join(missing)}", file=sys.stderr)
        return 1
    print(f"PASS all {checked} audited skills")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
