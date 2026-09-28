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

from port_26_3_common import Bundle, input_identity, write_json


ACC_PUBLIC = 0x0001
ACC_PRIVATE = 0x0002
ACC_PROTECTED = 0x0004
ACC_STATIC = 0x0008
ACC_FINAL = 0x0010
ACC_INTERFACE = 0x0200

MEMBER_OPCODES = {
    0xB2: "getstatic",
    0xB3: "putstatic",
    0xB4: "getfield",
    0xB5: "putfield",
    0xB6: "invokevirtual",
    0xB7: "invokespecial",
    0xB8: "invokestatic",
    0xB9: "invokeinterface",
}

# Operand byte counts for fixed-width JVM instructions. Opcodes not listed have no operands.
# tableswitch/lookupswitch/wide are handled separately because their widths are data-dependent.
FIXED_OPERANDS = {
    0x10: 1, 0x11: 2, 0x12: 1, 0x13: 2, 0x14: 2,
    0x15: 1, 0x16: 1, 0x17: 1, 0x18: 1, 0x19: 1,
    0x36: 1, 0x37: 1, 0x38: 1, 0x39: 1, 0x3A: 1,
    0x84: 2,
    0x99: 2, 0x9A: 2, 0x9B: 2, 0x9C: 2, 0x9D: 2, 0x9E: 2,
    0x9F: 2, 0xA0: 2, 0xA1: 2, 0xA2: 2, 0xA3: 2, 0xA4: 2,
    0xA5: 2, 0xA6: 2, 0xA7: 2, 0xA8: 2, 0xA9: 1,
    0xB2: 2, 0xB3: 2, 0xB4: 2, 0xB5: 2,
    0xB6: 2, 0xB7: 2, 0xB8: 2, 0xB9: 4, 0xBA: 4,
    0xBB: 2, 0xBC: 1, 0xBD: 2,
    0xC0: 2, 0xC1: 2, 0xC5: 3, 0xC6: 2, 0xC7: 2,
    0xC8: 4, 0xC9: 4,
}


