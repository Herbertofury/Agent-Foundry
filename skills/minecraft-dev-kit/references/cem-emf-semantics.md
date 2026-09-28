# OptiFine CEM / EMF conversion semantics

Research snapshot: 2026-09-06. Use `scripts/cem_ir.py` for authorized `.jem`/`.jpm` packs.

## Source structure

- `.jem` defines an entity model: texture, texture size, shadow size and a list of model entries.
- Each model entry targets a vanilla entity `part`, can **attach** to or replace that part, may inherit another custom model through `baseId`, may reference external `.jpm`, can scale, and can contain inline part-model fields and animations.
- `.jpm` defines reusable part geometry: texture/texture size, axis inversion, translation, rotation, UV mirroring, attachments, boxes, sprites, nested submodels, and submodel lists.

Preserve `attach` vs replace, `baseId`, model IDs, hierarchy, axis inversion/mirroring, `sizeAdd`/`sizesAdd`, texture mapping and attachment points.

## Geometry / UV

Boxes use `[x,y,z,width,height,depth]` coordinates. UV may be box-format `textureOffset` or per-face UVs, but those representations must not be mixed for one box. Sprites are also supported. Nested submodels inherit parent movement/rotation.

## Expression-driven animation

CEM animation is not primarily a clip/keyframe format. Each animation entry assigns an expression to a destination such as model translation (`tx/ty/tz`), rotation (`rx/ry/rz`), scale (`sx/sy/sz`), visibility, entity variables or render variables. Expressions are evaluated while rendering and may depend on time, limb swing/speed, age, head angles, frame time and other runtime data.

Therefore:

1. preserve destination-expression pairs verbatim;
2. identify stateful variables (`var.*` / `varb.*`) and render variables;
3. translate continuous formulas to equivalent runtime code/Molang-capable controller logic where possible;
4. only bake to finite keyframes if the source expression is provably periodic/bounded and the approximation is explicitly accepted;
5. test dynamic states, not only static screenshots.

## EMF oracle rule

For CEM-origin assets, Entity Model Features is an excellent behavior/rendering oracle. On Forge 1.20.1 the current snapshot includes EMF 3.0.11. Even when shipping a native/GeckoLib conversion, compare the source pack under EMF to the converted mod for part attachment, expressions, visibility, texture and pose behavior.
