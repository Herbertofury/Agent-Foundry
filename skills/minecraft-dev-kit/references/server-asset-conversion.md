# Server asset -> native mod conversion

## Goal

Convert an **authorized** server content bundle into a complete mod-owned asset family: geometry, textures, animations, state machines, hitboxes, seats/locators, items/blocks/furniture, sounds/particles, skills/AI, drops/recipes, localization, and runtime QA. Never equate a generated resource pack with full source semantics.


## One-command intake

Prefer `scripts/server_asset_pipeline.py` for a fresh authorized bundle when the whole conversion surface is unknown. It safely stages the source, detects ecosystems, runs only relevant semantic/model adapters, audits cross-file references, selects a dated target-renderer lane, and writes a consolidated migration manifest plus `PIPELINE-RECEIPT.json`. Use the individual scripts only when continuing from an existing checkpoint or testing a bounded subproblem.

## Source-of-truth order

Prefer the richest source and preserve all lower-level artifacts for cross-checking:

1. Original Blockbench `.bbmodel` / Animated Java `.ajmodel` plus embedded or sibling textures.
2. Server plugin configs and source packs: ModelEngine blueprints, MythicMobs packs, ItemsAdder/Oraxen/Nexo/Nova content/config, MythicCrucible furniture/items, MCPets/MythicMobs definitions.
3. Generated server resource pack: Java item/block models, blockstates, custom-model-data overrides, 1.21.4+ item definitions, textures, animated `.mcmeta`, fonts, sounds, shaders.
4. Runtime captures/logs/commands that expose hidden state transitions.
5. Client-downloaded resource pack alone. This is useful for visuals but usually cannot prove AI, skill graphs, hidden animations, drops, seats, hitbox logic, or server-only state.

If a source is encrypted/obfuscated/protected, do not bypass protection. Ask for the authorized authoring source or use visible/reference reconstruction instead.

## Intake

1. Preserve the original bundle untouched. Run `scripts/server_asset_stage.py` into a disposable/conversion workspace to create a safe byte-identical staged tree, per-file hashes, source identity, and rejected-path report.
2. Run `scripts/plugin_registry_audit.py`, then `scripts/server_plugin_inventory.py` and `scripts/server_plugin_coverage.py`. Audit registry identity routing first; inventory actual plugin/extension JAR descriptors plus config folders and classify them against `server-plugin-registry.json`. Unknown supplied identities remain explicit review items instead of disappearing from scope; run `scripts/unknown_plugin_triage.py` to generate evidence-driven classification candidates without auto-trusting them.
3. Run `scripts/server_asset_probe.py` against the original or staged directory/ZIP, then `scripts/adjacent_plugin_ir.py` and `scripts/server_family_ir.py` for recognized long-tail configs. Treat broad/family IR as a semantic checklist with unmatched-key evidence, not exact vendor parity.
4. If a resource pack exists, run `scripts/server_pack_resolver.py` and fix/record unresolved dependency closure. Use `scripts/java_model_ir.py` on important generated Java models to recover inherited geometry/UV/texture/display evidence.
5. Run `scripts/server_semantics_probe.py` when server configs or model state definitions are present. For each `.bbmodel`, run `scripts/bbmodel_ir.py` and `scripts/bbmodel_lint.py`. After Mythic/content IR exists, run `scripts/server_asset_link_audit.py` so model IDs, animation states, and cross-file references cannot silently disconnect.
6. Classify each file as authoring source, plugin semantics, generated runtime resource, or provenance-only.

## Semantic layers to recover

### Visual
- geometry, hierarchy, pivots/origins, cube inflate/mirroring;
- face UVs, texture dimensions, transparency, emissive layers, animated textures;
- locators/null objects, display transforms, scale and culling bounds;
- animation tracks, interpolation, loop mode, easing, keyframe events.

### Model runtime
Map special server-engine behaviors explicitly rather than discarding them:
- ModelEngine / similar seat or mount bones -> native passenger attachment points;
- hitbox bones -> entity dimensions or multipart hitboxes;
- item bones -> held/rendered child item layers;
- leash/nameplate/locator bones -> target-specific attachment points;
- default states / model states -> native animation-controller state machine;
- per-player rendering -> client capability/state synchronization when the mod needs it;
- root motion -> gameplay movement only when source behavior proves it, otherwise visual-only root motion.