def _scan_member_instructions(code: bytes, decode_member_ref) -> list[dict[str, Any]]:
    """Return exact field/method references used by JVM member instructions.

    Constant-pool presence alone is conservative and can include stale/unused entries. Walking the
    Code attribute records the invocation mode the JVM will actually execute, which lets release QA
    catch static/instance and class/interface drift that name+descriptor checks alone cannot see.
    """
    out: list[dict[str, Any]] = []
    pc = 0
    n = len(code)
    while pc < n:
        start = pc
        opcode = code[pc]
        pc += 1
        if opcode == 0xAA:  # tableswitch
            pad = (4 - (pc % 4)) % 4
            pos = pc + pad
            if pos + 12 > n:
                break
            low = struct.unpack_from(">i", code, pos + 4)[0]
            high = struct.unpack_from(">i", code, pos + 8)[0]
            count = max(0, high - low + 1)
            pc = pos + 12 + count * 4
            continue
        if opcode == 0xAB:  # lookupswitch
            pad = (4 - (pc % 4)) % 4
            pos = pc + pad
            if pos + 8 > n:
                break
            pairs = max(0, struct.unpack_from(">i", code, pos + 4)[0])
            pc = pos + 8 + pairs * 8
            continue
        if opcode == 0xC4:  # wide
            if pc >= n:
                break
            widened = code[pc]
            pc += 5 if widened == 0x84 else 3
            continue

        operand_count = FIXED_OPERANDS.get(opcode, 0)
        if pc + operand_count > n:
            break
        if opcode in MEMBER_OPCODES:
            cp_index = struct.unpack_from(">H", code, pc)[0]
            ref = decode_member_ref(cp_index)
            if ref:
                out.append({"pc": start, "opcode": opcode, "opcode_name": MEMBER_OPCODES[opcode], "cp_index": cp_index, **ref})
        pc += operand_count
    return out


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

    def members(pos: int, capture_code: bool = False) -> tuple[list[dict[str, Any]], int]:
        count, pos = _u2(data, pos)
        out = []
        for _ in range(count):
            flags, pos = _u2(data, pos)
            name_idx, pos = _u2(data, pos)
            desc_idx, pos = _u2(data, pos)
            attr_count, pos = _u2(data, pos)
            row: dict[str, Any] = {"name": utf8(name_idx), "descriptor": utf8(desc_idx), "access": flags}
            for _attr in range(attr_count):
                attr_name_idx, pos = _u2(data, pos)
                ln, pos = _u4(data, pos)
                end = pos + ln
                try:
                    attr_name = utf8(attr_name_idx)
                except Exception:
                    attr_name = ""
                if capture_code and attr_name == "Code":
                    p = pos
                    _max_stack, p = _u2(data, p)
                    _max_locals, p = _u2(data, p)
                    code_len, p = _u4(data, p)
                    if p + code_len <= end:
                        row["_code"] = data[p:p + code_len]
                pos = end
            out.append(row)
        return out, pos

    fields, off = members(off)
    methods, off = members(off, capture_code=True)

    # Parse class-level attributes needed for production-linkage proof. NestHost/NestMembers
    # matter for private-access legality on Java 11+, while BootstrapMethods exposes lambda and
    # method-handle linkage that ordinary constant-pool member scans cannot prove.
    bootstrap_methods = []
    nest_host = None
    nest_members: list[str] = []
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
        elif attr_name == "NestHost" and ln >= 2:
            idx, _ = _u2(data, off)
            nest_host = class_name(idx)
        elif attr_name == "NestMembers" and ln >= 2:
            pos = off
            count, pos = _u2(data, pos)
            for _nm in range(count):
                idx, pos = _u2(data, pos)
                nest_members.append(class_name(idx))
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
    bytecode_refs = []
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

    for method in methods:
        code = method.pop("_code", None)
        if not code:
            continue
        for ref in _scan_member_instructions(code, decode_member_ref_index):
            bytecode_refs.append({
                "caller_name": method["name"],
                "caller_descriptor": method["descriptor"],
                **ref,
            })

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
        "nest_host": nest_host,
        "nest_members": sorted(nest_members),
        "fields": sorted(fields, key=lambda x: (x["name"], x["descriptor"])),
        "methods": sorted(methods, key=lambda x: (x["name"], x["descriptor"])),
        "class_refs": sorted(class_refs),
        "member_refs": sorted(refs, key=lambda x: (x["owner"], x["kind"], x["name"], x["descriptor"])),
        "bytecode_member_refs": sorted(bytecode_refs, key=lambda x: (x["caller_name"], x["caller_descriptor"], x["pc"], x["owner"], x["name"])),
        "invokedynamic_refs": sorted(indy_refs, key=lambda x: (x.get("functional_interface") or "", x.get("sam_name") or "", x.get("sam_descriptor") or "")),
    }


