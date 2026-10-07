# Exact observable reference reconstruction

Use this lane when one or more **authorized** images, GIFs, turntables, or captures are the source of truth for a Minecraft model/texture/animation. The target is not “similar style”; it is convergence on the pixels and motion that the references actually expose.

## Exactness contract

Separate three claims:

1. **Observed exactness** — candidate renders agree with supplied reference views/times within explicit parity thresholds.
2. **Inferred coherence** — hidden/occluded geometry and unseen texels form a plausible, animation-safe 3D object but are not falsely labeled recovered.
3. **Native correctness** — the real Minecraft runtime proves scale, lighting, culling, animation state, event timing, collisions/hitboxes, VFX/SFX, networking and persistence.

A single image cannot uniquely determine unseen depth. Do not manufacture certainty. Add views/turntable frames until ambiguity collapses or preserve the smallest coherent hypothesis.

## Rights boundary

Exact reconstruction of third-party commercial art requires the user's ownership/authorization to reproduce it. Public store previews may be studied as a quality benchmark; do not bypass a paywall, protected pack, or license. `reference_reconstruction_pipeline.py` requires `rights.authorized=true` in its contract.

## Evidence-first workflow

### 1. Stage reference media

Run `reference_media_ingest.py` or the full `reference_reconstruction_pipeline.py`.

Preserve:
- original SHA-256;
- every staged frame + timing;
- alpha/background mask method;
- silhouette bbox/centroid/area;
- edges;
- palette evidence;
- high-information animation frames.

Foreground masks extracted from a baked background are evidence, not truth. Visually verify them before fitting.

### 2. Get a zero-start 3D hypothesis, then solve camera and large masses

When no usable model exists:
- use `reference_asset_scaffold.py` for semantic sword/staff/bow/armor/head-cosmetic/furniture/decor anchors from sparse/single-view evidence;
- use `reference_visual_hull.py` when two or more calibrated silhouettes exist; it voxel-carves a conservative visual hull and compresses it back into Minecraft cuboids;
- for a true constant-camera rotation GIF, use `reference_turntable_calibrate.py` to infer yaw/framing across the loop, then feed those views to the visual hull. Orthographic and perspective seeds are supported; for perspective provide/infer FOV + distance and refine when needed. Keep a tight/explicit visible subject-height prior when the outer reconstruction bounds contain padding.

Use `reference_auto_refine.py` when you want evidence-constrained coarse-to-fine fitting without manually listing every cube parameter. It detects which world axes are observable from the cameras, can fit camera framing first, then accepts only model-part changes that improve the multi-view objective.

Use `reference_cuboid_fit.py` when exact parameter control is needed. It can optimize cube sizes/origins, bone pivots, camera yaw/pitch/scale/framing, and optional projected cuboid-edge constraints for armor panels, guards, visors, seams, and other geometry that does not change the outer silhouette.

Order parameters coarse-to-fine:
1. projection/FOV or ortho scale + framing;
2. world scale and primary masses;
3. secondary silhouette breakers;
4. tertiary forms;
5. only then pivots/micro-geometry.

Do not allow a geometry parameter to compensate for a known camera error. Keep front/side/three-quarter evidence jointly active so one view cannot overfit.

### 3. Recover motion from GIF/video evidence

Use `reference_sequence_probe.py` to detect motion span, seam quality and high-information times. Use `reference_motion_partition.py` to propose independently moving visible regions when the rig is unknown. Use `reference_pose_sequence_fit.py` to inverse-fit selected bone **rotation and position** channels to staged silhouettes. Its local solver escalates difficult frames to a global search rather than silently accepting a weak pose.

The solved track is a **motion blockout**. Then refine:
- arcs;
- contact/foot plant;
- root travel;
- overlap/drag;
- anticipation/impact/recovery;
- secondary chains;
- loop seam;
- texture/internal-feature alignment.

Compare the full candidate loop with `reference_parity_gate.py`; do not judge only hand-picked keyframes.

### 4. Recover visible texture evidence

After geometry/camera alignment, use `reference_texture_bake.py` to project visible pixels back into the creature spec's box-UV atlas. It writes coverage plus an optional confidence map; cross-view color variance exposes lighting/calibration conflicts instead of silently averaging them away. If the preview has obvious baked illumination, `reference_texture_delight.py` can produce a conservative draft albedo/palette and emissive-candidate mask while preserving the original recovered atlas.

Rules:
- unobserved texels remain transparent or come from an explicitly supplied base; never hallucinate them as “recovered”;
- validate box-UV orientation against the target exporter/runtime;
- separate baked preview lighting from likely albedo/material ramps;
- consolidate noisy sampled colors into the target's intended pixel-art material language;
- preserve transparency/emissive evidence separately where applicable.

Additional views increase UV coverage and disambiguate materials.

### 5. Quantitative parity

`reference_parity_gate.py` supports stills and GIFs and measures:
- translation-aligned silhouette IoU;
- tolerant silhouette-edge agreement;
- internal image/geometry edge agreement, so identical silhouettes with wrong seams/panels still fail;
- SSIM;
- foreground CIEDE2000 color error;
- weighted observable score;
- DTW temporal correspondence for animations;
- duration ratio.

