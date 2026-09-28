#!/usr/bin/env python3
"""Build/query a deterministic JVM class/member index without loading or executing classes.

Used by Minecraft 26.3 ports to prove exact owner/name/descriptor ownership for Mixins,
reflection bridges, Access Transformers/Class Tweakers, inherited members, and packaged linkage.
"""
from __future__ import annotations

import argparse
import json
import io
import struct
import zipfile
from collections import deque
from pathlib import Path
from typing import Any

from port_26_3_common import Bundle, write_json


def _u1(data: bytes, off: int) -> tuple[int, int]:
    return data[off], off + 1


def _u2(data: bytes, off: int) -> tuple[int, int]:
    return struct.unpack_from(">H", data, off)[0], off + 2


def _u4(data: bytes, off: int) -> tuple[int, int]:
    return struct.unpack_from(">I", data, off)[0], off + 4


def parse_class(data: bytes, path: str = "<memory>") -> dict[str, Any]:
    if len(data) < 10 or data[:4] != b"\xca\xfe\xba\xbe":
        raise ValueError(f"not a JVM class file: {path}")
    minor = struct.unpack_from(">H", data, 4)[0]
    major = struct.unpack_from(">H", data, 6)[0]
    cp_count = struct.unpack_from(">H", data, 8)[0]
    cp: list[Any] = [None] * cp_count
    off = 10
    i = 1
    while i < cp_count:
        tag, off = _u1(data, off)
        if tag == 1:
            ln, off = _u2(data, off)
            raw = data[off:off + ln]
            off += ln
            cp[i] = (tag, raw.decode("utf-8", errors="replace"))
        elif tag in {3, 4}:
            off += 4
            cp[i] = (tag, None)
        elif tag in {5, 6}:
            off += 8
            cp[i] = (tag, None)
            i += 1
        elif tag in {7, 8, 16, 19, 20}:
            idx, off = _u2(data, off)
            cp[i] = (tag, idx)
        elif tag in {9, 10, 11, 12, 17, 18}:
            a, off = _u2(data, off)
            b, off = _u2(data, off)
            cp[i] = (tag, a, b)
        elif tag == 15:
            kind, off = _u1(data, off)
            ref, off = _u2(data, off)
            cp[i] = (tag, kind, ref)
        else:
            raise ValueError(f"unknown constant-pool tag {tag} in {path}")
        i += 1

    def utf8(idx: int) -> str:
        item = cp[idx]
        if not item or item[0] != 1:
            raise ValueError(f"bad Utf8 cp index {idx} in {path}")
        return item[1]

    def class_name(idx: int) -> str:
        if not idx:
            return ""
        item = cp[idx]
        if not item or item[0] != 7:
            raise ValueError(f"bad Class cp index {idx} in {path}")
        return utf8(item[1])

    access, off = _u2(data, off)
    this_idx, off = _u2(data, off)
    super_idx, off = _u2(data, off)
    interface_count, off = _u2(data, off)
    interfaces = []
    for _ in range(interface_count):
        idx, off = _u2(data, off)
        interfaces.append(class_name(idx))

    def skip_attributes(pos: int, count: int) -> int:
        for _ in range(count):
            _name_idx, pos = _u2(data, pos)
            ln, pos = _u4(data, pos)
            pos += ln
        return pos

    def members(pos: int) -> tuple[list[dict[str, Any]], int]:
        count, pos = _u2(data, pos)
        out = []
        for _ in range(count):
            flags, pos = _u2(data, pos)
            name_idx, pos = _u2(data, pos)
            desc_idx, pos = _u2(data, pos)
            attr_count, pos = _u2(data, pos)
            out.append({"name": utf8(name_idx), "descriptor": utf8(desc_idx), "access": flags})
            pos = skip_attributes(pos, attr_count)
        return out, pos

    fields, off = members(off)
    methods, off = members(off)

    # Parse class-level BootstrapMethods so invokedynamic/LambdaMetafactory call sites can be
    # validated by exact SAM owner/name/descriptor instead of disappearing behind the JVM bootstrap.
    bootstrap_methods = []
    attr_count, off = _u2(data, off)
    for _ in range(attr_count):
        name_idx, off = _u2(data, off)
        ln, off = _u4(data, off)
        end = off + ln
        try:
            attr_name = utf8(name_idx)
        except Exception:
            attr_name = ""
        if attr_name == "BootstrapMethods":
            pos = off
            count, pos = _u2(data, pos)
            for _bm in range(count):
                method_ref, pos = _u2(data, pos)
                argc, pos = _u2(data, pos)
                args = []
                for _arg in range(argc):
                    idx, pos = _u2(data, pos)
                    args.append(idx)
                bootstrap_methods.append({"method_ref": method_ref, "arguments": args})
        off = end

    def decode_member_ref_index(idx: int) -> dict[str, Any] | None:
        try:
            item = cp[idx]
            if not item or item[0] not in {9, 10, 11}:
                return None
            owner_name = class_name(item[1])
            nt = cp[item[2]]
            if not nt or nt[0] != 12:
                return None
            return {
                "kind": "field" if item[0] == 9 else "method",
                "interface": item[0] == 11,
                "owner": owner_name,
                "name": utf8(nt[1]),
                "descriptor": utf8(nt[2]),
            }
        except Exception:
            return None

    def decode_method_handle_index(idx: int) -> dict[str, Any] | None:
        try:
            item = cp[idx]
            if not item or item[0] != 15:
                return None
            ref = decode_member_ref_index(item[2])
            return {"reference_kind": item[1], **ref} if ref else None
        except Exception:
            return None

    def decode_method_type_index(idx: int) -> str | None:
        try:
            item = cp[idx]
            return utf8(item[1]) if item and item[0] == 16 else None
        except Exception:
            return None

    def return_object_type(desc: str) -> str | None:
        if ")" not in desc:
            return None
        ret = desc.rsplit(")", 1)[1]
        while ret.startswith("["):
            ret = ret[1:]
        return ret[1:-1] if ret.startswith("L") and ret.endswith(";") else None

    refs = []
    indy_refs = []
    class_refs = set()
    for item in cp[1:]:
        if not item:
            continue
        tag = item[0]
        if tag == 7:
            try:
                class_refs.add(utf8(item[1]))
            except Exception:
                pass
        elif tag in {9, 10, 11}:
            try:
                owner_name = class_name(item[1])
                nt = cp[item[2]]
                if not nt or nt[0] != 12:
                    continue
                refs.append({
                    "kind": "field" if tag == 9 else "method",
                    "interface": tag == 11,
                    "owner": owner_name,
                    "name": utf8(nt[1]),
                    "descriptor": utf8(nt[2]),
                })
            except Exception:
                continue

    # Decode LambdaMetafactory invokedynamic sites. These are a real production-linkage hazard:
    # ordinary member remapping does not prove the SAM name that the JVM will invoke.
    for item in cp[1:]:
        if not item or item[0] != 18:
            continue
        try:
            bsm_idx, nt_idx = item[1], item[2]
            if bsm_idx >= len(bootstrap_methods):
                continue
            nt = cp[nt_idx]
            if not nt or nt[0] != 12:
                continue
            call_name = utf8(nt[1])
            call_desc = utf8(nt[2])
            bm = bootstrap_methods[bsm_idx]
            bootstrap_handle = decode_method_handle_index(bm["method_ref"])
            if not bootstrap_handle:
                continue
            args = bm.get("arguments") or []
            sam_desc = decode_method_type_index(args[0]) if len(args) > 0 else None
            impl = decode_method_handle_index(args[1]) if len(args) > 1 else None
            instantiated_desc = decode_method_type_index(args[2]) if len(args) > 2 else None
            fi_owner = return_object_type(call_desc)
            row = {
                "bootstrap_owner": bootstrap_handle.get("owner"),
                "bootstrap_name": bootstrap_handle.get("name"),
                "bootstrap_descriptor": bootstrap_handle.get("descriptor"),
                "call_site_name": call_name,
                "call_site_descriptor": call_desc,
                "functional_interface": fi_owner,
                "sam_name": call_name,
                "sam_descriptor": sam_desc,
                "instantiated_descriptor": instantiated_desc,
                "implementation": impl,
            }
            if bootstrap_handle.get("owner") == "java/lang/invoke/LambdaMetafactory":
                row["kind"] = "lambda_metafactory"
            else:
                row["kind"] = "invokedynamic"
            indy_refs.append(row)
        except Exception:
            continue

    owner = class_name(this_idx)
    return {
        "path": path,
        "major": major,
        "minor": minor,
        "access": access,
        "owner": owner,
        "super": class_name(super_idx),
        "interfaces": interfaces,
        "fields": sorted(fields, key=lambda x: (x["name"], x["descriptor"])),
        "methods": sorted(methods, key=lambda x: (x["name"], x["descriptor"])),
        "class_refs": sorted(class_refs),
        "member_refs": sorted(refs, key=lambda x: (x["owner"], x["kind"], x["name"], x["descriptor"])),
        "invokedynamic_refs": sorted(indy_refs, key=lambda x: (x.get("functional_interface") or "", x.get("sam_name") or "", x.get("sam_descriptor") or "")),
    }