### Gameplay
When ModelEngine/MythicMobs semantics are present, read `modelengine-mythic-semantics.md` and run `scripts/mythic_skill_ir.py` before generating native logic.

When ItemsAdder/Oraxen/Nexo-style content configs are present, read `custom-content-plugin-semantics.md` and run `scripts/content_plugin_ir.py`; preserve unclassified keys as unresolved semantic evidence.

For other recognized server plugins, use `server-plugin-registry.json` + `scripts/adjacent_plugin_ir.py` + `scripts/server_family_ir.py` to determine the conversion-impact family. `generic` means **normalized migration evidence with unmatched-key preservation**, not exact vendor semantics. If configs materially control models, items, NPCs, quests, weapons, HUDs, vehicles/pets, world content, scripts, spells or other gameplay, explicitly account for every relevant field from the original source and add a dedicated adapter when family normalization is insufficient. Context-only plugins (permissions, packet libraries, logging, anticheat, maps, proxies, etc.) are still inventoried so they do not create false unknowns.

Translate server configs into normal mod logic:
- MythicMobs mechanics/triggers/conditions/targeters -> goals, state machine, server events, cooldowns, predicates, target selection;
- projectiles/effects -> native entities/particles/sounds/damage logic;
- drops/loot -> loot tables or code where dynamic behavior is required;
- custom items -> registered items/components/attributes/tool behavior;
- furniture -> block/block-entity/decorative entity + collision/seat/interaction/drop logic;
- recipes -> recipes/data generation;
- pets -> ownership, follow/stay, summon/dismiss, inventory/skills/skins;
- cosmetics/armor -> equipment/render layers and client synchronization.

## Target renderer decision

Do not force one animation library onto every conversion. Read `renderer-target-matrix.md` and run `scripts/renderer_target_selector.py` when the correct runtime is not already established.

- Generic `.bbmodel` and target supported by BBLib -> direct `.bbmodel` runtime can minimize lossy conversion; still prove performance/compatibility first.
- Entity/block/item/armor with established GeckoLib pipeline -> GeckoLib is the common general target.
- Existing AzureLib ecosystem -> preserve AzureLib rather than gratuitously rewriting.
- Player-body animations -> PlayerAnimationLibrary on supported modern targets; keep legacy PlayerAnimator only where older target compatibility requires it.
- OptiFine CEM source -> EMF semantics can serve as an oracle or runtime target when appropriate.
- Simple static model -> prefer native baked/model APIs; do not add an animation dependency unnecessarily.

For Forge 1.20.1 specifically, do not assume a library's newest release supports the target. Treat current BBLib as a reference/port candidate unless its target-version support is verified for the project.

## Cross-version resource-pack translation

Server packs may use a newer vanilla asset schema than the destination mod:

- legacy CustomModelData overrides -> retain predicate mapping or replace with registered mod items/models;
- 1.21.4+ item-model definitions -> map Reference/Select/Condition/RangeDispatch/Composite/Special semantics into the target version's item renderer/model overrides or native mod logic;
- display-entity furniture -> choose block entity vs decorative entity based on interaction/collision/state needs;
- generated per-bone Java models -> use as visual evidence, not as a substitute for the richer `.bbmodel` hierarchy when available.

Do not silently delete source states merely because the target vanilla model schema lacks a direct equivalent.

## Full-asset acceptance ledger

A server asset is not a "full mod asset" until applicable rows are accounted for:

- source/provenance and rights;
- model hierarchy, geometry, pivots, UVs, textures;
- all animation clips and interpolation/timing;
- named model states/variants/skins;
- locators, seats, hitboxes, held-item/leash/nameplate anchors;
- AI/goals, triggers, conditions, target selection;
- attacks/projectiles/damage/cooldowns/status effects;
- particles, sounds, keyframe events;
- items/armor/cosmetics/furniture/blocks;
- recipes/drops/loot/localization;
- persistence, ownership, spawn/despawn rules;
- server/client synchronization;
- deterministic visual parity plus native Minecraft client/server proof.

Mark any absent server-only semantics as **unknown/missing source**, never as silently equivalent.
