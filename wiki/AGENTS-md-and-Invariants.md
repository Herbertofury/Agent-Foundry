# AGENTS.md & Invariants

A good <code>AGENTS.md</code> is a **router**, not an encyclopedia.

## Put in AGENTS.md
- repository-wide execution rules;
- canonical source locations;
- commands needed for validation;
- local scope differences;
- short non-obvious rules an agent must see early.

## Move out of AGENTS.md
- long domain workflows → Skills;
- framework-specific detail → scoped instructions;
- long architecture explanations → references;
- non-negotiable user-visible behavior → invariant files;
- runtime proof → dedicated runtime standard;
- performance equivalence → performance acceptance standard.

## Why
Large repeated instruction blocks create drift, waste context, and make it harder to know which copy is authoritative.

**Agent Foundry principle: one truth, many thin adapters.**

**Root-cause fixes over regression workarounds.** Removing features, reducing work, adding waits/polling/retries, forcing serialization, duplicating work, or shifting cost elsewhere does not count as a completed fix when equivalent behavior or performance regresses. Temporary containment stays unresolved until the causal defect is repaired or the user explicitly accepts the tradeoff.

Canonical repository files:
- [PRODUCT_INVARIANTS.md](https://github.com/Herbertofury/Agent-Foundry/blob/main/PRODUCT_INVARIANTS.md)
- [AGENTS.md](https://github.com/Herbertofury/Agent-Foundry/blob/main/AGENTS.md)
- [MODERNIZATION_STANDARD.md](https://github.com/Herbertofury/Agent-Foundry/blob/main/MODERNIZATION_STANDARD.md)
