# Visual QA quality gates

Use the relevant gates before declaring a visual project or conversion complete.

## Source integrity

- Critical source assets are present and identifiable.
- Exact-preservation assets have SHA-256 hashes recorded where useful.
- Converted textures that should be byte-identical are compared byte-for-byte.
- No stale prior-version asset is silently substituted.
- Every upstream file is classified as exact runtime, derived runtime, or archival/provenance-only.
- Author-intended gameplay/visual sidecars are not silently discarded because they were global vanilla replacements in the source pack.
- If particles/sounds or another expected category are absent, the inventory proves the count is zero.

## Geometry / hierarchy

- Bone/part counts match the intended source representation.
- Parent-child hierarchy is equivalent.
- Pivots/origins are converted in the correct coordinate space.
- Bind-pose rotations use the correct signs/order.
- Cube origins, sizes, deformation/inflate, UVs, and mirroring match.
- Thin/negative-inflate parts remain intentional and do not collapse.
- No child part crosses the body because a parent transform was double-negated.

## Animation

- Loop duration matches source.
- Translation, rotation, and scale signs are correct.
- Linear, step, Catmull-Rom, Bezier, or expression-driven channels preserve their intended interpolation.
- Runtime animation overrides do not erase source bind pose accidentally.
- `resetPose()` is applied at the correct hierarchy level before additive animation.
- Opposing limbs preserve source phase/sign relationships.
- Blink/secondary motion is visibly tested, not only inferred from code.
- At least several checkpoints across the loop are inspected.

## Standalone / vanilla-derived content

- Namespaced standalone content does not accidentally override `assets/minecraft` or unrelated vanilla registries.
- Themed vanilla mechanics are checked against the target version's vanilla geometry, behavior and renderer as an oracle.
- Source-format adapter files are not copied blindly when the target has a native equivalent that preserves the same authored result more safely.
- Derived textures/models are regenerated deterministically and audited against the source pixels/data.
- Loot, recipes, localization, heads/skulls, paintings, particles/sounds and other companion content are included when authored for the source family.

## Grounded articulated poses

- Ground reference comes from a known-good standing/runtime pose and stays fixed across variants and before/after renders.
- Intended paw/foot/body contact points are measured numerically in world/model space, not judged only by pixels.
- Two-link articulated limbs use IK/contact targets when hand-picked angles cause floating or inconsistent reach.
- Whole-model minimum Y is checked in addition to named contact parts so tails or hidden cubes cannot penetrate the floor.
- Tail root placement is validated in parent/local bone space before adding wag/flick motion.
- Tail-body and tail-floor clearance are sampled over the entire additive idle envelope.
- Previously approved poses retain before/after rollback material, and unrelated methods/states are regression-locked where practical.

## Rendering

- 3D depth ordering is correct.
- Pixel textures use nearest-neighbor sampling unless intentionally filtered.
- Camera/scale are stable across comparison frames.
- Front, 3/4, side, and back views are available for conversion-sensitive models.
- Alternate layers (charged/emissive/armor) are composited as the runtime uses them.
- The preview is explicitly identified as deterministic render vs live capture.
- Suspicious output is cross-checked against a second render/runtime/vanilla reference before changing source solely to satisfy the preview.

## Release presentation

- Per-variant PNG and GIF exist when variants animate.
- All-variant gallery exists.
- Standalone companion assets are included in the approval gallery when relevant.
- MP4 exists when motion benefits from higher quality/size efficiency.
- Focused parity/anomaly sheet exists for repaired conversions.
- README notes source and verification scope.
- SHA-256 manifest and showcase ZIP are generated.
- Final material outputs are persisted to the project's canonical destination when available.
