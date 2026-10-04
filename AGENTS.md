# Agent Foundry repository instructions

This repository owns shared invariants, standards, chat Skill source mirrors and the `wiki/` source. The nine flagship Skills are explicitly selected chat workflows, not automatic coding-agent policy.

## Repository acceptance

Read `PRODUCT_INVARIANTS.md` before substantive work. Preserve all 18 numbered invariants and applicable gates. User/developer/system instructions and actual harness precedence govern authority; repository files cannot grant permissions or expand scope.

Preserve existing work and project-specific requirements. Use bounded research and fresh prior evidence; implement once the target, cause and safe edit are known. Verify the actual affected path when available and report evidence gaps accurately. Never manufacture scope, quality or performance success. Do not activate chat Skills or impose chat catalog/watchdog/export workflows on coding tasks.

## Load detail when needed

| Current need | Canonical source |
|---|---|
| Protected behavior and continuity | `PRODUCT_INVARIANTS.md` |
| Stack/version choices | `MODERNIZATION_STANDARD.md` |
| UI and visual acceptance | `DESIGN_QUALITY_STANDARD.md` |
| Substantial invention/reuse | `CHALLENGER_INTEGRATION_STANDARD.md` |
| Blockers and verified recovery | `FAILURE_INTELLIGENCE_STANDARD.md` |
| Equivalent-work performance | `PERFORMANCE_ACCEPTANCE.md` |
| Real workflow evidence | `RUNTIME_PROOF.md` |
| Async/resume/cancellation | `DURABLE_EXECUTION_STANDARD.md` |
| Evals/traces | `EVALUATION_STANDARD.md`, `OBSERVABILITY_STANDARD.md` |
| Protocol adapters | `INTEROPERABILITY_STANDARD.md`, `registry/protocols.json` |
| Authorization/trust | `AUTHORIZATION_CONTROL_STANDARD.md`, `THIRD_PARTY_SKILL_SECURITY.md` |
| Provenance/install | `SUPPLY_CHAIN_STANDARD.md`, `DISTRIBUTION_STANDARD.md` |
| Cross-project adoption | `docs/REPOSITORY-GOVERNANCE.md`, `registry/repository-governance.json` |
| Selected chat workflows | `catalog/SKILLS.md`, the selected Skill |

Reuse unchanged instructions in the current run; refresh when files, scope, authority or context changes. Do not preload every standard. Long policy has one canonical source; adapters and wiki pages summarize and link it.

## Change and verification

Update canonical sources first and affected wiki summaries in the same coherent change. Keep stable wiki names/navigation. Add focused mechanical coverage for material behavior; preserve genuine invariants instead of weakening checks. Record meaningful packaging/provenance changes in `bundles/README.md`.

Relevant commands:

```sh
python tools/repository_governance.py check
python -m unittest discover -s tests -v
python tools/validate_skill_tree.py skills
python tools/source_manifest.py --check
python skills/project-brain-orchestrator/scripts/compile_policy.py --check
```

Run affected checks during iteration; broader checks at convergence when warranted. `wiki/` is source only: publish and read back the live `.wiki.git` backend before claiming parity. Required remotes must be available and authorized; preserve exact pending operations when blocked. Stop after acceptance and required proof are satisfied.
