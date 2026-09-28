#!/usr/bin/env python3
"""Statically audit packaged JVM linkage against exact target/dependency class indexes.

Focuses on Minecraft/loader/dependency symbolic references that compile-time userdev/remapping can hide.
This is a pre-runtime gate, not a substitute for launching the packaged candidate.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from classfile_symbol_index import build_index, parse_class, resolve_member
from port_26_3_common import Bundle, write_json

DESC_CLASS_RX = re.compile(r"L([^;]+);")
DEFAULT_PREFIXES = ("net/minecraft/",)


def _merge_indexes(indexes: list[dict]) -> dict:
    classes = {}
    owners = {}
    for ix in indexes:
        source = ix.get("input") or "<index>"
        for name, cls in (ix.get("classes") or {}).items():
            if name not in classes:
                classes[name] = cls
                owners[name] = source
    return {"schema_version": 1, "input": ";".join(x.get("input") or "<index>" for x in indexes), "classes": classes, "owners": owners}


def _interesting(name: str, prefixes: tuple[str, ...]) -> bool:
    return any(name.startswith(p) for p in prefixes)


def audit(candidate: Path, indexes: list[dict], prefixes: tuple[str, ...] = DEFAULT_PREFIXES) -> dict:
    universe = _merge_indexes(indexes)
    classes = universe["classes"]
    bundle = Bundle(candidate)
    blockers = []
    warnings = []
    checked_refs = 0
    checked_classes = 0
    try:
        for path in bundle.names():
            if not path.endswith(".class"):
                continue
            try:
                cls = parse_class(bundle.read(path), path)
            except Exception as exc:
                warnings.append({"id": "candidate-class-parse-failure", "path": path, "message": str(exc)})
                continue
            checked_classes += 1
            # Constant-pool class references.
            for ref in cls.get("class_refs") or []:
                base = ref
                while base.startswith("["):
                    base = base[1:]
                if base.startswith("L") and base.endswith(";"):
                    base = base[1:-1]
                if _interesting(base, prefixes) and base not in classes:
                    blockers.append({"id": "unresolved-class-reference", "path": path, "message": f"{cls['owner']} references absent class {base}", "reference": base})
            # Member references with exact descriptors and inherited owner resolution.
            for ref in cls.get("member_refs") or []:
                owner = ref["owner"]
                if not _interesting(owner, prefixes):
                    continue
                checked_refs += 1
                if owner not in classes:
                    blockers.append({"id": "unresolved-member-owner", "path": path, "message": f"{cls['owner']} references {owner}.{ref['name']}{ref['descriptor']} but owner is absent", "reference": ref})
                    continue
                rr = resolve_member(universe, owner, ref["kind"], ref["name"], ref["descriptor"])
                if rr["status"] != "RESOLVED":
                    blockers.append({"id": "unresolved-member-reference", "path": path, "message": f"{cls['owner']} references {owner}.{ref['name']}{ref['descriptor']} but exact symbolic resolution failed ({rr['status']})", "reference": ref, "resolution": rr})
                # Descriptor-owned types must exist too when in the audited namespaces.
                for typ in DESC_CLASS_RX.findall(ref["descriptor"]):
                    if _interesting(typ, prefixes) and typ not in classes:
                        blockers.append({"id": "unresolved-descriptor-type", "path": path, "message": f"Descriptor for {owner}.{ref['name']} references absent type {typ}", "reference": ref, "missing_type": typ})

            # LambdaMetafactory call sites carry the functional-interface SAM name in invokedynamic,
            # outside ordinary owner/member constant-pool refs. Validate it explicitly because stale
            # mapped SAM names can otherwise survive packaging and throw AbstractMethodError.
            for indy in cls.get("invokedynamic_refs") or []:
                fi = indy.get("functional_interface")
                sam_name = indy.get("sam_name")
                sam_desc = indy.get("sam_descriptor")
                if fi and _interesting(fi, prefixes):
                    checked_refs += 1
                    if fi not in classes:
                        blockers.append({"id": "unresolved-indy-sam-owner", "path": path, "message": f"{cls['owner']} lambda targets absent functional interface {fi}", "invokedynamic": indy})
                    elif sam_name and sam_desc:
                        rr = resolve_member(universe, fi, "method", sam_name, sam_desc)
                        if rr["status"] != "RESOLVED":
                            blockers.append({"id": "unresolved-indy-sam", "path": path, "message": f"{cls['owner']} lambda SAM {fi}.{sam_name}{sam_desc} failed exact resolution ({rr['status']})", "invokedynamic": indy, "resolution": rr})
                    else:
                        warnings.append({"id": "indy-sam-incomplete", "path": path, "message": f"Could not fully decode SAM descriptor for invokedynamic {sam_name} in {cls['owner']}", "invokedynamic": indy})
                impl = indy.get("implementation") or {}
                impl_owner = impl.get("owner")
                if impl_owner and _interesting(impl_owner, prefixes):
                    checked_refs += 1
                    rr = resolve_member(universe, impl_owner, impl.get("kind", "method"), impl.get("name", ""), impl.get("descriptor"))
                    if rr["status"] != "RESOLVED":
                        blockers.append({"id": "unresolved-indy-implementation", "path": path, "message": f"{cls['owner']} invokedynamic implementation handle {impl_owner}.{impl.get('name')}{impl.get('descriptor')} failed exact resolution ({rr['status']})", "invokedynamic": indy, "resolution": rr})
    finally:
        bundle.close()

    # De-dupe identical linkage reports from repeated constant-pool entries.
    seen = set()
    unique = []
    for item in blockers:
        key = (item["id"], item.get("path"), item.get("message"))
        if key not in seen:
            seen.add(key)
            unique.append(item)
    blockers = unique
    return {
        "schema_version": 1,
        "candidate": str(candidate.resolve()),
        "indexes": [x.get("input") for x in indexes],
        "status": "FAIL" if blockers else "PASS_WITH_WARNINGS" if warnings else "PASS",
        "checked_classes": checked_classes,
        "checked_member_refs": checked_refs,
        "blockers": blockers,
        "warnings": warnings,
        "counts": {"blockers": len(blockers), "warnings": len(warnings), "ids": dict(Counter(x["id"] for x in blockers + warnings))},
        "runtime_boundary": "Static linkage proof cannot catch reflection, service loading, Mixin injection shape, resource/data failures, side-only initialization, or dynamic invokedynamic semantics. Launch the exact packaged artifact afterward.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("candidate", type=Path)
    ap.add_argument("--target-index", required=True, type=Path)
    ap.add_argument("--dependency-index", action="append", default=[], type=Path)
    ap.add_argument("--prefix", action="append", default=[])
    ap.add_argument("--json-out", type=Path)
    ap.add_argument("--fail-on-blocker", action="store_true")
    args = ap.parse_args()
    indexes = [json.loads(args.target_index.read_text(encoding="utf-8"))]
    indexes.extend(json.loads(p.read_text(encoding="utf-8")) for p in args.dependency_index)
    prefixes = tuple(args.prefix) if args.prefix else DEFAULT_PREFIXES
    result = audit(args.candidate, indexes, prefixes)
    if args.json_out:
        write_json(args.json_out, result)
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 3 if args.fail_on_blocker and result["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
