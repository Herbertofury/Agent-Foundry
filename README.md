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
| **Durable execution** | Resumable task state, idempotency, cancellation, human waits | [DURABLE_EXECUTION_STANDARD.md](./DURABLE_EXECUTION_STANDARD.md) |
| **Evaluation** | Real-harness behavioral delta, trigger controls, trajectory proof | [EVALUATION_STANDARD.md](./EVALUATION_STANDARD.md) |
| **Observability** | Vendor-neutral causal traces without making telemetry the truth store | [OBSERVABILITY_STANDARD.md](./OBSERVABILITY_STANDARD.md) |
| **Interoperability** | MCP / A2A / ACP / AG-UI / ACS boundary mapping | [INTEROPERABILITY_STANDARD.md](./INTEROPERABILITY_STANDARD.md) |
| **Authorization** | Policy decision/enforcement boundaries for sensitive actions | [AUTHORIZATION_CONTROL_STANDARD.md](./AUTHORIZATION_CONTROL_STANDARD.md) |
| **Skill trust** | Quarantine, scan, review, permission manifest, sandbox, pin | [THIRD_PARTY_SKILL_SECURITY.md](./THIRD_PARTY_SKILL_SECURITY.md) |
| **Supply chain** | Checksums, attestations, SBOM/AgBOM, release provenance | [SUPPLY_CHAIN_STANDARD.md](./SUPPLY_CHAIN_STANDARD.md) |
| **Distribution** | Open Agent Skills compatibility, multi-agent sync, locks | [DISTRIBUTION_STANDARD.md](./DISTRIBUTION_STANDARD.md) |

## Execution architecture

~~~mermaid
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
~~~

### The core loop

**Resolve identity → preserve acceptance → challenge before reinventing → implement → targeted test → checkpoint → runtime proof → publish → learn.**

The Foundry deliberately separates **procedure ownership** from **acceptance ownership**.

## The invariants that matter most

### 🧭 Preserve the real objective
Preserve requested functionality, quality, quantity, compatibility, provenance, fidelity, and verification.

### 🔎 Challenge before reinventing
Before substantial invention, actively look for stronger existing implementations across upstreams, GitHub, GitLab, Codeberg, forks, packages, plugins, standards, reference implementations, and authorized internal/commercial sources.

### 🧱 Blockers are routing signals
A failed route is not a deliverable.

### ⚡ Performance and quality improve together
Performance work succeeds only when the target metric improves **and** protected behavior stays intact.

### 🧪 Evidence beats confidence
A passing build is useful evidence. It is not a substitute for exercising the actual affected workflow when real runtime proof is available.

### 🧠 Never suffer the same failure twice
Verified nontrivial recoveries become reusable incident knowledge and regression protection.

### 🔁 Continuity survives everything
Skill switches, model changes, connectors, compaction, handoffs, retries, and timeouts do not erase accepted requirements, IDs, checkpoints, prior fixes, failed-route history, or the exact next action.

## Challenger intelligence

Every meaningful candidate gets one of these states:

<code>adopt</code> · <code>merge</code> · <code>port</code> · <code>wrap</code> · <code>backport</code> · <code>compose</code> · <code>reject</code> · <code>unresolved</code>

Read the full [Challenger & Integration Standard](./CHALLENGER_INTEGRATION_STANDARD.md).

## Trust + interoperability layer

The second challenger sweep found that the biggest missing pieces were not more prompt frameworks. They were **operational trust and open interoperability**.

Agent Foundry now has explicit homes for:
- MCP tool/context compatibility and durable Tasks;
- A2A agent-to-agent collaboration;
- ACP coding-agent/client compatibility;
- AG-UI application-facing interaction;
- OWASP ACS-compatible runtime controls and AgBOM concepts;
- real-harness Skill evaluation;
- OpenTelemetry-compatible observability;
- third-party Skill quarantine/scanning;
- SLSA-style artifact provenance;
- skills.sh / open Agent Skills distribution compatibility;
- desired-state multi-agent Skill synchronization.

See [registry/protocols.json](./registry/protocols.json) for version-sensitive protocol state.

## Chat-facing skill components

These are reusable skills for **ChatGPT chats**, not a roster of autonomous agents. Their names do not select a model, create an agent, grant tools, or expand permissions. Enable only the relevant skill for the chat task.

- **Ultimate Agent Governance**
- **Zero-Loss Chat Accelerator**
- **Project Brain Orchestrator**
- **Minecraft Dev Kit**
- **Minecraft Repair**
- **Project Visual QA Showcase**
- **Artifact Browser Companion**
- **Revenue Operator**
- **Skill Creator**

## Agent and repository execution

`AGENTS.md`, canonical standards, `agents/` adapters and `evals/` govern actual agent/repository execution separately. Keep adapters lean: point to the applicable canonical rule instead of copying every chat skill into each agent prompt. See [chat/agent boundaries](docs/CHAT-AND-AGENT-BOUNDARIES.md).

## Canonical bundle

- File: <code>ultimate-agent-governance-skill.zip</code>
- SHA-256: <code>8d42e1b1ead43a0342931c18adb708875391a62a561d99eff7429fae57742cf8</code>
- Size: <code>76,676 bytes</code>
- [Open canonical Drive bundle](https://drive.google.com/file/d/1uPozXLHOEJgqphore01mDoBtFnNmwkmR/view)

## Wiki

**https://github.com/Herbertofury/Agent-Foundry/wiki**

The repository keeps a source mirror under [wiki/](./wiki/) so documentation changes can be reviewed, versioned, validated, and automatically published.

---

<div align="center">

### Forge the behavior. Prove the result. Preserve the knowledge.

**Agent Foundry**

</div>
