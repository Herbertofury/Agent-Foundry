# Agent Foundry repository instructions

This repository is the canonical public home for Agent Foundry governance, skills documentation, product invariants, execution standards, and the source mirror for the GitHub Wiki.

## Source-of-truth map

- Global user-visible behavior: \`PRODUCT_INVARIANTS.md\`
- Modernization/fix-forward behavior: \`MODERNIZATION_STANDARD.md\`
- Unknown/blocker/recovery behavior: \`FAILURE_INTELLIGENCE_STANDARD.md\`
- Challenger discovery and reuse-before-rebuild: \`CHALLENGER_INTEGRATION_STANDARD.md\`
- Performance dual-success gate: \`PERFORMANCE_ACCEPTANCE.md\`
- Real runtime/workflow evidence: \`RUNTIME_PROOF.md\`
- Skill catalog: \`catalog/SKILLS.md\`
- Human-facing documentation: \`wiki/\` and \`docs/\`

Do not duplicate long canonical policy across adapters or wiki pages. Wiki pages summarize and link back to canonical files.

## Repository invariants

1. Preserve the user's actual goal, scope, capability, quality, quantity, compatibility, fidelity, provenance, and verification requirements.
2. A blocker is unresolved work, not completion.
3. Unknown/search miss is not proof of absence.
4. Before substantial invention, perform a bounded challenger/integration pass and prefer authorized reuse, merge, port, wrap, backport, or composition over rebuilding a weaker duplicate.
5. Once target + root cause + safe edit are known, cross into implementation. Do not let research or narration become the stall.
6. Performance changes must improve the requested metric and preserve protected behavior.
7. Build/static success is intermediate evidence; exercise the real affected workflow when available.
8. Verified nontrivial recoveries become reusable incident knowledge or regression evidence.
9. Skill/tool/model/connector transitions do not reset accepted requirements, canonical IDs, checkpoints, prior evidence, or exact next action.
10. Important rules should have the strongest practical mechanical enforcement: tests, audits, schemas, build gates, or evals.

## Change discipline

When changing a canonical standard:

1. Update the canonical file first.
2. Update affected wiki summaries/links in the same coherent change.
3. Add or adjust validation/evaluation coverage when the rule is important enough to keep.
4. Do not weaken prior invariants merely to make a check pass.
5. Record meaningful packaging/provenance changes in \`bundles/README.md\` or the appropriate catalog page.

## Wiki discipline

The \`wiki/\` directory is the version-controlled source mirror for the GitHub Wiki.

- \`wiki/Home.md\` is the wiki landing page.
- \`wiki/_Sidebar.md\` is the primary navigation.
- Keep page names stable to avoid broken wiki links.
- The publish workflow mirrors \`wiki/\` to GitHub Wiki.
- Canonical policy stays in root standards; wiki pages explain and navigate it.

## Pull requests

A good PR answers:

- What acceptance behavior changes?
- Which canonical source owns it?
- What challenger/reuse search was relevant?
- What tests/evals prove the change?
- What existing behavior was explicitly preserved?
- What documentation/wiki surface changed with it?

## Completion

Do one material challenge pass before closeout. Do not continue “just in case” loops after acceptance and required proof are satisfied.
