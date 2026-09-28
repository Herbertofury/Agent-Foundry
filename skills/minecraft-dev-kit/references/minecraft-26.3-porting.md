# Minecraft 26.3 porting fast path

Snapshot authority date: **2026-09-18**. Treat version pins as a reproducible baseline, not eternal latest versions. Before starting a new 26.3 port, re-check the official Fabric/NeoForge source named below; update the lock only when the upstream target actually changes.

## Target baseline

Minecraft 26.3 uses **Java 25** for both target profiles.

### Fabric profile

- Minecraft: `26.3`
- Java: `25`
- Loom: `1.17-SNAPSHOT` / Loom 1.17 generation
- Gradle: `9.6.0` per Fabric's 26.3 migration guidance
- Fabric Loader snapshot pin: `0.19.5`
- Fabric API snapshot pin: `0.160.7+26.3`
- Keep `org.gradle.configuration-cache=false` unless the current Loom line explicitly clears the known IDE/configuration-cache constraint.

Primary authorities:

- https://fabricmc.net/2026/09/15/263.html
- https://fabricmc.net/develop/
- https://maven.fabricmc.net/net/fabricmc/fabric-api/fabric-api/
- https://github.com/FabricMC/fabric-example-mod

### NeoForge profile

- Minecraft: `26.3`
- Java: `25`
- NeoForge snapshot pin: `26.3.0.1-beta`
- ModDevGradle: `2.0.147`
- Gradle wrapper: `9.2.1`
- Foojay toolchain resolver convention: `1.0.0`

The NeoForge pin above is a **beta snapshot** from the official 26.3 MDK. Revalidate the MDK before each fresh conversion and update the scaffold pin when NeoForge advances.

Primary authorities:

- https://github.com/NeoForgeMDKs/MDK-26.3-ModDevGradle
- https://docs.neoforged.net/docs/gettingstarted/
- https://projects.neoforged.net/neoforged/neoforge

## Mapping namespace law: 26.3 is unobfuscated

Minecraft Java **26.1+ ships unobfuscated/official names**. Treat `official` as the target namespace for 26.3. Do not add Yarn or Intermediary as a target mapping dependency merely because the source mod used them. Fabric stopped maintaining Yarn for the unobfuscated 26.x line; historical Yarn/Intermediary remain migration evidence for older sources.

The Dev Kit now treats mapping conversion as a lineage graph:

- Mojang official ProGuard mappings bridge obfuscated releases to official names where available;
- Fabric Intermediary bridges historical production `class_*` / `method_*` / `field_*` identifiers;
- historical Yarn bridges old Fabric named source identifiers to Intermediary/official identities;
- MCPConfig/TSRG/SRG bridge legacy Forge owners, members and JVM descriptors;
- exact legacy MCP named snapshots/stables are read from the source build and are **never guessed**;
- 26.3 itself is an identity/official endpoint rather than another mapping layer.

Use:

```text
python scripts/mapping_lineage.py plan --source-version 1.20.1 --loader fabric
python scripts/mapping_lineage.py harvest --source-version 1.20.1 --loader fabric --cache <cache>
python scripts/mapping_lineage.py normalize <mapping-file> --json-out <index.json>
python scripts/mapping_lineage.py query <index.json> --namespace intermediary --class net/minecraft/class_123 --member method_456 --descriptor '(...)V'
python scripts/prewarm_mc_26_3_mappings.py --cache <cache>
```

`prewarm_mc_26_3_mappings.py` covers common historical Forge/Fabric source lines from 1.7.10 through 1.21.1 plus 26.3 identity profiles. Add arbitrary project-specific profiles on demand. The cache manifest records checksummed source artifacts; missing network access is reported as incomplete rather than fabricated.

### Mixin/access/reflection remap surfaces

Run `scripts/mixin_surface_audit.py` automatically through intake/guard and separately when diagnosing a hook. For every Mixin or bytecode/access surface preserve and resolve:

