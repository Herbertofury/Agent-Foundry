#!/usr/bin/env python3
"""Inventory a Forge/NeoForge/Fabric/Quilt mod source tree or JAR and flag Minecraft 26.3 migration risks."""
from __future__ import annotations

import argparse
import json
import re
import tomllib
from collections import Counter
from pathlib import Path

from mapping_lineage import source_plan
from mixin_surface_audit import audit as audit_mixins
from port_26_3_common import Bundle, collect_text, input_identity, load_rules, md_escape, normalize_loader, scan_rules, write_json


def _json(bundle: Bundle, name: str) -> dict | None:
    try:
        return json.loads(bundle.read(name).decode("utf-8"))
    except Exception:
        return None


def _toml(bundle: Bundle, name: str) -> dict | None:
    try:
        return tomllib.loads(bundle.read(name).decode("utf-8"))
    except Exception:
        return None


def _props(text: str) -> dict[str, str]:
    out = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def _first_mc_version(value: object) -> str | None:
    """Return the first concrete-looking Minecraft release version embedded in metadata/ranges."""
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        for item in value:
            found = _first_mc_version(item)
            if found:
                return found
        return None
    if isinstance(value, dict):
        for item in value.values():
            found = _first_mc_version(item)
            if found:
                return found
        return None
    text = str(value)
    # Supports classic 1.x.y and the 26.x era. Avoid loader/plugin versions by only using this
    # helper on Minecraft-specific metadata or explicit fallback patterns below.
    m = re.search(r"(?<!\d)((?:1\.\d{1,2}(?:\.\d{1,2})?)|(?:2[6-9]\.\d+(?:\.\d+)?))(?!\d)", text)
    return m.group(1) if m else None


def detect_metadata(bundle: Bundle, names: list[str], text_files: dict[str, str]) -> dict:
    loaders: list[str] = []
    metadata: dict = {}
    minecraft_candidates: list[dict] = []
    if "fabric.mod.json" in names:
        loaders.append("fabric")
        data = _json(bundle, "fabric.mod.json") or {}
        fabric_mc = (data.get("depends") or {}).get("minecraft")
        metadata["fabric"] = {
            "id": data.get("id"),
            "version": data.get("version"),
            "name": data.get("name"),
            "minecraft": fabric_mc,
            "loader": (data.get("depends") or {}).get("fabricloader"),
            "environment": data.get("environment"),
            "mixins": data.get("mixins") or [],
            "access_widener": data.get("accessWidener"),
        }
        if (v := _first_mc_version(fabric_mc)):
            minecraft_candidates.append({"version": v, "source": "fabric.mod.json:depends.minecraft"})
    if "quilt.mod.json" in names:
        loaders.append("quilt")
        data = _json(bundle, "quilt.mod.json") or {}
        ql = data.get("quilt_loader") or {}
        metadata["quilt"] = {"id": ql.get("id"), "version": ql.get("version"), "metadata": ql.get("metadata"), "depends": ql.get("depends")}
        for dep in ql.get("depends") or []:
            if isinstance(dep, dict) and dep.get("id") == "minecraft":
                if (v := _first_mc_version(dep.get("versions"))):
                    minecraft_candidates.append({"version": v, "source": "quilt.mod.json:depends.minecraft"})
    neo_name = next((n for n in names if n.endswith("META-INF/neoforge.mods.toml")), None)
    forge_name = next((n for n in names if n.endswith("META-INF/mods.toml")), None)
    if neo_name:
        loaders.append("neoforge")
        data = _toml(bundle, neo_name) or {}
        mods = data.get("mods") or []
        metadata["neoforge"] = {"file": neo_name, "mods": mods, "dependencies": data.get("dependencies") or {}}
    if forge_name:
        loaders.append("forge")
        data = _toml(bundle, forge_name) or {}
        mods = data.get("mods") or []
        metadata["forge"] = {"file": forge_name, "mods": mods, "dependencies": data.get("dependencies") or {}}

    gradle_props_name = next((n for n in names if n.endswith("gradle.properties")), None)
    if gradle_props_name and gradle_props_name in text_files:
        metadata["gradle_properties"] = _props(text_files[gradle_props_name])
        mc = metadata["gradle_properties"].get("minecraft_version") or metadata["gradle_properties"].get("mc_version")
        if mc:
            metadata["declared_minecraft_version"] = mc
            if (v := _first_mc_version(mc)):
                minecraft_candidates.insert(0, {"version": v, "source": f"{gradle_props_name}:minecraft_version"})

    joined = "\n".join(text_files.values())
    # Buildscript/source fallbacks only when Minecraft is explicitly named nearby.
    for pattern, label in [
        (r"(?:minecraft_version|mc_version)\s*=\s*['\"]?([^\s'\"]+)", "build:minecraft_version"),
        (r"minecraft\s*\(?\s*['\"](?:com\.mojang:)?minecraft:?([^'\"]+)", "build:minecraft dependency"),
        (r"versionRange\s*=\s*['\"]([^'\"]+)['\"]", "metadata:versionRange"),
    ]:
        for m in re.finditer(pattern, joined, re.IGNORECASE):
            if (v := _first_mc_version(m.group(1))):
                minecraft_candidates.append({"version": v, "source": label})
                break

    if minecraft_candidates:
        # Preserve evidence; the first high-confidence candidate is the source baseline.
        metadata["minecraft_version_candidates"] = minecraft_candidates[:20]
        metadata["source_minecraft_version"] = minecraft_candidates[0]["version"]

    if not loaders:
        if re.search(r"\bnet\.neoforged\.", joined): loaders.append("neoforge")
        if re.search(r"\bnet\.minecraftforge\.", joined): loaders.append("forge")
        if re.search(r"\bnet\.fabricmc\.", joined): loaders.append("fabric")
    return {"loaders": sorted(set(loaders)), "metadata": metadata}


