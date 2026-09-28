# Premium combat animation, VFX and SFX

Use for premium mobs, elites and bosses after the rig and gameplay role are known.

## Motion quality hierarchy

Build movement in this order:

1. root/body weight transfer;
2. major limb/weapon action;
3. head/aim/focus;
4. secondary appendage follow-through;
5. micro-motion.

Particles cannot repair bad weight transfer or unreadable poses.

## State vocabulary

A premium normal combat mob should cover every state its gameplay can enter, typically including:

- idle plus at least one personality variation when appropriate;
- walk/run or equivalent locomotion;
- alert/aggro transition;
- multiple attacks matched to real move choices;
- hurt/flinch and optional stagger/knockback;
- spawn/emerge when the encounter needs it;
- death;
- role states such as block, parry, reload, cast, burrow, fly, swim, eat, sit or mount.

Elites/bosses add:

- phase transitions;
- directional dashes/repositions;
- combo branches;
- large casts/ults;
- summon/control states;
- recoveries/whiffs;
- stun/guard-break/enrage;
- cinematic intro/outro when justified.

## Attack timing contract

For every damaging move record:

`windup -> active -> recovery`

and tie gameplay to named markers such as:

- `telegraph_start`;
- `foot_contact`;
- `weapon_release`;
- `impact`;
- `projectile_spawn`;
- `recovery_start`;
- `recovery_end`.

Damage, hitbox activation, projectile spawn, VFX and SFX should derive from the same event contract instead of independent magic delays.

## Pose and timing standards

- Anticipation must expose intent before fast/high-damage moves.
- The impact pose must read in silhouette for at least one meaningful instant.
- Recovery length communicates punishability.
- Planted feet must not slide unless the move intentionally skids.
- Root motion must not double-apply with entity navigation.
- Weapon tips/hands/feet should travel in deliberate arcs, not zig-zag between keys.
- Turn/strafe movement must preserve body aim and foot logic.
- Phase transitions must end in a valid next-state bind/pose.

Use graph easing to communicate mass: light creatures accelerate/decelerate differently from stone/armored bosses.

## Combo design

Do not create 12 attacks that are only different animation files. Distinguish moves by combat purpose:

- fast check;
- committed heavy;
- gap closer;
- disengage/reposition;
- anti-circle/side coverage;
- ranged pressure;
- area denial;
- punish/heal interrupt;
- summon/control;
- defensive counter;
- phase signature.

A good AI chooses among these based on context.

## VFX language

Build each effect in layers:

1. **anticipation** - small, readable cue;
2. **action path** - slash trail/projectile/beam/travel cue;
3. **impact** - short high-contrast confirmation;
4. **aftermath** - optional debris, decal, lingering hazard.

Use family-level motifs: shape, color, particle motion and emissive treatment should tell the player which faction/damage school produced the effect.

Avoid:

- giant opaque effects hiding the attacker;
- constant full-screen emissive noise;
- effects whose radius contradicts the actual hitbox;
- identical impact language for harmless and lethal moves.

## SFX language

Treat sound as gameplay feedback, not decoration. Useful layers include:

- vocal/creature cue;
- weapon/body transient;
- magic/mechanical body;
- impact layer;
- tail/reverb/energy decay;
- locomotion/foley.

High-threat attacks need a recognizable pre-impact cue. Reuse motifs enough that players learn them, but vary pitch/timing/variants so repeated attacks do not sound like a sample machine.

## Synchronization QA

For each attack sample at least:

- 25% through windup;
- one frame/tick before impact;
- impact;
- one frame/tick after impact;
- mid recovery.

Verify model pose, hitbox, damage, VFX and SFX line up. Check at low/high client FPS and under normal server load.

## Performance QA

Stress-test simultaneous effects. Record:

- maximum concurrent mobs;
- maximum concurrent active skills;
- particle/VFX entity count;
- client frame-time impact;
- server tick impact;
- network traffic/state synchronization issues.

Prefer fewer high-value effect layers over many unbounded emitters.

## Machine-audited animation/event minimums

When creature specs are available, run `mob_animation_curve_audit.py` and `mob_event_marker_audit.py`. They fail empty motion, broken loop seams, missing attack impact/VFX/SFX markers and major impact-timing drift; they warn on suspiciously sparse attacks or implausibly large adjacent rotation jumps. These checks catch structural mistakes only—appeal, weight, arc quality, overlap and acting still require deterministic visual review and native runtime capture.

## Animation acceleration without accepting robotic output

`creature_animation_blockout.py` seeds conservative motion for the semantic rig archetypes; `creature_animation_retarget.py` transfers clips between compatible rigs by stable bone IDs and can scale positional motion. Treat both as pose/timing scaffolds. Every retarget must re-check foot/contact placement, arcs, overlap, proportion-driven reach and attack hitbox timing in visual/native QA.
