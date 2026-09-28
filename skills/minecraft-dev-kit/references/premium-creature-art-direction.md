# Premium creature art direction

Use this before final modeling/texturing decisions for an original premium mob family.

## Build a recognizable family language

Write five constraints that remain visible across the whole pack:

1. **Primary shape language** - round/soft, square/armored, triangular/aggressive, stretched/eldritch, etc.
2. **Proportion rule** - head/body/limb relationship and exaggeration style.
3. **Material hierarchy** - which surfaces dominate and which are accents.
4. **Color hierarchy** - neutral base, faction color, emissive/accent color.
5. **Detail hierarchy** - where dense detail is allowed and where forms stay quiet.

A player should recognize the faction in silhouette or grayscale before reading a name tag.

## Silhouette ladder

Design the whole roster on one sheet/mental lineup before polishing textures. Ensure:

- no two primary combat roles collapse to the same outline;
- boss silhouettes read at normal gameplay distance;
- important weapons/appendages remain visible during attacks;
- variants preserve family identity while changing at least one large/medium shape;
- negative space around arms, horns, wings, weapons or tails remains deliberate.

Check front, side and three-quarter views. A model that only works from its product-card angle is not done.

## Shape rhythm

Use large -> medium -> small forms. Avoid covering every surface with same-size cubes/details.

- Large forms establish anatomy and role.
- Medium forms explain armor, muscles, feathers, plates or equipment.
- Small forms reward close inspection and should not destroy the silhouette.

Keep asymmetry purposeful. One shoulder plate, damaged horn, pouch cluster or fungal growth can create identity more efficiently than extra noise everywhere.

## Pixel texture craft

Stay faithful to the chosen texel density. For Minecraft-native 16x/32x work:

- use clusters instead of one-pixel confetti;
- keep material ramps distinct;
- reserve the lightest/darkest values for focal structure;
- hue-shift shadows/highlights where it helps material identity;
- keep faces/eyes readable at actual gameplay scale;
- align UV density between adjacent parts unless a focal feature intentionally gets more resolution;
- avoid baked lighting that fights in-game lighting.

Use emissive detail sparingly as a focal signal, not a blanket glow layer.

## Material readability

At a glance, stone, bone, metal, leather, cloth, wood, chitin, flesh, fur and magic should not share the same contrast rhythm.

- metal: tight bright highlights, controlled dark separation;
- cloth: broader value groups, softer contrast;
- bone/stone: planar value breaks and edge wear used selectively;
- fur/feather: directional clusters, not random noise;
- organic/flesh: warmer/cooler transitions and softer structural edges;
- magical/emissive: dark support values around a limited luminous core.

## Faces and personality

Premium creatures need readable attention direction. Even non-humanoids benefit from:

- clear eye/face focal point;
- head tilt capability;
- asymmetric idle attention;
- jaw/beak/mouth articulation when attacks or sounds need it;
- brows/ears/crest/antennae/tail or equivalent secondary personality controls.

Do not add facial bones that never contribute to a visible state.

## Variant rule

Use roughly a 70/20/10 concept split as a design heuristic:

- ~70% shared family anatomy/visual language;
- ~20% role/variant-defining silhouette or equipment changes;
- ~10% palette, markings, damage/wear or special accents.

This is not a mathematical quota. It prevents two bad extremes: identical recolors and variants so different they stop reading as one family.

## Boss escalation

A boss should feel like the visual culmination of the family without becoming unrelated.

Escalate two or three of:

- scale;
- silhouette width/height;
- armor/appendage hierarchy;
- emissive focal points;
- weapon complexity;
- motion amplitude;
- environmental/VFX interaction.

Do not escalate every axis simultaneously; visual hierarchy needs quiet areas.

## Native-medium approval gate

Before calling the art direction locked:

- render/capture front, side, back and three-quarter from the real model;
- compare the whole roster at common scale;
- inspect at normal gameplay distance and close-up;
- inspect base lighting and dark/bright environments;
- check variants in grayscale/silhouette;
- verify texture filtering and atlas behavior in the actual client.
