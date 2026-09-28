# Animation reconstruction and animation artistry

Use when reproducing motion from GIF/video references or designing a polished animation set for a reconstructed model.

## Extract motion evidence first

For GIFs, run `scripts/gif_pose_sampler.py` and inspect both evenly spaced frames and high-motion frames. For video, first convert the relevant segment to a stable-FPS image sequence/GIF with FFmpeg, then sample it.

Record:

- FPS/frame duration;
- loop duration;
- first/last pose relationship;
- contact and impact frames;
- movement direction;
- root translation/rotation;
- limbs with phase offsets;
- parts with follow-through/drag;
- any smear-like pose exaggeration represented through cuboid transforms.

## Pose grammar

A convincing cycle normally needs fewer, stronger poses rather than dense near-duplicate keys.

### Locomotion

Identify:

- contact;
- down/compression;
- passing;
- up/extension;
- opposite contact.

Track the body/root separately from limb swing. Add head/tail/ear/cloth overlap after the base weight transfer is correct.

### Attack

Use:

1. anticipation;
2. acceleration;
3. impact/read frame;
4. recoil/overshoot;
5. recovery.

The impact pose must be readable in silhouette. Do not hide a weak attack under particles.

### Idle

Avoid perfectly synchronized sine-wave motion on every part. Use low-amplitude phase offsets:

- breathing/chest;
- head attention drift;
- tail/ear/finger secondary motion;
- occasional asymmetric micro-action.

### Flying/swimming

Separate propulsion cycle from body glide. Wings/fins should lead or lag the body based on the motion style. Keep body pitch/vertical oscillation coherent with the thrust phase.

## Timing reconstruction

From a reference GIF:

1. preserve the original frame durations when available;
2. mark extrema and impacts;
3. calculate relative timing between extrema;
4. recreate those ratios in Blockbench even if the final runtime uses a different FPS;
5. only smooth curves after pose timing matches.

If the reference holds a pose, keep the hold. Do not replace stylized stepped motion with uniformly smooth interpolation.

## Arc and overlap checks

For each important endpoint (hand, foot, horn tip, tail tip, weapon tip):

- trace its path over the cycle;
- look for unintended zig-zags;
- preserve deliberate arcs;
- check overlap phase against parent motion;
- make sure mirrored limbs are not accidentally identical when the source is offset.

## Blockbench implementation

Use position, rotation, and scale keys as needed. Use the graph editor for deliberate easing, not generic smoothing. Organize markers at gameplay events such as `impact`, `foot_contact`, `takeoff`, `land`, `cast`, `release`, `recovery`.

For GeckoLib, export model/animation assets in the expected resource directories and verify in the actual target version. Animation stacking/easings can be powerful, but reference fidelity comes first.

## Runtime animation set quality

For a production creature/entity, consider the complete state vocabulary implied by gameplay, not only the one reference clip:

- idle variants;
- walk;
- run/sprint;
- jump/takeoff/air/land;
- attack variants;
- hurt/flinch;
- death;
- sit/sleep/perch if applicable;
- swim/fly if applicable;
- interaction/petting/eating/shearing/etc. when mechanics require;
- transformation/phase changes for bosses;
- mount idle/ride/turn/start-stop where applicable.

MCModels' public catalog repeatedly treats animation count and gameplay-specific interaction animations as part of premium asset quality, ranging from small 4-6 animation pets to bosses with dozens or even 100+ animations. Use that as a quality bar for state completeness, not as a requirement to inflate key counts.

## Animation QA

- loop has no visible snap unless intentionally stepped;
- feet do not slide during planted contact;
- weight is supported over the correct limb(s);
- weapon/accessory does not clip through the body during important poses;
- tails/hair/cloth do not penetrate the ground;
- root motion does not double-apply with entity movement;
- custom roots reset to bind pose every frame before additive transforms;
- animation survives low and high client FPS;
- first-person/third-person/display contexts are checked when applicable.