1. target class owner;
2. member name in the source namespace;
3. exact JVM descriptor and overload;
4. injector kind, `@At` target, ordinal, slice and shift;
5. local-capture expectations;
6. `@Shadow`, `@Accessor`, `@Invoker`, `@Overwrite`, MixinExtras wrappers/conditions;
7. generated refmap entries where present;
8. Fabric class tweaker/access-widener entries;
9. Forge/NeoForge Access Transformer entries;
10. reflection and MethodHandle lookup strings;
11. compiled-class constant-pool residues when source is unavailable.

For Fabric 26.3, class-tweaker namespace must be `official`. Historical `named`/`intermediary` headers are blockers until translated. Descriptorless selectors, `remap=false`, `@Overwrite`, local capture and reflection are explicit manual/runtime-review surfaces, not automatic passes.

Static resolution is only the cheap gate. Any retained Mixin must still prove real target **PREPARE/APPLY** and execute the affected runtime path.

## Exact conversion oracle: names are only the first layer

The 26.3 lane now treats a port as four linked proofs before native runtime:

1. **Historical symbol lineage** — normalize Tiny/TSRG/SRG/Mojang ProGuard/MCP aliases, including the namespace of every JVM descriptor. `mapping_bridge.py` remaps object types inside descriptors as well as owner/member names; a correct method name with the wrong parameter/return namespace is not accepted.
2. **Exact target ownership** — `classfile_symbol_index.py` indexes the real 26.3 target without executing it and resolves inherited owners, overloads and descriptors. It also decodes LambdaMetafactory `invokedynamic` SAM sites so stale functional-interface method names cannot hide until `AbstractMethodError`.
3. **Whole-mod API migration** — `api_reference_migration.py` scans compiled old mod bytecode, translates its Minecraft class/member/SAM references through the source-version mapping indexes and resolves them against the 26.3 index. Exact survivors are separated from owner removal, descriptor/signature drift and genuine semantic-migration gaps. Never guess a replacement from a similar name.
4. **Zero-loss identity parity** — `content_identity_inventory.py` / `content_parity_audit.py` normalize data/resource identities across legitimate path migrations (for example `worldgen/configured_feature` -> `worldgen/feature`). `registration_identity_inventory.py` / `registration_parity_audit.py` separately preserve high-confidence code-registered block/item/entity/etc. IDs across old Forge, modern Forge/NeoForge and Fabric idioms.

`packaged_linkage_audit.py` then validates the exact shipped candidate's Minecraft member/descriptors and invokedynamic SAMs. `port_guard.py --strict-release` combines these proofs when their evidence is available. A static PASS remains pre-runtime evidence only.

### Autonomous repair loop

Do not treat compile/runtime errors as a stopping condition. For each coherent batch:

```text
source lineage + semantic plan
  -> implement target-native behavior
  -> exact mapping/Mixin/access/content/registration guard
  -> build/datagen
  -> port_failure_triage.py on the earliest fresh failure
  -> repair the causal issue
  -> narrow retest
  -> packaged linkage
  -> real server/client/integrated/restart proof
```

If the same failure remains unchanged after two repair attempts, change the evidence/implementation strategy rather than retrying the same command. Preserve known-good work while repairing the failed surface.

## Mandatory 26.3 intake

Run the source/JAR through `scripts/port_intake.py` before editing. Preserve its JSON manifest with the port checkpoint. It must identify:

- source loader(s), mod id/version and declared Minecraft range when available;
- Java/Gradle/build metadata clues;
- mixins, access wideners/transformers, services and compatibility hooks;
- code/data/assets/worldgen/config/network/save surfaces;
- known 26.3 migration hazards from `minecraft-26.3-port-rules.json`.

A JAR-only intake is evidence, not magical source recovery. Prefer upstream source, published source JARs, repository history, mappings and authorized decompilation/reconstruction in that order.

## High-value 26.3 migration breakpoints

### Fabric API removals / vanillaization

For 26.3, do not carry these old helpers forward:

- `CompostingChanceRegistry`
- `FuelRegistry`
- `FabricPotionBrewingBuilder`
- `StrippableBlockRegistry`
- `TillableBlockRegistry`
- `FlattenableBlockRegistry`

