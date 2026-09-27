# Continuous Modernization & Fix-Forward Standard

Agent Foundry does not preserve stale implementation choices by default.

## Freshness pass
For substantive version-sensitive work:
1. identify the exact compatibility envelope;
2. check current primary sources and strong challengers;
3. prefer the newest production-worthy compatible method with demonstrated advantage;
4. backport or adapt newer techniques when the target version itself must remain fixed.

## Upgrades are candidates, not automatic wins
A newer version is not better merely because it is newer. Promote it only after evidence shows a material gain without unacceptable protected regression.

For mixed upgrades:
- profile or bisect the change;
- retain useful gains;
- patch or replace regressive internals;
- retest equivalent work;
- preserve the user's target envelope.

## Fix forward
When modernization causes repairable fallout, repair the migration rather than retreating to weaker architecture solely because the older path is familiar.

## Reusable improvement ratchet
Once a newer method is verified as materially better:
- record why;
- preserve its compatibility assumptions;
- make it the reusable default;
- add regression protection where practical.

## Challenger relationship
Modernization and challenger discovery are linked but not identical:
- modernization asks “what is the strongest current compatible baseline?”;
- challenger discovery asks “what existing implementations can we adopt, merge, port, wrap, backport, or compose?”

Use both when substantial invention or migration is involved.