def build_index(path: Path, include_refs: bool = False, runtime_java: int = 25) -> dict[str, Any]:
    bundle = Bundle(path)
    try:
        classes: dict[str, Any] = {}
        selected: dict[str, tuple[int, int]] = {}
        variants: dict[str, list[dict[str, Any]]] = {}
        failures = []
        nested_archives = []

        def add_class(raw: bytes, display_path: str, release: int = 0, priority: int = 20, source_kind: str = "root") -> bool:
            try:
                cls = parse_class(raw, display_path)
                if not include_refs:
                    cls.pop("class_refs", None)
                    cls.pop("member_refs", None)
                    cls.pop("bytecode_member_refs", None)
                    cls.pop("invokedynamic_refs", None)
                owner = cls["owner"]
                variants.setdefault(owner, []).append({
                    "path": display_path,
                    "release": release,
                    "priority": priority,
                    "source_kind": source_kind,
                    "major": cls.get("major"),
                })
                score = (priority, release)
                if owner not in selected or score > selected[owner]:
                    selected[owner] = score
                    cls["selected_release"] = release
                    cls["source_kind"] = source_kind
                    classes[owner] = cls
                    return True
                return False
            except Exception as exc:
                failures.append({"path": display_path, "error": str(exc)})
                return False

        def manifest_is_multi_release(names: list[str], reader) -> bool:
            manifest = next((n for n in names if n.upper() == "META-INF/MANIFEST.MF"), None)
            if not manifest:
                return False
            try:
                text = reader(manifest).decode("utf-8", errors="replace")
            except Exception:
                return False
            # Continuation lines are irrelevant for the short Multi-Release attribute.
            return any(line.strip().lower() == "multi-release: true" for line in text.splitlines())

        def mr_release(name: str) -> int | None:
            parts = name.split("/")
            if len(parts) >= 4 and parts[0] == "META-INF" and parts[1] == "versions" and parts[2].isdigit() and name.endswith(".class"):
                return int(parts[2])
            return None

        def nested_candidate(name: str) -> bool:
            low = name.lower()
            return low.endswith(".jar") and (
                low.startswith("meta-inf/versions/")
                or low.startswith("meta-inf/jarjar/")
                or low.startswith("meta-inf/jars/")
                or low.startswith("jars/")
            )

        def index_zip(raw: bytes, display_path: str, depth: int = 1) -> int:
            if depth > 2:
                return 0
            count = 0
            with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                inner_names = zf.namelist()
                is_mr = manifest_is_multi_release(inner_names, zf.read)
                for inner in inner_names:
                    if not inner.endswith(".class"):
                        continue
                    release = mr_release(inner)
                    if release is not None:
                        if not is_mr or release > runtime_java:
                            continue
                    else:
                        release = 0
                    if add_class(zf.read(inner), f"{display_path}!/{inner}", release=release, priority=10, source_kind="nested"):
                        count += 1
                for inner in inner_names:
                    if not nested_candidate(inner):
                        continue
                    try:
                        child_raw = zf.read(inner)
                        child_count = index_zip(child_raw, f"{display_path}!/{inner}", depth + 1)
                        nested_archives.append({"path": f"{display_path}!/{inner}", "class_count": child_count, "depth": depth + 1})
                    except Exception as exc:
                        failures.append({"path": f"{display_path}!/{inner}", "error": f"nested JAR index failed: {exc}"})
            return count

        names = bundle.names()
        top_is_mr = manifest_is_multi_release(names, bundle.read)
        for name in names:
            if name.endswith(".class"):
                release = mr_release(name)
                if release is not None:
                    if not top_is_mr or release > runtime_java:
                        continue
                else:
                    release = 0
                add_class(bundle.read(name), name, release=release, priority=20, source_kind="root")

        # Mojang's modern server distribution is a bundler JAR. Fabric/NeoForge can also ship
        # nested libraries. Index recognized nested-JAR locations without executing anything.
        for name in names:
            if not nested_candidate(name):
                continue
            try:
                raw = bundle.read(name)
                nested_count = index_zip(raw, name)
                nested_archives.append({"path": name, "class_count": nested_count, "depth": 1})
            except Exception as exc:
                failures.append({"path": name, "error": f"nested JAR index failed: {exc}"})

        duplicate_owners = []
        for owner, rows in sorted(variants.items()):
            if len(rows) <= 1:
                continue
            duplicate_owners.append({
                "owner": owner,
                "selected": classes[owner].get("path"),
                "variants": sorted(rows, key=lambda x: (x["priority"], x["release"], x["path"])),
            })

        return {
            "schema_version": 2,
            "input": str(path.resolve()),
            "input_identity": input_identity(path),
            "runtime_java": runtime_java,
            "multi_release": top_is_mr,
            "class_count": len(classes),
            "classes": dict(sorted(classes.items())),
            "nested_archives": nested_archives,
            "duplicate_owners": duplicate_owners[:500],
            "failures": failures[:100],
        }
    finally:
        bundle.close()


