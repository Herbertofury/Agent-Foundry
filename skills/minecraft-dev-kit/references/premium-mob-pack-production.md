# Premium mob-pack production standard

Research snapshot: **2026-09-06**. Use this when the goal is an original mob/boss pack that should feel competitive with expensive commercial MCModels packs. This is a craft and QA benchmark, not permission to copy paid assets.

## Public benchmark anchors

Current public product descriptions establish several useful upper-end bars:

- **RPG Class Boss [Mega Bundle] (Full)**: six bosses, 96 VFX and 70+ SFX. Individual bosses publicly advertise two phases, roughly 12-13 attack moves and roughly 21-24 animations, plus advanced directional/distance-aware combat behavior and admin configuration guidance. Public full-bundle price observed: **$129.99**.
- **RPG Mobs & Boss [Mega Bundle]**: 14 mobs, four bosses, eight equipment pieces and eight mounts, with ItemsAdder/Oraxen/Nexo integration. Public price observed: **$99.99**.
- **The Fallen Devastator | Supreme Boss**: 50+ advertised animations, about 4,500 lines of MythicMobs configuration, custom VFX, item/decor sidecars, voice/model expansion, arena and soundtrack options. 2026 update notes discuss prediction, dynamic stagger/cooldown behavior and animation/skill synchronization.
- **Bandit Assault V1**: three combat archetypes with three variants each, 25+ animations per archetype, low advertised bone count, parry/stagger/dodge controls, player-count/stat scaling, custom hitboxes, cliff/fall safeguards and extensive configuration.
- **Historical Infantry Mob Pack**: multiple faction variants, about 14 attack animations per unit, breakable shields/weapons, mid-fight weapon swaps and self-healing behavior.

Source pages to re-check when freshness matters:

- https://mcmodels.net/products/15501/rpg-class-boss-mega-bundle
- https://mcmodels.net/products/13857/rpg-mobs-boss-mega-bundle
- https://mcmodels.net/products/10603/the-fallen-devastator-supreme-boss
- https://mcmodels.net/products/10387/bandit-assault-v1-mobpack
- https://mcmodels.net/products/15054/historical-infantry-mob-pack

## The Dev Kit target

Do not chase price or raw counts. Match or exceed the **production qualities** behind the strongest packs:

1. coherent visual family with instantly readable silhouettes;
2. gameplay-complete rigs and animation vocabularies;
3. authored combat, not random skill spam;
4. VFX and SFX synchronized to actual gameplay events;
5. distinct variants/archetypes rather than recolor padding;
6. data-driven tuning and admin/developer ergonomics;
7. aggressive performance discipline;
8. complete packaging, documentation and native runtime QA.

A premium pack is a small game-content product, not a folder of models.

## Production sequence

### 1. Write the pack bible before modeling

Lock:

- one-sentence fantasy/purpose;
- target biome/encounter context;
- silhouette language;
- proportion language;
- texture density and palette rules;
- shared materials and emissive language;
- scale ladder from smallest mob to boss;
- roster roles and intended combat relationships;
- variant rules;
- performance budget;
- target Minecraft/loader/runtime.

Read `premium-creature-art-direction.md` before final concept/model decisions. For repeatable original geometry/rig blockout, use `creature-spec-authoring.md` + `creature-rig-archetypes.json` and compile with `creature_spec_compiler.py`; preserve Blockbench `.bbmodel` as the artist master rather than treating its internal schema as the only structural truth.

### 2. Design the roster as a combat ecology

Use functional roles such as:

- fodder / swarm;
- skirmisher;
- bruiser;
- ranged pressure;
- controller / area denial;
- support / healer / summoner;
- elite;
- miniboss;
- boss.

Every roster member needs a reason to exist. If two mobs produce the same silhouette, movement rhythm and combat decision, merge them or redesign one.

### 3. Build one vertical-slice creature first

Before multiplying variants, finish one representative entity through:

`model -> UV/texture -> rig -> complete motion set -> gameplay -> VFX/SFX -> native client/server QA -> performance check`.

Use that entity to establish names, pivots, resource layout, animation event markers, hitbox rules and render budgets. Only then scale the family.

### 4. Treat attacks as timed contracts

Every attack/skill should explicitly define:

- anticipation/windup;
- active/impact window;
- recovery;
- range/shape;
- authoritative damage instant or interval;
- animation event marker;
- VFX event marker;
- SFX event marker;
- interrupt/stagger policy;
- movement/root-motion policy;
- cooldown/reuse policy;
- multiplayer/targeting behavior.

Hitboxes must follow the visible move instead of using invisible convenience damage. Large invisible hitboxes require an explicit telegraph/justification.

### 5. Build complete motion vocabularies

Counts are evidence of breadth, not the goal. For premium production, a normal combat mob commonly needs enough authored states to cover idle variation, locomotion, aggro/alert, attack variation, hurt/stagger, death and any role-specific actions. Elites/bosses add phase changes, specialized movement, recoveries, summons/casts, blocks/parries/dodges and cinematic transitions.

Read `premium-combat-animation-vfx-sfx.md` before animation/VFX closeout.

### 6. Author advanced encounter behavior

For elites and bosses, implement deliberate decision-making:

- distance-aware move selection;
- left/right/front/back repositioning where useful;
- target-change stability;
- anti-stuck/cliff/arena safeguards;
- telegraph-aware cooldown logic;
- phase transitions with state cleanup;
- stagger/interrupt immunity windows where justified;
- multiplayer target distribution and optional scaling;
- anti-cheese responses that remain fair;
- spawn/prebattle/death cleanup;
- deterministic persistence/synchronization.

Read `premium-encounter-ai.md` for the full behavior contract.

### 7. Make variants materially different

A premium variant should change at least two meaningful dimensions among silhouette/accessories, palette/material treatment, animation personality, combat behavior, audio identity, VFX identity or environmental role. Recolor-only variants are fine as bonus skins, not as the primary content count.

### 8. Build VFX and SFX as one combat language

Use recurring motifs by damage school/faction. Players should learn what a color, shape, motion and sound family means. Keep anticipation, impact and lingering effects visually distinct. VFX must never hide unreadable animation or substitute for a weak pose.

### 9. Optimize by design

Do not wait for a profiler to make the pack sane.

- Keep bones/cubes proportional to visible benefit.
- Reuse shared materials/textures where appropriate.
- Avoid per-tick global entity scans and repeated resource lookups.
- Cache immutable definitions; make combat/event logic event-driven where practical.
- Bound projectile/VFX/particle concurrency.
- Cull or sleep nonessential client effects outside useful range.
- Keep hitbox math and animation state synchronization deterministic.
- Load-test packs with many simultaneous entities, not one showcase mob.

A low bone count is not automatically better; invisible complexity with no visual/gameplay value is the thing to remove.

### 10. Ship as a product

A release-ready pack/mod includes:

- complete source projects and provenance;
- models/textures/animation/VFX/SFX resources;
- native gameplay implementation;
- configurable stats and balance knobs;
- spawn/registry/data definitions;
- localization;
- install/use/developer notes;
- compatibility/version statement;
- deterministic QA scene/commands;
- performance evidence;
- visual showcase from the real assets/runtime;
- hashes and reproducible artifact.

## Benchmark profiles

`premium_mob_pack_gate.py` supports public-benchmark-inspired profiles. They intentionally represent **equivalent scope**, not a requirement to copy another seller's design.

### `boss-mega-2026`

Use for a hero/boss bundle comparable in scope to the strongest current expensive boss bundles:

- at least 6 bosses;
- each boss has at least 2 phases, 10 authored attack moves and 18 animations;
- pack totals at least 72 authored animations, 60 VFX and 48 SFX;
- each boss declares advanced AI, telegraph and phase-transition behavior;
- configuration, integration, performance and native QA plans are present.