def build_index(path: Path, include_refs: bool = False) -> dict[str, Any]:
    bundle = Bundle(path)
    try:
        classes: dict[str, Any] = {}
        failures = []
        nested_archives = []

        def add_class(raw: bytes, display_path: str) -> None:
            try:
                cls = parse_class(raw, display_path)
                if not include_refs:
                    cls.pop("class_refs", None)
                    cls.pop("member_refs", None)
                    cls.pop("invokedynamic_refs", None)
                classes[cls["owner"]] = cls
            except Exception as exc:
                failures.append({"path": display_path, "error": str(exc)})

        names = bundle.names()
        for name in names:
            if name.endswith(".class"):
                add_class(bundle.read(name), name)

        # Mojang's modern server distribution is a bundler JAR. Index its embedded version JAR
        # automatically so callers can point this tool at the official server.jar directly.
        for name in names:
            if not (name.startswith("META-INF/versions/") and name.endswith(".jar")):
                continue
            try:
                raw = bundle.read(name)
                with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                    nested_count = 0
                    for inner in zf.namelist():
                        if inner.endswith(".class"):
                            add_class(zf.read(inner), f"{name}!/{inner}")
                            nested_count += 1
                nested_archives.append({"path": name, "class_count": nested_count})
            except Exception as exc:
                failures.append({"path": name, "error": f"nested JAR index failed: {exc}"})

        return {
            "schema_version": 1,
            "input": str(path.resolve()),
            "class_count": len(classes),
            "classes": dict(sorted(classes.items())),
            "nested_archives": nested_archives,
            "failures": failures[:100],
        }
    finally:
        bundle.close()


