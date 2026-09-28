#!/usr/bin/env python3
"""Fail-fast static audit for orchestration latency regressions."""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

MAX_SKILL_BYTES = 14_000
LEGACY_PRELOAD_MARKERS = (
    "Read `references/CORE.md`, `references/LEARNING.md`, and `references/PITFALLS.md` in full",
    "Open and read `.agents/LEARNING.md`, `.agents/PITFALLS.md`, and every matching module in full",
)


def read_yaml_implicit(text: str) -> bool | None:
    m = re.search(r"(?m)^\s*allow_implicit_invocation:\s*(true|false)\s*$", text)
    return None if not m else m.group(1) == "true"


def audit(root: Path) -> tuple[dict, list[str]]:
    skill = (root / "SKILL.md").read_text(encoding="utf-8")
    policy = json.loads((root / "policies" / "policy-catalog.json").read_text(encoding="utf-8"))
    root_doc = policy["documents"]["root"]
    memory = policy["documents"]["modules"]["MEMORY-CONTINUITY"]
    execution = policy["documents"]["modules"]["EXECUTION"]
    yaml_text = (root / "agents" / "openai.yaml").read_text(encoding="utf-8")
    errors: list[str] = []

    skill_bytes = len(skill.encode("utf-8"))
    if skill_bytes > MAX_SKILL_BYTES:
        errors.append(f"SKILL.md is {skill_bytes} bytes; limit is {MAX_SKILL_BYTES}")
    for marker in LEGACY_PRELOAD_MARKERS:
        if marker in skill or marker in root_doc:
            errors.append(f"legacy mandatory-preload marker remains: {marker}")
    required = {
        "Maximum Improvement Rule in skill": "Maximum Improvement Rule" in skill,
        "JIT module loading in root": "# JUST-IN-TIME RULE-MODULE LOADING" in root_doc,
        "delta watermark continuity": "delta watermark" in memory.lower(),
        "incremental continuity": "Incremental cross-chat delta sweep" in memory,
        "maximal improvement execution": "Maximum Improvement Rule" in execution,
        "build-first session invariant": ("Build-first session invariant" in skill and "Build-first session invariant" in execution),
        "status docs stay secondary": ("status" in skill.lower() and "runnable artifact" in skill.lower()),
        "no duplicate sweep rule": ("duplicate" in skill.lower() and "sweep" in skill.lower()),
    }
    for name, ok in required.items():
        if not ok:
            errors.append(f"missing performance contract: {name}")

    skill_name = root.name
    implicit = read_yaml_implicit(yaml_text)
    expected = True if skill_name == "project-compass-orchestrator" else False if skill_name == "agents-workflow-enforcer" else implicit
    if implicit is None:
        errors.append("agents/openai.yaml missing allow_implicit_invocation")
    elif implicit != expected:
        errors.append(f"implicit invocation is {implicit}; expected {expected} for {skill_name}")

    module_bytes = sum(len(v.encode("utf-8")) for v in policy["documents"]["modules"].values())
    report = {
        "skill": skill_name,
        "version": (root / "VERSION").read_text(encoding="utf-8").strip(),
        "skill_bytes": skill_bytes,
        "modular_root_bytes": len(root_doc.encode("utf-8")),
        "all_static_module_bytes": module_bytes,
        "mandatory_reference_preload_bytes": 0 if not any(m in skill or m in root_doc for m in LEGACY_PRELOAD_MARKERS) else module_bytes,
        "implicit_invocation": implicit,
        "jit_loading": "# JUST-IN-TIME RULE-MODULE LOADING" in root_doc,
        "delta_continuity": "delta watermark" in memory.lower(),
        "errors": errors,
    }
    return report, errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill-root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    report, errors = audit(args.skill_root.resolve())
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for k, v in report.items():
            if k != "errors":
                print(f"{k}: {v}")
        if errors:
            print("Performance audit failed:", file=sys.stderr)
            for e in errors:
                print(f"- {e}", file=sys.stderr)
    return 1 if errors else 0

if __name__ == "__main__":
    raise SystemExit(main())