def mapping_hints(text_files: dict[str, str]) -> dict:
    """Extract source mapping declarations. These are evidence, never a reason to guess a mapping coordinate."""
    joined = "\n".join(text_files.values())
    hints: list[dict] = []

    # ForgeGradle 2.x/3.x classic mapping notations.
    patterns = [
        (r"mappings\s*=\s*['\"]([^'\"]+)['\"]", "forge-mappings-assignment"),
        (r"mappings\s+channel\s*:\s*['\"]([^'\"]+)['\"]\s*,\s*version\s*:\s*['\"]([^'\"]+)['\"]", "forge-channel-version"),
        (r"mappings\s*=\s*\[\s*channel\s*:\s*['\"]([^'\"]+)['\"]\s*,\s*version\s*:\s*['\"]([^'\"]+)['\"]\s*\]", "forge-channel-version-map"),
        (r"mappings_channel\s*=\s*([^\s]+).*?mappings_version\s*=\s*([^\s]+)", "forge-properties-channel-version"),
    ]
    for rx, kind in patterns:
        for m in re.finditer(rx, joined, re.IGNORECASE | re.DOTALL):
            groups = [x.strip() for x in m.groups() if x is not None]
            value = ":".join(groups) if len(groups) > 1 else groups[0]
            hints.append({"kind": kind, "value": value})

    for m in re.finditer(r"net\.fabricmc:yarn:([^\s'\"\)]+)", joined):
        hints.append({"kind": "fabric-yarn", "value": m.group(1)})
    if re.search(r"officialMojangMappings\s*\(", joined):
        hints.append({"kind": "mojang-official", "value": "loom.officialMojangMappings()"})
    if re.search(r"net\.fabricmc:intermediary", joined) or re.search(r"\bintermediary\b", joined, re.IGNORECASE):
        hints.append({"kind": "fabric-intermediary", "value": "intermediary"})

    # Gradle property variants used by some templates.
    props = {}
    for name, text in text_files.items():
        if name.endswith("gradle.properties"):
            props.update(_props(text))
    for key in ("mappings", "mapping", "mappings_version", "mapping_version", "yarn_mappings"):
        if props.get(key):
            hints.append({"kind": f"property:{key}", "value": props[key]})

    # Keep stable order while de-duping.
    seen = set()
    unique = []
    for h in hints:
        token = (h["kind"], h["value"])
        if token not in seen:
            seen.add(token)
            unique.append(h)

    exact_legacy = None
    for h in unique:
        value = h["value"]
        if re.search(r"(?:snapshot|stable)[_:\-][0-9]", value, re.IGNORECASE) or re.match(r"(?:snapshot|stable):", value, re.IGNORECASE):
            exact_legacy = value
            break
    return {
        "declarations": unique,
        "exact_legacy_mapping_hint": exact_legacy,
        "uses_yarn": any(h["kind"] == "fabric-yarn" for h in unique),
        "uses_official_mojang": any(h["kind"] == "mojang-official" for h in unique),
        "uses_intermediary": any(h["kind"] == "fabric-intermediary" for h in unique),
    }


