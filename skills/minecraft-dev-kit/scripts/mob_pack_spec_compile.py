#!/usr/bin/env python3
"""Compile optional creature specs referenced by a premium mob-pack manifest."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from creature_spec_compiler import compile_animations, compile_events, compile_geometry, validate_spec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--markdown", type=Path)
    ap.add_argument("--json", dest="json_out", type=Path)
    args = ap.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    root = args.root
    args.out.mkdir(parents=True, exist_ok=True)
    rows = []
    failures = 0
    seen = 0
    for entity in manifest.get("entities", []):
        ref = entity.get("creature_spec")
        if not ref:
            continue
        seen += 1
        spec_path = root / ref
        row = {"entity": entity.get("id"), "spec": str(ref), "result": "fail", "issues": []}
        if not spec_path.is_file():
            row["issues"] = [{"level": "error", "code": "missing", "message": "creature spec file missing"}]
            failures += 1
            rows.append(row)
            continue
        try:
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
        except Exception as exc:
            row["issues"] = [{"level": "error", "code": "parse", "message": str(exc)}]
            failures += 1
            rows.append(row)
            continue
        issues = validate_spec(spec) if isinstance(spec, dict) else []
        if not isinstance(spec, dict):
            issues = []
            row["issues"] = [{"level": "error", "code": "root", "message": "spec root must be object"}]
            failures += 1
            rows.append(row)
            continue
        row["issues"] = [i.__dict__ for i in issues]
        if any(i.level == "error" for i in issues):
            failures += 1
            rows.append(row)
            continue
        eid = entity.get("id") or spec.get("id") or f"entity_{seen}"
        geo = args.out / f"{eid}.geo.json"
        anim = args.out / f"{eid}.animation.json"
        events = args.out / f"{eid}.events.json"
        geo.write_text(json.dumps(compile_geometry(spec), indent=2) + "\n", encoding="utf-8")
        anim.write_text(json.dumps(compile_animations(spec), indent=2) + "\n", encoding="utf-8")
        events.write_text(json.dumps(compile_events(spec), indent=2) + "\n", encoding="utf-8")
        row.update({"result": "pass", "geo": str(geo), "animation": str(anim), "events": str(events)})
        rows.append(row)

    result = {"result": "fail" if failures else "pass", "specs": seen, "failures": failures, "entities": rows,
              "note": "Compiled outputs are deterministic structural/runtime QA artifacts; artist masters and native runtime proof remain authoritative for final quality."}
    lines = ["# Creature Spec Pack Compile", "", f"- Result: **{result['result'].upper()}**", f"- Specs found: {seen}", f"- Failures: {failures}", ""]
    if seen == 0:
        lines.append("No creature specs declared; this optional authoring lane was skipped.")
    else:
        lines += ["## Entities", ""]
        for row in rows:
            lines.append(f"- `{row['entity']}`: **{row['result'].upper()}** - `{row['spec']}`")
            for issue in row.get("issues", []):
                lines.append(f"  - {issue['level'].upper()} `{issue['code']}`: {issue['message']}")
    md = "\n".join(lines) + "\n"
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(md, encoding="utf-8")
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(md, end="")
    return 2 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
