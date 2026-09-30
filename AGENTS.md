# Agent Foundry repository instructions

This repository is the canonical public home for Agent Foundry governance, skills documentation, product invariants, execution standards, and the source mirror for the GitHub Wiki.

## Source-of-truth map

- Global user-visible behavior: <code>PRODUCT_INVARIANTS.md</code>
- Modernization/fix-forward behavior: <code>MODERNIZATION_STANDARD.md</code>
- Unknown/blocker/recovery behavior: <code>FAILURE_INTELLIGENCE_STANDARD.md</code>
- Challenger discovery and reuse-before-rebuild: <code>CHALLENGER_INTEGRATION_STANDARD.md</code>
- Performance dual-success gate: <code>PERFORMANCE_ACCEPTANCE.md</code>
- Real runtime/workflow evidence: <code>RUNTIME_PROOF.md</code>
- Durable async/resume semantics: <code>DURABLE_EXECUTION_STANDARD.md</code>
- Real-harness eval behavior: <code>EVALUATION_STANDARD.md</code>
- Trace/event semantics: <code>OBSERVABILITY_STANDARD.md</code>
- Agent/tool/agent/client/UI/control protocols: <code>INTEROPERABILITY_STANDARD.md</code>
- Sensitive-action policy boundaries: <code>AUTHORIZATION_CONTROL_STANDARD.md</code>
- Third-party Skill trust: <code>THIRD_PARTY_SKILL_SECURITY.md</code>
- Bundle provenance and attestations: <code>SUPPLY_CHAIN_STANDARD.md</code>
- Skill install/sync/update compatibility: <code>DISTRIBUTION_STANDARD.md</code>
- Version-sensitive protocol facts: <code>registry/protocols.json</code>
- Skill catalog: <code>catalog/SKILLS.md</code>
- Human-facing documentation: <code>wiki/</code> and <code>docs/</code>

Do not duplicate long canonical policy across adapters or wiki pages.

## Repository invariants

1. Preserve the user's actual goal, scope, capability, quality, quantity, compatibility, fidelity, provenance, and verification requirements.
2. A blocker is unresolved work, not completion.
3. Unknown/search miss is not proof of absence.
4. Before substantial invention, perform a bounded challenger/integration pass and prefer authorized reuse, merge, port, wrap, backport, or composition over rebuilding a weaker duplicate.
5. Once target + root cause + safe edit are known, cross into implementation.
6. Performance is an always-on zero-loss ratchet: for substantive changes that touch runtime work, perform a bounded no-loss performance pass, adopt verified wins, and treat each proven improvement as the new floor. Never accept faster-by-doing-less or a material regression in any relevant protected metric.
7. Root-cause fixes over regression workarounds: repair the causal defect or bottleneck instead of removing/disabling features, shrinking work, adding sleeps/delays/polling/retries, forcing serialization/blocking, duplicating work, or shifting cost elsewhere. Any such materially regressive workaround is temporary containment, remains unresolved, and is not the final fix unless the user explicitly accepts the tradeoff.
8. Build/static success is intermediate evidence; exercise the real affected workflow when available.
9. Verified nontrivial recoveries become reusable incident knowledge or regression evidence.
10. Skill/tool/model/connector transitions do not reset accepted requirements, canonical IDs, checkpoints, prior evidence, or exact next action.
11. Important rules should have the strongest practical mechanical enforcement.
12. Third-party Skills remain untrusted until provenance, content, capabilities, and security evidence are reviewed.
13. Sensitive actions require real authorization/enforcement boundaries; prompt text alone is not a security boundary.
14. Published bundles must have verifiable source/digest lineage, and signed attestations should be preferred when the build path supports them.
15. Protocol adapters preserve native task, cancellation, permission, identity, and streaming semantics rather than flattening them for convenience.

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
