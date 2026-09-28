# Premium creature / combat SFX production

Use when a premium mob/boss pack includes vocalizations, attacks, impacts, movement or phase/cinematic audio.

## Audio is gameplay information

A premium sound set should make important states readable even when the player is not staring directly at the mob. Keep separate sound roles:

- vocal/personality;
- locomotion/foley;
- anticipation/telegraph;
- action/weapon/magic body;
- impact confirmation;
- recovery/effort;
- phase/cinematic/ambient identity.

High-threat moves need recognizable anticipation. Impact audio must happen at the same authored event contract as damage/VFX, not on an unrelated timer.

## SFX definition contract

Record per sound identity:

- semantic role (`telegraph`, `action`, `impact`, `vocal`, `foley`, `phase`, `ambient`);
- one or more real source files;
- spatialized vs UI/global playback;
- volume and pitch range;
- max concurrency;
- cooldown/retrigger rule;
- optional subtitle/localization key;
- duration expectations;
- variation group.

`mob_sfx_contract_audit.py` verifies attack SFX definitions/files, marker mapping, role, concurrency and variation. `procedural_sfx_blockout.py` can create deterministic timing/prototype WAV/OGG drafts; those are **not** a substitute for final authored sound design.

## Variation

Repeated combat sounds should not replay one identical sample indefinitely. Use 2-5 variations for frequent footsteps, grunts and impacts when the asset budget permits, plus a conservative pitch range. Signature boss telegraphs may intentionally stay more consistent so players learn them.

## Mix hierarchy

Prioritize:

1. lethal telegraph;
2. player-facing impact confirmation;
3. phase/major state cue;
4. voice/personality;
5. foley/ambient detail.

Do not let every ambient/foley layer compete at the same loudness as a lethal cast cue.

## Runtime proof

Test overlapping mobs and multiplayer. Verify distance attenuation, subtitle behavior when supported, no stuck loops, no duplicated playback from client+server event handling, and cleanup on cancel/death/chunk unload.
