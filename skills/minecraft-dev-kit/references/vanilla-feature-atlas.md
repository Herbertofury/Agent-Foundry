# Vanilla Feature Atlas and dependency-closed backports

## Purpose

Use this reference whenever a mod targets one Minecraft version but references vanilla content, registries, behavior, assets, data, networking, or persistence semantics from another version. The objective is not merely to make the identifier resolve: reproduce the vanilla dependency graph required for faithful behavior while remaining compatible with authoritative external backport providers.

## Hard rule: resolve now, implement only after the base port gate

If an identifier is absent from the target version, do not delete it, replace it with an arbitrary older analogue, register a dead placeholder, or suppress the warning until its version lineage is resolved. During the **base target-native port**, query and record the lineage/closure immediately, but keep future-vanilla content disabled by default. The certified base port comes first; future-vanilla parity is a separate post-port opt-in layer.

After the base port passes, always surface the recorded dependencies as an explicit backport offer. If the user declines, retain the certified target-native port and preserve the offer manifest for later. If exact source-version behavior depends on the future feature, label it **required for exact source-version parity** rather than silently claiming parity.

Classify each dependency as one of:

- **VANILLA_TARGET** — the target vanilla version already owns the feature. Reuse it; never duplicate-register it.
- **EXTERNAL_PROVIDER** — an installed backport provider has been proven to own the exact requested feature on the exact loader/version lane. Soft-link and delegate to it.
- **EMBEDDED_BACKPORT_REQUIRED** — target vanilla does not own it and no proven provider is supplying it. Backport the complete required vanilla dependency closure.
- **UNRESOLVED** — the atlas or authoritative source evidence is insufficient. Hydrate/refresh the atlas or inspect the exact official source version; do not guess.

## Sound model: three separate identities

Never treat “sound” as a single resource. Track independently:

1. **SoundEvent registry identity** — whether vanilla registers the exact namespaced event in that version.
2. **`sounds.json` definition** — whether that event has a resource definition and its exact `replace`, subtitle, weights, stream, attenuation-distance, preload, and referenced-name semantics.
3. **external OGG object(s)** — the exact asset-index objects and Mojang SHA-1 hashes used by the definition.

A real registered vanilla SoundEvent can have no `sounds.json` definition. Therefore a runtime `Missing sound for event` line is not sufficient evidence of a missing OGG and is not automatically a future-version feature. The atlas must report registration and definition lineage separately.

When an event is defined, require every referenced OGG to exist and hash-match the source version's Mojang asset index. When it is registered but intentionally/known to be undefined, preserve that distinction rather than fabricating an OGG.

## Post-port offer contract

The atlas is both a discovery tool and an exact backport-offer generator. Discovery may happen while Phase A is being ported; implementation may not.

For each cross-version feature, the offer must report:

```text
Feature ID:
Kind:
Source / first-seen version:
Target presence:
Why the mod touches it:
Parity role: OPTIONAL_ENHANCEMENT | REQUIRED_FOR_EXACT_SOURCE_PARITY
Decision if opted in: VANILLA_TARGET | EXTERNAL_PROVIDER | EMBEDDED_BACKPORT_REQUIRED | UNRESOLVED
Provider + ownership evidence:
Exact dependency closure:
Asset/data/code provenance and hashes where applicable:
Client/server/network/save/world impact:
Required QA lanes:
Base port gate: PASSED before implementation
Default state: OFF
```

Always produce an offer result after a full port. `NONE_REQUIRED` is a valid result. Never treat silence as proof there are no future-vanilla dependencies.

For implementation authorization, use a passing `port-guard` report plus explicit opt-in. Planning/querying is allowed before that gate so the work can be estimated, but generated plans are **offer-only** until the base port passes.

## Complete dependency closure

For every cross-version vanilla dependency, resolve each surface below as **REQUIRED**, **NOT_APPLICABLE**, or **PROVIDED_EXTERNALLY**. “It compiles” is not an allowed resolution.

- runtime behavior and game logic;
- registry identity, bootstrap order, defaults, holders/tags, and lifecycle;
- data-pack JSON: tags, recipes, loot tables, advancements, predicates, functions, damage types, worldgen/structure/biome/dimension data where referenced;
- resource-pack JSON: `sounds.json`, models, blockstates, item definitions/components, atlases, shaders, fonts, particles, equipment/UI definitions where referenced;
- textures, sounds, structures, language files, and other binary/resources with exact provenance when preservation matters;
- translations, subtitles, accessibility strings, and discoverability text;
- particles, game events, stats, criteria, triggers, and side effects emitted by the vanilla behavior;
- network packets, registry synchronization, codecs, stream codecs, protocol IDs, data attachments/components, and client/server ownership where transmitted;
- save/NBT/data-component/data-fixer semantics where persisted;
- commands, creative placement, recipes, loot/acquisition, spawn rules, and other ways the feature becomes reachable;
- worldgen, structures, biomes, dimensions, placement/modifier chains, and bootstrap data when behavior depends on them;
- rendering, models, animation, item/entity/block UI, camera/input hooks where visible;
- common/server authority and dedicated-server safety;
- compatibility ownership and duplicate-registration prevention.

For a SoundEvent specifically, “complete” means the registry event **and** exact source-version definition state **and**, when defined, exact referenced OGG objects **and** the trigger behavior that actually plays it. Do not backport a dead sound name without the vanilla behavior that requires it.

## Atlas authority and provenance

Use a layered authority model:

