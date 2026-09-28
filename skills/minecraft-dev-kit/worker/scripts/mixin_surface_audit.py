#!/usr/bin/env python3
"""Audit Mixin/remap/class-tweaker/access-transformer/reflection surfaces before a Minecraft 26.3 port.

This is a conservative migration audit. It does not claim a Mixin is valid merely because the
selector parses; final proof still requires target bytecode + real Mixin PREPARE/APPLY/runtime QA.
"""
from __future__ import annotations

import argparse
import json
import re
import struct
from collections import Counter
from pathlib import Path

from port_26_3_common import Bundle, collect_text, md_escape, write_json

SOURCE_EXTS = (".java", ".kt", ".kts", ".groovy")
MIXIN_ANNOTATIONS = (
    "Mixin", "Shadow", "Accessor", "Invoker", "Overwrite", "Inject", "Redirect",
    "ModifyArg", "ModifyArgs", "ModifyVariable", "ModifyConstant", "ModifyExpressionValue",
    "ModifyReceiver", "ModifyReturnValue", "WrapOperation", "WrapMethod", "WrapWithCondition",
)
LEGACY_MEMBER_RX = re.compile(r"\b(?:func_\d+_[A-Za-z_]*|field_\d+_[A-Za-z_]*|m_\d+_|f_\d+_|method_\d+|field_\d+|class_\d+)\b")
INTERMEDIARY_RX = re.compile(r"\b(?:class|method|field)_\d+\b")
REFLECTION_RX = re.compile(r"\b(?:getDeclaredField|getDeclaredMethod|getField|getMethod|Class\.forName|MethodHandles\.lookup|findVirtual|findStatic|findSpecial|findGetter|findSetter)\b")


