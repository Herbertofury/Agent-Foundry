# Premium encounter AI and gameplay contract

Use for authored combat mobs/elites/bosses. The goal is readable, fair and replayable behavior that feels intentional instead of random skill spam.

## State model

Use an explicit server-authoritative state machine/behavior graph. At minimum model the states that actually exist, such as:

- dormant/prebattle;
- acquire/approach;
- combat neutral;
- attack commitment;
- reposition;
- recovery;
- hurt/stagger;
- phase transition;
- summon/cast;
- stunned/guard-broken;
- death/cleanup.

Every transition needs entry/exit cleanup. Never leave stale animation flags, hitboxes, invulnerability, speed modifiers or VFX after a canceled skill or phase change.

## Context-aware move selection

Choose moves using real context rather than one random weighted table. Inputs can include:

- target distance and relative angle;
- line of sight;
- recent move history;
- cooldowns;
- target movement/velocity;
- boss health/phase;
- nearby players/adds;
- arena bounds/terrain risk;
- stagger/guard state;
- threat/aggro history.

Keep enough randomness to prevent exact scripts, but preserve role identity and fairness.

## Telegraph fairness

High damage, crowd control or large-area attacks need a proportional warning. The warning can be animation, sound, VFX, movement lock or a combination. Do not hide lethal behavior inside ordinary locomotion.

## Movement quality

Support the encounter with:

- distance-aware walk/run switching;
- directional strafe/dash/reposition where useful;
- anti-stuck recovery;
- cliff/fall/void awareness;
- arena-boundary behavior;
- navigation fallback when the direct path fails;
- no oscillating move/stop state caused by tiny threshold changes.

Movement animation state must remain synchronized with actual velocity/navigation.

## Target management

For multiplayer:

- do not swap target every tick;
- add hysteresis/commitment to threat changes;
- define when off-target pressure is allowed;
- avoid permanently tunneling one player when the design calls for group pressure;
- make summons/projectiles inherit ownership/team correctly;
- clean target references on death/logout/dimension change.

## Stagger, parry and interruption

If supported, explicitly define:

- which moves can be interrupted;
- stagger meter/threshold;
- immunity windows;
- guard/parry timing;
- knockback policy;
- diminishing returns or dynamic cooldowns;
- phase-transition immunity.

Prevent interrupt-lock without making the mob arbitrarily immune to player feedback.

## Scaling

Optional player-count/difficulty scaling should be data-driven. Prefer controlled scaling of health, stagger threshold, add count, cooldown or move selection. Avoid multiplying every number blindly; that can turn fair telegraphs into one-shots or create damage sponges.

## Anti-cheese

Handle exploits only when they matter to the encounter:

- unreachable ledges;
- permanent ranged kiting;
- doorway trapping;
- out-of-arena attacks;
- summon accumulation;
- safe-zone abuse.

Responses must remain telegraphed and thematic. Do not punish legitimate positioning just to force a script.

## Phase design

A phase should change decisions, not only recolor the boss or increase damage. Change one or more of:

- available moves;
- movement strategy;
- arena pressure;
- summons;
- defense/stagger rules;
- attack combinations;
- VFX/SFX language;
- objective/weak-point state.

Phase transitions require atomic cleanup and one authoritative phase value.

## Runtime QA matrix

Test at least:

- one player melee;
- one player ranged;
- multiple players attacking from different angles;
- target death/logout/change;
- terrain obstacle and cliff edge;
- low/high health transition;
- repeated stagger/interrupt attempts;
- canceled skill/phase transition overlap;
- chunk unload/reload or equivalent persistence path when applicable;
- many simultaneous mobs for server/client load.

Inspect fresh logs and actual state, not only visual output.

## Encounter graph source

For bosses/minibosses, keep a small explicit encounter graph (`encounter_file`) beside the gameplay implementation. Run `mob_encounter_graph_audit.py` to verify entry/terminal states, state/attack references, guarded transitions, reachability and phase-state presence. The graph is a design/provenance contract; production code may implement it directly or map it into a richer state machine, but runtime behavior must remain traceable back to the authored graph.