def inventory(names: list[str], text_files: dict[str, str]) -> dict:
    low_names = [n.lower() for n in names]
    def count_suffix(*suffixes: str) -> int:
        return sum(1 for n in low_names if n.endswith(suffixes))
    def count_re(pattern: str) -> int:
        rx = re.compile(pattern)
        return sum(1 for n in low_names if rx.search(n))
    mixin_cfgs = [n for n in names if n.lower().endswith(".mixins.json") or "/mixins." in n.lower() and n.lower().endswith(".json")]
    access_wideners = [n for n in names if n.lower().endswith((".accesswidener", ".classtweaker"))]
    access_transformers = [n for n in names if n.lower().endswith("accesstransformer.cfg")]
    services = [n for n in names if "/meta-inf/services/" in "/" + n.lower()]
    data_gen_markers = [n for n, text in text_files.items() if "DataGenerator" in text or "GatherDataEvent" in text or "runDatagen" in text]
    return {
        "files": len(names),
        "java_sources": count_suffix(".java"),
        "kotlin_sources": count_suffix(".kt", ".kts"),
        "compiled_classes": count_suffix(".class"),
        "json_resources": count_suffix(".json"),
        "textures_png": count_suffix(".png"),
        "sounds_ogg": count_suffix(".ogg"),
        "lang_files": count_re(r"/lang/.*\.json$"),
        "models": count_re(r"/models/.*\.json$"),
        "blockstates": count_re(r"/blockstates/.*\.json$"),
        "recipes": count_re(r"/recipe[s]?/.*\.json$"),
        "loot_tables": count_re(r"/loot_table[s]?/.*\.json$"),
        "tags": count_re(r"/tags/.*\.json$"),
        "advancements": count_re(r"/advancement[s]?/.*\.json$"),
        "worldgen": count_re(r"/worldgen/"),
        "structures": count_re(r"/structure[s]?/"),
        "mixins": mixin_cfgs,
        "access_wideners": access_wideners,
        "access_transformers": access_transformers,
        "services": services,
        "datagen_markers": data_gen_markers[:50],
    }


def java_gradle_hints(text_files: dict[str, str]) -> dict:
    joined = "\n".join(text_files.values())
    versions = []
    for pattern in [r"JavaLanguageVersion\.of\((\d+)\)", r"options\.release\s*=\s*(\d+)", r"VERSION_(\d+)"]:
        versions += [int(x) for x in re.findall(pattern, joined)]
    wrappers = []
    for name, text in text_files.items():
        if name.endswith("gradle-wrapper.properties"):
            m = re.search(r"gradle-([0-9][0-9.]+)-", text)
            if m: wrappers.append(m.group(1))
    loom = sorted(set(re.findall(r"loom_version\s*=\s*([^\s]+)", joined)))
    moddev = sorted(set(re.findall(r"net\.neoforged\.moddev['\"\s]+version\s+['\"]([^'\"]+)", joined)))
    return {
        "explicit_java_targets": sorted(set(versions)),
        "gradle_wrapper_versions": sorted(set(wrappers)),
        "loom_versions": loom,
        "moddevgradle_versions": moddev,
    }


