#!/usr/bin/env python3
"""Deterministic triage for Minecraft Java logs and crash reports."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

FATAL_PATTERNS = [
    ("class_not_found", re.compile(r"ClassNotFoundException:\s*([^\s]+)")),
    ("no_class_def", re.compile(r"NoClassDefFoundError:\s*([^\s]+)")),
    ("no_such_method", re.compile(r"NoSuchMethodError:\s*(.*)")),
    ("no_such_field", re.compile(r"NoSuchFieldError:\s*(.*)")),
    ("mixin_apply", re.compile(r"(?:MixinApplyError|MixinTransformerError|InvalidInjectionException|InjectionError)")),
    ("verify_error", re.compile(r"VerifyError|AnalyzerException|Insufficient maximum stack size")),
    ("mod_loading", re.compile(r"ModLoadingException|LoadingFailedException|Missing mandatory dependencies")),
    ("duplicate_mod", re.compile(r"DuplicateModsFoundException|duplicate mod", re.I)),
    ("unsupported_class", re.compile(r"UnsupportedClassVersionError")),
    ("exception_init", re.compile(r"ExceptionInInitializerError")),
    ("fatal", re.compile(r"\bFATAL\b")),
    ("error", re.compile(r"/(?:ERROR)\]")),
]

MOD_PATTERNS = [
    re.compile(r"Found mod file\s+(.+?\.jar)\s+of type"),
    re.compile(r"\[([^\]]+\.jar)(?:%\d+)?!/:?([^\]]*)\]"),
]

TRANSFORMER_MOD_RE = re.compile(r"TRANSFORMER/([A-Za-z0-9_.-]+)@([^/\s]+)/")
MODID_EVENT_RE = re.compile(r"(?:for modid|modid)\s+([A-Za-z0-9_.-]+)", re.I)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def detect_identity(lines: list[str]) -> dict:
    identity: dict[str, object] = {}
    for line in lines[:1200]:
        if "ModLauncher running: args" in line:
            m = re.search(r"--version,\s*([^,\]]+)", line)
            if m:
                identity["minecraft"] = m.group(1).strip()
            m = re.search(r"--launchTarget,\s*([^,\]]+)", line)
            if m:
                identity["launch_target"] = m.group(1).strip()
            m = re.search(r"--gameDir,\s*([^,\]]+)", line)
            if m:
                identity["game_dir"] = m.group(1).strip()
            m = re.search(r"--fml\.forgeVersion,\s*([^,\]]+)", line)
            if m:
                identity["loader"] = "Forge"
                identity["loader_version"] = m.group(1).strip()
        if "NeoForge" in line and "version" in line.lower() and "loader_version" not in identity:
            m = re.search(r"NeoForge[^0-9]*([0-9]+(?:\.[0-9A-Za-z+-]+)+)", line, re.I)
            if m:
                identity["loader"] = "NeoForge"
                identity["loader_version"] = m.group(1)
        if "Fabric Loader" in line:
            m = re.search(r"Fabric Loader\s+([0-9][^\s]*)", line)
            identity["loader"] = "Fabric"
            if m:
                identity["loader_version"] = m.group(1)
        if "Quilt Loader" in line:
            m = re.search(r"Quilt Loader\s+([0-9][^\s]*)", line)
            identity["loader"] = "Quilt"
            if m:
                identity["loader_version"] = m.group(1)
        if "java version" in line.lower():
            m = re.search(r"java version\s+([^\s]+)", line, re.I)
            if m:
                identity["java"] = m.group(1)
            m = re.search(r"OS\s+(.+?)\s+arch\s+([^\s]+)\s+version\s+([^\s]+)", line)
            if m:
                identity["os"] = m.group(1).strip()
                identity["arch"] = m.group(2)
                identity["os_version"] = m.group(3)
    return identity


def extract_mods(lines: list[str]) -> list[dict]:
    mods = []
    seen = set()
    for line in lines:
        m = MOD_PATTERNS[0].search(line)
        if m:
            fn = m.group(1).strip()
            if fn not in seen:
                seen.add(fn)
                mods.append({"filename": fn})
    return mods


def signal_score(kind: str, line: str, index: int, total: int) -> int:
    base = {
        "class_not_found": 100,
        "no_class_def": 95,
        "no_such_method": 100,
        "no_such_field": 100,
        "mixin_apply": 90,
        "verify_error": 85,
        "mod_loading": 95,
        "duplicate_mod": 100,
        "unsupported_class": 100,
        "exception_init": 80,
        "fatal": 75,
        "error": 25,
    }.get(kind, 10)
    # Later errors are more likely to be the terminal crash, but only as a tiebreaker.
    return base + int(10 * index / max(1, total))


def extract_signals(lines: list[str]) -> list[dict]:
    signals = []
    for idx, line in enumerate(lines, start=1):
        for kind, rx in FATAL_PATTERNS:
            m = rx.search(line)
            if not m:
                continue
            entry = {
                "line": idx,
                "kind": kind,
                "text": line.strip(),
                "score": signal_score(kind, line, idx, len(lines)),
            }
            if m.lastindex:
                entry["detail"] = m.group(1).strip()
            mod_match = MODID_EVENT_RE.search(line)
            if mod_match:
                entry["modid"] = mod_match.group(1)
            signals.append(entry)
            # Prevent generic ERROR from duplicating a specific hit on same line.
            if kind != "error":
                break
    return signals


def extract_transformer_mods(lines: list[str]) -> Counter:
    counts = Counter()
    for line in lines:
        for modid, version in TRANSFORMER_MOD_RE.findall(line):
            counts[(modid, version)] += 1
    return counts


def build_context(lines: list[str], signals: list[dict], radius: int = 3) -> list[dict]:
    contexts = []
    selected = sorted(signals, key=lambda x: (-x["score"], -x["line"]))[:20]
    seen_ranges = set()
    for s in selected:
        lo = max(1, s["line"] - radius)
        hi = min(len(lines), s["line"] + radius)
        key = (lo, hi)
        if key in seen_ranges:
            continue
        seen_ranges.add(key)
        contexts.append({
            "focus_line": s["line"],
            "kind": s["kind"],
            "lines": [{"line": n, "text": lines[n - 1]} for n in range(lo, hi + 1)],
        })
    return contexts


def triage(path: Path) -> dict:
    text = read_text(path)
    lines = text.splitlines()
    signals = extract_signals(lines)
    transformer_counts = extract_transformer_mods(lines)
    implicated = defaultdict(int)
    for s in signals:
        if "modid" in s:
            implicated[s["modid"]] += s["score"]
        for modid, version in TRANSFORMER_MOD_RE.findall(s["text"]):
            implicated[f"{modid}@{version}"] += s["score"]
    result = {
        "path": str(path),
        "line_count": len(lines),
        "identity": detect_identity(lines),
        "mods": extract_mods(lines),
        "signals": sorted(signals, key=lambda x: (x["line"], x["kind"])),
        "top_signals": sorted(signals, key=lambda x: (-x["score"], -x["line"]))[:25],
        "implicated_mods": [
            {"key": key, "score": score} for key, score in sorted(implicated.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
        "transformer_mod_frequency": [
            {"modid": k[0], "version": k[1], "count": v}
            for k, v in transformer_counts.most_common(30)
        ],
        "contexts": build_context(lines, signals),
    }
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("log", type=Path)
    ap.add_argument("--pretty", action="store_true")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    data = triage(args.log)
    out = json.dumps(data, indent=2 if args.pretty else None, ensure_ascii=False)
    if args.output:
        args.output.write_text(out + "\n", encoding="utf-8")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
