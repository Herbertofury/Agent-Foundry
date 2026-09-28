# Server model / animation / custom-content ecosystem atlas

Research snapshot: 2026-09-06. Use current official docs/repositories again when version compatibility is load-bearing.


## Canonical 2026-and-older server plugin coverage registry

Use `server-plugin-registry.json` as the machine-readable coverage source. The 2026-09-06 snapshot currently classifies **277** named systems/aliases across direct assets, gameplay semantics, presentation, bridges, and context-only infrastructure. It deliberately includes current Paper/Purpur/Folia ecosystems **and** common legacy/migration sources (for example AureliumSkills -> AuraSkills, PlayerAnimator, HolographicDisplays, CrackShot, older GUI/scoreboard/furniture systems).

Do **not** treat the named registry as a closed universe. Run `scripts/plugin_registry_audit.py`, then `scripts/server_plugin_inventory.py` and `scripts/server_plugin_coverage.py` against a staged bundle. The audit rejects normalized alias/marker collisions and generic categories with no semantic route. Inventory hashes only actual plugin/extension-container JARs (not server libraries), reads Bukkit/Paper/Bungee/Velocity/Geyser-extension descriptors without executing/decompiling bytecode, records config folders, follows declared dependencies, resolves aliases, and surfaces every unknown JAR/config identity. An unknown supplied plugin must be classified before claiming full-server parity; never silently assume it is irrelevant. Run `scripts/unknown_plugin_triage.py` for each unknown: it scans supplied config/source text, infers likely semantic families, extracts references/commands/dependencies, and emits a **candidate** registry entry without mutating the canonical registry or decompiling/executing JARs.

Run `scripts/adjacent_plugin_ir.py` plus `scripts/server_family_ir.py` for recognized long-tail conversion-impact configs. The broad layer extracts IDs/commands/semantic groups; the family layer normalizes weapons, NPC/story, presentation, RPG, magic, mobs, pets/vehicles, economy/loot, world, resource-pack, custom-content, model/animation, and scripting families while preserving unmatched key paths. These are migration/checklist layers, not proof of vendor-specific parity; promote a family to a dedicated adapter when exact behavior depends on its schema.

The current snapshot has **7 first-class**, **181 generic family-normalized**, and **89 context-only** entries. `plugin_registry_export.py` generates a Drive-friendly Markdown/CSV atlas from the canonical JSON registry so research and tooling cannot drift into separate lists.

### Coverage cross-check sources

Use integration hubs as discovery evidence because they expose real plugin interoperability. Current ResourcePackManager documentation enumerates pack integrations such as ModelEngine, FreeMinecraftModels, EliteMobs, Nova, Oraxen, ItemsAdder, Nexo, BetterHUD, ValhallaMMO, RealisticSurvival, InfiniteVehicles, BackpackPlus, MMOInventory, BetterStructures and others. BetonQuest's integration list similarly cross-checks Citizens, Denizen, AuraSkills, MythicMobs, MMOItems/MMOCore/MythicLib, Magic, mcMMO, Skript, holograms, WorldGuard/WorldEdit and legacy/current quest bridges. Keep these hubs in the research loop when updating the registry, but do not let them replace direct source inspection.

## Highest-priority systems

| System | Role | Conversion value | Dev Kit policy |
|---|---|---|---|
| Blockbench | Canonical authoring environment | `.bbmodel`, textures, pivots, animations, plugins | Core tool; preserve source project whenever available |
| ModelEngine 4 | Server model/animation engine | Generic Blockbench source, generated pack, states, special bones | Tier S adapter target; pair with MythicMobs configs |
| MythicMobs | Server mob/skill engine | AI, mechanics, triggers, conditions, targeters, projectiles, drops | Tier S gameplay-semantic translator |
| MythicCrucible | Items/blocks/furniture | Props, items, recipes, mechanics | Tier S content-semantic translator when present |
| BetterModel / BetterModel2 | Open server model engine | Generic `.bbmodel`, generated RP, animation/hitbox/player model concepts | Tier S architecture/reference source |
| FreeMinecraftModels | Open server model engine | `.bbmodel`/`.fmmodel`, RP generation, props, mounts, hitboxes, custom items | Tier S architecture/reference source |
| ItemsAdder | Broad custom-content plugin | Items, blocks, furniture, entities, HUD, fonts, sounds | Tier S config/RP adapter; proprietary assets remain link/licensed-source only |
| Oraxen | Custom-content plugin | Items, blocks, furniture, glyphs, armor, RP mechanics | Tier S adapter; **paid license forbids redistribution of builds/source** |
| Nexo | Custom-content plugin | Items, furniture, 1.21.4+ item-model system, generated RP | Tier S adapter; preserve new item-model semantics |
| Nova | Paper custom-content framework | Items, blocks, GUIs, addon content | Tier A adapter/reference |
| MCPets | Pet system around ModelEngine/MythicMobs | ownership/follow/stay/skins/pet behavior | Tier A for pet conversion |
| Animated Java | Blockbench -> datapack/RP animation | `.ajmodel`, locators, easing, variants, function events | Tier S source adapter/reference |

## Mod-side render / animation targets