def render_md(result: dict) -> str:
    lines = [
        "# Minecraft 26.3 Port Intake",
        "",
        f"- Input: `{result['input']['path']}`",
        f"- Input identity SHA-256: `{result['input']['sha256']}`",
        f"- Detected loaders: `{', '.join(result['detected']['loaders']) or 'unknown'}`",
        f"- Source Minecraft version: `{result.get('source_minecraft_version') or 'unresolved'}`",
        f"- Target loader for rule scan: `{result.get('target_loader') or 'not forced'}`",
        f"- Rule snapshot: `{result['rules']['snapshot_date']}`",
        "",
        "## Mapping lineage",
        "",
    ]
    hints = result.get("mapping_hints") or {}
    declarations = hints.get("declarations") or []
    if declarations:
        for item in declarations:
            lines.append(f"- `{md_escape(item['kind'])}` → `{md_escape(item['value'])}`")
    else:
        lines.append("No explicit source mapping declaration was parsed.")
    if result.get("mapping_plan"):
        lines += ["", "Required historical mapping evidence before translating to official/unobfuscated 26.3:"]
        for item in result["mapping_plan"].get("sources") or []:
            lines.append(f"- `{item['id']}` — {item['reason']}")
    lines += [
        "",
        "## Mixin / access / remap surfaces",
        "",
        f"- Static audit status: `{result['mixin_audit']['status']}`",
        f"- Blockers: `{len(result['mixin_audit']['blockers'])}`",
        f"- Warnings/manual-review surfaces: `{len(result['mixin_audit']['warnings'])}`",
        "- Runtime rule: static parsing is not proof; exact owner/member/descriptor and real Mixin PREPARE/APPLY remain mandatory where Mixins exist.",
        "",
        "## Inventory",
        "",
        "| Surface | Count / value |",
        "|---|---:|",
    ]
    for key, value in result["inventory"].items():
        if isinstance(value, list):
            value = len(value)
        lines.append(f"| {md_escape(key)} | {md_escape(value)} |")
    lines += ["", "## 26.3 migration findings", ""]
    if not result["findings"]:
        lines.append("No configured 26.3 static migration patterns were detected. This is not runtime proof.")
    else:
        for finding in result["findings"]:
            lines += [
                f"### {finding['severity'].upper()} — `{finding['id']}`",
                "",
                finding["summary"],
                "",
                f"Remediation: {finding['remediation']}",
                "",
            ]
            for ev in finding["evidence"][:8]:
                loc = ev["path"] + (f":{ev['line']}" if ev.get("line") else "")
                lines.append(f"- `{loc}`" + (f" — `{md_escape(ev.get('match'))}`" if ev.get("match") else ""))
            lines.append("")
    lines += [
        "## Next gate",
        "",
        "Harvest/normalize the required historical mapping evidence, create a loader-native 26.3 target, resolve every Mixin/access/reflection surface against official 26.3 owners+descriptors, then run `port_guard.py` before native runtime QA.",
        "",
    ]
    return "\n".join(lines)


def inspect(path: Path, target_loader: str | None = None) -> dict:
    target_loader = normalize_loader(target_loader) if target_loader else None
    bundle = Bundle(path)
    try:
        names = bundle.names()
        text_files = collect_text(bundle, names)
        detected = detect_metadata(bundle, names, text_files)
        mh = mapping_hints(text_files)
        source_version = detected.get("metadata", {}).get("source_minecraft_version")
        source_loader = (detected.get("loaders") or [target_loader or "unknown"])[0]
        try:
            mapping_plan = source_plan(source_version, source_loader, mh.get("exact_legacy_mapping_hint")) if source_version else None
        except Exception as exc:
            mapping_plan = {"status": "unresolved", "error": str(exc), "source": {"minecraft": source_version, "loader": source_loader}}
        mixin_audit = audit_mixins(path, "26.3", target_loader)
        result = {
            "schema_version": 2,
            "target_minecraft": "26.3",
            "target_loader": target_loader,
            "source_minecraft_version": source_version,
            "input": input_identity(path),
            "detected": detected,
            "inventory": inventory(names, text_files),
            "build_hints": java_gradle_hints(text_files),
            "mapping_hints": mh,
            "mapping_plan": mapping_plan,
            "mixin_audit": mixin_audit,
            "rules": {k: v for k, v in load_rules().items() if k != "rules"},
            "findings": scan_rules(names, text_files, target_loader),
        }
        counts = Counter(f["severity"] for f in result["findings"])
        result["finding_counts"] = dict(counts)
        return result
    finally:
        bundle.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("--target-loader", choices=["forge", "neoforge", "fabric", "quilt"])
    ap.add_argument("--json-out", type=Path)
    ap.add_argument("--md-out", type=Path)
    ap.add_argument("--fail-on-blocker", action="store_true")
    args = ap.parse_args()
    result = inspect(args.input, args.target_loader)
    if args.json_out:
        write_json(args.json_out, result)
    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        args.md_out.write_text(render_md(result), encoding="utf-8")
    if not args.json_out and not args.md_out:
        print(json.dumps(result, indent=2, sort_keys=True))
    blocker = result["finding_counts"].get("blocker", 0) or len(result.get("mixin_audit", {}).get("blockers") or [])
    return 2 if args.fail_on_blocker and blocker else 0


if __name__ == "__main__":
    raise SystemExit(main())
