# Contributing to Agent Foundry

Agent Foundry values improvements that make agents more capable **and** more reliable without shrinking acceptance.

## Before proposing a major new subsystem
Perform a challenger/integration pass. Link mature prior art and explain whether each important candidate should be adopted, merged, ported, wrapped, backported, composed, rejected, or left unresolved.

## Canonical policy changes
When changing an invariant or execution standard:
1. edit the canonical root standard;
2. update affected wiki summaries;
3. add or update mechanical validation/evals where practical;
4. state what existing behavior is preserved;
5. avoid duplicating the full policy in multiple places.

## Pull request checklist
- [ ] The user-visible objective is explicit.
- [ ] No existing capability was silently removed.
- [ ] Challenger/reuse research was performed when relevant.
- [ ] Changed behavior has targeted verification.
- [ ] Runtime proof is included when the real workflow is available.
- [ ] Performance claims use equivalent-work evidence.
- [ ] New nontrivial recovery knowledge is captured.
- [ ] Wiki/docs remain synchronized.
- [ ] No secrets, credentials, or private user data are committed.

## Design preference
Prefer:
- one canonical policy with thin adapters;
- reusable mechanisms over one-off patches;
- explicit state over ambiguous prose;
- strong evidence over confident language;
- composition over needless reinvention;
- implementation after sufficient discovery, not endless research.