Composting/cooking/brewing fuel behavior moved toward item components (`DataComponents.COMPOSTABLE`, `DataComponents.COOKING_FUEL`, `DataComponents.BREWING_FUEL`). Brewing recipes are data-driven. Stripping/tilling/flattening are represented through the newer block-transformer data/component model.

The fluids API also changed; migrate old colored-name helper use to the current `FluidVariantAttributes.getColoredName` flow and check current callbacks.

### Input / client

Minecraft 26.3 removed GLFW in favor of SDL. Direct LWJGL GLFW constants/calls are a port blocker. Use vanilla `InputConstants` and current input abstractions. Custom text input widgets need to cooperate with the current `TextInputManager` behavior.

### Worldgen / registries

Do not mechanically rename compile errors. Inventory the full data graph because 26.3 changes registry/data ownership:

- configured feature data converges into `worldgen/feature`;
- surface rules become material rules (`worldgen/material_rule`) with material conditions;
- number providers are split/registrable as float/int provider families;
- block-state providers are registrable/reworked;
- old block codecs / `block_type` assumptions must be reviewed;
- recipes/advancements and custom reloadable registries have changed reloadability semantics.

Run datagen where the project uses it, then diff generated resources against the source inventory instead of accepting compilation alone.

## Loader strategy

Keep Fabric and NeoForge native by default. Do **not** introduce Architectury or another cross-loader abstraction merely because two outputs are requested. A shared `common` module is justified only when the source already has a multi-loader architecture or the duplicated behavior is material enough to offset abstraction/runtime risk.

For a dual-loader conversion:

1. Freeze one source-behavior inventory.
2. Create separate `fabric` and `neoforge` target profiles.
3. Share loader-agnostic code/assets deliberately, not by moving loader APIs into common code.
4. Run `port_guard.py` independently for each target.
5. Build and runtime-test each loader independently; one green loader is not evidence for the other.

## Conversion sequence

1. Run `port_intake.py` on the best source authority and preserve the manifest.
2. Run `port_26_3_pipeline.py` (or equivalent scaffold + evidence steps) without overwriting source. Preserve source content and code-registration identity inventories.
3. Harvest/normalize the exact historical mappings. For compiled source, use `api_reference_migration.py` against an exact 26.3 class index before blindly editing compile failures.
4. Resolve semantic migration tasks plus exact Mixin/access/reflection surfaces. Keep future-vanilla parity additions disabled during Phase A.
5. Run changed-path tests and `port_guard.py`; fix source content/registration parity loss immediately rather than deferring it to release.
6. Build/datagen with Java 25. Triage the earliest causal failure with `port_failure_triage.py`, repair and narrow-retest until the coherent candidate builds.
7. Audit the exact packaged JAR with `packaged_linkage_audit.py`; strict release requires the strongest exact-symbol/content evidence applicable to the source.
8. Dedicated-server gate for common/server/data/registry/world/network behavior.
9. Native client or client+integrated-server gate for rendering/input/UI/entities/animation/sound/synced behavior and retained Mixins.
10. Restart/persistence proof for save/config/state changes.
11. Hash/package source + runnable JAR + intake/guard/build/runtime evidence.
12. Only after Phase A is independently certified, offer and separately test the opt-in future-vanilla parity layer.

## Performance-port discipline

26.3's performance is not permission to preserve old hot-path mistakes. During a port, challenge these surfaces explicitly:

- per-frame/per-tick allocations and registry scans;
- render-event global entity/block/item scans;
- synchronous chunk/world queries on client render paths;
- repeated resource/model parsing;
- polling that can be event-driven or cached;
- unbounded networking/serialization churn;
- mixins aimed at obsolete internals when a target API now exists.

Preserve behavior first, then use target-native APIs and event/caching structure to remove source-era overhead where measurable. Benchmark a representative scene/workload before and after any claimed optimization.

## Release proof

A 26.3 release is not complete because `gradlew build` succeeds. The release record must include the loader-specific baseline actually used, Java version, final artifact hash, source inventory accounting, guard result, dedicated-server evidence when applicable, native client/integrated-server evidence when applicable, and known intentional differences.
