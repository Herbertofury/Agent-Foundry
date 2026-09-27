# Failure Intelligence

Agent Foundry treats failure as structured information.

## Unknown ≠ absent
A search miss, parser miss, provider miss, auth miss, or incomplete page is not proof that something does not exist.

## Blocker escalation
A required failure should trigger:
1. decisive evidence capture;
2. failure classification;
3. materially different recovery route;
4. targeted retest;
5. checkpoint;
6. reusable incident knowledge when nontrivial.

## Never suffer the same failure twice
Verified fixes become recovery recipes and regression evidence.

## No unchanged retry loops
A retry is justified only by new evidence, changed parameters, changed route, repaired auth/environment, provider-requested delay, or another real state transition.

[Read the canonical standard](https://github.com/Herbertofury/Agent-Foundry/blob/main/FAILURE_INTELLIGENCE_STANDARD.md)
