#!/usr/bin/env python3
"""Resolve retained source Mixins against an exact target JVM symbol index.

This is a structural gate before real Mixin PREPARE/APPLY. It validates target owners,
injector selectors, @At member references, Shadows/Accessors/Invokers when statically inferable,
and reports descriptor ambiguity instead of guessing.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Iterable

from classfile_symbol_index import resolve_member
from port_26_3_common import Bundle, collect_text, write_json

INJECTORS = [
    "Inject", "Redirect", "ModifyArg", "ModifyArgs", "ModifyVariable", "ModifyConstant",
    # MixinExtras surfaces are common in modern mods and are just as descriptor-sensitive.
    "ModifyExpressionValue", "ModifyReceiver", "ModifyReturnValue",
    "WrapOperation", "WrapMethod", "WrapWithCondition",
]


def _annotation_bodies(text: str, annotation: str) -> Iterable[tuple[int, str]]:
    rx = re.compile(r"@" + re.escape(annotation) + r"\b")
    for m in rx.finditer(text):
        pos = m.end()
        while pos < len(text) and text[pos].isspace():
            pos += 1
        if pos >= len(text) or text[pos] != "(":
            yield m.start(), ""
            continue
        start = pos + 1
        depth = 1
        pos += 1
        quote = None
        esc = False
        while pos < len(text) and depth:
            ch = text[pos]
            if quote:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == quote:
                    quote = None
            else:
                if ch in {'"', "'"}:
                    quote = ch
                elif ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
            pos += 1
        yield m.start(), text[start:pos - 1] if depth == 0 else text[start:]


def _line(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def _imports(text: str) -> dict[str, str]:
    out = {}
    for m in re.finditer(r"^\s*import\s+([\w.$]+)\s*;", text, re.MULTILINE):
        fq = m.group(1)
        out[fq.rsplit(".", 1)[-1]] = fq.replace(".", "/")
    return out


def _mixin_targets(text: str) -> list[dict]:
    imports = _imports(text)
    out = []
    for pos, body in _annotation_bodies(text, "Mixin"):
        for target in re.findall(r"([A-Za-z_$][\w$]*)\.class", body):
            owner = imports.get(target)
            if owner:
                out.append({"owner": owner, "line": _line(text, pos), "source": target + ".class"})
        for fq in re.findall(r"[\"']([A-Za-z_$][\w.$/]+)[\"']", body):
            if "." in fq or "/" in fq:
                out.append({"owner": fq.replace(".", "/"), "line": _line(text, pos), "source": fq})
    # Stable de-dupe.
    seen = set()
    unique = []
    for item in out:
        key = (item["owner"], item["line"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def _quoted_values(expr: str) -> list[str]:
    return re.findall(r"[\"']([^\"']+)[\"']", expr)


def _selectors(text: str) -> list[dict]:
    out = []
    for ann in INJECTORS:
        for pos, body in _annotation_bodies(text, ann):
            for m in re.finditer(r"\bmethod\s*=\s*(\{.*?\}|[\"'][^\"']+[\"'])", body, re.DOTALL):
                for value in _quoted_values(m.group(1)):
                    out.append({"kind": "method", "selector": value, "line": _line(text, pos), "annotation": ann})
            # @At(target = "Lowner;name(desc)ret") member references live inside injector body.
            for value in re.findall(r"\btarget\s*=\s*[\"']([^\"']+)[\"']", body):
                out.append({"kind": "at-target", "selector": value, "line": _line(text, pos), "annotation": ann})
    # Accessor/Invoker explicit target strings.
    for ann, kind in [("Accessor", "field"), ("Invoker", "method")]:
        for pos, body in _annotation_bodies(text, ann):
            vals = _quoted_values(body)
            if vals:
                out.append({"kind": kind, "selector": vals[0], "line": _line(text, pos), "annotation": ann})
    return out


def _shadow_names(text: str) -> list[dict]:
    out = []
    # Conservative Java/Kotlin-ish next-declaration extraction. Descriptor is intentionally not guessed.
    for pos, _body in _annotation_bodies(text, "Shadow"):
        tail = text[pos:pos + 1200]
        end_ann = tail.find("\n")
        decl = tail[end_ann + 1:] if end_ann >= 0 else tail
        # Method declaration first.
        mm = re.search(r"(?:public|protected|private|static|final|abstract|native|synchronized|\s|@[\w.()=,\"']+)+[\w.$<>?,\[\] ]+\s+([A-Za-z_$][\w$]*)\s*\(", decl)
        if mm:
            out.append({"kind": "method", "selector": mm.group(1), "line": _line(text, pos), "annotation": "Shadow"})
            continue
        fm = re.search(r"(?:public|protected|private|static|final|volatile|transient|\s|@[\w.()=,\"']+)+[\w.$<>?,\[\] ]+\s+([A-Za-z_$][\w$]*)\s*(?:[;=])", decl)
        if fm:
            out.append({"kind": "field", "selector": fm.group(1), "line": _line(text, pos), "annotation": "Shadow"})
    return out


def _overwrite_names(text: str) -> list[dict]:
    out = []
    # @Overwrite carries no selector string: the following method declaration is the selector.
    # Do not guess a descriptor from Java source here; exact overload ambiguity must stay visible.
    for pos, _body in _annotation_bodies(text, "Overwrite"):
        tail = text[pos:pos + 1800]
        end_ann = tail.find("\n")
        decl = tail[end_ann + 1:] if end_ann >= 0 else tail
        mm = re.search(r"(?:public|protected|private|static|final|abstract|native|synchronized|strictfp|\s|@[\w.()=,\"']+)+[\w.$<>?,\[\] ]+\s+([A-Za-z_$][\w$]*)\s*\(", decl)
        if mm:
            out.append({"kind": "method", "selector": mm.group(1), "line": _line(text, pos), "annotation": "Overwrite"})
    return out


def parse_member_selector(selector: str, default_owner: str, declared_kind: str) -> dict:
    raw = selector.strip()
    owner = default_owner
    name = raw
    descriptor = None
    kind = declared_kind

    # Mixin target notation: Lowner;name(desc)ret or Lowner;field:Desc
    m = re.match(r"^L([^;]+);([^(:]+)(\([^)]*\).+)$", raw)
    if m:
        owner, name, descriptor = m.group(1), m.group(2), m.group(3)
        kind = "method"
        return {"owner": owner, "name": name, "descriptor": descriptor, "kind": kind, "raw": raw}
    m = re.match(r"^L([^;]+);([^:]+):(.+)$", raw)
    if m:
        owner, name, descriptor = m.group(1), m.group(2), m.group(3)
        kind = "field"
        return {"owner": owner, "name": name, "descriptor": descriptor, "kind": kind, "raw": raw}
    # owner/name(desc) form.
    m = re.match(r"^([\w/$]+)[/.]([A-Za-z_$][\w$]*)(\([^)]*\).+)$", raw)
    if m:
        owner, name, descriptor = m.group(1).replace(".", "/"), m.group(2), m.group(3)
        kind = "method"
        return {"owner": owner, "name": name, "descriptor": descriptor, "kind": kind, "raw": raw}
    # name(desc)ret.
    m = re.match(r"^([A-Za-z_$<>][\w$<>]*)(\([^)]*\).+)$", raw)
    if m:
        name, descriptor = m.group(1), m.group(2)
        kind = "method"
    return {"owner": owner, "name": name, "descriptor": descriptor, "kind": kind, "raw": raw}


def resolve_project(project: Path, target_index: dict) -> dict:
    bundle = Bundle(project)
    try:
        names = bundle.names()
        texts = collect_text(bundle, names)
    finally:
        bundle.close()

    resolved = []
    warnings = []
    blockers = []
    for path, text in texts.items():
        if not path.lower().endswith((".java", ".kt", ".kts", ".groovy")) or "@Mixin" not in text:
            continue
        targets = _mixin_targets(text)
        if not targets:
            warnings.append({"id": "mixin-target-unparsed", "path": path, "line": None, "message": "Mixin source found but target owner could not be inferred statically; require compiled annotation/bytecode resolution."})
            continue
        if len(targets) > 1:
            # Multi-target Mixins are legal; each selector is evaluated against every owner conservatively.
            warnings.append({"id": "mixin-multi-target", "path": path, "line": targets[0]["line"], "message": f"Mixin declares {len(targets)} targets; selectors must resolve for the intended target set."})
        selectors = _selectors(text) + _shadow_names(text) + _overwrite_names(text)
        for target in targets:
            owner = target["owner"]
            if owner not in (target_index.get("classes") or {}):
                blockers.append({"id": "mixin-target-owner-missing", "path": path, "line": target["line"], "message": f"Target class {owner} is absent from the exact target symbol index."})
                continue
            for sel in selectors:
                declared_kind = "method" if sel["kind"] in {"method", "at-target"} else sel["kind"]
                parsed = parse_member_selector(sel["selector"], owner, declared_kind)
                if parsed["kind"] not in {"method", "field"}:
                    warnings.append({"id": "mixin-selector-unparsed", "path": path, "line": sel["line"], "message": f"Could not classify selector {sel['selector']!r}."})
                    continue
                result = resolve_member(target_index, parsed["owner"], parsed["kind"], parsed["name"], parsed["descriptor"])
                row = {"path": path, "line": sel["line"], "annotation": sel["annotation"], "target_owner": owner, "selector": parsed, "resolution": result}
                if result["status"] == "RESOLVED":
                    resolved.append(row)
                    if parsed["descriptor"] is None:
                        warnings.append({"id": "mixin-selector-unique-but-descriptorless", "path": path, "line": sel["line"], "message": f"{sel['annotation']} selector {parsed['name']!r} is currently unique but descriptorless; pin the exact descriptor before release to resist overload drift."})
                elif result["status"] == "AMBIGUOUS":
                    blockers.append({"id": "mixin-selector-ambiguous", "path": path, "line": sel["line"], "message": f"Selector {parsed['name']!r} matches multiple target members; add the exact JVM descriptor.", "resolution": result})
                elif result["status"] == "OWNER_MISSING":
                    blockers.append({"id": "mixin-selector-owner-missing", "path": path, "line": sel["line"], "message": f"Selector owner {parsed['owner']} is absent from target index.", "resolution": result})
                else:
                    blockers.append({"id": "mixin-selector-member-missing", "path": path, "line": sel["line"], "message": f"Selector {parsed['name']!r}{parsed['descriptor'] or ''} does not resolve on {parsed['owner']} or inherited owners.", "resolution": result})

    return {
        "schema_version": 1,
        "project": str(project.resolve()),
        "target_index": target_index.get("input"),
        "status": "FAIL" if blockers else "PASS_WITH_WARNINGS" if warnings else "PASS",
        "resolved": resolved,
        "blockers": blockers,
        "warnings": warnings,
        "counts": {"resolved": len(resolved), "blockers": len(blockers), "warnings": len(warnings), "ids": dict(Counter(x["id"] for x in blockers + warnings))},
        "runtime_boundary": "Structural resolution is necessary but not sufficient. Retained Mixins still require real PREPARE/APPLY and affected behavior proof in the exact 26.3 runtime.",
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