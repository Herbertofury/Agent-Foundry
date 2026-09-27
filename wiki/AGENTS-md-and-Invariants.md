# AGENTS.md & Invariants

A good \`AGENTS.md\` is a **router**, not an encyclopedia.

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

Canonical repository files:
- [PRODUCT_INVARIANTS.md](https://github.com/Herbertofury/Agent-Foundry/blob/main/PRODUCT_INVARIANTS.md)
- [AGENTS.md](https://github.com/Herbertofury/Agent-Foundry/blob/main/AGENTS.md)
- [MODERNIZATION_STANDARD.md](https://github.com/Herbertofury/Agent-Foundry/blob/main/MODERNIZATION_STANDARD.md)
