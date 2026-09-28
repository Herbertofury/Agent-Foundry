#!/usr/bin/env python3
"""Inventory namespaced Minecraft content identities for zero-loss ports.

The inventory normalizes known 26.3 data-path moves (configured_feature -> feature,
configured_carver -> carver, surface_rule -> material_rule) so parity measures content identity
rather than obsolete folder spelling. It does not execute mod code.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from port_26_3_common import Bundle, write_json

PATH_ALIASES = {
    "worldgen/configured_feature": "worldgen/feature",
    "worldgen/configured_carver": "worldgen/carver",
    "worldgen/surface_rule": "worldgen/material_rule",
    "recipes": "recipe",
    "loot_tables": "loot_table",
    "advancements": "advancement",
}

DATA_EXTS = {".json", ".nbt", ".mcfunction", ".snbt"}
ASSET_EXTS = {".json", ".png", ".mcmeta", ".ogg", ".fsh", ".vsh", ".glsl", ".json5"}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _strip_suffix(path: str) -> str:
    for suffix in (".png.mcmeta", ".json", ".png", ".ogg", ".nbt", ".snbt", ".mcfunction", ".mcmeta", ".json5"):
        if path.endswith(suffix):
            return path[:-len(suffix)]
    return path


def _entry(category: str, namespace: str, ident: str, path: str, data: bytes, subtype: str | None = None) -> dict:
    row = {"category": category, "id": f"{namespace}:{ident}", "path": path, "size": len(data), "sha256": _sha(data)}
    if subtype:
        row["subtype"] = subtype
    return row


def _logical_resource_name(name: str) -> str | None:
    """Map a source-tree resource path to the path it will have inside the mod JAR.

    The same inventory routine must work on source trees, generated-resource trees and packaged JARs.
    Ignore ordinary Java/build/cache files rather than mistaking them for pack resources.
    """
    clean = name.replace("\\", "/").lstrip("./")
    if clean.startswith(("data/", "assets/")) or clean in {"fabric.mod.json", "quilt.mod.json", "META-INF/neoforge.mods.toml", "META-INF/mods.toml"}:
        return clean
    marker = "/resources/"
    if marker in clean and clean.startswith("src/"):
        return clean.split(marker, 1)[1]
    return None


def inventory(path: Path) -> dict:
    bundle = Bundle(path)
    entries = []
    meta = []
    try:
        raw_names = bundle.names()
        for name in raw_names:
            logical = _logical_resource_name(name)
            if not logical:
                continue
            parts = logical.split("/")
            low = logical.lower()
            try:
                data = bundle.read(name)
            except Exception:
                continue
            if len(parts) >= 4 and parts[0] == "data":
                ns = parts[1]
                rel = "/".join(parts[2:])
                # Tags are a distinct identity family whose registry is encoded in the path.
                if rel.startswith("tags/") and low.endswith(".json"):
                    ident = _strip_suffix(rel[len("tags/"):])
                    entries.append(_entry("tag", ns, ident, logical, data))
                    continue
                if rel.startswith("structures/") and Path(low).suffix in {".nbt", ".snbt"}:
                    ident = _strip_suffix(rel[len("structures/"):])
                    entries.append(_entry("structure-template", ns, ident, logical, data))
                    continue
                if rel.startswith("functions/") and low.endswith(".mcfunction"):
                    ident = _strip_suffix(rel[len("functions/"):])
                    entries.append(_entry("function", ns, ident, logical, data))
                    continue
                if Path(low).suffix in DATA_EXTS:
                    parent = "/".join(parts[2:-1])
                    # For nested registries, preserve all folders between namespace and file.
                    canonical = PATH_ALIASES.get(parent, parent)
                    ident_tail = _strip_suffix(parts[-1])
                    # If registry directory has deeper content paths, they are already part of parent;
                    # split known registry roots from logical id path where practical.
                    roots = [
                        "worldgen/feature", "worldgen/configured_feature", "worldgen/placed_feature", "worldgen/carver", "worldgen/configured_carver",
                        "worldgen/biome", "worldgen/material_rule", "worldgen/surface_rule", "worldgen/material_condition", "worldgen/noise_settings",
                        "worldgen/density_function", "worldgen/noise", "worldgen/processor_list", "worldgen/template_pool", "worldgen/structure", "worldgen/structure_set",
                        "dimension", "dimension_type", "recipe", "recipes", "loot_table", "loot_tables", "advancement", "advancements", "damage_type",
                        "chat_type", "trim_material", "trim_pattern", "banner_pattern", "instrument", "painting_variant", "wolf_variant", "cat_variant",
                        "villager_trade", "trade_set", "enchantment", "jukebox_song", "test_environment", "test_instance"
                    ]
                    matched = next((r for r in sorted(roots, key=len, reverse=True) if rel.startswith(r + "/")), None)
                    if matched:
                        registry = PATH_ALIASES.get(matched, matched)
                        ident = _strip_suffix(rel[len(matched) + 1:])
                        entries.append(_entry("data-registry", ns, ident, logical, data, registry))
                    elif low.endswith(".json"):
                        entries.append(_entry("data-json", ns, _strip_suffix(rel), logical, data))
                    continue
            if len(parts) >= 4 and parts[0] == "assets":
                ns = parts[1]
                rel = "/".join(parts[2:])
                if rel == "sounds.json":
                    try:
                        obj = json.loads(data.decode("utf-8"))
                        for key in sorted(obj) if isinstance(obj, dict) else []:
                            entries.append(_entry("sound-event", ns, key, logical, json.dumps(obj[key], sort_keys=True).encode("utf-8")))
                    except Exception:
                        meta.append({"id": "unparsed-sounds-json", "path": logical})
                    continue
                if rel.startswith("lang/") and low.endswith(".json"):
                    try:
                        obj = json.loads(data.decode("utf-8"))
                        locale = Path(rel).stem
                        for key in sorted(obj) if isinstance(obj, dict) else []:
                            entries.append(_entry("translation-key", ns, key, logical, str(obj[key]).encode("utf-8"), locale))
                    except Exception:
                        meta.append({"id": "unparsed-lang-json", "path": logical})
                    continue
                category = None
                prefix = None
                for pfx, cat in [
                    ("blockstates/", "blockstate"), ("models/", "model"), ("textures/", "texture"), ("particles/", "particle"),
                    ("shaders/", "shader"), ("post_effect/", "post-effect"), ("font/", "font"), ("atlases/", "atlas"),
                ]:
                    if rel.startswith(pfx):
                        category, prefix = cat, pfx
                        break
                if category and Path(low).suffix in ASSET_EXTS:
                    ident = _strip_suffix(rel[len(prefix):])
                    entries.append(_entry(category, ns, ident, logical, data))
                    continue
        # Include metadata-declared mod ids as identity evidence from packaged or source-tree locations.
        for raw_name in raw_names:
            logical = _logical_resource_name(raw_name)
            if logical != "fabric.mod.json":
                continue
            try:
                data = bundle.read(raw_name)
                obj = json.loads(data.decode("utf-8"))
                if obj.get("id"):
                    entries.append(_entry("mod-id", str(obj["id"]), str(obj["id"]), logical, data))
            except Exception:
                meta.append({"id": "unparsed-fabric-mod-json", "path": raw_name})
    finally:
        bundle.close()

    # De-duplicate by canonical identity. Source trees may contain the same generated resource in more than
    # one resources root; that must not inflate parity counts or create fake missing content.
    by_identity = {}
    duplicate_paths = {}
    for row in sorted(entries, key=lambda x: (x["category"], x.get("subtype", ""), x["id"], x["path"])):
        key = (row["category"], row.get("subtype"), row["id"])
        if key not in by_identity:
            by_identity[key] = row
        else:
            duplicate_paths.setdefault(str(key), [by_identity[key]["path"]]).append(row["path"])
            if row["sha256"] != by_identity[key]["sha256"]:
                meta.append({"id": "duplicate-identity-different-bytes", "identity": list(key), "paths": duplicate_paths[str(key)]})
    unique = list(by_identity.values())
    unique.sort(key=lambda x: (x["category"], x.get("subtype", ""), x["id"]))
    return {
        "schema_version": 1,
        "input": str(path.resolve()),
        "entry_count": len(unique),
        "counts": {
            "category": dict(Counter(x["category"] for x in unique)),
            "data_registry": dict(Counter(x.get("subtype") for x in unique if x["category"] == "data-registry")),
        },
        "entries": unique,
        "notes": meta,
        "canonical_path_aliases": PATH_ALIASES,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()
    result = inventory(args.input)
    if args.json_out:
        write_json(args.json_out, result)
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())