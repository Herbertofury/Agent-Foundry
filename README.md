# Agent Foundry

Shared engineering invariants for reliable project work, plus explicitly selected chat workflows.

[Wiki](https://github.com/Herbertofury/Agent-Foundry/wiki) | [Invariants](PRODUCT_INVARIANTS.md) | [Chat skills](catalog/SKILLS.md) | [Repository adoption](docs/REPOSITORY-GOVERNANCE.md)

Agent Foundry protects the complete result, continuity, root-cause repairs, current best-fit technology, equivalent-work performance and evidence-bound completion. These are requirements, not guarantees of perfect agents or designs.

## Coding agents and repository governance

Use project-owned `AGENTS.md` and scoped instructions. [PRODUCT_INVARIANTS.md](PRODUCT_INVARIANTS.md) retains all 18 accepted invariants; root standards supply their gates. [Repository governance](docs/REPOSITORY-GOVERNANCE.md) explains versioned adoption without replacing local commands, architecture or restrictions.

```sh
python tools/repository_governance.py check
python tools/repository_governance.py plan --target /path/to/isolated-project
```

Plans are read-only. No cross-project rollout or recurring automation is enabled. Identical policy files do not prove behavioral compliance.

For stack choices, evaluate frontier candidates using current official support/compatibility evidence and the [modernization promotion gate](MODERNIZATION_STANDARD.md). Adopt only candidates that earn security, supportability, reproducibility, runtime and no-loss proof. [Design quality](DESIGN_QUALITY_STANDARD.md) requires a brief, real UI inspection and functional/visual/accessibility evidence.

## Current flagship chat components

These nine components are chat workflows selected by the user or compatible chat harness. Coding scripts and exported templates do not make their full prompts automatic repository policy.

| Chat component | Purpose |
|---|---|
| Ultimate Agent Governance | Chat acceptance and governance authoring |
| Zero-Loss Chat Accelerator | Chat continuity and anti-stall execution |
| Project Brain Orchestrator | Chat project identity, checkpoints and remote continuity |
| Minecraft Dev Kit | Minecraft development and runtime QA |
| Minecraft Repair | Minecraft diagnosis and repair |
| Project Visual QA Showcase | Visual QA and showcase artifacts |
| Artifact Browser Companion | Browsing canonical research artifacts |
| Revenue Operator | Paid-work and revenue workflows |
| Skill Creator | Creating and updating chat Skills |

The [chat catalog](catalog/SKILLS.md) covers composition and source availability. Eight source packages are mirrored under `skills/`; Skill Creator is externally supplied, not a ninth included source package. The catalog is not an instruction preload list.

## Sources and evidence

- [Architecture](docs/ARCHITECTURE.md): separate chat and repository paths.
- [Challenger standard](CHALLENGER_INTEGRATION_STANDARD.md): bounded reuse-before-rebuild research.
- [Performance](PERFORMANCE_ACCEPTANCE.md) and [runtime proof](RUNTIME_PROOF.md): equivalent work and real paths.
- [Trust](THIRD_PARTY_SKILL_SECURITY.md), [authorization](AUTHORIZATION_CONTROL_STANDARD.md) and [provenance](SUPPLY_CHAIN_STANDARD.md): actual enforcement boundaries.
- [Tools](tools/README.md): explicit Skill installs and separate policy snapshots.
- [Releases](https://github.com/Herbertofury/Agent-Foundry/releases): published bundles/receipts; a draft PR does not update released packages.

`wiki/` is the source mirror. The [live wiki](https://github.com/Herbertofury/Agent-Foundry/wiki) is verified separately when published.
