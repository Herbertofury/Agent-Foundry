# Product Invariant Authoring

Use product invariants for behavior that must remain true across features, refactors, and future UI surfaces.

## Required shape

Each invariant should include:

1. **Rule** — one direct statement of what must always be true.
2. **Scope** — where it applies automatically.
3. **Required behavior** — observable user/product behavior.
4. **Architecture requirement** — shared mechanism that makes compliance the default.
5. **Exceptions** — only narrow, explicit exceptions; omit if none.
6. **Regression requirements** — tests/static checks/build gates.
7. **Acceptance test** — a simple pass/fail question.

## Quality checks

A strong invariant is:

- observable;
- stable across implementation refactors;
- specific enough to test;
- enforced near the shared causal owner;
- explicit about ambiguity/fallback behavior;
- hostile to fake compliance;
- narrow enough not to burden unrelated tasks.

Do not use an invariant for ordinary style preferences or facts easily inferred from code/configuration.