The current public commercial reference exceeds several of these floors (96 VFX, 70+ SFX); the gate floor leaves room for fewer but more substantial effects while still requiring premium breadth.

### `mob-mega-2026`

Use for a broad creature/ecology pack:

- at least 12 standard mobs;
- at least 3 bosses/minibosses;
- at least 6 meaningful variants across the family;
- at least 6 equipment/drop/sidecar assets or equivalent gameplay content;
- strong role coverage, biome/spawn intent, complete standard animation states and pack-level QA.

### `supreme-boss-2026`

Use for one unusually deep encounter:

- at least 2 phases;
- at least 12 attack moves;
- at least 32 authored animations;
- at least 10 VFX and 8 SFX;
- at least 6 advanced AI/encounter features;
- explicit tuning controls, prediction/anti-cheese safeguards, phase cleanup and native runtime stress QA.

## Required QA

Run `scripts/premium_mob_pack_pipeline.py` during pack convergence. It composes:

- manifest/production gate;
- animation-state coverage audit;
- model complexity/performance-budget audit;
- attack timing/telegraph checks;
- creature-spec structural compilation where declared;
- attack animation impact-marker cross-linking;
- file/reference closure where source paths are supplied;
- premium benchmark equivalence report.

Then use Project Visual QA Showcase on the real assets and Minecraft Dev Kit native runtime gates. A green static premium scorecard is not permission to skip in-game proof.

## Fast original-authoring lane

For a creature that does not already have an artist master:

1. estimate/choose silhouette proportions and a rig archetype;
2. generate a semantic cuboid first-pass with `creature_blockout_generator.py`;
3. repack/validate box UVs with `creature_uv_packer.py`;
4. refine the creature spec and compile it with `creature_spec_compiler.py`;
5. move into Blockbench for the artist master, texture painting and curve polish;
6. preserve the spec as structural provenance or explicitly promote the artist master when it becomes authoritative;
7. run geometry/rig, animation-curve, event-marker and encounter-graph audits before native Visual QA.

The blockout generator supports humanoid, quadruped, avian, serpentine, arthropod, floating and dragon/multi-limb starting anatomies. These are proportion/rig accelerators, never finished designs.

## Premium release strictness

During iteration, warnings are diagnostic. At release convergence run:

`premium_mob_pack_pipeline.py ... --strict`

Strict mode converts every JSON-reported warning finding into a release blocker. Resolve, justify in source with an explicit supported override where the specific audit allows one, or change the asset/design. Do not ship a top-tier pack by accumulating ignored warnings.

Current premium pipeline coverage includes scope/art-direction completeness, animation-state mapping, model budgets, creature-spec compilation, geometry/rig quality, exact silhouette-clone detection, PNG/material/emissive audit, meaningful variants, staged VFX, SFX files/variation/spatialization, animation event timing, motion-curve structure, encounter graphs, combat-purpose/selection depth, native runtime contracts, a generated implementation ledger and deterministic visual/runtime shot lists.

## Production accelerators

Starting-point generators are intentionally separated from final-quality gates:

- `creature_blockout_generator.py`: semantic first-pass geometry/rig for seven anatomy families;
- `creature_uv_packer.py`: deterministic box-UV layout/growth;
- `creature_texture_blockout.py`: material-aware texture/emissive first pass;
- `creature_animation_blockout.py`: conservative idle/locomotion/hurt/death motion seeds;
- `creature_animation_retarget.py`: semantic-bone animation transfer across compatible variants/proportions;
- `procedural_sfx_blockout.py`: deterministic WAV/OGG timing prototypes;
- `premium_mob_runtime_plan.py`: target-native implementation ledger.

Generated starting assets never satisfy the artistry gate by themselves. Hand/refine the model, texture, curves, VFX/SFX and gameplay until deterministic visual/native QA converges.
