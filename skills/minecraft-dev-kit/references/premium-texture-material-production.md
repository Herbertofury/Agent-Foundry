# Premium pixel texture and material production

Use for original premium mob textures after silhouette/geometry are stable.

## Material-first workflow

Do not texture by adding random pixel noise. Define a small material vocabulary first: skin/fur/chitin, cloth/leather, metal/stone/bone/wood, magic/emissive, damage/wear, etc. Each material should own a distinct value rhythm, hue behavior and cluster language.

For each material record:

- 3-6 meaningful ramp values for Minecraft-native work unless the reference/style genuinely needs more;
- shadow/highlight hue direction;
- edge-highlight policy;
- cluster/pattern language;
- whether it can be emissive or translucent;
- which cubes/regions use it.

`creature_texture_blockout.py` can produce a deterministic **first-pass material texture** from a creature spec + material recipe. It is a blockout, not final art. Refine it by hand/artist reasoning in the canonical texture editor/Blockbench, then audit the actual PNG with `creature_texture_audit.py`.

## Face hierarchy

Spend contrast where gameplay needs attention:

1. face/eyes/mouth or equivalent attention point;
2. role-defining weapon/core/crest;
3. major material boundaries;
4. secondary wear/markings;
5. low-contrast filler planes.

A texture that gives every cube equal contrast looks noisy even if every pixel is technically polished.

## Cluster discipline

Prefer connected 2-6 pixel clusters at 16x/32x densities. Single-pixel marks should have a reason: eye glint, rivet, chip, magical mote, etc. Large fractions of isolated singleton pixels usually indicate noise rather than material description.

## Shading and Minecraft lighting

Use texture shading to describe form/material, not to bake one fixed world light direction across the whole creature. In-game light still needs to read correctly. Top/bottom/side face value changes may help blockout readability, but final shading should not fight runtime lighting.

## Emissive hierarchy

Keep emissive coverage sparse and meaningful. An emissive mask should normally identify focal cores, eyes, runes, vents, magic seams or phase-state accents. If half the body glows, the focal hierarchy disappears and combat VFX become harder to read.

## Variant texture rule

Palette variants only count as premium content when they support a real ecology/faction/phase purpose. Pack-count variants should change at least two meaningful dimensions (silhouette/attachments/materials/animation/combat/audio/VFX/environmental role), even if a recolor is also included.

## Texture audit interpretation

`creature_texture_audit.py` checks dimensions, alpha behavior, palette/noise indicators, duplicate textures, emissive coverage and spec compatibility. Thresholds are warnings, not universal art laws. Visual inspection at native game scale is authoritative.
