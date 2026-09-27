<div align="center">

# ⚒️ Agent Foundry

### Build agents that finish the job.

**Skills · AGENTS.md · Invariants · Governance · Evals · Recovery Intelligence · Challenger Discovery · Zero-Loss Execution**

[![Status](https://img.shields.io/badge/status-active-success?style=for-the-badge)](https://github.com/Herbertofury/Agent-Foundry)
[![Zero Loss](https://img.shields.io/badge/philosophy-zero--loss-7c3aed?style=for-the-badge)](./PRODUCT_INVARIANTS.md)
[![Governance](https://img.shields.io/badge/governance-evidence--bound-0f766e?style=for-the-badge)](./AGENTS.md)
[![Wiki](https://img.shields.io/badge/wiki-Agent%20Foundry-2563eb?style=for-the-badge)](https://github.com/Herbertofury/Agent-Foundry/wiki)
[![Last Commit](https://img.shields.io/github/last-commit/Herbertofury/Agent-Foundry?style=for-the-badge)](https://github.com/Herbertofury/Agent-Foundry/commits/main)

**A living engineering system for reliable AI agents: preserve the goal, search for superior existing work, execute without scope loss, prove the real result, and turn failures into reusable improvements.**

[Explore the Wiki](https://github.com/Herbertofury/Agent-Foundry/wiki) · [Read the Invariants](./PRODUCT_INVARIANTS.md) · [Browse Skills](./catalog/SKILLS.md) · [Build a Skill](./docs/SKILL-AUTHORING.md)

</div>

---

## Why Agent Foundry exists

Most agent failures are not caused by a lack of raw capability. They come from losing the real objective during execution: restarting solved work, shrinking scope, accepting blockers as completion, rebuilding inferior duplicates, skipping runtime proof, or forgetting the fix the next time the same failure appears.

**Agent Foundry is the system that prevents that.**

It combines reusable Skills, repository-level agent instructions, product invariants, execution standards, evaluation gates, failure intelligence, continuity rules, and challenger discovery into one coherent architecture.

> **Maximum useful effort. Minimum wasted motion. No manufactured success.**

## The Foundry stack

| Layer | Purpose | Canonical home |
|---|---|---|
| **Product invariants** | Non-negotiable behavior that must survive every tool/skill/model switch | [PRODUCT_INVARIANTS.md](./PRODUCT_INVARIANTS.md) |
| **AGENTS.md** | Lean repository-wide instructions and source-of-truth routing | [AGENTS.md](./AGENTS.md) |
| **Ultimate Agent Governance** | Shared acceptance boundary across substantive work | [catalog/SKILLS.md](./catalog/SKILLS.md#ultimate-agent-governance) |
| **Zero-Loss Chat Accelerator** | Continuity, anti-stall execution, no rediscovery, fast causal loops | [catalog/SKILLS.md](./catalog/SKILLS.md#zero-loss-chat-accelerator) |
| **Project Brain Orchestrator** | Durable project identity, checkpoints, Drive/GitHub persistence | [catalog/SKILLS.md](./catalog/SKILLS.md#project-brain-orchestrator) |
| **Domain skills** | Own the actual procedure for Minecraft, artifacts, revenue, repair, QA, etc. | [catalog/SKILLS.md](./catalog/SKILLS.md) |
| **Challenger intelligence** | Find, compare, adopt, merge, port, wrap, backport or compose superior work | [CHALLENGER_INTEGRATION_STANDARD.md](./CHALLENGER_INTEGRATION_STANDARD.md) |
| **Failure intelligence** | Unknown ≠ absent; blocker escalation; reusable incident recovery | [FAILURE_INTELLIGENCE_STANDARD.md](./FAILURE_INTELLIGENCE_STANDARD.md) |
| **Runtime proof** | Real workflow evidence outranks static confidence | [RUNTIME_PROOF.md](./RUNTIME_PROOF.md) |
| **Performance acceptance** | Faster and better together; never faster by doing less | [PERFORMANCE_ACCEPTANCE.md](./PERFORMANCE_ACCEPTANCE.md) |

## Execution architecture

\`\`\`mermaid
flowchart TD
    U[User goal] --> A[AGENTS.md / product invariants]
    A --> G[Ultimate Agent Governance]
    G --> Z[Zero-Loss execution substrate]
    Z --> D[Domain skill owns procedure]
    D --> C[Challenger & integration scan]
    C --> I[Implement / merge / port / compose]
    I --> T[Targeted tests]
    T --> R[Real runtime / workflow proof]
    R --> P[Durable checkpoint & publication]
    R --> F[Failure intelligence / regression fixture]
    F --> G
    P --> N[Next task resumes from verified state]
\`\`\`

### The core loop

**Resolve identity → preserve acceptance → challenge before reinventing → implement → targeted test → checkpoint → runtime proof → publish → learn.**

The Foundry deliberately separates **procedure ownership** from **acceptance ownership**. A domain skill knows *how* to do the work. Governance ensures the work does not quietly become smaller, weaker, less verified, or disconnected from the user's actual goal.

## The invariants that matter most

### 🧭 Preserve the real objective
Do not optimize for an easy-looking completion. Preserve requested functionality, quality, quantity, compatibility, provenance, fidelity, and verification.

### 🔎 Challenge before reinventing
Before substantial invention, actively look for stronger existing implementations across upstreams, GitHub, GitLab, Codeberg, forks, packages, plugins, standards, reference implementations, and authorized internal/commercial sources. Reuse the best authorized parts instead of rebuilding weaker duplicates.

### 🧱 Blockers are routing signals
A failed route is not a deliverable. Repair the environment, change the route, install the dependency, fix auth, switch implementation, or preserve an explicit unresolved checkpoint.

### ⚡ Performance and quality improve together
Performance work succeeds only when the target metric improves **and** protected behavior stays intact.

### 🧪 Evidence beats confidence
A passing build is useful evidence. It is not a substitute for exercising the actual affected workflow when real runtime proof is available.

### 🧠 Never suffer the same failure twice
Verified nontrivial recoveries become reusable incident knowledge and regression protection.

### 🔁 Continuity survives everything
Skill switches, model changes, connectors, compaction, handoffs, retries, and timeouts do not erase accepted requirements, IDs, checkpoints, prior fixes, failed-route history, or the exact next action.

## Challenger intelligence

Agent Foundry treats ecosystem discovery as an engineering phase, not casual browsing.

Every meaningful candidate gets one of these states:

\`adopt\` · \`merge\` · \`port\` · \`wrap\` · \`backport\` · \`compose\` · \`reject\` · \`unresolved\`

A strong result is often **composition**, not a single winner: one project may have the best parser, another the best caching model, another the best UI behavior, and a fourth the best compatibility layer.

Read the full [Challenger & Integration Standard](./CHALLENGER_INTEGRATION_STANDARD.md).

## Skills are executable engineering knowledge

A Foundry Skill is not just a prompt. A good Skill can carry:

- concise trigger metadata;
- deterministic scripts for fragile/repeatable work;
- evaluation fixtures;
- compatibility rules;
- reference standards;
- packaged assets;
- recovery knowledge;
- real validation procedures;
- connector/tool guidance;
- cross-skill inheritance rules.

See [Skill Authoring](./docs/SKILL-AUTHORING.md).

## Current flagship components

- **Ultimate Agent Governance** — the shared execution constitution and governance architecture.
- **Zero-Loss Chat Accelerator** — persistent anti-stall orchestration and continuity.
- **Project Brain Orchestrator** — project identity, checkpoints, persistence, and resume logic.
- **Minecraft Dev Kit** — implementation, ports, conversions, benchmarking, and runtime proof.
- **Minecraft Repair** — bounded diagnosis/repair that returns control to the active project workflow.
- **Project Visual QA Showcase** — deterministic visual evidence and comparison.
- **Artifact Browser Companion** — desktop/browser companions around canonical research artifacts.
- **Revenue Operator** — real-world monetization and paid-work execution.
- **Skill Creator** — reusable Skill design and packaging.

The catalog grows without forcing every skill into every task. **One truth, many focused overlays.**

## Canonical bundle

The current validated **Ultimate Agent Governance** Skill bundle is mirrored durably on Google Drive:

- File: \`ultimate-agent-governance-skill.zip\`
- SHA-256: \`8d42e1b1ead43a0342931c18adb708875391a62a561d99eff7429fae57742cf8\`
- Size: \`76,676 bytes\`
- [Open canonical Drive bundle](https://drive.google.com/file/d/1uPozXLHOEJgqphore01mDoBtFnNmwkmR/view)

See [bundles/README.md](./bundles/README.md) for provenance and packaging rules.

## Repository map

\`\`\`text
Agent-Foundry/
├── AGENTS.md
├── PRODUCT_INVARIANTS.md
├── MODERNIZATION_STANDARD.md
├── FAILURE_INTELLIGENCE_STANDARD.md
├── CHALLENGER_INTEGRATION_STANDARD.md
├── PERFORMANCE_ACCEPTANCE.md
├── RUNTIME_PROOF.md
├── catalog/
│   └── SKILLS.md
├── docs/
│   ├── ARCHITECTURE.md
│   └── SKILL-AUTHORING.md
├── bundles/
│   └── README.md
├── wiki/                  # canonical wiki source mirror
└── .github/
    ├── workflows/
    └── ISSUE_TEMPLATE/
\`\`\`

## Wiki

The Wiki is the friendly, browsable layer over the same canonical standards:

**https://github.com/Herbertofury/Agent-Foundry/wiki**

The repository keeps a source mirror under [wiki/](./wiki/) so documentation changes can be reviewed, versioned, validated, and automatically published rather than becoming an untracked second truth.

## Contributing

Improvements are welcome when they make the system measurably more reliable, capable, complete, reusable, or easier to operate **without manufacturing success by weakening acceptance**.

Read [CONTRIBUTING.md](./CONTRIBUTING.md) before changing a canonical standard.

---

<div align="center">

### Forge the behavior. Prove the result. Preserve the knowledge.

**Agent Foundry**

</div>
