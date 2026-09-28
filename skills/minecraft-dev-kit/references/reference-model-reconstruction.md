# Reference-to-model reconstruction lab

Use this workflow when the target model, texture, prop, creature, cosmetic, or animation must be reconstructed from one or more visual references rather than from source geometry.

The objective is not merely stylistic similarity. Match every observable property of the reference as closely as the available evidence allows, while labeling genuinely unobservable hidden geometry as an inference rather than pretending it was recovered exactly.

## 1. Evidence intake

Preserve the original reference untouched. Record:

- image/GIF dimensions and frame timing;
- transparent vs baked background;
- camera perspective clues;
- visible front/side/top planes;
- known Minecraft scale anchors (player head, 16-pixel item, block, hand, hitbox, UI slot, etc.);
- animation cycle length and obvious contact frames;
- likely texture density (commonly 16x-style or 32x-style on MCModels assets, but infer from the actual reference);
- occluded surfaces and ambiguous depth.

For high-fidelity inverse work, read `reference-exact-reconstruction.md` and prefer `scripts/reference_reconstruction_pipeline.py`. Its staged tools recover frame/mask/palette evidence, fit cameras/cuboids, fit GIF pose tracks, back-project visible texture texels, and quantify still/GIF parity. `reference_asset_probe.py` and `gif_pose_sampler.py` remain useful lightweight probes.

## 2. Solve the camera before over-modeling

A wrong camera can make correct geometry look wrong.

1. Estimate orthographic vs perspective projection from parallel edges and foreshortening.
2. Match yaw/pitch/roll and subject framing first.
3. Anchor a known-length feature to establish world scale.
4. Render a primitive blockout and compare silhouette before adding detail.
5. If a single view is ambiguous, keep 2-3 depth hypotheses briefly and eliminate them with cast-shadow, overlap, face-area, or animation evidence.

Do not compensate for a camera error by distorting the model.

## 3. Build silhouette-first

Work from largest visual masses to smallest accents:

1. primary body/head/prop mass;
2. secondary limbs, handles, horns, wings, plates, fins, leaves, clothing layers;
3. tertiary silhouette breakers such as ears, spikes, hair tufts, vines, straps, fingers, teeth;
4. planes/transparency for thin parts when that matches Minecraft visual language better than many tiny cubes;
5. only then add micro-geometry.

At each stage render against the reference and compare occupied silhouette. A model with excellent texture but the wrong silhouette is not high fidelity.

## 4. Infer hidden depth conservatively

From a single image, exact unseen geometry is mathematically underdetermined. Use these priors in order:

- visible edge lengths and face foreshortening;
- symmetry when the design supports it;
- repeated motif thicknesses;
- Minecraft pixel/unit consistency;
- plausible joint clearances for animation;
- cast shadows and self-occlusion;
- category anatomy (quadruped, humanoid, bird, dragon, furniture, weapon, etc.);
- lowest-complexity hidden solution that preserves all visible evidence.

When the user requests an exact replica, define exactness as **pixel-level visible-view parity plus internally consistent hidden surfaces**, not impossible recovery of unseen information.

## 5. Rig architecture before animation

Create pivots where motion actually originates. Typical hierarchy:

```text
root
  body
    chest
      neck
        head
      arm_l -> forearm_l -> hand_l
      arm_r -> forearm_r -> hand_r
    pelvis
      leg_l -> shin_l -> foot_l
      leg_r -> shin_r -> foot_r
    tail_01 -> tail_02 -> ...
```

For creatures, add independent chains for ears, jaw, wings, fins, antennae, tendrils, hair, cloth, or accessory layers when the reference shows secondary motion.

Rules:

- pivot at the anatomical/mechanical joint, not the cube center by convenience;
- keep bind pose clean and reproducible;
- name mirrored parts consistently;
- avoid a single oversized bone when reference motion requires local overlap;
- test extreme poses for clipping before polishing animation;
- reset custom root/parent parts to bind pose before additive runtime transforms.

## 6. Texture reconstruction order

Read `references/pixel-texture-art.md` for the full texture discipline. In brief:

1. lock texel density and UV ratio;
2. recover large color families;
3. recover material-separated ramps;
4. paint large clusters and value planes;
5. add edge accents and focal contrast;
6. add sparse material noise only where the reference supports it;
7. reproduce transparency/emissive regions;
8. validate at native Minecraft viewing size, not only zoomed-in.

Do not use smooth anti-aliased painting on a deliberately pixel-art target unless the source clearly does.

## 7. Animation reconstruction from GIF/video

Read `references/animation-reconstruction.md`.

Extract and match:

- cycle length;
- contact poses;
- passing/extreme poses;
- ease timing;
- root travel;
- arc direction;
- overlap/drag on appendages;
- attack anticipation, impact, recoil, recovery;
- idle asymmetry and breathing micro-motion;
- loop seam.

Prefer pose accuracy over excessive keyframe count. Add keyframes only where they preserve a visible change in trajectory, timing, or silhouette.

## 8. Reference render loop

Use a deterministic camera, FOV/projection, resolution, background, and lighting. Keep those fixed while judging geometry.

Recommended iteration loop:

```text
reference -> blockout -> render -> visual_match_gate
          -> silhouette correction
          -> proportion correction
          -> texture/UV correction
          -> rig/pose correction
          -> animation timing correction
          -> native Minecraft proof
```

Use `scripts/reference_parity_gate.py` for strict still/GIF observable parity and `visual_match_gate.py` for legacy/simple comparisons. Metrics are diagnostics plus regression gates, never a substitute for human inspection or native runtime proof.

## 9. Fidelity gates

Do not call a reconstruction complete until all observable categories pass:

- silhouette: no material missing/excess lobes or thickness errors;
- proportions: major landmarks align;
- camera: the candidate is not being rescued by a different view;
- value structure: major light/dark groups match;
- palette/materials: hue families and material separation match;
- texel density: no unintended stretching/mixels;
- facial/readability landmarks: eyes/mouth/nose/crest/etc. match position and scale;
- negative space: gaps between limbs/accessories match;
- pose: joint angles and weight distribution match;
- animation: contact/extreme timing and loop seam match;
- runtime: no clipping, floating, disappearing, transform accumulation, missing texture, or atlas warnings.

For a single reference view, preserve a render from that exact view as the primary acceptance target. Add front/side/back QA renders to ensure inferred hidden surfaces remain coherent.

## 10. Model class routing

Choose the target format based on actual use:

- vanilla Java block/item: Java Block/Item model + display transforms;
- vanilla/modded Java entity with code model: Modded Entity workflow;
- GeckoLib animated entity/item/block/armor: GeckoLib model + `.geo.json` + `.animation.json` + texture;
- Bedrock entity: Bedrock geometry + animation controllers;
- plugin/server content: ModelEngine/ItemsAdder/Nexo/Oraxen/Crucible format as required by the project;
- cross-edition asset: preserve a neutral Blockbench source and export per target rather than forcing one compromised runtime format.

Never assume a marketplace dependency is the user's runtime architecture; reconstruct the art into the project's native mod stack whenever that is the actual goal.