| System | Best use | Important note |
|---|---|---|
| GeckoLib 5 / GeckoLib 4 | Animated entities, blocks, items, armor | Strong general-purpose mod target; version-match exactly |
| AzureLib | Existing AzureLib projects / complex keyframes | Preserve if already canonical; do not rewrite for fashion |
| BBLib / BlockbenchLib | Direct Generic `.bbmodel` rendering/animation | Particularly interesting for MCModels-style Generic models; current project explicitly targets unsupported MCModels-like models. Verify target-version support before adoption |
| PlayerAnimationLibrary (PAL) | Modern player-body animation | Official successor to PlayerAnimator; loads old format too |
| PlayerAnimator | Legacy player animation | Frozen predecessor; retain only for target versions PAL does not cover |
| Entity Model Features (EMF) | OptiFine CEM/JEM/JPM compatibility | Excellent semantic oracle/runtime for CEM-origin assets |
| Citadel | Code-driven/advanced entity animation ecosystem | Useful for projects already built around it; not a universal `.bbmodel` converter |
| blockbench-import-library | Server/Fabric direct `.bbmodel`/`.ajmodel` experimentation | Valuable parser/runtime reference; not the default client-mod target |

## Blockbench authoring helpers worth keeping in the toolbox

- GeckoLib Models & Animations plugin.
- Animated Java.
- CEM Template Loader for OptiFine/EMF work.
- Root Motion Extractor to diagnose/extract locomotion and foot sliding.
- Bakery to bake complex curves where a target needs linearized keyframes; preserve the original curves first.
- Animation Sliders for controlled motion editing.
- Resourcepack Packager for pack assembly/QA.
- Texture Stitcher for deterministic atlas/sheet work.
- UV Locker and Quick Box-UV Layout for geometry edits without accidental UV drift.
- VoxelShape generators for turning visual furniture/block geometry into collision/selection shapes.
- Ground Plane Editor / Animated Platforms for contact and moving-platform locomotion QA.
- Brush Plus / Smudge Brush / Grayscale Preview for texture-material/value iteration.

## Acquisition / Drive policy

**Safe to catalogue/link:** all systems above.

**Open-source code may be mirrored when it materially helps a project:** BetterModel, FreeMinecraftModels, BBLib, Animated Java, GeckoLib, PAL, EMF and other projects whose license permits the intended copy. Keep license/provenance with every mirror and prefer source/release URLs over stale binaries.

**Do not blindly mirror paid/proprietary plugin binaries or marketplace assets:** ModelEngine paid distributions, Mythic premium plugins/assets, ItemsAdder paid builds/assets, Oraxen builds/source beyond its license, Nexo paid distributions, MCPets/marketplace content, and MCModels paid products. Store links/metadata unless the user supplies an authorized licensed copy for their own project.

## Public source links

- ModelEngine / MythicMobs / MythicCrucible docs: https://wiki.mythiccraft.io/
- MCModels marketplace: https://mcmodels.net/
- BetterModel: https://github.com/toxicity188/BetterModel
- BetterModel2 fork studied: https://github.com/AttlerCrow/BetterModel2
- FreeMinecraftModels: https://github.com/MagmaGuy/FreeMinecraftModels
- BBLib: https://github.com/DogifiedV2/bblib
- ItemsAdder: https://itemsadder.com/
- Oraxen: https://github.com/oraxen/oraxen
- Nexo docs: https://docs.nexomc.com/
- Nova: https://github.com/xenondevs/Nova
- Animated Java: https://github.com/Animated-Java/animated-java
- GeckoLib: https://github.com/bernie-g/geckolib
- PlayerAnimationLibrary docs: https://docs.zigythebird.com/pal/intro/
- Entity Model Features: https://github.com/Traben-0/Entity_Model_Features
- Blockbench plugins: https://www.blockbench.net/plugins/

## Second-wave custom-content systems to recognize

These are important intake ecosystems even when a dedicated semantic adapter has not yet reached first-class parity. `content_plugin_ir.py` identifies them, preserves recognized runtime-semantic candidate fields, and keeps unknown keys explicit rather than dropping them.

- **CraftEngine** — modern Paper/Folia server-side content framework for custom items, real/custom blocks, furniture and recipes. Community source is GPLv3; premium-only features/support remain licensed. Its Forge/Fabric-like block behavior model makes it especially valuable as a server-to-native-mod semantic reference.
- **ExecutableItems / ExecutableBlocks** — Ssomar custom item/block systems centered on activators/actions/conditions and optional resource-pack models. Treat activator graphs as gameplay semantics, not merely item metadata.
- **MMOItems** — RPG item/stat/ability/crafting ecosystem tied to MythicLib/Mythic integrations. Preserve item stats, abilities, generators/templates, custom blocks, recipes and drops independently from model appearance.
- **EcoItems** — config-driven custom items/effects/conditions/triggers in the eco/libreforge ecosystem. Preserve trigger/effect/condition graphs and item identity.
- **HMCCosmetics / HMCWraps** — resource-pack cosmetic/item appearance systems. HMCCosmetics is open source and has its own converter history for other cosmetic formats; preserve cosmetic slot/attachment/state semantics and pack model identity.
- **HatCosmetics** — lighter CustomModelData wearable-hat ecosystem; useful as a simple cosmetic conversion/reference lane.

Do not promote a generic parser result to full semantic parity. Add a dedicated reference/adapter whenever an active project uses plugin-specific fields that remain unclassified.
