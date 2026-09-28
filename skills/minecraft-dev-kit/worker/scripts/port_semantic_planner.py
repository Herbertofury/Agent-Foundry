#!/usr/bin/env python3
"""Generate an evidence-backed semantic migration plan for a Minecraft mod -> 26.3.

This complements name mappings: it identifies API/data/runtime concepts that changed meaning or
ownership and records the required target-native adaptation plus the QA lane that proves parity.
It never rewrites behavior merely because a regex matched.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from port_26_3_common import Bundle, collect_text, input_identity, md_escape, write_json
from port_intake import inspect

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "references" / "minecraft-26.3-semantic-migrations.json"


def load_catalog() -> dict:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def _scan_rule(rule: dict, names: list[str], text_files: dict[str, str]) -> list[dict]:
    evidence = []
    pattern = rule["pattern"]
    kind = rule["kind"]
    if kind == "path_regex":
        rx = re.compile(pattern, re.IGNORECASE)
        for name in names:
            if rx.search(name):
                evidence.append({"path": name})
                if len(evidence) >= 50:
                    break
    elif kind == "content_regex":
        rx = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        for name, text in text_files.items():
            for m in rx.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                context = text[max(0, m.start() - 100):min(len(text), m.end() + 180)].replace("\n", " ").strip()
                evidence.append({"path": name, "line": line, "match": m.group(0)[:180], "context": context[:360]})
                if len(evidence) >= 50:
                    break
            if len(evidence) >= 50:
                break
    return evidence


def plan(path: Path, target_loader: str) -> dict:
    bundle = Bundle(path)
    try:
        names = bundle.names()
        texts = collect_text(bundle, names)
    finally:
        bundle.close()
    intake = inspect(path, target_loader)
    catalog = load_catalog()
    tasks = []
    for rule in catalog.get("rules", []):
        loader = rule.get("loader", "any")
        if loader not in {"any", target_loader}:
            continue
        evidence = _scan_rule(rule, names, texts)
        if not evidence:
            continue
        qa = list(rule.get("qa") or [])
        category = rule.get("category", "other")
        automation = rule.get("automation", "semantic")
        tasks.append({
            "id": rule["id"],
            "category": category,
            "severity": rule.get("severity", "high"),
            "loader": loader,
            "replacement": rule["replacement"],
            "automation": automation,
            "qa": qa,
            "evidence": evidence,
            "status": "OPEN",
            "acceptance": [
                "source behavior/content represented in target-native 26.3 implementation",
                "no unexplained source inventory loss",
                *(f"pass {x}" for x in qa),
            ],
        })

    # Always include cross-cutting work when the intake proves these surfaces exist.
    inv = intake.get("inventory") or {}
    mix = intake.get("mixin_audit") or {}
    if (inv.get("mixins") or mix.get("source_mixin_surfaces") or mix.get("compiled_mixin_surfaces")):
        tasks.append({
            "id": "exact-mixin-target-resolution",
            "category": "mixin",
            "severity": "blocker",
            "loader": target_loader,
            "replacement": "Resolve every retained Mixin against exact 26.3 target class owner/member/JVM descriptor and then prove PREPARE/APPLY in the real runtime.",
            "automation": "target-class-index",
            "qa": ["target-symbol-index", "mixin-prepare-apply", "native-runtime"],
            "evidence": [{"path": x.get("path")} for x in (mix.get("source_mixin_surfaces") or [])[:50]],
            "status": "OPEN",
            "acceptance": ["all target owners exist", "all member selectors resolve unambiguously", "Mixin PREPARE/APPLY succeeds", "affected behavior works at runtime"],
        })
    if (inv.get("access_wideners") or inv.get("access_transformers")):
        tasks.append({
            "id": "exact-access-rule-resolution",
            "category": "access",
            "severity": "blocker",
            "loader": target_loader,
            "replacement": "Resolve every access rule to official 26.3 owner/member/descriptor; remove only when target-native public API truly supersedes it.",
            "automation": "target-class-index",
            "qa": ["target-symbol-index", "build", "native-runtime"],
            "evidence": [{"path": x} for x in (inv.get("access_wideners") or inv.get("access_transformers") or [])[:50]],
            "status": "OPEN",
            "acceptance": ["every access target exists", "no stale historical namespace", "runtime path exercised"],
        })
    reflection_count = sum(len(x.get("reflection") or []) for x in mix.get("source_mixin_surfaces") or [])
    if reflection_count:
        tasks.append({
            "id": "reflection-methodhandle-resolution",
            "category": "linkage",
            "severity": "blocker",
            "loader": target_loader,
            "replacement": "Resolve reflection/MethodHandle strings against the exact target symbol index or replace them with stable public APIs; ordinary remapping cannot fix string literals.",
            "automation": "target-class-index",
            "qa": ["target-symbol-index", "packaged-linkage", "native-runtime"],
            "evidence": [{"reflection_surface_count": reflection_count}],
            "status": "OPEN",
            "acceptance": ["all required runtime lookups resolve", "packaged candidate exercises reflective path"],
        })

    # Stable priority ordering: blocker first, then category and id.
    sev = {"blocker": 0, "high": 1, "medium": 2, "info": 3}
    tasks.sort(key=lambda x: (sev.get(x["severity"], 9), x["category"], x["id"]))
    groups = defaultdict(list)
    for task in tasks:
        groups[task["category"]].append(task["id"])
    return {
        "schema_version": 1,
        "input": input_identity(path),
        "target": {"minecraft": "26.3", "loader": target_loader, "java": 25, "namespace": "official"},
        "source": {
            "minecraft": intake.get("source_minecraft_version"),
            "detected_loaders": intake.get("detected", {}).get("loaders") or [],
            "mapping_plan": intake.get("mapping_plan"),
        },
        "task_count": len(tasks),
        "counts": {
            "severity": dict(Counter(x["severity"] for x in tasks)),
            "category": dict(Counter(x["category"] for x in tasks)),
        },
        "groups": dict(sorted(groups.items())),
        "tasks": tasks,
        "execution_rule": "Resolve exact names/owners/descriptors first, then semantic API/data changes, then build, then strongest applicable runtime proof. A compile fix is not accepted if source behavior/content is lost.",
    }


def render_md(result: dict) -> str:
    lines = [
        "# Minecraft 26.3 Semantic Port Plan", "",
        f"Input: `{result['input']['path']}`", f"Target: `26.3 / {result['target']['loader']} / Java 25 / official names`", "",
        f"Open migration tasks: **{result['task_count']}**", "",
    ]
    by_cat = defaultdict(list)
    for task in result["tasks"]:
        by_cat[task["category"]].append(task)
    for cat in sorted(by_cat):
        lines += [f"## {cat}", ""]
        for task in by_cat[cat]:
            lines.append(f"- **{task['id']}** [{task['severity']}] — {task['replacement']}")
            lines.append(f"  - automation: `{task['automation']}`; QA: `{', '.join(task['qa']) or 'project-specific'}`")
            for ev in task["evidence"][:6]:
                if ev.get("path"):
                    loc = ev["path"] + (f":{ev['line']}" if ev.get("line") else "")
                    lines.append(f"  - evidence: `{md_escape(loc)}`" + (f" — `{md_escape(ev.get('match'))}`" if ev.get("match") else ""))
        lines.append("")
    lines += ["## Acceptance rule", "", result["execution_rule"], ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("--loader", required=True, choices=["fabric", "neoforge"])
    ap.add_argument("--json-out", type=Path)
    ap.add_argument("--md-out", type=Path)
    args = ap.parse_args()
    result = plan(args.input, args.loader)
    if args.json_out:
        write_json(args.json_out, result)
    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        args.md_out.write_text(render_md(result), encoding="utf-8")
    if not args.json_out and not args.md_out:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