def _member_matches(cls: dict[str, Any], kind: str, name: str, descriptor: str | None) -> list[dict[str, Any]]:
    rows = cls["fields" if kind == "field" else "methods"]
    return [x for x in rows if x["name"] == name and (descriptor is None or x["descriptor"] == descriptor)]


def resolve_member(index: dict[str, Any], owner: str, kind: str, name: str, descriptor: str | None = None) -> dict[str, Any]:
    owner = owner.replace(".", "/")
    if kind not in {"field", "method"}:
        raise ValueError("kind must be field or method")
    classes = index.get("classes") or {}
    if owner not in classes:
        return {"status": "OWNER_MISSING", "owner": owner, "kind": kind, "name": name, "descriptor": descriptor, "candidates": []}

    queue = deque([(owner, 0)])
    seen = set()
    hits = []
    while queue:
        cur, depth = queue.popleft()
        if cur in seen or cur not in classes:
            continue
        seen.add(cur)
        cls = classes[cur]
        matches = _member_matches(cls, kind, name, descriptor)
        for item in matches:
            hits.append({"declaring_owner": cur, "depth": depth, **item})
        # Exact declaration on nearest owner wins, but collect all same-depth interface ambiguity.
        if hits and depth > hits[0]["depth"]:
            break
        parents = []
        if cls.get("super"):
            parents.append(cls["super"])
        parents.extend(cls.get("interfaces") or [])
        for p in parents:
            queue.append((p, depth + 1))

    if not hits:
        # Name-only diagnostic candidates are useful when a descriptor drifted.
        near = []
        queue = deque([(owner, 0)])
        seen.clear()
        while queue:
            cur, depth = queue.popleft()
            if cur in seen or cur not in classes or depth > 8:
                continue
            seen.add(cur)
            cls = classes[cur]
            for item in _member_matches(cls, kind, name, None):
                near.append({"declaring_owner": cur, "depth": depth, **item})
            if cls.get("super"):
                queue.append((cls["super"], depth + 1))
            for p in cls.get("interfaces") or []:
                queue.append((p, depth + 1))
        return {"status": "MEMBER_MISSING", "owner": owner, "kind": kind, "name": name, "descriptor": descriptor, "candidates": near[:50]}

    if descriptor is None and len(hits) > 1:
        return {"status": "AMBIGUOUS", "owner": owner, "kind": kind, "name": name, "descriptor": None, "candidates": hits}
    return {"status": "RESOLVED", "owner": owner, "kind": kind, "name": name, "descriptor": descriptor, "candidates": hits}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    ix = sub.add_parser("index")
    ix.add_argument("input", type=Path)
    ix.add_argument("--include-refs", action="store_true")
    ix.add_argument("--out", type=Path)
    q = sub.add_parser("query")
    q.add_argument("index", type=Path)
    q.add_argument("--owner", required=True)
    q.add_argument("--kind", choices=["field", "method"], required=True)
    q.add_argument("--name", required=True)
    q.add_argument("--descriptor")
    args = ap.parse_args()

    if args.cmd == "index":
        result = build_index(args.input, args.include_refs)
        if args.out:
            write_json(args.out, result)
        else:
            print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if not result["failures"] else 2
    data = json.loads(args.index.read_text(encoding="utf-8"))
    result = resolve_member(data, args.owner, args.kind, args.name, args.descriptor)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "RESOLVED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