1. **Mojang version manifest, per-version metadata, mappings/download metadata, and asset indexes** for official release/snapshot lineage and exact downloadable hashes.
2. **misode/mcmeta** for version-controlled Mojang-generated registry/data/resource history from its supported floor through the latest snapshot. Pin exact branch revisions used to build the atlas.
3. **PrismarineJS/minecraft-data** for normalized historical protocol/registry/sound observations, especially before mcmeta's supported floor. Label these observations as derived/historical; do not promote them over contradictory Mojang evidence.
4. **Burger, ViaVersion mappings, Mojang mappings, and exact source/decompiled runtime inspection** as on-demand code/protocol extraction aids when metadata alone cannot close behavior/network dependencies.
5. **Backport mods** such as Vanilla Backport are compatibility providers only. They are never the historical authority for what vanilla contains.

The atlas should be metadata/provenance complete, not wastefully byte-duplicated. Keep exact official hashes/indexes and hydrate heavy JAR/OGG bytes on demand, then verify them before use.

## Latest-to-oldest coverage contract

Maintain the atlas as a living version graph from the latest available snapshot/release backward through Mojang's official version manifest, with normalized older observations where public historical tooling extends further back. For each observed version, retain as available:

- version type/time, data version, protocol, resource/data-pack versions;
- client/server JAR and mappings hashes/URLs;
- asset-index identity/hash and logical-object map;
- registries and entries;
- SoundEvent registrations;
- `sounds.json` definitions and referenced OGG logical paths;
- resource/data JSON path inventory;
- generated reports such as blocks, commands, item components, tags, and other registry-backed data;
- source provenance/revision for every derived observation.

Do not invent chronological precision for normalized historical aliases when the source does not provide authoritative release timestamps. Label the ordering/coverage limit explicitly.

## External provider precedence

Vanilla Backport and similar mods should work as providers, not competitors.

1. Detect provider by real mod metadata/class probes, not filename alone.
2. Prove per-feature ownership. Provider presence alone does not prove that its exact version/loader build supplies every requested feature. **Fail closed as `UNRESOLVED` when a provider is installed but ownership is not proven**; do not either suppress the embedded implementation or double-register it based only on presence.
3. If provider ownership is proven from exact bytecode/source/runtime evidence for the requested feature, let it own registration/behavior/resources and suppress only the overlapping embedded implementation.
4. Use reflection/service boundaries/events/optional APIs so the base mod has no hard optional-provider linkage.
5. If provider is absent and standalone behavior is required, enable the embedded dependency-closed fallback.
6. Never double-register registry IDs, double-trigger behavior, duplicate recipes/loot/spawns, or bind saves simultaneously to both providers.
7. For persistent content, test the same save with provider present and then removed. Missing-registry warnings for the removed provider may be acceptable only when the world continues safely and the embedded fallback owns subsequent behavior.

## Required QA lanes

For every new backported dependency family, run applicable lanes against the exact release candidate:

- static dependency-closure audit;
- exact production symbolic-linkage validation;
- native client + integrated server for resource/render/sound/gameplay behavior;
- dedicated server for common/server/registry/data/network behavior;
- provider absent / embedded fallback;
- provider present / external ownership;
- same-world provider removal when registry/save persistence can matter;
- exact sound/resource asset-index hash verification where sound/resources are involved;
- exactly-once behavior checks when provider and embedded hooks could overlap.

A compile-only, datagen-only, or fresh-world-only result cannot certify provider compatibility or persistent fallback.

## Dev Kit CLI contract

Prefer the newest verified `mmv-devkit` and use its Vanilla Feature Atlas commands when present:

```text
mmv-devkit vanilla-atlas verify --atlas VANILLA-ATLAS.json
mmv-devkit vanilla-atlas query --atlas VANILLA-ATLAS.json --id <namespaced-id> --target <mc-version>
mmv-devkit vanilla-atlas sound-status --atlas VANILLA-ATLAS.json --id <sound-event> --target <mc-version>
mmv-devkit vanilla-atlas diff --atlas VANILLA-ATLAS.json --from <old> --to <new> --kind <family>
mmv-devkit vanilla-atlas providers --atlas VANILLA-ATLAS.json --mods-dir <mods>
mmv-devkit vanilla-atlas plan-backport --atlas VANILLA-ATLAS.json --target <mc> --source <newer-mc> --feature <id> --mods-dir <mods> --provider vanillabackport --provider-inventory <exact-provider-inventory.json>
# Offer-only is the default. To authorize post-port implementation:
mmv-devkit vanilla-atlas plan-backport --atlas VANILLA-ATLAS.json --target <mc> --source <newer-mc> --feature <id> --port-report port-guard-report.json --opt-in --json
mmv-devkit vanilla-atlas providers --atlas VANILLA-ATLAS.json --mods-dir <mods>
mmv-devkit vanilla-atlas plan-backport --atlas VANILLA-ATLAS.json --target <old> --source <new> --feature <id> --mods-dir <mods>
```

The backport planner must fail closed when the feature is not represented in the atlas; refresh or hydrate authoritative evidence instead of generating a placeholder.

## Release evidence

Preserve at least:

```text
Target Minecraft / loader / Java:
Source vanilla version(s):
Atlas build identity + SHA-256:
Atlas source revisions:
Feature IDs requested:
Target presence status:
Registration / definition / external-object status for sounds:
Provider detection + proven ownership:
Dependency-closure disposition per surface:
Embedded fallback identity:
Production-linkage gate:
Provider-absent runtime:
Provider-present runtime:
Same-world provider-removal runtime:
Dedicated-server runtime:
Asset/object hash verification:
Warnings by owner:
Final release SHA-256:
Drive/GitHub publication identity:
```

Never upgrade a metadata observation into stronger runtime parity than the evidence supports.
