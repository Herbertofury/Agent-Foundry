# Standalone source-pack porting

Use this when converting a resource pack, add-on, replacement skin/model, or similar upstream work into independent namespaced game/mod content.

## 1. Inventory the entire upstream package

Do not stop at the obvious mob texture/model. Hash and classify every file, including:

- models / geometry / animation / controllers
- base, charged, emissive, armor, alternate and blink assets
- item/block textures and models
- particles and sounds
- loot, recipes, advancements, tags, names/localization
- paintings, heads, skulls, blocks, TNT, drops, icons, eggs
- selector/properties files, manifests, pack metadata and backups

Explicitly prove when a category is absent (for example, **0 source particle files** and **0 source sound files**) rather than assuming there are none.

## 2. Convert author-intended sidecars, not only the headline mob

When the project goal is a **fully standalone** port, treat upstream assets that globally replaced vanilla as evidence of the author's intended content family. Convert relevant sidecars into dedicated namespaced content instead of either:

1. dropping them as "not mob assets", or
2. globally replacing vanilla in the new project.

Example: a pack that replaces Creeper + gunpowder + TNT + Creeper Head + a painting should become a standalone Creeper variant plus its own gunpowder, TNT, head and painting when that matches project intent.

Keep unrelated vanilla content untouched unless the user explicitly requests a global override.

## 3. Preserve semantics, not format-specific implementation artifacts

Literal file parity is not always runtime parity. Distinguish:

- **author content** — art, geometry, motion, behavior intent, names, sidecars
- **source-format adapter** — implementation details needed only because of the original format

If a source-format adapter merely reproduces a vanilla primitive, use the target runtime's native primitive and preserve the exact visible result.

Example: a resource pack may use a custom one-cube Blockbench TNT JSON solely to select six 16x16 faces inside a 64x64 atlas. In a standalone Forge port, prefer **vanilla TNT cube geometry and vanilla TNT renderer/behavior**, deterministically extract the exact authored side/top/bottom pixels, and retain the original atlas/model in the provenance mirror. Do not blindly carry a format adapter when it causes broken target rendering.

For derived assets, ship a deterministic generator and an audit that proves the generated pixels/data equal the source semantics.

## 4. Use vanilla as the oracle for reskinned vanilla mechanics

When an upstream asset is fundamentally a themed vanilla feature, baseline against the target version's vanilla implementation:

- block geometry/model parent
- blockstates/properties
- placement/destruction behavior
- ignition paths and chain reactions
- entity fuse/tick/explosion behavior
- renderer transforms and flash/swell behavior
- loot semantics
- item transforms
- skull/head placement semantics

Copy or delegate to vanilla behavior where practical, then change only the namespaced identity and source-authored visuals. This reduces accidental behavior drift.

## 5. Build a source-accounting gate

Maintain three explicit classes:

- **exact runtime mappings** — byte-identical source files used directly
- **derived runtime mappings** — deterministically generated from source and verified against source semantics
- **archival/provenance-only inputs** — pack metadata, selectors, backups, or genuinely non-runtime files

Every upstream file must be accounted for. Author-intended gameplay/visual sidecars should not silently land in provenance-only.

## 6. Animation fidelity rules

- Preserve source blink timing and secondary motion.
- Preserve hierarchy, pivots, leg phase relationships, interpolation and source expressions.
- Do not invent missing bones because an animation references legacy targets absent from shipped geometry.
- Map a legacy channel onto a real equivalent part only when the intent is clear; document the mapping.
- If adding tasteful liveliness beyond the source, keep it bounded, regression-lock the source baseline, and avoid inventing rotation axes that the source never authored unless the user explicitly wants creative reinterpretation.

## 7. QA the whole content family

The approval package should show more than the mob:

- all mobs/variants in one grid
- per-variant GIFs for actual motion/blinking
- front / 3/4 / side / back model checks
- charged/emissive/alternate states
- source-linked sidecar items/blocks/heads/paintings/particles where applicable
- focused before/after comparison for repaired defects

For a changed sidecar such as TNT, include the block and its active/primed state when motion or flashing matters.

## 8. Treat the QA renderer as fallible

A deterministic preview can itself be wrong. When a render looks implausible:

1. compare against the runtime model/data,
2. compare against the target game's vanilla equivalent,
3. inspect UV normalization, parent-model resolution, transforms and texture filtering,
4. use an independent render path or live-runtime capture when available.

Do not patch the project merely to satisfy a buggy preview, and do not declare a project correct merely because one renderer looks good.
