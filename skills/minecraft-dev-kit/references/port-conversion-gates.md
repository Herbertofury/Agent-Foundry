# Port and conversion gates

## Feature authority

For an old mod with partial newer rewrites, do not choose one version blindly. Treat the newest upstream release/source as behavioral/API authority where appropriate, while using older content-rich releases as feature/content authority when newer versions intentionally or accidentally omit material.

Build an explicit matrix of versions -> content/features -> implementation status -> target mapping.

## Mandatory phase ordering: base port before vanilla backport enhancements

A full conversion has two deliberately separate milestones. Do not collapse them.

### Phase A — full target-native mod port

Complete every mod-owned source/content/runtime surface first, using target-version APIs and behaviorally valid adaptations where needed. Future-vanilla additions remain disabled during this gate. The Phase A artifact must independently pass the conversion acceptance list below and the strongest applicable real-runtime QA. Run the Dev Kit port guard against this base artifact (`scripts/port_guard.py` for the 26.3 Fabric/NeoForge fast path; use the installed `mmv-devkit port-guard` command where that orchestrator gate is the active project contract).

Cross-version vanilla dependencies discovered during Phase A are **requirements evidence**, not permission to inject them into the base build. Record each one for the post-port offer. If a behaviorally equivalent target-native adaptation exists, use it for the base port. If no valid target-native adaptation can preserve the mod behavior, label the missing vanilla dependency a **source-parity blocker**; do not mislabel the base artifact as exact source-version parity.

### Phase B — always-offered, opt-in vanilla parity layer

After Phase A passes, always produce a backport offer. Default state is **OFF**. The offer must contain a complete requirements manifest with, for every feature:

- exact namespaced vanilla feature/resource/registry ID;
- source Minecraft version and first-seen version;
- why the mod references/requires it;
- target-version presence state;
- **optional enhancement** vs **required for exact source-version parity**;
- complete dependency-closure surfaces and exact assets/data/code that must be carried;
- external provider candidates and per-feature ownership proof;
- embedded fallback requirements if opted in and provider-absent;
- client/server/common ownership, networking/persistence/world/save impact;
- required QA lanes and disable/provider-removal recovery expectations.

If there are no future-vanilla requirements, still emit the offer result as `NONE_REQUIRED` rather than silently skipping the check. Do not mutate the certified Phase A artifact merely to prepare the offer.

Implementation of Phase B requires explicit opt-in. Preserve the Phase A build as a clean independently runnable baseline, then certify the opted-in build/layer separately.

## Complete source inventory

Before declaring a full port, preserve the intake/source identity and classify the complete inventory in a port ledger. For 26.3, `scripts/port_26_3_pipeline.py` initializes this evidence and `scripts/port_guard.py --strict-release` refuses unresolved/missing inventory surfaces.

Before declaring a full port:

- enumerate source code packages/classes;
- registries and content IDs;
- entities, blocks, items, effects, dimensions, worldgen, structures, loot, recipes, tags, advancements;
- models, textures, animations, sounds, particles, shaders, localization;
- data generators and generated data;
- config/network/save formats;
- compatibility hooks/integrations;
- source-pack sidecars and variants;
- archival assets needed for provenance or faithful regeneration.

Classify each item as carried directly, regenerated/derived, intentionally superseded, intentionally excluded by project guardrail, or still missing.

## Conversion acceptance

A conversion is not complete until:

1. Target loader + Minecraft build passes.
2. Full intended content accounting has no unexplained gaps.
3. Deterministic audits/regression tests pass.
4. Dedicated server loads when supported.
5. Native client reaches a real world and exercises representative content.
6. Models/textures/animations are visually checked in the real renderer.
7. Network/state/save behavior is exercised where affected.
8. Restart/persistence is proven for stateful changes.
9. Final artifact and source are reproducible and hashed.
10. Known intentional differences are documented, not hidden.

## Compatibility-first world rule

When project guardrails require a standalone/forever-world-safe port, do not modify vanilla Overworld/Nether/End world generation merely to surface ported content. Prefer dedicated dimensions, structures, portals, recipes, or opt-in mechanics unless the original intended behavior and project requirements explicitly demand vanilla worldgen changes.

## Dependency-owned inheritance and remap ownership

Do not assume a changed method belongs to the class where source code calls it. During backports, a method can be inherited from a dependency-owned superclass/interface whose production mapping differs from the project class hierarchy.

For each unresolved/stale member:

- resolve the declaring owner across project + dependency + Minecraft/loader hierarchies;
- map by declaring owner and exact descriptor;
- include dependency classes in hierarchy analysis without repackaging them as project output;
- distinguish compile visibility from runtime ownership.

A dependency supplied through jar-in-jar or an upstream mod can be visible to javac yet intentionally owned/loaded elsewhere at runtime. Do not copy dependency classes into the port merely to make remapping or validation easier; validate against the real runtime dependency graph instead.
