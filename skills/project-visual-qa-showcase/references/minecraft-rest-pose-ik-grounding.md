# Minecraft Rest-Pose IK, Grounding, and Tail QA

Use this reference when repairing or authoring seated, loaf, side-rest, sploot/sprawl, lying, crouched, or other grounded entity poses.

## 1. Ground plane is world-space truth

- Derive the Minecraft floor from a known-good standing/reference pose, usually the lowest intended paw/foot contact point in world/model coordinates.
- Keep that reference fixed across before/after renders and across pose variants.
- Never auto-snap or auto-center each pose independently to the preview floor; that can hide runtime floating or floor penetration.
- Measure contact numerically in the same transformed hierarchy used by the renderer/runtime.
- For each intended support foot/paw/body contact, report `contact_y - ground_y` and gate it with a small positive tolerance.
- Inspect the whole mesh minimum Y as well as named contact parts. A paw can be correct while another cube/tail penetrates the floor.

## 2. Solve limbs from contact targets, not guessed angles

For articulated two-link legs, prefer static IK for grounded poses instead of hand-tuning upper/lower rotations.

Given link lengths `l1`, `l2`, a target vector `(targetY, targetZ)` in the limb's solve plane, and bind-axis offsets `a1`, `a2`:

```text
d = clamp(hypot(targetY, targetZ), abs(l1-l2)+eps, l1+l2-eps)
knee = acos(clamp((d^2-l1^2-l2^2)/(2*l1*l2), -1, 1))
target = atan2(targetZ, targetY)
upper = target - atan2(l2*sin(knee), l1+l2*cos(knee)) - a1
lower = knee + a1 - a2
paw = -(upper + lower)
```

- Use the actual exported/bind geometry to compute link vectors and lengths; do not assume vanilla proportions.
- Apply lateral offsets/yaw/roll separately from the planar IK solve.
- If a paw still floats, adjust the contact target/reach before moving the hip pivot unless the pose genuinely requires a hip translation.
- Clamp only where anatomy/runtime safety requires it; a clamp that is too tight can create systematic floating.
- When preserving a previously approved pose, regression-lock everything except the specific IK/contact parameter being changed.

## 3. Separate pose orientation from contact translation

- Rotating a whole model changes every descendant's world-space contact height. Recompute the required world/model Y compensation after the final rotation is known.
- For horse-style or side-rest poses, do not confuse "legs to the side" with "rotate the entire creature like a fallen log." Keep the lower-body/rest orientation and independently counter-rotate torso/neck/head when the desired silhouette is upright or alert.
- Verify orientation with transformed basis vectors (for example each part's world-space local-up vector), not only screenshots.

## 4. Audit every grounded pose family

For every rest state and every variant, sample multiple animation times and check:

- intended forepaw/foot contacts
- intended hind-paw/foot contacts
- torso/belly/hip contact when applicable
- whole-model minimum Y
- head/neck clearance
- leg-body and leg-leg overlap
- tail-body and tail-floor clearance

Use front, three-quarter, side, and back deterministic renders. A side camera can hide a floating far paw or tail behind the body.

## 5. Tail placement uses bone-space semantics

Before changing a tail, establish the tail bone's local growth axis, parent transform, bind rotation, and segment hierarchy.

- Do not fix clipping by adding arbitrary yaw/side offsets without understanding the local axis; that can turn the tail into a sideways lever.
- Place the root first, then shape distal segments.
- Keep static tail pose and lively secondary motion separate.
- Static pose must already clear body and floor before adding wag/flick motion.

### Rest-tail style guidance

- **Upright sit:** tail curls beside/behind the haunches; distal tip may wag softly.
- **Loaf:** tail wraps compactly along the hip/body edge or forepaws; motion should be tiny and cozy.
- **Horse/side rest:** tail lies/trails naturally behind the haunches with a mild side curve; avoid burying it under the torso.
- **Sploot/sprawl:** tail trails rearward between or above rear legs with a soft tip flick.
- **Alternate sit:** preserve the pose silhouette, but ensure the root is supported and the distal segment remains visible from multiple angles.

## 6. Lively-tail animation must be pose-aware

Use low-amplitude additive motion on top of a correct static base pose. A good default is a slower root movement plus a delayed, slightly larger distal segment:

```text
rootYaw += sin(phase) * rootAmp
tipYaw  += sin(phase - lag) * tipAmp
```

- Root amplitude should generally be smaller than distal amplitude.
- Add occasional asymmetric flicks rather than constant metronomic wagging for cat-like idles.
- Reduce amplitude for loaf/side-rest states; allow more for alert/upright sits.
- Never animate a support limb or tail through the floor merely to make the pose feel lively.
- Sample the full additive animation envelope when testing collisions, not only its neutral frame.

## 7. Before/after and rollback discipline

When correcting an approved or user-reviewed pose:

- Preserve the complete previous source or at minimum the exact affected source files plus deterministic before renders.
- Produce before/after views from the same camera, scale, fixed ground plane, and animation time.
- Record the exact intended delta (for example "rear-leg IK reach only") and regression-test that unrelated pose methods stayed byte-for-byte or semantically unchanged.
- Keep stable enum/state IDs when adding new rest states; append new IDs instead of reordering existing save-visible values.

## 8. Required pass criteria

Do not call a rest-pose fix complete until all relevant conditions hold:

- intended contact points are within the chosen ground tolerance across sampled times/variants
- no mesh part penetrates the floor beyond tolerance
- tail root/tip clear the body and floor over the full idle envelope
- multi-angle renders agree with the numeric measurements
- the deterministic renderer uses the same hierarchy and transform conventions as runtime
- before/after rollback material exists when changing an already-approved pose
