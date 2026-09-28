#!/usr/bin/env python3
"""Audit every compiled Minecraft API reference in an old mod against the exact 26.3 target.

The tool does not execute mod code. It translates historical source-namespace owners/member names/JVM
descriptors through normalized same-version mapping indexes, then resolves the resulting Mojang-readable
symbols against a classfile_symbol_index.py index of the real 26.3 runtime. Missing exact symbols are
reported as semantic-migration work rather than guessed replacements.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from classfile_symbol_index import build_index, resolve_member
from mapping_bridge import bridge, class_aliases, remap_descriptor
from port_26_3_common import write_json

MC_PREFIX = "net/minecraft/"
READABLE_NAMESPACES = {"mojang_named", "official"}


def _target_class(indexes: list[dict], source_ns: str, owner: str) -> tuple[str | None, dict]:
    owner = owner.replace(".", "/")
    if source_ns in READABLE_NAMESPACES:
        return owner, {source_ns: owner}
    aliases = class_aliases(indexes, source_ns, owner)
    return aliases.get("mojang_named") or aliases.get("official"), aliases


def _target_descriptor(indexes: list[dict], source_ns: str, desc: str) -> tuple[str, list[dict]]:
    if source_ns in READABLE_NAMESPACES:
        return desc, []
    mapped = remap_descriptor(indexes, desc, source_ns, "mojang_named")
    return mapped["descriptor"], mapped.get("unresolved") or []


def _member_translation(indexes: list[dict], source_ns: str, owner: str, kind: str, name: str, desc: str) -> dict[str, Any]:
    target_owner, aliases = _target_class(indexes, source_ns, owner)
    target_desc, unresolved_types = _target_descriptor(indexes, source_ns, desc)
    target_name = name if source_ns in READABLE_NAMESPACES else None
    bridge_result = None
    if source_ns not in READABLE_NAMESPACES:
        bridge_result = bridge(indexes, source_ns, owner, name, desc)
        target_name = (bridge_result.get("members") or {}).get("mojang_named") or (bridge_result.get("members") or {}).get("official")
        target_owner = (bridge_result.get("classes") or {}).get("mojang_named") or (bridge_result.get("classes") or {}).get("official") or target_owner
        target_desc = (bridge_result.get("descriptor_by_namespace") or {}).get("mojang_named") or target_desc
    return {
        "source": {"owner": owner, "kind": kind, "name": name, "descriptor": desc, "namespace": source_ns},
        "target": {"owner": target_owner, "kind": kind, "name": target_name, "descriptor": target_desc},
        "class_aliases": aliases,
        "descriptor_unresolved_types": unresolved_types,
        "mapping_bridge": bridge_result,
    }


def _class_translation(indexes: list[dict], source_ns: str, owner: str) -> dict[str, Any]:
    target, aliases = _target_class(indexes, source_ns, owner)
    return {"source": {"class": owner, "namespace": source_ns}, "target": {"class": target}, "class_aliases": aliases}


def _classify_resolution(target_index: dict, translated: dict) -> dict:
    target = translated["target"]
    owner, name, desc, kind = target.get("owner"), target.get("name"), target.get("descriptor"), target.get("kind")
    if translated.get("descriptor_unresolved_types"):
        return {"status": "MAPPING_GAP", "reason": "descriptor contains source classes that could not be mapped exactly", "translation": translated}
    if not owner or not name:
        return {"status": "MAPPING_GAP", "reason": "historical owner/member could not be bridged to Mojang-readable source-version names", "translation": translated}
    rr = resolve_member(target_index, owner, kind, name, desc)
    if rr["status"] == "RESOLVED":
        return {"status": "EXACT_26_3", "translation": translated, "resolution": rr}
    if rr["status"] == "MEMBER_MISSING" and rr.get("candidates"):
        return {"status": "DESCRIPTOR_OR_SIGNATURE_DRIFT", "translation": translated, "resolution": rr, "reason": "same member name exists in target hierarchy but exact JVM descriptor does not"}
    return {"status": rr["status"], "translation": translated, "resolution": rr, "reason": "exact 26.3 symbolic resolution failed; semantic replacement required"}


def audit(source_mod: Path, source_namespace: str, mapping_indexes: list[dict], target_index: dict) -> dict:
    source_index = build_index(source_mod, include_refs=True)
    results = []
    class_results = []
    seen_members = set()
    seen_classes = set()

    for source_class, cls in (source_index.get("classes") or {}).items():
        for ref in cls.get("class_refs") or []:
            base = ref
            while base.startswith("["):
                base = base[1:]
            if base.startswith("L") and base.endswith(";"):
                base = base[1:-1]
            if not base.startswith(MC_PREFIX):
                continue
            key = (source_class, base)
            if key in seen_classes:
                continue
            seen_classes.add(key)
            tr = _class_translation(mapping_indexes, source_namespace, base)
            target = tr["target"]["class"]
            status = "EXACT_26_3" if target and target in (target_index.get("classes") or {}) else "MAPPING_GAP" if not target else "OWNER_MISSING"
            class_results.append({"source_class": source_class, "status": status, "translation": tr})

        for ref in cls.get("member_refs") or []:
            if not ref.get("owner", "").startswith(MC_PREFIX):
                continue
            key = (source_class, ref["kind"], ref["owner"], ref["name"], ref["descriptor"])
            if key in seen_members:
                continue
            seen_members.add(key)
            tr = _member_translation(mapping_indexes, source_namespace, ref["owner"], ref["kind"], ref["name"], ref["descriptor"])
            row = _classify_resolution(target_index, tr)
            row["source_class"] = source_class
            row["reference_kind"] = "constant_pool_member"
            results.append(row)

        for indy in cls.get("invokedynamic_refs") or []:
            fi = indy.get("functional_interface")
            sam_name = indy.get("sam_name")
            sam_desc = indy.get("sam_descriptor")
            if fi and fi.startswith(MC_PREFIX) and sam_name and sam_desc:
                key = (source_class, "indy-sam", fi, sam_name, sam_desc)
                if key not in seen_members:
                    seen_members.add(key)
                    tr = _member_translation(mapping_indexes, source_namespace, fi, "method", sam_name, sam_desc)
                    row = _classify_resolution(target_index, tr)
                    row["source_class"] = source_class
                    row["reference_kind"] = "invokedynamic_sam"
                    row["invokedynamic"] = indy
                    results.append(row)

    status_counts = Counter(x["status"] for x in results)
    class_status_counts = Counter(x["status"] for x in class_results)
    unresolved_statuses = {"MAPPING_GAP", "OWNER_MISSING", "MEMBER_MISSING", "DESCRIPTOR_OR_SIGNATURE_DRIFT", "AMBIGUOUS"}
    blockers = [x for x in results if x["status"] in unresolved_statuses]
    class_blockers = [x for x in class_results if x["status"] != "EXACT_26_3"]
    return {
        "schema_version": 1,
        "source_mod": str(source_mod.resolve()),
        "source_namespace": source_namespace,
        "source_class_count": source_index.get("class_count", 0),
        "target_index": target_index.get("input"),
        "status": "FAIL" if blockers or class_blockers else "PASS",
        "member_reference_count": len(results),
        "class_reference_count": len(class_results),
        "counts": {"members": dict(status_counts), "classes": dict(class_status_counts), "blockers": len(blockers) + len(class_blockers)},
        "member_references": results,
        "class_references": class_results,
        "blockers": class_blockers + blockers,
        "rule": "Only exact mapped owner/member/JVM-descriptor references are considered mechanically portable. Missing symbols become semantic migration tasks; this tool never guesses a replacement from a similar name.",
        "runtime_boundary": "Static API-reference migration does not prove behavior, injection shape, side-only initialization, data/resource correctness, or runtime compatibility. Build and real runtime gates remain required.",
    }


def render_md(result: dict) -> str:
    lines = [
        "# Minecraft 26.3 API Reference Migration Audit", "",
        f"**Status: {result['status']}**", "",
        f"Source: `{result['source_mod']}`", f"Source namespace: `{result['source_namespace']}`", f"Target index: `{result.get('target_index')}`", "",
        "## Counts", "", f"- Source classes: {result['source_class_count']}", f"- Minecraft class refs: {result['class_reference_count']}", f"- Minecraft member/SAM refs: {result['member_reference_count']}", f"- Blocking migration gaps: {result['counts']['blockers']}", "",
        "## Blocking migration gaps", "",
    ]
    if not result["blockers"]:
        lines.append("None in the statically visible Minecraft API reference set.")
    else:
        for row in result["blockers"][:200]:
            tr = row.get("translation") or {}
            src = tr.get("source") or {}
            tgt = tr.get("target") or {}
            if "owner" in src:
                lines.append(f"- **{row['status']}** `{src.get('owner')}.{src.get('name')}{src.get('descriptor')}` -> `{tgt.get('owner')}.{tgt.get('name')}{tgt.get('descriptor')}` ({row.get('reason','exact resolution failed')})")
            else:
                lines.append(f"- **{row['status']}** class `{src.get('class')}` -> `{tgt.get('class')}`")
    lines += ["", "## Rule", "", result["rule"], "", "## Runtime boundary", "", result["runtime_boundary"], ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source_mod", type=Path)
    ap.add_argument("--source-namespace", required=True, help="exact namespace of compiled source refs, e.g. intermediary, yarn_named, srg, mcp_named, mojang_named")
    ap.add_argument("--mapping-index", action="append", default=[], required=False, type=Path, help="normalized mapping index for the source Minecraft version; repeatable")
    ap.add_argument("--target-index", required=True, type=Path)
    ap.add_argument("--json-out", type=Path)
    ap.add_argument("--md-out", type=Path)
    ap.add_argument("--fail-on-gap", action="store_true")
    args = ap.parse_args()
    indexes = [json.loads(p.read_text(encoding="utf-8")) for p in args.mapping_index]
    target = json.loads(args.target_index.read_text(encoding="utf-8"))
    result = audit(args.source_mod, args.source_namespace, indexes, target)
    if args.json_out:
        write_json(args.json_out, result)
    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        args.md_out.write_text(render_md(result), encoding="utf-8")
    if not args.json_out and not args.md_out:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 3 if args.fail_on_gap and result["status"] != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
