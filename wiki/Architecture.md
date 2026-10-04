# Architecture

Shared product invariants feed two distinct instruction surfaces.

```mermaid
flowchart TD
    I[Shared product invariants and standards] --> C[Explicitly selected chat workflows]
    I --> R[Reviewed repository governance adapter]
    C --> D[Chat domain procedure and continuity]
    R --> L[Project AGENTS.md and scoped local instructions]
    D --> V[Relevant runtime and acceptance evidence]
    L --> V
```

The nine [flagship components](Skills-Catalog) are chat workflows. In selected chats, the domain Skill owns procedure; Governance, Zero-Loss and Project Brain provide relevant acceptance/continuity overlays without resetting state.

Coding agents use project instructions and reviewed shared policy. They do not automatically load chat orchestration, catalogs, watchdogs or all-in-one contracts. [Repository Governance Sync](Repository-Governance-Sync) preserves local commands and checks adopted digests.

Tests, audits, runtime proof and visual review validate specific behavior. File parity does not guarantee semantic compliance, perfect design or agent quality.
