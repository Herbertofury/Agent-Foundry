#!/usr/bin/env python3
"""Resolve Fabric class-tweaker/access-widener and Forge/NeoForge AT targets against exact 26.3 classes."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from classfile_symbol_index import resolve_member
from port_26_3_common import Bundle, collect_text, write_json


def _resolve_class(index: dict, owner: str) -> bool:
    return owner.replace(".", "/") in (index.get("classes") or {})


def _fabric_entries(path: str, text: str) -> list[dict]:
    rows = []
    meaningful = [(i, raw.split("#", 1)[0].strip()) for i, raw in enumerate(text.splitlines(), 1) if raw.split("#", 1)[0].strip()]
    if not meaningful:
        return rows
    for line, value in meaningful[1:]:
        parts = value.split()
        if not parts:
            continue
        # Transitive access wideners prefix the operation; normalize it away.
        if parts[0].startswith("transitive-"):
            parts[0] = parts[0][len("transitive-"):]
        if len(parts) >= 3 and parts[1] == "class":
            rows.append({"path": path, "line": line, "kind": "class", "owner": parts[2]})
        elif len(parts) >= 5 and parts[1] in {"method", "field"}:
            rows.append({"path": path, "line": line, "kind": parts[1], "owner": parts[2], "name": parts[3], "descriptor": parts[4]})
    return rows


def _at_entries(path: str, text: str) -> list[dict]:
    rows = []
    for line, raw in enumerate(text.splitlines(), 1):
        value = raw.split("#", 1)[0].strip()
        if not value:
            continue
        parts = value.split()
        if len(parts) < 2:
            continue
        owner = parts[1].replace(".", "/")
        if len(parts) == 2:
            rows.append({"path": path, "line": line, "kind": "class", "owner": owner})
            continue
        member = parts[2]
        if "(" in member:
            name, desc = member.split("(", 1)
            rows.append({"path": path, "line": line, "kind": "method", "owner": owner, "name": name, "descriptor": "(" + desc})
        else:
            rows.append({"path": path, "line": line, "kind": "field", "owner": owner, "name": member, "descriptor": None})
    return rows


def resolve_project(project: Path, target_index: dict) -> dict:
    bundle = Bundle(project)
    try:
        names = bundle.names()
        texts = collect_text(bundle, names)
    finally:
        bundle.close()
    entries = []
    for path, text in texts.items():
        low = path.lower()
        if low.endswith((".accesswidener", ".classtweaker")):
            entries.extend(_fabric_entries(path, text))
        elif low.endswith("accesstransformer.cfg"):
            entries.extend(_at_entries(path, text))

    resolved, blockers, warnings = [], [], []
    for row in entries:
        owner = row["owner"].replace(".", "/")
        if not _resolve_class(target_index, owner):
            blockers.append({"id": "access-owner-missing", **row, "message": f"Access rule owner {owner} is absent from exact target index."})
            continue
        if row["kind"] == "class":
            resolved.append({**row, "owner": owner, "resolution": "RESOLVED"})
            continue
        rr = resolve_member(target_index, owner, row["kind"], row["name"], row.get("descriptor"))
        if rr["status"] == "RESOLVED":
            resolved.append({**row, "owner": owner, "resolution": rr})
            if row.get("descriptor") is None:
                warnings.append({"id": "access-member-descriptorless", **row, "message": f"Access rule for {owner}.{row['name']} is name-only; currently unique but pin descriptor if target format supports it."})
        elif rr["status"] == "AMBIGUOUS":
            blockers.append({"id": "access-member-ambiguous", **row, "message": f"Access rule {owner}.{row['name']} is ambiguous across overloads/inheritance.", "resolution": rr})
        else:
            blockers.append({"id": "access-member-missing", **row, "message": f"Access rule {owner}.{row['name']}{row.get('descriptor') or ''} does not resolve in target hierarchy.", "resolution": rr})
    return {
        "schema_version": 1,
        "project": str(project.resolve()),
        "target_index": target_index.get("input"),
        "status": "FAIL" if blockers else "PASS_WITH_WARNINGS" if warnings else "PASS",
        "entries": entries,
        "resolved": resolved,
        "blockers": blockers,
        "warnings": warnings,
        "counts": {"entries": len(entries), "resolved": len(resolved), "blockers": len(blockers), "warnings": len(warnings), "ids": dict(Counter(x["id"] for x in blockers + warnings))},
        "runtime_boundary": "Exact access target resolution does not prove that widening/transforming that member preserves behavior. Build and exercise the affected runtime path.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("--target-index", type=Path, required=True)
    ap.add_argument("--json-out", type=Path)
    ap.add_argument("--fail-on-blocker", action="store_true")
    args = ap.parse_args()
    index = json.loads(args.target_index.read_text(encoding="utf-8"))
    result = resolve_project(args.project, index)
    if args.json_out:
        write_json(args.json_out, result)
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 3 if args.fail_on_blocker and result["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
