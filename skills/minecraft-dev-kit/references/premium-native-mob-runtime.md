# Premium native mob runtime blueprint

Research snapshot: **2026-09-06**. Use when turning an authored premium roster into a Forge/NeoForge/Fabric-native implementation. Version-specific APIs must be checked against the target project at implementation time.

## GeckoLib 4 entity architecture

Current GeckoLib 4 guidance uses:

- an entity class extending a normal Minecraft `Entity`/`LivingEntity` subtype (commonly `PathfinderMob`) and implementing `GeoEntity`;
- an instance `AnimatableInstanceCache` created through `GeckoLibUtil`;
- `registerControllers(AnimatableManager.ControllerRegistrar)`;
- a `GeoModel` subclass;
- a `GeoEntityRenderer` subclass registered with the client renderer event/registry;
- server-triggered non-looping animations through the `GeoEntity` triggerable-animation system;
- controller keyframe handlers for presentation callbacks, including custom instructions.

Official public docs/examples to re-check when freshness matters:

- https://github.com/bernie-g/geckolib/wiki/Custom-GeckoLib-Entity
- https://github.com/bernie-g/geckolib/wiki/Geckolib-Entities-(Geckolib4)
- https://github.com/bernie-g/geckolib/wiki/Triggerable-Animations-(Geckolib4)
- https://github.com/bernie-g/geckolib/wiki/The-Animation-Controller-(Geckolib4)

## Authority boundary

**Server gameplay is authoritative.** The server owns:

- attack selection and cooldown;
- phase/AI state;
- movement/navigation commitment;
- hitbox evaluation and damage;
- projectile spawn;
- stun/stagger/interrupt state;
- persistent state and drops.

The client owns presentation:

- rendered animation;
- local particles/trails that do not affect gameplay;
- camera-facing visual layers;
- non-authoritative sound/visual embellishment.

A `devkit_event:damage:*` timeline marker is a synchronization label, **not permission to apply damage from a client keyframe callback**. The server schedules the damage event from the same authored marker time and attack start tick. Client custom-instruction handlers may use the matching token for VFX/SFX and diagnostics.

## Attack execution contract

For each attack:

1. server validates state/target/range/cooldown;
2. server enters attack commitment and records `attackStartTick` + attack id;
3. server calls/causes the synced triggerable animation;
4. server schedules authoritative active window(s) from manifest marker time/timing contract;
5. client animation reaches matching custom markers for VFX/SFX;
6. server resolves hitbox/projectile/damage and state changes;
7. server enters recovery and clears commitment at the authored recovery boundary;
8. cancel/interrupt paths atomically clear scheduled events and presentation state.

Never independently tune Java delay constants after animation timing changes. Generate/read them from the same pack contract or fail cross-link QA.

## Entity runtime contract

Each production entity should declare enough native runtime information to implement and test it deterministically:

- dimensions;
- tracking range/update interval;
- core attributes;
- spawn category/rules or explicit encounter-only status;
- persistence policy;
- fire/water/environmental flags where relevant;
- phase/combat state fields that must synchronize;
- boss-bar policy where relevant;
- loot/XP/drop behavior;
- despawn rules;
- difficulty/player-count scaling policy.

`mob_runtime_contract_audit.py` validates this layer. `premium_mob_runtime_plan.py` expands it into a concrete implementation/file/QA plan for the target project.

## Runtime implementation order

1. register entity types + attributes;
2. register renderer/model resources;
3. implement synced state and persistence;
4. implement locomotion/navigation/targets;
5. implement one attack end-to-end with server timing + animation + VFX/SFX;
6. implement encounter graph/remaining attacks;
7. add spawn/loot/config/data;
8. add debug commands and deterministic QA harness;
9. run dedicated-server proof;
10. run native client/integrated-server visual/combat proof;
11. run stress/restart/persistence gates.

## Performance rules

- no global entity scans per tick when spatial/query/event alternatives exist;
- no per-frame resource parsing;
- cache immutable attack/animation definitions;
- keep client-only presentation work off the server;
- reuse bounded particle/sound objects/definitions;
- use navigation/goal cadence appropriate to gameplay rather than every-tick expensive re-planning;
- test simultaneous pack entities, not only one boss in an empty arena.