def _member_matches(cls: dict[str, Any], kind: str, name: str, descriptor: str | None) -> list[dict[str, Any]]:
    rows = cls["fields" if kind == "field" else "methods"]
    return [x for x in rows if x["name"] == name and (descriptor is None or x["descriptor"] == descriptor)]


def resolve_declared_member(index: dict[str, Any], owner: str, kind: str, name: str, descriptor: str | None = None) -> dict[str, Any]:
    """Resolve only a member declared directly on owner, without inherited fallback.

    Access wideners/class tweakers/ATs mutate a declaration. Treating an inherited member as a
    success can produce a static false-pass even though the transformer will not find that member
    on the named class at runtime.
    """
    owner = owner.replace(".", "/")
    if kind not in {"field", "method"}:
        raise ValueError("kind must be field or method")
    classes = index.get("classes") or {}
    if owner not in classes:
        return {"status": "OWNER_MISSING", "owner": owner, "kind": kind, "name": name, "descriptor": descriptor, "candidates": []}
    matches = _member_matches(classes[owner], kind, name, descriptor)
    if not matches:
        near = _member_matches(classes[owner], kind, name, None)
        return {"status": "MEMBER_MISSING", "owner": owner, "kind": kind, "name": name, "descriptor": descriptor, "candidates": [{"declaring_owner": owner, "depth": 0, **x} for x in near]}
    hits = [{"declaring_owner": owner, "depth": 0, **x} for x in matches]
    if descriptor is None and len(hits) > 1:
        return {"status": "AMBIGUOUS", "owner": owner, "kind": kind, "name": name, "descriptor": None, "candidates": hits}
    return {"status": "RESOLVED", "owner": owner, "kind": kind, "name": name, "descriptor": descriptor, "candidates": hits}


def is_subclass(index: dict[str, Any], child: str, parent: str) -> bool:
    """Return whether child inherits from/implements parent using the indexed hierarchy."""
    child = child.replace(".", "/")
    parent = parent.replace(".", "/")
    if child == parent:
        return True
    classes = index.get("classes") or {}
    queue = deque([child])
    seen: set[str] = set()
    while queue:
        cur = queue.popleft()
        if cur in seen or cur not in classes:
            continue
        seen.add(cur)
        cls = classes[cur]
        parents = ([cls.get("super")] if cls.get("super") else []) + list(cls.get("interfaces") or [])
        for candidate in parents:
            if candidate == parent:
                return True
            if candidate and candidate not in seen:
                queue.append(candidate)
    return False


def nest_host(index: dict[str, Any], owner: str) -> str:
    owner = owner.replace(".", "/")
    cls = (index.get("classes") or {}).get(owner) or {}
    return cls.get("nest_host") or owner


def resolve_member(index: dict[str, Any], owner: str, kind: str, name: str, descriptor: str | None = None) -> dict[str, Any]:
    owner = owner.replace(".", "/")
    if kind not in {"field", "method"}:
        raise ValueError("kind must be field or method")
    classes = index.get("classes") or {}
    if owner not in classes:
        return {"status": "OWNER_MISSING", "owner": owner, "kind": kind, "name": name, "descriptor": descriptor, "candidates": []}

    # Constructors are never inherited. Treating a superclass <init> as a valid match is a
    # dangerous static false pass: JVM invokespecial constructor resolution is owner-exact.
    if kind == "method" and name == "<init>":
        return resolve_declared_member(index, owner, kind, name, descriptor)

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
    ix.add_argument("--runtime-java", type=int, default=25, help="runtime Java used to select Multi-Release JAR classes (default: 25 for Minecraft 26.3)")
    ix.add_argument("--out", type=Path)
    q = sub.add_parser("query")
    q.add_argument("index", type=Path)
    q.add_argument("--owner", required=True)
    q.add_argument("--kind", choices=["field", "method"], required=True)
    q.add_argument("--name", required=True)
    q.add_argument("--descriptor")
    args = ap.parse_args()

    if args.cmd == "index":
        result = build_index(args.input, args.include_refs, runtime_java=args.runtime_java)
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