Use strict thresholds appropriate to the source. A green score is necessary evidence, not permission to ignore a visibly wrong detail.

### 6. Residual-driven refinement

For each failed view/time, classify the residual before editing:
- camera/framing;
- missing/excess silhouette;
- incorrect depth/occlusion;
- pivot/pose;
- UV orientation/stretch;
- material/palette;
- animation timing;
- VFX/SFX/gameplay presentation.

Use `reference_residual_map.py` to separate missing silhouette from excess silhouette into connected regions. Change the earliest causal owner, rerender only invalidated views/times, then rerun the full parity set at convergence. Do not hide a camera or hierarchy defect with texture noise.

### 7. Native-medium proof

Use Project Visual QA Showcase on the actual model/texture/animation source, then Minecraft Dev Kit native client/integrated-server proof. For articulated entities, inspect non-obvious animation times and all important views. Exact marketing-preview parity is not enough if the native entity clips, floats, desyncs or disappears.

## Model-class routing

- **Mob/boss:** creature spec / Blockbench artist master -> GeckoLib/native renderer + gameplay/runtime contracts.
- **Weapon/item:** use the closest semantic scaffold before auto-refine. Built-ins cover sword, dagger, greatsword, axe, mace, hammer, spear, polearm/glaive, scythe, shield, crossbow, staff and bow; fit hand/display transforms separately from world geometry.
- **Armor/cosmetic:** use armor/head-cosmetic scaffolds and `player-rig-oracles.json`; preserve default/slim rig differences and test first/third person plus armor layers.
- **Furniture/decor:** use placement/seat/interaction locators, fit world geometry, then validate collision and interaction volumes separately.
- **Skill icons/UI/item sprites:** use `reference_sprite_extract.py` for grid/component extraction and nearest-neighbor reconstruction. A filtered/compressed preview cannot reveal original pixels that are no longer present.
- **Animated texture/UI asset:** use frame-exact texture tools rather than inventing 3D geometry.

## Pack-level premium consistency

When several assets are meant to ship as one commercial-quality family, run `reference_pack_consistency_audit.py`. It checks family texel-density drift, shared material-palette drift, declared-distinct shape clones and byte-identical recolor padding while preserving intentional class differences. Mark assets `must_be_distinct` when variety is a product promise; coherence is not an excuse to clone silhouettes.

Use the split marketplace regressions to keep validation stall-safe:
- `reference_marketplace_static_selftest.py` — semantic asset breadth, player/world context fitting, icon extraction and pack anti-clone rules;
- `reference_marketplace_motion_selftest.py` — perspective turntable/hull and internal-edge animation recovery.

The older full marketplace self-test is opt-in only; do not make release validation depend on a monolithic long command when the two bounded lanes prove the same frontier more reliably.

## Full contract pipeline

`reference_reconstruction_pipeline.py <contract.json> --out <dir>` is the durable orchestrator. It uses bounded child-process leases and produces `RECONSTRUCTION-RECEIPT.json` plus hashes for material outputs. Supported contract stages are:

`media -> temporal probe + optional sprite extraction -> semantic scaffold or still/perspective/orthographic turntable visual hull -> automatic/explicit geometry-camera refinement -> attachment/context fit -> motion partition + silhouette/internal-edge pose fits -> visible texture bake/confidence/de-light draft -> parity + residuals -> optional pack-consistency audit`.

Preserve the contract with the final asset so later iterations can rerun the same evidence rather than rediscovering cameras/frames/thresholds.

## Release bar

Do not say “exact” unless every supplied required view/time passes its recorded parity threshold and a human review finds no material observable mismatch. Say **inferred** for unseen structure. Say **native verified** only after the actual target Minecraft build has been loaded and exercised.

## Reference authority and collection reconciliation

Before fitting, reconcile original ChatGPT/Drive/project references with
`scripts/reference_catalog.py ROOT --policy POLICY.json --output CATALOG.json`.
The explicit policy assigns directory roles and per-file overrides; unknown files
stay unclassified. Primary designs, alternate states, baseline textures,
inspiration, rejected iterations and superseded art are distinct roles. Preserve
original bytes and record source/decision links. Byte-duplicate and decoded-pixel-duplicate groups are reported separately,
never deleted automatically. PNG metadata differences do not establish a new design.
Pixel comparison includes orientation, color-profile bytes and all animation frames/timing.

For a modeling target, add `variant`, optional `state`, and `expected_sha256` to
its override. Use `--variant ID --state base` to require exactly one hash-pinned
primary/state target. A filename, folder membership, or newer timestamp alone
must not silently approve a reference. Rejected/superseded art cannot be selected.
Run `reference_catalog_selftest.py` after changing this gate.

A catalog verifies identity and selection only. It does not prove that a model
looks like its reference. Keep reference-view geometry, eyes/lashes, crown and
hair volume, foot attachments, materials, glow and animation acceptance separate
from build/server success. Preserve the user's no-image-generation requirement
when it applies; native screenshots must always remain distinguishable from
concept art and offline renders.
