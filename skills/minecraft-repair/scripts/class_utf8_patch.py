#!/usr/bin/env python3
"""Patch proven UTF-8 constant-pool symbols in .class files inside a JAR.

This is intentionally narrow. It does not rewrite bytecode instructions or stack maps.
Use it only when a constant-pool owner/name/descriptor substitution is sufficient.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import zipfile
from pathlib import Path

U1 = struct.Struct(">B")
U2 = struct.Struct(">H")
U4 = struct.Struct(">I")

FIXED_TAG_BYTES = {
    3: 4,  # Integer
    4: 4,  # Float
    5: 8,  # Long
    6: 8,  # Double
    7: 2,  # Class
    8: 2,  # String
    9: 4,  # Fieldref
    10: 4, # Methodref
    11: 4, # InterfaceMethodref
    12: 4, # NameAndType
    15: 3, # MethodHandle
    16: 2, # MethodType
    17: 4, # Dynamic
    18: 4, # InvokeDynamic
    19: 2, # Module
    20: 2, # Package
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_replacements(items: list[str]) -> list[tuple[bytes, bytes, str, str]]:
    out = []
    for item in items:
        if "=" not in item:
            raise ValueError(f"replacement must be OLD=NEW: {item}")
        old, new = item.split("=", 1)
        if not old:
            raise ValueError("OLD cannot be empty")
        out.append((old.encode("utf-8"), new.encode("utf-8"), old, new))
    return out


def patch_class(data: bytes, replacements, require_all=False):
    if len(data) < 10 or data[:4] != b"\xca\xfe\xba\xbe":
        raise ValueError("not a class file")
    cp_count = U2.unpack_from(data, 8)[0]
    pos = 10
    out = bytearray(data[:10])
    cp_index = 1
    counts = {old_s: 0 for _, _, old_s, _ in replacements}
    changed_strings = []
    while cp_index < cp_count:
        if pos >= len(data):
            raise ValueError("truncated constant pool")
        tag = data[pos]
        out.append(tag)
        pos += 1
        if tag == 1:
            if pos + 2 > len(data):
                raise ValueError("truncated UTF8 length")
            length = U2.unpack_from(data, pos)[0]
            pos += 2
            payload = data[pos:pos + length]
            if len(payload) != length:
                raise ValueError("truncated UTF8 payload")
            new_payload = payload
            per_string = []
            for old_b, new_b, old_s, new_s in replacements:
                c = new_payload.count(old_b)
                if c:
                    new_payload = new_payload.replace(old_b, new_b)
                    counts[old_s] += c
                    per_string.append({"old": old_s, "new": new_s, "count": c})
            if len(new_payload) > 65535:
                raise ValueError("patched UTF8 constant exceeds class-file u2 length")
            out.extend(U2.pack(len(new_payload)))
            out.extend(new_payload)
            if per_string:
                changed_strings.append({"cp_index": cp_index, "replacements": per_string})
            pos += length
        elif tag in FIXED_TAG_BYTES:
            size = FIXED_TAG_BYTES[tag]
            if pos + size > len(data):
                raise ValueError(f"truncated constant tag {tag}")
            out.extend(data[pos:pos + size])
            pos += size
            if tag in (5, 6):
                cp_index += 1
        else:
            raise ValueError(f"unsupported constant-pool tag {tag} at index {cp_index}")
        cp_index += 1
    out.extend(data[pos:])
    if require_all:
        missing = [k for k, v in counts.items() if v == 0]
        if missing:
            raise ValueError(f"required replacement(s) not found in class: {missing}")
    return bytes(out), counts, changed_strings


def clone_info(info: zipfile.ZipInfo) -> zipfile.ZipInfo:
    ni = zipfile.ZipInfo(info.filename, date_time=info.date_time)
    ni.compress_type = info.compress_type
    ni.comment = info.comment
    ni.extra = info.extra
    ni.create_system = info.create_system
    ni.create_version = info.create_version
    ni.extract_version = info.extract_version
    ni.flag_bits = info.flag_bits
    ni.volume = info.volume
    ni.internal_attr = info.internal_attr
    ni.external_attr = info.external_attr
    return ni


def patch_jar(src: Path, dst: Path, replacements, class_regex: str | None, require_old: bool):
    rx = re.compile(class_regex) if class_regex else None
    report = {
        "source": str(src),
        "output": str(dst),
        "source_sha256": sha256_file(src),
        "changed_entries": [],
        "replacement_totals": {old_s: 0 for _, _, old_s, _ in replacements},
        "signature_files": [],
    }
    with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(dst, "w") as zout:
        bad = zin.testzip()
        if bad:
            raise ValueError(f"source JAR has corrupt entry: {bad}")
        for info in zin.infolist():
            data = zin.read(info)
            upper = info.filename.upper()
            if upper.startswith("META-INF/") and upper.endswith((".SF", ".RSA", ".DSA", ".EC")):
                report["signature_files"].append(info.filename)
            should_patch = info.filename.endswith(".class") and (rx is None or rx.search(info.filename))
            if should_patch:
                patched, counts, changed_strings = patch_class(data, replacements, require_all=False)
                if patched != data:
                    report["changed_entries"].append({
                        "entry": info.filename,
                        "before_sha256": hashlib.sha256(data).hexdigest(),
                        "after_sha256": hashlib.sha256(patched).hexdigest(),
                        "counts": counts,
                        "constant_pool_changes": changed_strings,
                    })
                    for k, v in counts.items():
                        report["replacement_totals"][k] += v
                    data = patched
            zout.writestr(clone_info(info), data)
    if require_old:
        missing = [k for k, v in report["replacement_totals"].items() if v == 0]
        if missing:
            dst.unlink(missing_ok=True)
            raise ValueError(f"required replacement(s) not found anywhere in selected classes: {missing}")
    with zipfile.ZipFile(dst, "r") as zf:
        bad = zf.testzip()
        if bad:
            raise ValueError(f"output JAR has corrupt entry: {bad}")
    report["output_sha256"] = sha256_file(dst)
    return report


def dry_run(src: Path, replacements, class_regex: str | None):
    rx = re.compile(class_regex) if class_regex else None
    report = {
        "source": str(src),
        "source_sha256": sha256_file(src),
        "candidate_entries": [],
        "replacement_totals": {old_s: 0 for _, _, old_s, _ in replacements},
        "signature_files": [],
    }
    with zipfile.ZipFile(src, "r") as zf:
        bad = zf.testzip()
        if bad:
            raise ValueError(f"source JAR has corrupt entry: {bad}")
        for info in zf.infolist():
            upper = info.filename.upper()
            if upper.startswith("META-INF/") and upper.endswith((".SF", ".RSA", ".DSA", ".EC")):
                report["signature_files"].append(info.filename)
            if not info.filename.endswith(".class") or (rx and not rx.search(info.filename)):
                continue
            data = zf.read(info)
            _, counts, changed_strings = patch_class(data, replacements)
            if any(counts.values()):
                report["candidate_entries"].append({"entry": info.filename, "counts": counts, "constant_pool_changes": changed_strings})
                for k, v in counts.items():
                    report["replacement_totals"][k] += v
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("jar", type=Path)
    ap.add_argument("--output", type=Path)
    ap.add_argument("--replace", action="append", required=True, help="OLD=NEW; may be repeated")
    ap.add_argument("--class-regex", help="Only consider class entry names matching this regex")
    ap.add_argument("--require-old", action="store_true", help="Fail if any OLD term is not found in selected classes")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--pretty", action="store_true")
    ap.add_argument("--report", type=Path)
    args = ap.parse_args()
    replacements = parse_replacements(args.replace)
    if args.dry_run:
        report = dry_run(args.jar, replacements, args.class_regex)
    else:
        if not args.output:
            ap.error("--output is required unless --dry-run is used")
        report = patch_jar(args.jar, args.output, replacements, args.class_regex, args.require_old)
    text = json.dumps(report, indent=2 if args.pretty else None, ensure_ascii=False)
    if args.report:
        args.report.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
