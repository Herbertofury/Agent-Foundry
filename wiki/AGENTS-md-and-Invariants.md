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


## Remote durability is part of completion

For substantive project work, keep the latest coherent checkpoint on durable remotes rather than trusting the current chat. Source/history belongs in the canonical GitHub/VCS repository; material artifacts and checkpoint exports belong in connected Google Drive when available; and projects that use GitHub Wiki must keep the **actual live Wiki** synchronized. A repo-side <code>wiki/</code> mirror is canonical source, not proof of publication.

A missing or stale required remote remains unresolved work. The closeout question is simple: **could a fresh chat resume from verified remote state without this conversation?**
