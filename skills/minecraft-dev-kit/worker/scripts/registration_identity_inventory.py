#!/usr/bin/env python3
"""Extract high-confidence code-registered Minecraft content identities without executing mod code.

This complements data/resource identity inventory. It recognizes common Fabric, Forge, NeoForge and
legacy Forge registration idioms and only promotes IDs to hard parity evidence when both registry
family and literal namespaced/path identity are recoverable. Ambiguous literals remain notes.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from port_26_3_common import Bundle, write_json

REGISTRY_NAMES = {
    "BLOCK": "block", "BLOCKS": "block",
    "ITEM": "item", "ITEMS": "item",
    "ENTITY_TYPE": "entity_type", "ENTITY_TYPES": "entity_type", "ENTITIES": "entity_type",
    "BLOCK_ENTITY_TYPE": "block_entity_type", "BLOCK_ENTITY_TYPES": "block_entity_type", "TILE_ENTITIES": "block_entity_type",
    "MOB_EFFECT": "mob_effect", "MOB_EFFECTS": "mob_effect", "POTIONS": "potion", "POTION": "potion",
    "SOUND_EVENT": "sound_event", "SOUND_EVENTS": "sound_event",
    "PARTICLE_TYPE": "particle_type", "PARTICLE_TYPES": "particle_type",
    "MENU": "menu", "MENU_TYPES": "menu",
    "ATTRIBUTE": "attribute", "ATTRIBUTES": "attribute",
    "ENCHANTMENT": "enchantment", "ENCHANTMENTS": "enchantment",
    "RECIPE_SERIALIZER": "recipe_serializer", "RECIPE_SERIALIZERS": "recipe_serializer",
    "RECIPE_TYPE": "recipe_type", "RECIPE_TYPES": "recipe_type",
    "FLUID": "fluid", "FLUIDS": "fluid",
    "CREATIVE_MODE_TAB": "creative_mode_tab", "CREATIVE_MODE_TABS": "creative_mode_tab",
    "DATA_COMPONENT_TYPE": "data_component_type", "DATA_COMPONENT_TYPES": "data_component_type",
}

SPECIALIZED_FACTORIES = {
    "createBlocks": "block", "createItems": "item", "createEntities": "entity_type",
    "createBlockEntities": "block_entity_type", "createSounds": "sound_event",
    "createParticles": "particle_type", "createMenus": "menu", "createFluids": "fluid",
}

MODID_RX = re.compile(r"\b(?:MOD_ID|MODID|MODID_STRING|MOD_ID_STRING)\s*=\s*[\"']([a-z0-9_.-]+)[\"']")
DEFERRED_GENERIC_RX = re.compile(
    r"DeferredRegister(?:\s*<[^;=]+>)?\s+([A-Z][A-Z0-9_]*)\s*=\s*DeferredRegister\.(?:create|create\w*)\s*\(\s*(?:ForgeRegistries|Registries|BuiltInRegistries)\.([A-Z0-9_]+)", re.S
)
DEFERRED_SPECIAL_RX = re.compile(r"DeferredRegister(?:\.[A-Za-z0-9_]+)?\s+([A-Z][A-Z0-9_]*)\s*=\s*DeferredRegister\.(create[A-Za-z0-9_]+)\s*\(")
VAR_REGISTER_RX = re.compile(r"\b([A-Z][A-Z0-9_]*)\.register\s*\(\s*[\"']([a-z0-9_./-]+)[\"']")
DIRECT_REGISTRY_RX = re.compile(
    r"Registry\.register\s*\(\s*(?:BuiltInRegistries|Registries|Registry)\.([A-Z0-9_]+).*?(?:ResourceLocation|Identifier)(?:\.of)?\s*\(\s*(?:[A-Z][A-Z0-9_]*|[\"'][a-z0-9_.-]+[\"'])\s*,\s*[\"']([a-z0-9_./-]+)[\"']", re.S
)
DIRECT_FULL_ID_RX = re.compile(
    r"Registry\.register\s*\(\s*(?:BuiltInRegistries|Registries|Registry)\.([A-Z0-9_]+).*?(?:ResourceLocation|Identifier)(?:\.parse|\.tryParse|\.of)?\s*\(\s*[\"']([a-z0-9_.-]+):([a-z0-9_./-]+)[\"']", re.S
)
LEGACY_PATTERNS = [
    ("block", re.compile(r"GameRegistry\.registerBlock\s*\([^,]+,\s*[\"']([a-z0-9_./-]+)[\"']")),
    ("item", re.compile(r"GameRegistry\.registerItem\s*\([^,]+,\s*[\"']([a-z0-9_./-]+)[\"']")),
    ("block_entity_type", re.compile(r"GameRegistry\.registerTileEntity\s*\([^,]+,\s*[\"']([a-z0-9_./:-]+)[\"']")),
    ("entity_type", re.compile(r"EntityRegistry\.registerModEntity\s*\([^,]+,\s*[\"']([a-z0-9_./-]+)[\"']")),
]
UNTYPED_ID_RX = re.compile(r"(?:setRegistryName|ResourceLocation|Identifier)(?:\.of)?\s*\(\s*(?:[A-Z][A-Z0-9_]*\s*,\s*)?[\"']([a-z0-9_./:-]+)[\"']")


def _source_files(bundle: Bundle):
    for name in bundle.names():
        if name.lower().endswith((".java", ".kt", ".kts")):
            try:
                yield name, bundle.read(name).decode("utf-8", errors="replace")
            except Exception:
                continue


def _namespace_from_id(value: str, default: str | None) -> tuple[str | None, str]:
    if ":" in value:
        ns, path = value.split(":", 1)
        return ns, path
    return default, value


def inventory(path: Path) -> dict:
    bundle = Bundle(path)
    entries = []
    notes = []
    try:
        files = list(_source_files(bundle))
        joined = "\n".join(text for _, text in files)
        modids = sorted(set(MODID_RX.findall(joined)))
        default_ns = modids[0] if len(modids) == 1 else None
        if len(modids) > 1:
            notes.append({"id": "multiple-modids", "values": modids, "message": "Multiple MOD_ID literals found; unqualified registration paths are not promoted unless namespace is otherwise explicit."})

        for file_name, text in files:
            var_registry = {}
            for m in DEFERRED_GENERIC_RX.finditer(text):
                cat = REGISTRY_NAMES.get(m.group(2))
                if cat:
                    var_registry[m.group(1)] = cat
            for m in DEFERRED_SPECIAL_RX.finditer(text):
                cat = SPECIALIZED_FACTORIES.get(m.group(2))
                if cat:
                    var_registry[m.group(1)] = cat
            for m in VAR_REGISTER_RX.finditer(text):
                cat = var_registry.get(m.group(1))
                if not cat:
                    continue
                if not default_ns:
                    notes.append({"id": "registration-namespace-unresolved", "path": file_name, "variable": m.group(1), "value": m.group(2)})
                    continue
                entries.append({"category": cat, "id": f"{default_ns}:{m.group(2)}", "path": file_name, "confidence": "high", "evidence": "DeferredRegister.register literal"})
            for m in DIRECT_REGISTRY_RX.finditer(text):
                cat = REGISTRY_NAMES.get(m.group(1))
                if cat and default_ns:
                    entries.append({"category": cat, "id": f"{default_ns}:{m.group(2)}", "path": file_name, "confidence": "high", "evidence": "Registry.register + literal namespace variable/path"})
            for m in DIRECT_FULL_ID_RX.finditer(text):
                cat = REGISTRY_NAMES.get(m.group(1))
                if cat:
                    entries.append({"category": cat, "id": f"{m.group(2)}:{m.group(3)}", "path": file_name, "confidence": "high", "evidence": "Registry.register + full literal id"})
            for cat, rx in LEGACY_PATTERNS:
                for m in rx.finditer(text):
                    ns, ident = _namespace_from_id(m.group(1), default_ns)
                    if ns:
                        entries.append({"category": cat, "id": f"{ns}:{ident}", "path": file_name, "confidence": "high", "evidence": "legacy Forge registration literal"})
                    else:
                        notes.append({"id": "legacy-registration-namespace-unresolved", "path": file_name, "category": cat, "value": ident})
            # Keep untyped registry/resource IDs as planning evidence only; never hard-gate them.
            for m in UNTYPED_ID_RX.finditer(text):
                value = m.group(1)
                ns, ident = _namespace_from_id(value, default_ns)
                if ns:
                    notes.append({"id": "untyped-resource-id", "path": file_name, "value": f"{ns}:{ident}"})
    finally:
        bundle.close()

    by_key = {}
    for row in entries:
        key = (row["category"], row["id"])
        if key not in by_key:
            by_key[key] = row
    unique = sorted(by_key.values(), key=lambda x: (x["category"], x["id"]))
    return {
        "schema_version": 1,
        "input": str(path.resolve()),
        "mod_id_candidates": modids if 'modids' in locals() else [],
        "entry_count": len(unique),
        "counts": dict(Counter(x["category"] for x in unique)),
        "entries": unique,
        "notes": notes[:500],
        "rule": "Only high-confidence registry-family + literal-ID recoveries are hard parity evidence. Ambiguous resource strings remain planning notes rather than false blockers.",
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