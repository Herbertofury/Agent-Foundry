#!/usr/bin/env python3
"""Measure Minecraft creature model complexity against manifest budgets."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def as_list(v: Any) -> list[Any]:
    return v if isinstance(v, list) else []


def as_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def count_bbmodel(data: dict[str, Any]) -> tuple[int, int, int]:
    cubes = len([e for e in as_list(data.get("elements")) if isinstance(e, dict)])
    groups = data.get("groups")
    if isinstance(groups, list):
        bones = len([g for g in groups if isinstance(g, dict)])
    else:
        bones = 0
        outliner = as_list(data.get("outliner"))
        stack = list(outliner)
        while stack:
            item = stack.pop()
            if isinstance(item, dict):
                bones += 1
                stack.extend(as_list(item.get("children")))
    animations = data.get("animations")
    anim_count = len(animations) if isinstance(animations, (list, dict)) else 0
    return bones, cubes, anim_count


def count_gecko(data: dict[str, Any]) -> tuple[int, int, int]:
    geos = data.get("minecraft:geometry")
    if not isinstance(geos, list):
        return 0, 0, 0
    bones = 0
    cubes = 0
    for geo in geos:
        if not isinstance(geo, dict):
            continue
        for bone in as_list(geo.get("bones")):
            if isinstance(bone, dict):
                bones += 1
                cubes += len([c for c in as_list(bone.get("cubes")) if isinstance(c, dict)])
    return bones, cubes, 0


def inspect(path: Path) -> tuple[int, int, int, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return 0, 0, 0, "unreadable"
    if "minecraft:geometry" in data:
        b, c, a = count_gecko(data)
        return b, c, a, "gecko-geo"
    b, c, a = count_bbmodel(data)
    return b, c, a, "bbmodel-like"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--markdown", type=Path)
    ap.add_argument("--json", type=Path, dest="json_out")
    args = ap.parse_args()
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    root = args.root.resolve()
    rows: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []

    for ent in as_list(data.get("entities")):
        if not isinstance(ent, dict):
            continue
        eid = str(ent.get("id", "<entity>"))
        ref = ent.get("model_file")
        perf = ent.get("performance") if isinstance(ent.get("performance"), dict) else {}
        bone_budget = as_int(perf.get("bone_budget"))
        cube_budget = as_int(perf.get("cube_budget"))
        if not ref:
            findings.append({"level": "error", "entity": eid, "code": "model.missing", "message": "No model_file"})
            continue
        p = Path(str(ref))
        p = p if p.is_absolute() else root / p
        if not p.is_file():
            findings.append({"level": "error", "entity": eid, "code": "model.not_found", "message": str(ref)})
            continue
        bones, cubes, anims, fmt = inspect(p)
        if fmt == "unreadable":
            findings.append({"level": "error", "entity": eid, "code": "model.unreadable", "message": str(ref)})
        if bone_budget and bones > bone_budget:
            findings.append({"level": "error", "entity": eid, "code": "budget.bones", "message": f"{bones} bones exceeds budget {bone_budget}"})
        if cube_budget and cubes > cube_budget:
            findings.append({"level": "error", "entity": eid, "code": "budget.cubes", "message": f"{cubes} cubes exceeds budget {cube_budget}"})
        rows.append({"entity": eid, "format": fmt, "bones": bones, "bone_budget": bone_budget, "cubes": cubes, "cube_budget": cube_budget, "asset_animations": anims})

    errors = [f for f in findings if f["level"] == "error"]
    lines = [
        "# Mob Model Complexity Audit",
        "",
        f"- Result: **{'PASS' if not errors else 'FAIL'}**",
        f"- Models inspected: **{len(rows)}**",
        "",
        "|Entity|Format|Bones|Budget|Cubes|Budget|Asset animations|",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        lines.append(f"|{r['entity']}|{r['format']}|{r['bones']}|{r['bone_budget'] or '-'}|{r['cubes']}|{r['cube_budget'] or '-'}|{r['asset_animations']}|")
    lines += ["", "## Findings", ""]
    if not findings:
        lines.append("- None.")
    else:
        for f in findings:
            lines.append(f"- **{f['level'].upper()}** `{f['code']}` [{f['entity']}]: {f['message']}")
    lines += ["", "Model budgets are design constraints, not universal quality scores. A budget should only be tightened when the visual/gameplay result survives.", ""]
    report = "\n".join(lines)
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(report, encoding="utf-8")
    else:
        sys.stdout.write(report)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps({"result": "pass" if not errors else "fail", "rows": rows, "findings": findings}, indent=2) + "\n", encoding="utf-8")
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
