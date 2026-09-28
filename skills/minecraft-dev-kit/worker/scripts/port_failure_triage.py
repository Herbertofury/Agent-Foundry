#!/usr/bin/env python3
"""Classify Minecraft 26.3 port build/runtime failures into actionable repair families.

Consumes Gradle/javac/Mixin/loader/runtime logs and emits deterministic root-cause candidates,
next tools, and the narrowest QA lane to rerun after repair. It does not mutate source.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

RULES = [
    {
        "id": "javac-cannot-find-symbol",
        "phase": "compile",
        "severity": "blocker",
        "rx": r"cannot find symbol(?:.|\n){0,450}?symbol:\s+(?:class|method|variable)\s+([^\n]+)",
        "cause": "The source still names an API/member/type that is absent from the 26.3 compile graph. This can be a mapping rename, semantic API removal, wrong owner, or missing dependency.",
        "next": ["mapping_lineage.py", "port_semantic_planner.py", "classfile_symbol_index.py"],
        "qa": ["compile"]
    },
    {
        "id": "javac-package-missing",
        "phase": "compile",
        "severity": "blocker",
        "rx": r"package\s+([\w.]+)\s+does not exist",
        "cause": "A package owner moved/vanished or a dependency is absent. Loader package drift and Fabric/NeoForge API changes are common during 26.3 ports.",
        "next": ["port_semantic_planner.py", "dependency metadata/build graph"],
        "qa": ["gradle-sync", "compile"]
    },
    {
        "id": "javac-override-signature-drift",
        "phase": "compile",
        "severity": "blocker",
        "rx": r"method does not override or implement a method from a supertype|name clash:|is not abstract and does not override abstract method",
        "cause": "An inherited method/interface contract changed owner, name, descriptor, generic signature, or return type.",
        "next": ["classfile_symbol_index.py", "mapping_lineage.py"],
        "qa": ["compile", "runtime-behavior"]
    },
    {
        "id": "binary-nosuchmethod",
        "phase": "linkage",
        "severity": "blocker",
        "rx": r"(?:java\.lang\.)?NoSuchMethodError:\s*([^\n]+)",
        "cause": "Packaged bytecode linked to the wrong owner/name/descriptor or incompatible dependency version.",
        "next": ["classfile_symbol_index.py", "packaged linkage audit", "dependency graph"],
        "qa": ["packaged-linkage", "native-runtime"]
    },
    {
        "id": "binary-nosuchfield",
        "phase": "linkage",
        "severity": "blocker",
        "rx": r"(?:java\.lang\.)?NoSuchFieldError:\s*([^\n]+)",
        "cause": "Packaged bytecode references a field that moved/renamed/changed descriptor or exists only in a different dependency line.",
        "next": ["classfile_symbol_index.py", "mapping_lineage.py"],
        "qa": ["packaged-linkage", "native-runtime"]
    },
    {
        "id": "binary-abstractmethod",
        "phase": "linkage",
        "severity": "blocker",
        "rx": r"(?:java\.lang\.)?AbstractMethodError:\s*([^\n]+)",
        "cause": "An interface/SAM/override descriptor or invokedynamic lambda target no longer matches production runtime semantics.",
        "next": ["classfile_symbol_index.py", "invokedynamic/SAM production audit"],
        "qa": ["packaged-linkage", "native-runtime"]
    },
    {
        "id": "missing-class-linkage",
        "phase": "linkage",
        "severity": "blocker",
        "rx": r"(?:ClassNotFoundException|NoClassDefFoundError):\s*([^\n]+)",
        "cause": "A required class is absent at linkage time. For optional integrations this often means the optional type leaked into descriptors/signatures before guards can run.",
        "next": ["dependency graph", "optional linkage audit", "classfile_symbol_index.py"],
        "qa": ["provider-present", "provider-absent", "packaged-linkage"]
    },
    {
        "id": "mixin-target-missing",
        "phase": "mixin-prepare",
        "severity": "blocker",
        "rx": r"Mixin target ([\w.$/]+) was not found|@Mixin target ([\w.$/]+) was not found",
        "cause": "The Mixin target owner no longer exists under that 26.3 official name or the wrong environment/version is loaded.",
        "next": ["mixin_surface_audit.py", "classfile_symbol_index.py", "mapping_lineage.py"],
        "qa": ["mixin-prepare-apply", "native-runtime"]
    },
    {
        "id": "mixin-injection-failure",
        "phase": "mixin-apply",
        "severity": "blocker",
        "rx": r"(?:Critical injection failure|InjectionError|InvalidInjectionException|No candidates were found matching|could not find any targets matching)[^\n]*",
        "cause": "The owner/member/descriptor may map, but the bytecode shape/injection point/ordinal/slice/locals changed. Do not solve this by weakening require/expect without behavior proof.",
        "next": ["mixin exact target resolver", "target bytecode inspection", "native runtime"],
        "qa": ["mixin-prepare-apply", "affected-behavior"]
    },
    {
        "id": "mixin-refmap-problem",
        "phase": "mixin-prepare",
        "severity": "high",
        "rx": r"(?:No refMap loaded|Reference map .* could not be read|refmap.*(?:missing|not found))",
        "cause": "A historical remap artifact/refmap leaked into the unobfuscated 26.3 path or the Mixin build configuration is incomplete.",
        "next": ["mixin_surface_audit.py", "build configuration"],
        "qa": ["mixin-prepare-apply"]
    },
    {
        "id": "registry-missing-entry",
        "phase": "data-registry",
        "severity": "blocker",
        "rx": r"(?:Unknown registry key|Unknown element|Missing referenced registry entry|Unbound values in registry|Registry .* contains no key)[^\n]*",
        "cause": "A data/resource registry path/key/provider moved or was not generated/loaded for 26.3.",
        "next": ["port_semantic_planner.py", "datagen diff", "registry inventory"],
        "qa": ["datagen", "server", "restart"]
    },
    {
        "id": "codec-data-failure",
        "phase": "data-registry",
        "severity": "blocker",
        "rx": r"(?:com\.mojang\.serialization|Codec|DataResult)[^\n]*(?:error|failed|missing|unknown|invalid)[^\n]*",
        "cause": "The 26.3 data schema/codec shape differs from the source resource. Translate semantics instead of deleting the data file.",
        "next": ["port_semantic_planner.py", "datagen diff"],
        "qa": ["datagen", "server", "world-load"]
    },
    {
        "id": "unsupported-class-version",
        "phase": "toolchain",
        "severity": "blocker",
        "rx": r"UnsupportedClassVersionError|class file has wrong version|invalid source release:\s*25",
        "cause": "The build/runtime is not actually using the required Java 25 toolchain or a dependency was compiled for an incompatible Java level.",
        "next": ["toolchain lock", "java -version", "Gradle toolchain diagnostics"],
        "qa": ["build"]
    },
    {
        "id": "duplicate-mod-id",
        "phase": "loader",
        "severity": "blocker",
        "rx": r"(?:Duplicate Mods|duplicate mod id|Found duplicate mods)[^\n]*",
        "cause": "Two artifacts provide the same mod identity, commonly from stale source + target jars or bundled dependencies.",
        "next": ["runtime mods inventory"],
        "qa": ["loader-start"]
    }
]


def triage(text: str) -> dict:
    findings = []
    for rule in RULES:
        rx = re.compile(rule["rx"], re.IGNORECASE | re.MULTILINE | re.DOTALL)
        matches = []
        for m in rx.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            snippet = m.group(0).replace("\n", " ")[:700]
            captures = [g for g in m.groups() if g]
            matches.append({"line": line, "snippet": snippet, "captures": captures})
            if len(matches) >= 20:
                break
        if matches:
            findings.append({k: v for k, v in rule.items() if k != "rx"} | {"evidence": matches})
    phase_order = {"toolchain": 0, "loader": 1, "compile": 2, "linkage": 3, "mixin-prepare": 4, "mixin-apply": 5, "data-registry": 6}
    sev_order = {"blocker": 0, "high": 1, "medium": 2}
    findings.sort(key=lambda x: (phase_order.get(x["phase"], 99), sev_order.get(x["severity"], 99), x["id"]))
    earliest = findings[0] if findings else None
    return {
        "schema_version": 1,
        "status": "FAILURE_CLASSIFIED" if findings else "NO_KNOWN_SIGNATURE",
        "finding_count": len(findings),
        "counts": {"phase": dict(Counter(x["phase"] for x in findings)), "severity": dict(Counter(x["severity"] for x in findings))},
        "earliest_probable_cause": earliest,
        "findings": findings,
        "rule": "Repair the earliest causal failure first. Do not shotgun-edit later cascades until the earlier phase is green.",
    }


def render_md(result: dict) -> str:
    lines = ["# Minecraft 26.3 Failure Triage", "", f"Status: **{result['status']}**", ""]
    if not result["findings"]:
        lines += ["No known deterministic signature matched. Inspect the first exception/root cause and extend the triage catalog rather than guessing.", ""]
        return "\n".join(lines)
    first = result["earliest_probable_cause"]
    lines += ["## Earliest probable cause", "", f"**{first['id']}** — {first['cause']}", "", f"Next: `{', '.join(first['next'])}`", ""]
    lines += ["## All findings", ""]
    for f in result["findings"]:
        lines.append(f"- **{f['id']}** [{f['phase']}/{f['severity']}] — {f['cause']}")
        for ev in f["evidence"][:4]:
            lines.append(f"  - line {ev['line']}: `{ev['snippet'][:300]}`")
    lines += ["", "## Repair order", "", result["rule"], ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("log", type=Path)
    ap.add_argument("--json-out", type=Path)
    ap.add_argument("--md-out", type=Path)
    args = ap.parse_args()
    text = args.log.read_text(encoding="utf-8", errors="replace")
    result = triage(text)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        args.md_out.write_text(render_md(result), encoding="utf-8")
    if not args.json_out and not args.md_out:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["findings"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
