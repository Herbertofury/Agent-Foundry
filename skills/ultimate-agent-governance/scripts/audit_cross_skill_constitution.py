#!/usr/bin/env python3
"""Audit skill entrypoints for the shared execution-constitution bridge."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys

MARKER = "<!-- UAG_EXECUTION_CONSTITUTION:v0.3.5 -->"
BOOTSTRAP = "<!-- UAG_BOOTSTRAP:v0.3.5 -->"
GOVERNANCE_URI = "skills://ultimate-agent-governance/skill.md"
REQUIRED = [
    "No blocker closeout",
    "Unknown is not absent",
    "Never suffer the same failure twice",
    "No fake or partial success",
    "Performance is an always-on zero-loss ratchet",
    "Modernize and fix forward",
    "Challenge before reinventing",
    "Real proof beats structural proof",
    "Continuity is mandatory",
    "Remote durability is part of completion",
    "Completeness must be proven",
]


def skill_files(root: Path):
    root = root.resolve()
    if root.is_file() and root.name.lower() == "skill.md":
        yield root
        return
    if (root / "SKILL.md").is_file():
        yield root / "SKILL.md"
        return
    for p in sorted(root.rglob("SKILL.md")):
        # Installed/plugin-managed templates can be excluded by caller; never infer success from absence.
        yield p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path, help="Skill directory, SKILL.md, or parent tree")
    ap.add_argument("--ignore", action="append", default=[], help="Skill directory name to ignore (repeatable)")
    args = ap.parse_args()
    ignore = set(args.ignore)
    checked = 0
    failures: list[tuple[str, list[str]]] = []
    for p in skill_files(args.root):
        name = p.parent.name
        if name in ignore:
            continue
        checked += 1
        text = p.read_text(encoding="utf-8")
        missing = []
        if MARKER not in text:
            missing.append(MARKER)
        if BOOTSTRAP not in text:
            missing.append(BOOTSTRAP)
        if name != "ultimate-agent-governance" and GOVERNANCE_URI not in text:
            missing.append(GOVERNANCE_URI)
        for token in REQUIRED:
            if token.lower() not in text.lower():
                missing.append(token)
        if missing:
            failures.append((name, missing))
            print(f"FAIL {name}: missing {', '.join(missing)}", file=sys.stderr)
        else:
            print(f"PASS {name}")
    if checked == 0:
        print("FAIL no SKILL.md files found", file=sys.stderr)
        return 2
    if failures:
        print(f"FAIL {len(failures)} of {checked} skills missing shared execution constitution", file=sys.stderr)
        return 1
    print(f"PASS all {checked} audited skills carry bootstrap + {MARKER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
