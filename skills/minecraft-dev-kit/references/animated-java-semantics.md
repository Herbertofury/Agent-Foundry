# Animated Java conversion semantics

Research snapshot: 2026-09-06. Revalidate current schema when format compatibility is load-bearing.

## Distinguish source layers

- `.ajmodel` is the authoring project and should be preserved when available.
- Animated Java's **Plugin Blueprint** JSON is a current exported runtime/interchange form. It is richer than a vanilla Java item model and should not be reduced to bone keyframes prematurely.
- Generated resource-pack/datapack assets are downstream evidence, not substitutes for the authoring/runtime blueprint.

Use `scripts/animated_java_blueprint_ir.py` for Plugin Blueprint JSON.

## Current Plugin Blueprint semantics

The current public schema requires `format_version` and `settings.id`, then exposes textures, texture palettes, nodes, and animations.

### Textures and palette state

A texture may be embedded custom PNG data or a Minecraft resource-location reference. Custom textures may carry animated-texture metadata: interpolate, frame dimensions, frametime and explicit frame/time entries. Texture palettes define named states and an active state; animations can switch palette states through global texture keyframes.

### Node types

Preserve node type rather than flattening everything to a bone:

- `bone`: cuboid elements with from/to/rotation, shade, light emission, per-face UV, tint, texture or texture-palette provider, display rotation;
- `item_display`: item stack + display context plus common display properties;
- `block_display`: block state plus common display properties;
- `text_display`: text/alignment/background/opacity/see-through/shadow properties;
- `structure`: semantic/grouping node;
- `camera`: camera path/state source;
- `locator`: attachment/effect/event anchor.

Default transformations may contain a full matrix and/or decomposed/position/rotation/head-rotation/scale forms. Preserve the original representation before coordinate conversion.

Common display semantics include billboard mode, custom sky/block brightness, custom name, glow color/state, shadow radius/strength. These may require native entity/display equivalents or an explicit approximation in older target versions.

### Animation

A dynamic animation carries:

- loop mode `once`, `hold`, or `loop` (loop may have a Molang `loop_delay`);
- Molang `blend_weight` and `start_delay`;
- numeric duration;
- global texture-state keyframes;
- global event keyframes;
- per-node position/rotation/scale tracks.

Transformation values are Molang vector expressions, not just literals. Keyframe interpolation supports linear + named easing, Bezier handles, Catmull-Rom and step. Never bake these curves before preserving the original expression/interpolation data.

Event keyframes are named API events; map them to native animation events/server-authoritative gameplay hooks when they affect mechanics, or client audiovisual hooks when presentation-only.

## Mod conversion policy

1. Preserve `.ajmodel` and the exported Plugin Blueprint when both exist.
2. Build a semantic ledger for display nodes, locators, camera, palette states, events, Molang, interpolation, easing and loop behavior.
3. On modern display-entity targets, reproduce display semantics directly where practical. On older targets such as Forge 1.20.1, decide explicitly whether each display feature becomes native renderer geometry, a child entity/layer, UI/text renderer, or a documented unsupported source feature.
4. Do not translate event keyframes blindly to client-only callbacks if they drive damage, spawning, projectiles or other authoritative behavior.
5. Compare the converted model at multiple times/states and against the original AJ runtime/export when available.
