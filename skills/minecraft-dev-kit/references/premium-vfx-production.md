# Premium mob VFX production

Use for boss/mob attack effects and phase/environmental effects.

## Four-stage effect grammar

Author significant effects as a readable sequence:

1. **anticipation** - tells the player what is coming;
2. **action** - connects attacker/projectile/weapon to the move;
3. **impact** - confirms the gameplay event and actual area;
4. **aftermath** - optional residue/hazard/debris that communicates persistent state.

Not every move needs all four, but dangerous boss attacks should almost never skip anticipation and impact.

## VFX contract fields

A premium VFX definition should record:

- id + family/damage-school motif;
- coverage mode (`hitbox-aligned`, `weapon-trail`, `projectile`, `target-local`, `aura`);
- anticipation/action/impact recipes;
- optional aftermath;
- impact/telegraph radius where spatially meaningful;
- max concurrency;
- attachment locator(s);
- texture/particle references;
- emissive/blend intent;
- color/shape motif description;
- cleanup/lifetime policy.

`mob_vfx_contract_audit.py` cross-checks attack VFX references, stage completeness, concurrency budgets, locators and hitbox-aligned radius agreement.

## Readability rules

- Telegraph footprint must not materially undersell a lethal hitbox.
- Impact particles should not obscure the attack pose for longer than necessary.
- Persistent hazards need a distinct lingering visual state.
- Reuse faction motifs so players learn them.
- Do not make every effect maximum brightness/opacity/particle count.
- Large effects need bounded lifetime and concurrency.

## Runtime proof

Stress-test many simultaneous attacks. Inspect client frame time, particle counts, network/state synchronization and cleanup after cancellation, phase transition, entity death and chunk unload.
