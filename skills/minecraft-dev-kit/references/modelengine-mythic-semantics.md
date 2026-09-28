# ModelEngine + MythicMobs semantic preservation

Research snapshot: **2026-09-06**. Re-check current official MythicCraft docs when exact attributes are load-bearing.

This reference exists to prevent a common lossy conversion: copying the model and animation files while throwing away the server state machine that actually drives them.

## Mythic skill-line grammar

A common MythicMobs skill line is structurally:

```text
mechanic{argument=value;...} @targeter{argument=value;...} ~trigger <condition/modifier> chance
```

The mechanic is the action. Targeters select entity/location targets. Triggers determine when the line fires. Health modifiers/conditions and chance further gate execution. Meta-skill calls can pass parameters down the skill tree. Preserve these as separate IR fields rather than keeping only the raw YAML string.

Official-source evidence:
- MythicMobs skill docs describe mechanics, targeters, triggers, health modifiers, chance, and parameterized meta-skills: `https://git.mythiccraft.io/mythiccraft/MythicMobs/-/wikis/Skills/Skills`.

## ModelEngine animation state semantics

### `state`

Treat a ModelEngine state call as an animation-controller transition, not merely "play clip by name". Preserve when present:

- model id: `modelid`, aliases `m`, `mid`, `model`;
- state/animation id: `state`, alias `s`;
- speed: `speed`, alias `sp`;
- transition in/out: `lerpin`/`li`, `lerpout`/`lo`;
- force replay: `force`/`f`;
- priority: `priority`, aliases `p`, `pr`;
- forced loop mode: `loop`/`l`;
- forced override: `override`/`ov`;
- current docs also expose `skiplastframe`/`skip` for loop handling;
- removal lanes can include instant/no-lerp semantics and priority targeting.

Loop modes documented for state playback include `ONCE`, `LOOP`, and `HOLD`. Do not flatten HOLD into LOOP or ONCE; HOLD is semantically "remain on final frame until removed".

### `modstate` / `modifyanimation`

A playing animation can be mutated after start. Preserve dynamic modifications to:

- speed;
- lerp-in/lerp-out;
- loop mode (`ONCE`, `LOOP`, `HOLD`, plus `RESET` for returning to BBModel configuration);
- override mode;
- priority where applicable.

A native conversion therefore needs either a controller capable of live parameter mutation or a faithful state-machine equivalent.

Official-source evidence:
- State mechanic docs/history: `https://git.mythiccraft.io/mythiccraft/model-engine-4/-/wikis/Skills/Mechanics/State`.
- ModifyState docs/history: `https://git.mythiccraft.io/mythiccraft/model-engine-4/-/wikis/Skills/Mechanics/ModifyState`.
- ModelEngine technical docs describe its newer priority state-machine animation system: `https://git.mythiccraft.io/mythiccraft/model-engine-4/-/wikis/Technical/Animation-Systems`.

## Bone and attachment semantics

Never delete a non-rendering group merely because it has no cube. It may be gameplay-critical.

Known public ModelEngine bone conventions include:

- `h_` prefix: head behavior;
- `hi_` prefix: inherited head behavior for descendants;
- bone id `mount`: mount behavior in the documented convention;
- mount/dismount mechanics can also target explicit seat/mount bones;
- leash mechanics target a specific leash bone;
- model-tag mechanics operate on name-tag bones;
- hitbox mechanics can configure sub-hitbox behavior;
- controller mechanics include movement/jump/no-fall behavior;
- bone mechanics include programmatic bone animation, parent changes, part swaps, and cycling parts.

Preserve the original bone name and UUID in conversion IR even when mapping it to a clearer native semantic name.

## Model mechanics that imply non-visual behavior

When these appear in configs, treat them as explicit migration work rather than documentation-only:

- model create/apply/remove/remap/submodel/render-init;
- state/state-toggle/modify-state;
- root-motion settings;
- render scale vs hitbox scale;
- mount/dismount (driver and passenger seats);
- move/jump/no-fall controller access;
- hitbox/sub-hitbox controls;
- leash/leash-self;
- tag/nameplate text and visibility;
- programmatic bone animation;
- change-parent, change-part, cycle-parts.

These often require client/server state synchronization in a mod because server plugins can own both gameplay and rendering decisions centrally.

## Translation policy

1. Parse the skill line into a typed IR before generating any mod code.
2. Resolve meta-skill references transitively when source files are available; preserve passed parameters/placeholders rather than substituting guesses.
3. Build an event graph: source trigger -> conditions/chance -> targeter -> mechanic(s) -> animation/model state side effect.
4. Build a model-state graph: state start/stop/toggle/modify -> clip -> priority/loop/override/lerp -> exit condition.
5. Build an attachment map: source bone UUID/name -> semantic role -> target implementation.
6. Keep server-authoritative actions (damage, AI, cooldowns, ownership, drops) on the logical server. Keep rendering/animation on the client with explicit synchronized state.
7. Preserve ordering. A `delay`, `cancel`, meta-skill call, or state mutation can make two apparently similar skill lists behave differently.
8. Mark unsupported or missing semantics as conversion blockers; never silently omit them.
