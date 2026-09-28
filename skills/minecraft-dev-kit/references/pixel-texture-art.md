# Minecraft pixel texture artistry

Use this for models, entities, items, armor, cosmetics, furniture, VFX sprites, animated textures, and texture repair/reconstruction.

## Core visual law

Minecraft-style art reads from controlled clusters, not from indiscriminate noise. Preserve pixel-to-model scale whenever the target style calls for Minecraft-native texel density. Blockbench's Minecraft style guidance explicitly emphasizes preserving UV pixel ratio and avoiding stretched/squashed texels.

## Palette construction

Build palettes by material, not by one global brightness ladder.

For each material define:

- base hue family;
- shadow hue shift;
- highlight hue shift;
- saturation behavior;
- darkest structural accent;
- brightest focal accent;
- optional emissive ramp.

Typical low-res asset benefits from 3-6 meaningful values per material. More colors are justified only when they create a readable new surface, light effect, gradient step, or focal accent.

## Cluster discipline

Prefer:

- connected 2-8 pixel clusters over isolated single-pixel salt-and-pepper noise;
- large readable value masses first;
- intentional corner/edge highlights;
- repeated motifs with controlled variation;
- asymmetric detail at focal zones, not random everywhere.

Avoid:

- uniform dithering over the entire surface;
- one-pixel noise that vanishes at game scale;
- pillow shading around every cube;
- texture detail that contradicts geometry edges;
- excessive outlines on internal surfaces.

## Material cues

### Wood / bark

Use directional bands, knots, grain interruption, and darker creases. Keep grain direction consistent with the object's construction.

### Metal

Use sharper value jumps, sparse bright edge hits, dark reflective bands, and clean planes. Damage should interrupt reflections rather than merely add brown noise.

### Cloth / leather

Use broad folds, seam/strap logic, softer highlights, and darker compression zones around joints.

### Stone

Use broken clusters, chips, strata, and sparse hue temperature shifts. Keep the large form readable before adding speckle.

### Organic skin/fur

Use anatomy-guided value masses. Fur reads from clumped directional accents, not static noise on every pixel.

### Leaves/moss/flowers

Use overlapping color clusters and silhouette variation. For modded flora, keep petal/leaf centers readable at normal distance; use planes/alpha strategically for fine foliage.

### Magic/energy

Separate glow core, colored body, and falloff edge. Animated energy should change shape/intensity, not only hue, when the reference does.

## UV and texel density

- Establish a target pixels-per-Blockbench-unit ratio and preserve it across connected parts unless the reference deliberately mixes scale.
- Use box UV when it creates coherent wrapping efficiently; use per-face UV when orientation and local control matter.
- Hide seams under natural construction boundaries where possible.
- Keep mirrored UV only when mirrored texture is actually acceptable; break symmetry for scars, runes, facial details, text, or asymmetric wear.
- Never stretch a 1-pixel line into a visibly wider rectangle by accident.

## Facial readability

At 16x-style density, one pixel can change expression drastically. Lock:

1. eye spacing;
2. eye vertical level;
3. pupil/highlight direction;
4. brow/upper-lid angle;
5. mouth width/offset;
6. nose/snout landmark;
7. cheek/jaw shadow.

Judge from the intended in-game camera distance, not only at 800% zoom.

## Emissive/glow work

Use emissive masks only for intended luminous regions. Preserve a non-emissive material read beneath the glow when the runtime supports it. Check how the chosen renderer/library handles emissive + animated textures; GeckoLib 4 documentation currently notes that its animated textures are not compatible with GeckoLib emissive textures, so design around that limitation rather than shipping a broken combination.

## Animated textures

Use `scripts/animated_texture_builder.py` to build a vertical frame strip and `.png.mcmeta` safely.

Animation design patterns:

- pulse: slow brightness/value expansion and contraction;
- shimmer: localized highlight movement, not full-image brightness cycling;
- rune: sparse sequential illumination;
- flame/energy: shape evolution plus intensity variation;
- eye blink: long holds with very short transition/closed frames;
- liquid: directional texture flow with loop-consistent endpoints.

For sprite-like changes, prefer discrete frames. Use `interpolate: true` for effects where smooth blending is desired and faithful.

## Acceptance checks

- texture is crisp at native scale;
- no unintended antialiasing/blur;
- no UV stretching;
- seams are hidden or intentional;
- palette remains readable under Minecraft lighting;
- emissive regions do not flatten the whole material;
- animated texture loops without a visible hitch;
- mipmapped distance does not destroy the subject's defining landmarks.
