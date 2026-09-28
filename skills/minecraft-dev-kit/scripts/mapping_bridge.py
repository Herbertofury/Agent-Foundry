#!/usr/bin/env python3
"""Compose normalized historical mapping indexes to bridge exact source symbols between namespaces.

Designed for same-Minecraft-version lineage such as Yarn -> Intermediary/obfuscated -> Mojang named,
or MCP named -> SRG -> obfuscated. It is deliberately descriptor-aware and does not pretend that
same-version mappings alone can solve semantic API changes across Minecraft versions.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any



DESC_CLASS_RX = re.compile(r"L([^;]+);")


def class_aliases(indexes: list[dict], namespace: str, class_name: str) -> dict[str, str]:
    """Compose exact class aliases across same-version mapping indexes."""
    known = {namespace: class_name.replace(".", "/")}
    changed = True
    while changed:
        changed = False
        for ix, row in _rows(indexes, "classes"):
            names = row.get("names") or {}
            if any(names.get(ns) == value for ns, value in known.items()):
                for ns, value in names.items():
                    if value and ns not in known:
                        known[ns] = value
                        changed = True
    return known


def remap_descriptor(indexes: list[dict], descriptor: str, source_namespace: str, target_namespace: str) -> dict[str, Any]:
    """Remap every object type inside a JVM descriptor without guessing missing aliases."""
    unresolved = []
    mapped = descriptor
    # Work from the original string so repeated class names are replaced consistently.
    replacements = {}
    for cls in DESC_CLASS_RX.findall(descriptor):
        aliases = class_aliases(indexes, source_namespace, cls)
        target = aliases.get(target_namespace)
        if target:
            replacements[cls] = target
        else:
            unresolved.append({"class": cls, "known_aliases": aliases})
    for src, dst in replacements.items():
        mapped = mapped.replace(f"L{src};", f"L{dst};")
    return {
        "status": "RESOLVED" if not unresolved else "PARTIAL",
        "source_namespace": source_namespace,
        "target_namespace": target_namespace,
        "source_descriptor": descriptor,
        "descriptor": mapped,
        "unresolved": unresolved,
    }


def descriptor_variants(indexes: list[dict], descriptor: str, source_namespace: str) -> dict[str, str]:
    namespaces = {source_namespace}
    for ix in indexes:
        namespaces.update(ix.get("namespaces") or [])
    out = {}
    for ns in namespaces:
        out[ns] = remap_descriptor(indexes, descriptor, source_namespace, ns)["descriptor"]
    return out

def _rows(indexes: list[dict], section: str):
    for ix in indexes:
        for row in ix.get(section, []) or []:
            yield ix, row


def _descriptor_set(row: dict) -> set[str]:
    return {x for x in (row.get("descriptor"), row.get("target_descriptor")) if x}


def _matches_descriptor(row: dict, known: set[str]) -> bool:
    if not known:
        return True
    row_desc = _descriptor_set(row)
    return not row_desc or bool(row_desc & known)


def bridge(indexes: list[dict], namespace: str, class_name: str, member: str | None = None, descriptor: str | None = None) -> dict[str, Any]:
    class_name = class_name.replace(".", "/")
    known_classes = {namespace: class_name}
    known_members = {namespace: member} if member else {}
    descriptors = {descriptor} if descriptor else set()
    descriptor_by_namespace = descriptor_variants(indexes, descriptor, namespace) if descriptor else {}
    evidence = []

    if member is not None and not descriptor:
        return {
            "schema_version": 1,
            "status": "DESCRIPTOR_REQUIRED",
            "message": "Exact member bridging requires a JVM descriptor. Recover it from compiled source/JAR or the mapping/classfile index instead of guessing an overload.",
            "classes": known_classes,
            "members": known_members,
            "descriptors": [],
            "evidence": [],
        }

    # MCP CSV aliases are globally unique SRG ids for methods/fields, so they can enrich exact
    # member lineage once either side is known.
    aliases = []
    for ix in indexes:
        aliases.extend(ix.get("aliases") or [])

    changed = True
    while changed:
        changed = False
        # Expand class aliases first.
        for ix, row in _rows(indexes, "classes"):
            names = row.get("names") or {}
            if any(names.get(ns) == value for ns, value in known_classes.items()):
                for ns, value in names.items():
                    if value and ns not in known_classes:
                        known_classes[ns] = value
                        changed = True
                        evidence.append({"type": "class", "source": ix.get("source_path"), "names": names})
        if member is None:
            continue

        # Expand member aliases only when owner and descriptor lineage are compatible.
        for section in ("fields", "methods"):
            for ix, row in _rows(indexes, section):
                owners = row.get("owner") or {}
                names = row.get("names") or {}
                shared = False
                for ns, known_owner in known_classes.items():
                    if owners.get(ns) != known_owner:
                        continue
                    known_name = known_members.get(ns)
                    if known_name and names.get(ns) == known_name:
                        shared = True
                        break
                if not shared:
                    continue
                descriptor_ns = row.get("descriptor_namespace") or ((ix.get("namespaces") or [None])[0])
                target_descriptor_ns = row.get("target_descriptor_namespace")
                expected_primary = descriptor_by_namespace.get(descriptor_ns) if descriptor_ns else None
                expected_secondary = descriptor_by_namespace.get(target_descriptor_ns) if target_descriptor_ns else None
                row_descs = _descriptor_set(row)
                if row_descs:
                    compatible = False
                    if expected_primary and row.get("descriptor") == expected_primary:
                        compatible = True
                    if expected_secondary and row.get("target_descriptor") == expected_secondary:
                        compatible = True
                    if not expected_primary and not expected_secondary and _matches_descriptor(row, descriptors):
                        compatible = True
                    if not compatible:
                        continue
                for ns, value in owners.items():
                    if value and ns not in known_classes:
                        known_classes[ns] = value
                        changed = True
                for ns, value in names.items():
                    if value and ns not in known_members:
                        known_members[ns] = value
                        changed = True
                before = len(descriptors)
                descriptors |= _descriptor_set(row)
                changed |= len(descriptors) != before
                evidence.append({"type": section[:-1], "source": ix.get("source_path"), "owner": owners, "names": names, "descriptor": row.get("descriptor"), "target_descriptor": row.get("target_descriptor")})

        # MCP human-name aliases do not carry owner/descriptor; only attach them to a known exact
        # SRG id, never by fuzzy human name.
        for row in aliases:
            srg, mcp = row.get("srg"), row.get("mcp_named")
            if known_members.get("srg") == srg and mcp and "mcp_named" not in known_members:
                known_members["mcp_named"] = mcp
                changed = True
                evidence.append({"type": "mcp-alias", "srg": srg, "mcp_named": mcp})
            if known_members.get("mcp_named") == mcp and srg and "srg" not in known_members:
                known_members["srg"] = srg
                changed = True
                evidence.append({"type": "mcp-alias", "srg": srg, "mcp_named": mcp})

    status = "RESOLVED" if len(known_classes) > 1 or (member is not None and len(known_members) > 1) else "UNRESOLVED"
    return {
        "schema_version": 1,
        "status": status,
        "query": {"namespace": namespace, "class": class_name, "member": member, "descriptor": descriptor},
        "classes": dict(sorted(known_classes.items())),
        "members": dict(sorted(known_members.items())),
        "descriptors": sorted(descriptors),
        "descriptor_by_namespace": descriptor_by_namespace,
        "evidence": evidence,
        "boundary": "This composes exact aliases for one source Minecraft version. Cross-version semantic replacement still requires the 26.3 semantic planner, target class index, build, and runtime proof.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--index", action="append", required=True, type=Path)
    ap.add_argument("--namespace", required=True)
    ap.add_argument("--class", dest="class_name", required=True)
    ap.add_argument("--member")
    ap.add_argument("--descriptor")
    ap.add_argument("--to")
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()
    indexes = [json.loads(p.read_text(encoding="utf-8")) for p in args.index]
    result = bridge(indexes, args.namespace, args.class_name, args.member, args.descriptor)
    if args.to:
        result["requested_target"] = {
            "namespace": args.to,
            "class": result["classes"].get(args.to),
            "member": result["members"].get(args.to) if args.member else None,
        }
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "RESOLVED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
