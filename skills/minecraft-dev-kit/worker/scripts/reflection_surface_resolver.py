#!/usr/bin/env python3
"""Resolve common Minecraft reflection/MethodHandle source surfaces against an exact class index.

Ordinary remapping cannot rewrite string member names safely. This gate catches the common explicit
patterns without pretending to solve arbitrary dynamic reflection. Unparsed dynamic surfaces remain
visible as warnings and still require packaged native runtime proof.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from classfile_symbol_index import resolve_declared_member, resolve_member
from port_26_3_common import Bundle, collect_text, write_json

SOURCE_EXTS = (".java", ".kt", ".kts", ".groovy")
REFLECTION_TOKEN_RX = re.compile(r"\b(?:Class\.forName|getDeclaredField|getDeclaredMethod|getField|getMethod|findVirtual|findStatic|findSpecial|findGetter|findSetter|findStaticGetter|findStaticSetter|ObfuscationReflectionHelper\.findField|ObfuscationReflectionHelper\.findMethod)\b")
CLASS_FOR_NAME_RX = re.compile(r"Class\.forName\s*\(\s*[\"']([^\"']+)[\"']")
CLASS_MEMBER_RX = re.compile(r"([A-Za-z_$][\w.$]*)\.class\s*\.\s*(getDeclaredMethod|getMethod|getDeclaredField|getField)\s*\(\s*[\"']([^\"']+)[\"']")
HANDLE_RX = re.compile(r"(?:MethodHandles\s*\.\s*lookup\s*\(\s*\)\s*\.)?(findVirtual|findStatic|findSpecial|findGetter|findSetter|findStaticGetter|findStaticSetter)\s*\(\s*([A-Za-z_$][\w.$]*)\.class\s*,\s*[\"']([^\"']+)[\"']")
ORH_RX = re.compile(r"ObfuscationReflectionHelper\s*\.\s*(findField|findMethod)\s*\(\s*([A-Za-z_$][\w.$]*)\.class\s*,\s*[\"']([^\"']+)[\"']")


def _line(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def _imports(text: str) -> dict[str, str]:
    out = {}
    for m in re.finditer(r"^\s*import\s+([\w.$]+)\s*;?", text, re.MULTILINE):
        fq = m.group(1)
        if fq.endswith(".*"):
            continue
        out[fq.rsplit(".", 1)[-1]] = fq.replace(".", "/")
    return out


def _owner(expr: str, imports: dict[str, str]) -> str | None:
    expr = expr.strip().replace("$", "$" )
    if "/" in expr:
        return expr
    if "." in expr:
        return expr.replace(".", "/")
    return imports.get(expr)


def _minecraft(owner: str | None) -> bool:
    return bool(owner and owner.startswith("net/minecraft/"))


def _resolve_member(index: dict, owner: str, kind: str, name: str, declared_only: bool, row: dict) -> tuple[dict | None, dict | None]:
    resolver = resolve_declared_member if declared_only else resolve_member
    result = resolver(index, owner, kind, name, None)
    if result["status"] == "RESOLVED":
        warning = {
            "id": "reflection-member-descriptorless" if kind == "method" else "reflection-field-name-only",
            **row,
            "message": f"Reflection target {owner}.{name} resolves now, but source lookup does not encode an exact JVM descriptor; packaged/native proof is still required.",
            "resolution": result,
        }
        return None, warning
    if result["status"] == "AMBIGUOUS":
        return ({"id": "reflection-member-ambiguous", **row, "message": f"Reflection target {owner}.{name} is ambiguous across exact target members; pin the intended overload/descriptor or replace the reflection path.", "resolution": result}, None)
    return ({"id": "reflection-member-missing", **row, "message": f"Reflection target {owner}.{name} does not resolve in the exact target symbol index.", "resolution": result}, None)


def resolve_project(project: Path, target_index: dict) -> dict:
    bundle = Bundle(project)
    try:
        names = bundle.names()
        texts = collect_text(bundle, names)
    finally:
        bundle.close()

    resolved = []
    blockers = []
    warnings = []
    surfaces = []
    for path, text in texts.items():
        if not path.lower().endswith(SOURCE_EXTS) or not REFLECTION_TOKEN_RX.search(text):
            continue
        imports = _imports(text)
        handled_spans: list[tuple[int, int]] = []

        for m in CLASS_FOR_NAME_RX.finditer(text):
            raw = m.group(1)
            owner = raw.replace(".", "/")
            if not _minecraft(owner):
                continue
            row = {"path": path, "line": _line(text, m.start()), "surface": "Class.forName", "owner": owner, "raw": m.group(0)}
            handled_spans.append(m.span())
            if owner not in (target_index.get("classes") or {}):
                blockers.append({"id": "reflection-class-missing", **row, "message": f"Class.forName target {owner} is absent from the exact target symbol index."})
            else:
                resolved.append({**row, "resolution": "RESOLVED"})

        for m in CLASS_MEMBER_RX.finditer(text):
            cls_expr, api, name = m.group(1), m.group(2), m.group(3)
            owner = _owner(cls_expr, imports)
            if not _minecraft(owner):
                continue
            kind = "method" if "Method" in api else "field"
            declared_only = api.startswith("getDeclared")
            row = {"path": path, "line": _line(text, m.start()), "surface": api, "owner": owner, "kind": kind, "name": name, "raw": m.group(0)}
            handled_spans.append(m.span())
            blocker, warning = _resolve_member(target_index, owner, kind, name, declared_only, row)
            if blocker:
                blockers.append(blocker)
            else:
                resolved.append(row)
            if warning:
                warnings.append(warning)

        for m in HANDLE_RX.finditer(text):
            api, cls_expr, name = m.group(1), m.group(2), m.group(3)
            owner = _owner(cls_expr, imports)
            if not _minecraft(owner):
                continue
            kind = "field" if any(x in api for x in ("Getter", "Setter")) else "method"
            row = {"path": path, "line": _line(text, m.start()), "surface": api, "owner": owner, "kind": kind, "name": name, "raw": m.group(0)}
            handled_spans.append(m.span())
            blocker, warning = _resolve_member(target_index, owner, kind, name, False, row)
            if blocker:
                blockers.append(blocker)
            else:
                resolved.append(row)
            if warning:
                warnings.append(warning)

        for m in ORH_RX.finditer(text):
            api, cls_expr, name = m.group(1), m.group(2), m.group(3)
            owner = _owner(cls_expr, imports)
            if not _minecraft(owner):
                continue
            kind = "field" if api == "findField" else "method"
            row = {"path": path, "line": _line(text, m.start()), "surface": f"ObfuscationReflectionHelper.{api}", "owner": owner, "kind": kind, "name": name, "raw": m.group(0)}
            handled_spans.append(m.span())
            blocker, warning = _resolve_member(target_index, owner, kind, name, False, row)
            if blocker:
                blockers.append(blocker)
            else:
                resolved.append(row)
            if warning:
                warnings.append(warning)

        tokens = []
        for m in REFLECTION_TOKEN_RX.finditer(text):
            if any(a <= m.start() < b for a, b in handled_spans):
                continue
            tokens.append({"token": m.group(0), "line": _line(text, m.start())})
        if tokens:
            warnings.append({
                "id": "reflection-dynamic-surface-unresolved",
                "path": path,
                "line": tokens[0]["line"],
                "message": "Reflection/MethodHandle surface could not be reduced to a literal Minecraft owner+member statically. Keep it in the runtime acceptance path; do not assume remapping fixed it.",
                "tokens": tokens[:40],
            })
        surfaces.append({"path": path, "handled": len(handled_spans), "unresolved_tokens": tokens[:40]})

    return {
        "schema_version": 1,
        "project": str(project.resolve()),
        "target_index": target_index.get("input"),
        "status": "FAIL" if blockers else "PASS_WITH_WARNINGS" if warnings else "PASS",
        "surfaces": surfaces,
        "resolved": resolved,
        "blockers": blockers,
        "warnings": warnings,
        "counts": {"resolved": len(resolved), "blockers": len(blockers), "warnings": len(warnings), "ids": dict(Counter(x["id"] for x in blockers + warnings))},
        "runtime_boundary": "Static reflection resolution only covers literal/common lookup forms. Computed names, aliases, generated handles and runtime-only branches require exact packaged native proof.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("--target-index", required=True, type=Path)
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