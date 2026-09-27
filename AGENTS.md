# Agent Foundry repository instructions

This repository is the canonical public home for Agent Foundry governance, skills documentation, product invariants, execution standards, and the source mirror for the GitHub Wiki.

## Source-of-truth map

- Global user-visible behavior: <code>PRODUCT_INVARIANTS.md</code>
- Modernization/fix-forward behavior: <code>MODERNIZATION_STANDARD.md</code>
- Unknown/blocker/recovery behavior: <code>FAILURE_INTELLIGENCE_STANDARD.md</code>
- Challenger discovery and reuse-before-rebuild: <code>CHALLENGER_INTEGRATION_STANDARD.md</code>
- Performance dual-success gate: <code>PERFORMANCE_ACCEPTANCE.md</code>
- Real runtime/workflow evidence: <code>RUNTIME_PROOF.md</code>
- Skill catalog: <code>catalog/SKILLS.md</code>
- Human-facing documentation: <code>wiki/</code> and <code>docs/</code>

Do not duplicate long canonical policy across adapters or wiki pages.

## Repository invariants

1. Preserve the user's actual goal, scope, capability, quality, quantity, compatibility, fidelity, provenance, and verification requirements.
2. A blocker is unresolved work, not completion.
3. Unknown/search miss is not proof of absence.
4. Before substantial invention, perform a bounded challenger/integration pass and prefer authorized reuse, merge, port, wrap, backport, or composition over rebuilding a weaker duplicate.
5. Once target + root cause + safe edit are known, cross into implementation.
6. Performance changes must improve the requested metric and preserve protected behavior.
7. Build/static success is intermediate evidence; exercise the real affected workflow when available.
8. Verified nontrivial recoveries become reusable incident knowledge or regression evidence.
9. Skill/tool/model/connector transitions do not reset accepted requirements, canonical IDs, checkpoints, prior evidence, or exact next action.
10. Important rules should have the strongest practical mechanical enforcement.

## Change discipline

When changing a canonical standard:
1. update the canonical file first;
2. update affected wiki summaries/links in the same coherent change;
3. add or adjust validation/evaluation coverage when the rule is important enough to keep;
4. do not weaken prior invariants merely to make a check pass;
5. record meaningful packaging/provenance changes in <code>bundles/README.md</code>.

## Wiki discipline

The <code>wiki/</code> directory is the version-controlled source mirror for the GitHub Wiki.

- <code>wiki/Home.md</code> is the landing page.
- <code>wiki/_Sidebar.md</code> is primary navigation.
- Keep page names stable.
- The publish workflow mirrors <code>wiki/</code> to GitHub Wiki.
- Canonical policy stays in root standards; wiki pages explain and navigate it.

## Completion

Do one material challenge pass before closeout. Do not continue “just in case” loops after acceptance and required proof are satisfied.
