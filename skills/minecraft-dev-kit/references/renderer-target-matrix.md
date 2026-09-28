# Minecraft model / animation target matrix

Research snapshot: **2026-09-06**. This is a routing aid, not a substitute for current version verification before dependency changes.

## Forge 1.20.1 priority lane

### General animated entity/block/item/armor

**GeckoLib 4.8.4** is the strongest established default for Forge 1.20.1 as of this snapshot. CurseForge lists `geckolib-forge-1.20.1-4.8.4.jar`, uploaded 2026-06-20. Use it when converting into GeckoLib semantics is not materially lossy.

### Direct Generic `.bbmodel`

**BlockbenchLib / BBLib 1.0.3** is architecturally ideal for Generic `.bbmodel` fidelity and explicitly targets MCModels-style unsupported Generic models, but its published builds are **NeoForge 1.21.1** and **Forge 1.18.2**, not Forge 1.20.1. For 1.20.1:

1. do not silently pull an incompatible JAR;
2. use BBLib as parser/runtime architecture reference;
3. choose GeckoLib/native conversion, or deliberately port BBLib to 1.20.1 as its own tested subproject when direct Generic semantics materially reduce loss.

BBLib 1.0.3 publicly lists locators, billboards, flipbook textures, controller/Molang animation, extra render layers, per-bone overrides, and hitbox derivation. Those are useful parity targets even when not using the library directly.

### CEM / OptiFine entity-model source

Use **Entity Model Features (EMF)** as a semantic oracle and, when appropriate, runtime. CurseForge lists 1.20.1 Forge/NeoForge **3.0.11**. For a native entity conversion, compare output against EMF rendering rather than guessing CEM semantics.

### Player-body animation

Modern **Player Animation Library (PAL)** currently targets 1.21.1 / 1.21.7+ / 26.x on Fabric/NeoForge; it is not a drop-in Forge 1.20.1 target. Forge 1.20.1 still has the legacy **KosmX PlayerAnimator** `1.0.2-rc1+1.20` lane. Preserve interoperability layers and avoid hard-exclusive player transforms.

### Animated Java / display-entity source

Treat `.ajmodel` as rich authoring source: variants, locators, easing/tweening, function/effect keyframes, text/item/block/interaction display concepts, Molang, and camera paths can exceed the semantics of a simple entity bone animation.

**blockbench-import-library** is a strong modern reference/runtime for Generic and Animated Java models, including variants, locator pose listeners, effect keyframes, interpolation/loop semantics, dynamic hitboxes/scale, ridability, name tags, leashes and display culling. Its active releases are focused on modern versions, so for 1.20.1 use it as semantic/parser reference unless a compatible build is explicitly verified or ported.

## Decision order

1. **Static/simple** -> native Minecraft baked/entity model APIs.
2. **Existing project already on a competent renderer** -> preserve the current library unless it blocks source fidelity.
3. **Generic `.bbmodel`, direct target supported** -> direct parser/runtime can avoid exporter loss.
4. **General skeletal/cuboid animated asset** -> GeckoLib/AzureLib based on project lineage and exact target support.
5. **CEM source** -> EMF oracle/runtime or a verified native conversion.
6. **Player-body source** -> PAL on supported modern targets, legacy PlayerAnimator on older Forge targets unless PAL is deliberately backported.
7. **Animated Java/display source** -> preserve AJ-specific variants/locators/effects/interactions; do not reduce it to bone keyframes without an explicit parity decision.

## Mandatory comparison before choosing a target

Score each candidate on:

- exact target Minecraft + loader support;
- source geometry types (cubes/meshes/display nodes/text);
- hierarchy and locator support;
- interpolation/easing/Molang support;
- animation blending, priorities and live state mutation;
- texture animation/emissive/billboard support;
- per-bone render overrides and attachments;
- hitbox/mount/leash/nameplate support;
- player compatibility when applicable;
- network/client-server state ownership;
- performance and culling;
- license/redistribution fit;
- native runtime QA burden.

Choose least **semantic loss**, not fewest lines of code.

## Current public provenance

- GeckoLib: `https://www.curseforge.com/minecraft/mc-mods/geckolib`
- BBLib / BlockbenchLib: `https://www.curseforge.com/minecraft/mc-mods/blockbenchlib`
- EMF: `https://www.curseforge.com/minecraft/mc-mods/entity-model-features`
- PAL: `https://www.curseforge.com/minecraft/mc-mods/player-animation-library`
- PlayerAnimator: `https://www.curseforge.com/minecraft/mc-mods/playeranimator`
- Animated Java: `https://github.com/Animated-Java/animated-java`
- blockbench-import-library: `https://github.com/tomalbrc/blockbench-import-library`
