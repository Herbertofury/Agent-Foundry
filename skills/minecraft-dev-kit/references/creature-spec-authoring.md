# Creature specification authoring

Use this when building an original premium creature family from scratch, especially when repeatability, variants, procedural blockout, or runtime synchronization matter.

## Why a separate creature spec exists

Do **not** make `.bbmodel` the only machine-readable source of truth. Blockbench documents `.bbmodel` as its internal project format and warns that it can change; Blockbench 5.0 also separated groups from outliner hierarchy and corrected animation keyframe axis directions. Preserve the artist's `.bbmodel`, but keep reusable structural intent in a stable Dev Kit creature spec.

The spec is not a replacement for artistic judgment. It is a deterministic contract for:

- hierarchy and semantic bone names;
- pivots and parentage;
- cuboid blockout and UV placement;
- visible bounds and texture dimensions;
- animation names, lengths, loop policies, and bone tracks;
- gameplay marker vocabulary;
- variant inheritance metadata;
- performance budgets.

The Dev Kit compiler targets GeckoLib 4-style `.geo.json` + `.animation.json` runtime assets because those are explicit runtime formats. Continue to use Blockbench for sculptural cuboid placement, texture painting, curve editing, pose polish, and visual QA.

## Coordinate contract

Creature specs use Gecko/Bedrock model-space directly:

- positions, pivots, cube origins, and sizes are model units;
- rotations are degrees;
- a bone transform is local to its parent;
- cube `origin` + `size` defines its axis-aligned base volume before optional cube pivot/rotation;
- animation positions/rotations/scales are local bone channels.

Never guess or silently flip axes during import. When converting from an external source, establish that source's coordinate semantics first and record the transform used.

## Minimal schema

```json
{
  "schema_version": 1,
  "id": "mire_stalker",
  "texture": {"width": 64, "height": 64},
  "visible_bounds": {"width": 2.5, "height": 3.0, "offset": [0, 1.1, 0]},
  "bones": [
    {"id": "root", "pivot": [0, 0, 0]},
    {"id": "body", "parent": "root", "pivot": [0, 12, 0]},
    {"id": "head", "parent": "body", "pivot": [0, 18, -2]}
  ],
  "cubes": [
    {"id": "torso", "bone": "body", "origin": [-4, 8, -3], "size": [8, 10, 6], "uv": [0, 0]}
  ],
  "animations": [
    {
      "name": "idle",
      "length": 2.0,
      "loop": true,
      "bones": {
        "body": {
          "rotation": [
            {"time": 0.0, "value": [0, 0, 0]},
            {"time": 1.0, "value": [2, 0, 0], "lerp": "catmullrom"},
            {"time": 2.0, "value": [0, 0, 0]}
          ]
        }
      }
    }
  ]
}
```

## Authoring sequence

1. Pick a semantic rig archetype from `creature-rig-archetypes.json`.
2. Establish silhouette and scale with the fewest meaningful volumes possible.
3. Place pivots at actual joints before adding decorative geometry.
4. Add secondary silhouette masses only where they materially improve recognition or motion.
5. Lay out UVs with consistent texel density and deliberate seams.
6. Define the complete animation vocabulary before polishing individual clips.
7. Compile with `scripts/creature_spec_compiler.py` and run its lint checks.
8. Import/compare the generated runtime model in the actual mod; use Blockbench for the artist master and final curve/texture work.
9. After artist changes, either update the spec or explicitly mark the artist asset as the new structural authority. Never let two silently divergent sources both claim to be canonical.

## Premium rig principles

- Prefer one semantic bone per real articulation or needed runtime attachment, not one bone per cube.
- Put held-item, projectile, VFX, sound, seat/mount, head/look, ground/contact, and hitbox locators on semantically named nodes when the runtime needs them.
- Separate visual bones from gameplay hitbox definitions. A large visual appendage does not automatically need an expensive collision primitive.
- Keep root motion policy explicit. In most combat mobs the server owns authoritative translation while animation supplies local pose motion.
- Preserve mirrored left/right naming consistently (`arm_l`, `arm_r`, etc.) so procedural retargeting and QA can reason about symmetry.
- For bosses, isolate phase-specific attachments so phase transitions can enable/disable them cleanly rather than spawning duplicate model state.

## Variant strategy

Use one of three explicit variant modes:

- **material variant**: same silhouette/rig, new texture/material/emissive language;
- **attachment variant**: same base rig plus removable horns, armor, packs, weapons, foliage, etc.;
- **behavioral/body variant**: meaningfully altered proportions, animation personality, or combat role.

Do not mutate the shared base merely to make a variant visually different. Capture deltas explicitly and keep inherited bone IDs stable when animation sharing is intentional.

## Acceptance

The compiler passing means the structure is valid, not beautiful. Premium acceptance still requires:

- deliberate silhouette and proportions;
- hand-inspected UV/texture craft;
- non-mechanical animation arcs and timing;
- VFX/SFX/gameplay synchronization;
- multi-angle/multi-time deterministic visual QA;
- real Minecraft client/server runtime proof and stress testing.

## Event-marker runtime bridge

The compiler emits every creature-spec marker into the GeckoLib animation `timeline` as a custom instruction token:

`devkit_event:<kind>:<marker-id>`

If multiple events share a timestamp, tokens are joined with `||`. It also emits a readable `.events.json` sidecar. For Forge/NeoForge gameplay, register a GeckoLib custom-instruction keyframe handler and route these tokens into authoritative server/gameplay events as appropriate. The animation event is a synchronization signal; authoritative damage/state still belongs to server logic.

Premium attack manifests declare `impact_marker`, `vfx_marker`, and `sfx_marker`. `mob_event_marker_audit.py` requires those markers to exist in the mapped attack animation and checks the damage-impact marker against the declared windup endpoint.