def line_no(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def class_utf8_constants(data: bytes) -> list[str]:
    """Extract CONSTANT_Utf8 values from a class file without executing or loading it."""
    if len(data) < 10 or data[:4] != b"\xca\xfe\xba\xbe":
        return []
    count = struct.unpack_from(">H", data, 8)[0]
    i = 10
    values: list[str] = []
    index = 1
    try:
        while index < count:
            tag = data[i]
            i += 1
            if tag == 1:  # Utf8
                ln = struct.unpack_from(">H", data, i)[0]
                i += 2
                raw = data[i:i + ln]
                i += ln
                values.append(raw.decode("utf-8", errors="replace"))
            elif tag in {3, 4}:  # int/float
                i += 4
            elif tag in {5, 6}:  # long/double, consumes 2 cp slots
                i += 8
                index += 1
            elif tag in {7, 8, 16, 19, 20}:
                i += 2
            elif tag in {9, 10, 11, 12, 17, 18}:
                i += 4
            elif tag == 15:
                i += 3
            else:
                return values
            index += 1
    except (IndexError, struct.error):
        return values
    return values


def parse_mixin_configs(bundle: Bundle, names: list[str]) -> list[dict]:
    out = []
    for name in names:
        low = name.lower()
        if not low.endswith(".json") or not (low.endswith(".mixins.json") or "mixin" in Path(low).name):
            continue
        try:
            data = json.loads(bundle.read(name).decode("utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict) or not any(k in data for k in ("mixins", "client", "server", "package", "plugin", "refmap")):
            continue
        classes = []
        for key in ("mixins", "client", "server"):
            for item in data.get(key) or []:
                if isinstance(item, str):
                    classes.append({"environment": key, "class": item})
        out.append({
            "path": name,
            "package": data.get("package"),
            "required": data.get("required"),
            "min_version": data.get("minVersion"),
            "compatibility_level": data.get("compatibilityLevel"),
            "plugin": data.get("plugin"),
            "refmap": data.get("refmap"),
            "classes": classes,
        })
    return out


def parse_class_tweakers(text_files: dict[str, str]) -> list[dict]:
    out = []
    for name, text in text_files.items():
        low = name.lower()
        if not low.endswith((".accesswidener", ".classtweaker")):
            continue
        lines = [(idx + 1, raw.strip()) for idx, raw in enumerate(text.splitlines()) if raw.strip() and not raw.lstrip().startswith("#")]
        if not lines:
            out.append({"path": name, "header": None, "namespace": None, "entries": 0})
            continue
        header = lines[0][1]
        m = re.match(r"^(accessWidener|classTweaker)\s+v(\d+)\s+(\S+)", header)
        out.append({
            "path": name,
            "header": header,
            "kind": m.group(1) if m else None,
            "version": int(m.group(2)) if m else None,
            "namespace": m.group(3) if m else None,
            "entries": max(0, len(lines) - 1),
            "legacy_symbols": sorted(set(LEGACY_MEMBER_RX.findall(text)))[:50],
        })
    return out


def parse_access_transformers(text_files: dict[str, str]) -> list[dict]:
    out = []
    for name, text in text_files.items():
        if not name.lower().endswith("accesstransformer.cfg"):
            continue
        entries = []
        for idx, raw in enumerate(text.splitlines(), 1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            entries.append({"line": idx, "text": line, "legacy_symbols": LEGACY_MEMBER_RX.findall(line)})
        out.append({"path": name, "entries": entries[:500], "entry_count": len(entries)})
    return out


def source_surfaces(text_files: dict[str, str]) -> tuple[list[dict], list[dict], list[dict]]:
    surfaces, warnings, blockers = [], [], []
    annotation_rx = re.compile(r"@("
        + "|".join(re.escape(x) for x in MIXIN_ANNOTATIONS)
        + r")\b(?:\s*\((.*?)\))?", re.DOTALL)
    selector_rx = re.compile(r"\b(?:method|target)\s*=\s*(?:\{\s*)?\"([^\"]+)\"")
    for name, text in text_files.items():
        if not name.lower().endswith(SOURCE_EXTS):
            continue
        anns = []
        for m in annotation_rx.finditer(text):
            ann = m.group(1)
            body = (m.group(2) or "").strip()
            item = {"annotation": ann, "line": line_no(text, m.start()), "body": body[:1000]}
            anns.append(item)
            if ann == "Overwrite":
                warnings.append({"id": "mixin-overwrite", "path": name, "line": item["line"], "message": "@Overwrite is a high-collision port surface; prove target semantics and competing Mixins."})
            if "remap = false" in body or "remap=false" in body:
                warnings.append({"id": "mixin-remap-false", "path": name, "line": item["line"], "message": "remap=false bypasses mapping assistance; verify the target is intentionally stable/non-Minecraft in 26.3."})
            if "LocalCapture" in body:
                warnings.append({"id": "mixin-local-capture", "path": name, "line": item["line"], "message": "local capture is bytecode-layout sensitive; regenerate/verify locals against the exact 26.3 target method."})
        selectors = []
        for m in selector_rx.finditer(text):
            selector = m.group(1)
            row = {"selector": selector, "line": line_no(text, m.start()), "has_descriptor": "(" in selector}
            selectors.append(row)
            legacy = LEGACY_MEMBER_RX.findall(selector)
            if legacy:
                blockers.append({"id": "legacy-mixin-selector", "path": name, "line": row["line"], "message": f"Mixin selector still contains historical mapped symbol(s): {', '.join(sorted(set(legacy)))}"})
            elif not row["has_descriptor"]:
                warnings.append({"id": "descriptorless-mixin-selector", "path": name, "line": row["line"], "message": f"Descriptorless selector {selector!r} is overload/version-drift sensitive; resolve exact owner+descriptor for 26.3."})
        legacy_symbols = sorted(set(LEGACY_MEMBER_RX.findall(text)))
        if legacy_symbols:
            # This may be source mapping residue outside Mixins too; 26.3 target source must be official/unobfuscated.
            blockers.append({"id": "legacy-mapped-symbols", "path": name, "line": None, "message": "Source contains SRG/Intermediary-style Minecraft symbol(s) incompatible with a finished official-name 26.3 target: " + ", ".join(legacy_symbols[:12])})
        reflection = []
        for m in REFLECTION_RX.finditer(text):
            reflection.append({"token": m.group(0), "line": line_no(text, m.start())})
        if reflection:
            warnings.append({"id": "reflection-remap-surface", "path": name, "line": reflection[0]["line"], "message": "Reflection/method-handle lookup strings are outside ordinary remapping; inventory aliases and runtime-test the exact path."})
        if anns or selectors or reflection or legacy_symbols:
            surfaces.append({"path": name, "annotations": anns, "selectors": selectors, "reflection": reflection, "legacy_symbols": legacy_symbols[:100]})
    return surfaces, warnings, blockers


def compiled_surfaces(bundle: Bundle, names: list[str]) -> tuple[list[dict], list[dict]]:
    surfaces, blockers = [], []
    mixin_markers = {
        "Lorg/spongepowered/asm/mixin/Mixin;", "Lorg/spongepowered/asm/mixin/Shadow;",
        "Lorg/spongepowered/asm/mixin/injection/Inject;", "Lorg/spongepowered/asm/mixin/injection/Redirect;",
    }
    for name in names:
        if not name.endswith(".class"):
            continue
        try:
            constants = class_utf8_constants(bundle.read(name))
        except Exception:
            continue
        if not any(x in mixin_markers for x in constants):
            continue
        legacy = sorted({m.group(0) for s in constants for m in LEGACY_MEMBER_RX.finditer(s)})
        suspicious_targets = [s for s in constants if ("net/minecraft/" in s or "net.minecraft." in s) and len(s) < 500]
        surfaces.append({"path": name, "legacy_symbols": legacy[:100], "minecraft_strings": suspicious_targets[:100]})
        if legacy:
            blockers.append({"id": "compiled-legacy-mixin-symbols", "path": name, "line": None, "message": "Compiled Mixin constant pool contains legacy mapped symbol(s): " + ", ".join(legacy[:12])})
    return surfaces, blockers


def refmap_surfaces(bundle: Bundle, names: list[str]) -> list[dict]:
    out = []
    for name in names:
        low = name.lower()
        if not low.endswith(".json") or "refmap" not in low:
            continue
        try:
            data = json.loads(bundle.read(name).decode("utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        mappings = data.get("mappings") or {}
        data_sections = data.get("data") or {}
        out.append({"path": name, "mixin_entries": len(mappings), "data_namespaces": sorted(data_sections.keys()) if isinstance(data_sections, dict) else []})
    return out


def audit(path: Path, target_minecraft: str = "26.3", target_loader: str | None = None) -> dict:
    bundle = Bundle(path)
    try:
        names = bundle.names()
        text_files = collect_text(bundle, names)
        configs = parse_mixin_configs(bundle, names)
        tweakers = parse_class_tweakers(text_files)
        ats = parse_access_transformers(text_files)
        src, warnings, blockers = source_surfaces(text_files)
        compiled, compiled_blockers = compiled_surfaces(bundle, names)
        blockers.extend(compiled_blockers)
        refs = refmap_surfaces(bundle, names)

        if target_minecraft == "26.3" and target_loader == "fabric":
            for tw in tweakers:
                ns = tw.get("namespace")
                if not ns:
                    blockers.append({"id": "invalid-class-tweaker-header", "path": tw["path"], "line": 1, "message": "Class tweaker/access widener header could not be parsed."})
                elif ns != "official":
                    blockers.append({"id": "fabric-26.3-class-tweaker-namespace", "path": tw["path"], "line": 1, "message": f"26.3 is unobfuscated; class tweaker namespace must be official, found {ns!r}."})
                if tw.get("kind") == "accessWidener":
                    warnings.append({"id": "legacy-access-widener-header", "path": tw["path"], "line": 1, "message": "Fabric 26.1+ calls this class tweaking; preserve compatibility only if Loom validates it, otherwise migrate header/file format deliberately."})

        if target_minecraft == "26.3" and target_loader in {"neoforge", "forge"}:
            for at in ats:
                bad = [e for e in at["entries"] if e["legacy_symbols"]]
                if bad:
                    blockers.append({"id": "legacy-access-transformer-symbols", "path": at["path"], "line": bad[0]["line"], "message": "Access Transformer still contains historical SRG/intermediary-style member names; 26.3 target ATs need current official owners/members/descriptors."})

        # Config-level migration notes.
        for cfg in configs:
            if cfg.get("refmap"):
                warnings.append({"id": "mixin-refmap-present", "path": cfg["path"], "line": None, "message": f"Mixin config declares refmap {cfg['refmap']!r}; verify whether target-unobfuscated 26.3 still requires/generated it and reject stale source-namespace entries."})
            level = str(cfg.get("compatibility_level") or "")
            if level and level not in {"JAVA_25", "25"}:
                warnings.append({"id": "mixin-compatibility-level", "path": cfg["path"], "line": None, "message": f"Mixin compatibilityLevel is {level!r}; target runtime is Java 25, so validate actual classfile features/Mixin service compatibility."})

        counts = Counter(x["id"] for x in blockers + warnings)
        return {
            "schema_version": 1,
            "input": str(path.resolve()),
            "target": {"minecraft": target_minecraft, "loader": target_loader},
            "status": "FAIL" if blockers else "PASS_WITH_WARNINGS" if warnings else "PASS",
            "mixin_configs": configs,
            "source_mixin_surfaces": src,
            "compiled_mixin_surfaces": compiled,
            "class_tweakers": tweakers,
            "access_transformers": ats,
            "refmaps": refs,
            "blockers": blockers,
            "warnings": warnings,
            "counts": {
                "mixin_configs": len(configs),
                "source_mixin_files": len(src),
                "compiled_mixin_classes": len(compiled),
                "class_tweakers": len(tweakers),
                "access_transformers": len(ats),
                "refmaps": len(refs),
                "blockers": len(blockers),
                "warnings": len(warnings),
                "finding_ids": dict(counts),
            },
            "runtime_boundary": "Static selector/name checks do not prove Mixin correctness. Final target must resolve owner+member+descriptor and pass real Mixin PREPARE/APPLY plus relevant client/server runtime paths.",
        }
    finally:
        bundle.close()


def render_md(result: dict) -> str:
    lines = [
        "# Mixin / Remap Surface Audit",
        "",
        f"**Status: {result['status']}**",
        "",
        f"Input: `{result['input']}`",
        f"Target: `{result['target']['minecraft']}` / `{result['target'].get('loader') or 'unspecified loader'}`",
        "",
        "## Counts",
        "",
    ]
    for key, value in result["counts"].items():
        if key != "finding_ids":
            lines.append(f"- {key}: `{value}`")
    lines += ["", "## Blockers", ""]
    if not result["blockers"]:
        lines.append("None detected by the static audit.")
    else:
        for item in result["blockers"]:
            loc = item["path"] + (f":{item['line']}" if item.get("line") else "")
            lines.append(f"- **{item['id']}** `{md_escape(loc)}` — {item['message']}")
    lines += ["", "## Warnings / manual bytecode review surfaces", ""]
    if not result["warnings"]:
        lines.append("None.")
    else:
        for item in result["warnings"]:
            loc = item["path"] + (f":{item['line']}" if item.get("line") else "")
            lines.append(f"- **{item['id']}** `{md_escape(loc)}` — {item['message']}")
    lines += ["", "## Runtime boundary", "", result["runtime_boundary"], ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("--target-minecraft", default="26.3")
    ap.add_argument("--loader", choices=["forge", "neoforge", "fabric", "quilt"])
    ap.add_argument("--json-out", type=Path)
    ap.add_argument("--md-out", type=Path)
    ap.add_argument("--fail-on-blocker", action="store_true")
    args = ap.parse_args()
    result = audit(args.input, args.target_minecraft, args.loader)
    if args.json_out:
        write_json(args.json_out, result)
    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        args.md_out.write_text(render_md(result), encoding="utf-8")
    if not args.json_out and not args.md_out:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 3 if args.fail_on_blocker and result["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())