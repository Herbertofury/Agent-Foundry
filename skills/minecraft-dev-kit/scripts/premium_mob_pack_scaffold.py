#!/usr/bin/env python3
"""Create a premium mob-pack development scaffold and manifest."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

PROFILE_COUNTS = {
    "boss-mega-2026": ("boss", 6),
    "mob-mega-2026": ("mob", 12),
    "supreme-boss-2026": ("boss", 1),
    "custom": ("mob", 1),
}


def entity_template(kind: str, index: int) -> dict:
    eid = f"{kind}_{index:02d}"
    is_boss = kind == "boss"
    base_anims = ["idle", "walk", "hurt", "death", "attack_01", "attack_02", "attack_03"]
    if is_boss:
        base_anims += ["phase_transition"]
    attacks = []
    for n in range(1, 4):
        attacks.append({
            "id": f"attack_{n:02d}",
            "animation": f"attack_{n:02d}",
            "windup": 0.35,
            "active": 0.10,
            "recovery": 0.45,
            "hitbox": "TODO",
            "cooldown": 2.0,
            "vfx": f"{eid}_attack_{n:02d}_vfx",
            "sfx": f"{eid}_attack_{n:02d}_sfx",
            "telegraph": "TODO",
            "interrupt_policy": "TODO",
            "impact_marker": f"impact_{n:02d}",
            "vfx_marker": f"vfx_{n:02d}",
            "sfx_marker": f"sfx_{n:02d}",
            "purpose": "TODO",
            "selection": {"min_range": 0.0, "max_range": 4.0, "weight": 1.0, "phases": [1, 2] if is_boss else [1], "max_repeat": 1}
        })
    return {
        "id": eid,
        "name": f"TODO {kind.title()} {index}",
        "kind": kind,
        "role": "TODO",
        "archetype": "TODO",
        "variants": ["base"],
        "model_file": f"models/{eid}.bbmodel",
        "creature_spec": f"specs/{eid}.creature.json",
        **({"encounter_file": f"encounters/{eid}.encounter.json"} if is_boss else {}),
        "animations": base_anims,
        "phases": 2 if is_boss else 1,
        "attacks": attacks,
        "vfx": [a["vfx"] for a in attacks],
        "sfx": [a["sfx"] for a in attacks],
        "ai_features": ["distance-aware-selection", "target-hysteresis", "anti-stuck", "telegraph-aware-cooldown"] if is_boss else ["distance-aware-selection", "target-hysteresis"],
        "performance": {"bone_budget": 24 if is_boss else 16, "cube_budget": 96 if is_boss else 64, "max_vfx_concurrency": 12 if is_boss else 6, "max_sfx_concurrency": 12 if is_boss else 8},
        "runtime": {
            "dimensions": [1.0 if not is_boss else 1.5, 2.0 if not is_boss else 3.0],
            "tracking_range": 10 if not is_boss else 14,
            "update_interval": 3,
            "attributes": {"max_health": 40 if not is_boss else 300, "movement_speed": 0.25, "attack_damage": 6 if not is_boss else 14},
            "spawn": {"mode": "encounter-only" if is_boss else "natural", "biome_tags": ["TODO"] if not is_boss else [], "weight": 8 if not is_boss else 1},
            "persistence": "boss" if is_boss else "normal",
            "synced_fields": ["combat_state"] + (["phase", "stagger"] if is_boss else []),
            **({"boss_bar": {"enabled": True}, "scaling": {"enabled": True}} if is_boss else {})
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--pack-id", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--profile", choices=PROFILE_COUNTS, default="custom")
    ap.add_argument("--minecraft", default="1.20.1")
    ap.add_argument("--loader", default="Forge")
    args = ap.parse_args()

    root = args.out
    for rel in ["models", "specs", "encounters", "textures", "animations", "sounds", "vfx", "data", "qa", "docs"]:
        (root / rel).mkdir(parents=True, exist_ok=True)
    kind, count = PROFILE_COUNTS[args.profile]
    entities = [entity_template(kind, i + 1) for i in range(count)]
    if args.profile == "mob-mega-2026":
        # Broad pack profile also needs bosses/minibosses. Keep placeholders explicit.
        entities += [entity_template("boss", i + 1) for i in range(3)]

    manifest = {
        "schema_version": 1,
        "pack": {"id": args.pack_id, "name": args.name, "profile": args.profile, "minecraft": args.minecraft, "loader": args.loader, "version": "0.1.0-dev"},
        "art_direction": {
            "fantasy": "TODO one-sentence pack fantasy/purpose",
            "silhouette_language": "TODO",
            "palette_rules": "TODO",
            "material_language": "TODO",
            "texture_density": "16x or 32x - choose deliberately",
            "scale_ladder": "TODO",
            "variant_rule": "TODO",
        },
        "entities": entities,
        "sidecars": {"equipment": [], "drops": [], "props": [], "items": []},
        "controls": {"tuning": ["health", "damage", "cooldowns", "stagger", "spawn"], "documentation": ["install", "configuration", "developer notes"]},
        "qa": {"native_client": True, "dedicated_server": True, "stress": {"simultaneous_entities": 24}, "visual_showcase": True},
    }
    (root / "premium-mob-pack.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for ent in entities:
        animations = []
        for name in ent["animations"]:
            markers = []
            if name.startswith("attack_"):
                suffix = name.split("attack_", 1)[1]
                markers = [
                    {"id": f"vfx_{suffix}", "time": 0.30, "kind": "vfx"},
                    {"id": f"sfx_{suffix}", "time": 0.32, "kind": "sfx"},
                    {"id": f"impact_{suffix}", "time": 0.35, "kind": "damage"}
                ]
            animations.append({"name": name, "length": 1.0 if name != "idle" else 2.0, "loop": name in {"idle", "walk", "run", "fly", "swim"}, "markers": markers, "bones": {}})
        spec = {
            "schema_version": 1,
            "id": ent["id"],
            "texture": {"width": 64, "height": 64},
            "visible_bounds": {"width": 2.5, "height": 3.0, "offset": [0, 1.0, 0]},
            "bones": [
                {"id": "root", "pivot": [0, 0, 0]},
                {"id": "body", "parent": "root", "pivot": [0, 12, 0]},
                {"id": "head", "parent": "body", "pivot": [0, 18, 0]}
            ],
            "cubes": [],
            "animations": animations
        }
        (root / ent["creature_spec"]).write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
        if ent.get("encounter_file"):
            attack_ids = [a["id"] for a in ent["attacks"]]
            encounter = {
                "schema_version": 1,
                "entity": ent["id"],
                "entry": "prebattle",
                "states": [
                    {"id": "prebattle", "kind": "setup", "transitions": [{"to": "phase_1", "when": "prebattle_complete"}]},
                    {"id": "phase_1", "kind": "combat", "attacks": attack_ids, "transitions": [{"to": "phase_transition", "when": "health_ratio<=0.5"}, {"to": "death", "when": "health<=0"}]},
                    {"id": "phase_transition", "kind": "phase_transition", "transitions": [{"to": "phase_2", "when": "transition_animation_complete"}]},
                    {"id": "phase_2", "kind": "combat", "attacks": attack_ids, "transitions": [{"to": "death", "when": "health<=0"}]},
                    {"id": "death", "kind": "death", "transitions": []}
                ]
            }
            (root / ent["encounter_file"]).write_text(json.dumps(encounter, indent=2) + "\n", encoding="utf-8")
    (root / "docs" / "PACK-BIBLE.md").write_text(
        f"# {args.name} - Pack Bible\n\nFill this before art lock.\n\n- Fantasy/purpose:\n- Biome/encounter context:\n- Silhouette language:\n- Proportion language:\n- Palette/material rules:\n- Scale ladder:\n- Roster roles:\n- Variant rules:\n- Performance budget:\n- Target: {args.minecraft} {args.loader}\n",
        encoding="utf-8",
    )
    print(root / "premium-mob-pack.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
