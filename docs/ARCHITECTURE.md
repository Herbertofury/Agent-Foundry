# Architecture

Shared engineering invariants feed two distinct instruction surfaces.

| Surface | Entry point | Owns |
|---|---|---|
| Chat workflows | Explicitly selected Skill | Chat orchestration, continuity and domain procedure |
| Coding agents/repositories | Project-owned AGENTS.md and scoped instructions | Local setup, commands, restrictions and reviewed shared policy |
| Shared standards | Product invariants and root standards | Protected behavior, current-stack promotion, runtime/performance proof and trust |
| Mechanical evidence | Tests, audits and versioned locks | Specific checks, not blanket agent-quality guarantees |

The nine flagship components belong to the chat surface. In a selected chat, the narrowest domain Skill owns procedure; Governance, Zero-Loss and Project Brain supply relevant overlays without resetting state. Repository instructions do not require their activation.

`tools/foundry_sync.py` distributes explicitly selected Skill packages. `tools/repository_governance.py` separately plans/checks policy snapshots while preserving local instructions. Neither is automatic cross-project deployment. See [repository governance](REPOSITORY-GOVERNANCE.md).
