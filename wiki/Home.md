<div align="center">

# ⚒️ Agent Foundry

### Build agents that finish the job.

**Skills · AGENTS.md · Invariants · Governance · Challenger Intelligence · Failure Recovery · Runtime Proof**

[Repository](https://github.com/Herbertofury/Agent-Foundry) · [Getting Started](Getting-Started) · [Skills Catalog](Skills-Catalog) · [Architecture](Architecture)

</div>

---

Agent Foundry is a living engineering system for making AI agents **more capable without becoming less reliable**.

It exists to prevent the failure modes that ruin long, ambitious agent work:

- forgetting requirements after a handoff or tool switch;
- restarting solved discovery;
- accepting blockers as completion;
- rebuilding weaker duplicates instead of integrating mature work;
- calling a build “done” without exercising the actual workflow;
- optimizing performance by silently doing less;
- suffering the same recoverable failure again.

## The Foundry promise

> **Preserve the goal. Challenge before reinventing. Implement once the path is known. Prove the real result. Preserve the knowledge.**

| Explore | What it gives you |
|---|---|
| 🧭 [Getting Started](Getting-Started) | The shortest path into Agent Foundry |
| 🏗️ [Architecture](Architecture) | How governance, Zero-Loss, domain skills, and project continuity compose |
| 🧰 [Skills Catalog](Skills-Catalog) | The flagship skill ecosystem |
| 📜 [AGENTS.md & Invariants](AGENTS-md-and-Invariants) | What must remain true across every workflow |
| ⚡ [Zero-Loss Execution](Zero-Loss-Execution) | Anti-stall, continuity, no rediscovery |
| 👑 [Ultimate Agent Governance](Ultimate-Agent-Governance) | The shared acceptance constitution |
| 🔎 [Challenger & Integration](Challenger-and-Integration-Standard) | Reuse-before-rebuild and best-of-breed composition |
| 🧠 [Failure Intelligence](Failure-Intelligence) | Unknown ≠ absent; blockers route forward |
| 📈 [Performance & Runtime Proof](Performance-and-Runtime-Proof) | Faster **and** correct; evidence over confidence |
| 🔌 [Cross-Agent Compatibility](Cross-Agent-Compatibility) | Thin adapters, one canonical truth |
| 🛠️ [Building a Skill](Building-a-Skill) | How to build reusable, testable Skills |
| 🌌 [Project Constellation Integration](Project-Constellation-Integration) | Durable project memory and continuation |
| 🗺️ [Roadmap](Roadmap) | Where the Foundry goes next |

## Core execution loop

\`\`\`mermaid
flowchart LR
    A[Resolve identity] --> B[Freeze acceptance]
    B --> C[Challenge before reinventing]
    C --> D[Implement]
    D --> E[Targeted test]
    E --> F[Checkpoint]
    F --> G[Real workflow proof]
    G --> H[Publish]
    H --> I[Learn & reuse]
    I --> A
\`\`\`

## What makes it different

Agent Foundry is deliberately **not** one giant universal prompt.

It is a layered system:
- **invariants** define what may never be sacrificed;
- **governance** defines the shared acceptance boundary;
- **Zero-Loss** keeps execution moving without losing state;
- **domain skills** own the actual procedure;
- **Project Brain** preserves identity, checkpoints, and publication;
- **evals/audits/runtime proof** turn important rules into evidence.

That separation keeps the system powerful without flooding every task with irrelevant ceremony.

---

### Start here → [Getting Started](Getting-Started)
