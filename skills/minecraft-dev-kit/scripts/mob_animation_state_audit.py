#!/usr/bin/env python3
"""Audit declared mob animation state coverage and cross-check source model files."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def as_list(v: Any) -> list[Any]:
    return v if isinstance(v, list) else []


def asset_animation_names(path: Path) -> set[str]:
    try:
        data = load(path)
    except Exception:
        return set()
    anims = data.get("animations")
    if isinstance(anims, list):
        return {str(a.get("name")) for a in anims if isinstance(a, dict) and a.get("name")}
    if isinstance(anims, dict):
        return {str(k) for k in anims.keys()}
    return set()


def has(names: list[str], terms: list[str]) -> bool:
    low = [x.lower() for x in names]
    return any(any(t in name for t in terms) for name in low)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--root", type=Path, default=None)
    ap.add_argument("--markdown", type=Path)
    ap.add_argument("--json", type=Path, dest="json_out")
    args = ap.parse_args()

    data = load(args.manifest)
    root = args.root.resolve() if args.root else None
    findings: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    required_common = {
        "idle": ["idle"],
        "locomotion": ["walk", "run", "fly", "swim", "crawl", "slither", "hover"],
        "hurt": ["hurt", "flinch", "stagger", "hit"],
        "death": ["death", "die"],
    }

    for ent in as_list(data.get("entities")):
        if not isinstance(ent, dict):
            continue
        eid = str(ent.get("id", "<entity>"))
        kind = str(ent.get("kind", "mob")).lower()
        declared = [str(x) for x in as_list(ent.get("animations"))]
        asset_names: set[str] = set()
        model_ref = ent.get("model_file")
        anim_ref = ent.get("animation_file")
        for ref in (anim_ref, model_ref):
            if root and ref:
                p = Path(str(ref))
                p = p if p.is_absolute() else root / p
                if p.is_file():
                    asset_names |= asset_animation_names(p)
        missing_states = [state for state, terms in required_common.items() if not has(declared, terms)]
        if kind == "boss" and not has(declared, ["phase", "transform", "enrage", "transition"]):
            missing_states.append("phase_transition")
        if as_list(ent.get("attacks")) and not has(declared, ["attack", "slash", "strike", "bite", "shoot", "cast", "slam", "combo", "skill"]):
            missing_states.append("attack")
        if missing_states:
            findings.append({"level": "error", "entity": eid, "code": "state.missing", "message": ", ".join(missing_states)})
        missing_in_asset = sorted(set(declared) - asset_names) if asset_names else []
        if asset_names and missing_in_asset:
            findings.append({"level": "error", "entity": eid, "code": "asset.animation_missing", "message": f"Declared animations missing from source asset: {missing_in_asset}"})
        undeclared_asset = sorted(asset_names - set(declared)) if asset_names else []
        if undeclared_asset:
            findings.append({"level": "warning", "entity": eid, "code": "asset.animation_unmapped", "message": f"Source animations not represented in manifest: {undeclared_asset}"})
        rows.append({
            "entity": eid,
            "kind": kind,
            "declared": len(declared),
            "asset_detected": len(asset_names),
            "missing_states": missing_states,
            "missing_in_asset": missing_in_asset,
            "unmapped_asset": undeclared_asset,
        })

    errors = [f for f in findings if f["level"] == "error"]
    lines = [
        "# Mob Animation State Audit",
        "",
        f"- Result: **{'PASS' if not errors else 'FAIL'}**",
        f"- Entities: **{len(rows)}**",
        f"- Errors: **{len(errors)}**",
        f"- Warnings: **{sum(1 for f in findings if f['level'] == 'warning')}**",
        "",
        "## Entity coverage",
        "",
        "|Entity|Kind|Declared|Asset detected|Missing states|",
        "|---|---|---:|---:|---|",
    ]
    for r in rows:
        lines.append(f"|{r['entity']}|{r['kind']}|{r['declared']}|{r['asset_detected']}|{', '.join(r['missing_states']) or '-'}|")
    lines += ["", "## Findings", ""]
    if not findings:
        lines.append("- None.")
    else:
        for f in findings:
            lines.append(f"- **{f['level'].upper()}** `{f['code']}` [{f['entity']}]: {f['message']}")
    report = "\n".join(lines) + "\n"
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
