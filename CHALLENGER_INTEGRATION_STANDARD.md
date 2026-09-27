# Challenger & Integration Standard

> **Challenge before reinventing. Compose the strongest authorized pieces.**

This standard governs substantial invention, integration, modernization, conversion, migration, performance engineering, and tooling work.

## Goal
Before building a large capability from scratch, actively determine whether mature existing work can make the result better, faster, more compatible, more complete, or easier to maintain.

## Search surface
Use a bounded, relevance-driven pass across sources such as:
- upstream projects and official implementations;
- GitHub, GitLab, Codeberg and significant forks;
- package/plugin ecosystems;
- standards and reference implementations;
- mature libraries and frameworks;
- authorized internal, purchased, or commercial implementations when the user has rights to use them.

Do not search every ecosystem mechanically when it is irrelevant.

## Candidate decisions
Every material candidate should end in one explicit state:

| Decision | Meaning |
|---|---|
| \`adopt\` | use substantially as-is |
| \`merge\` | ingest useful internals into the target |
| \`port\` | move implementation across version/platform/runtime |
| \`wrap\` | keep the implementation behind a stable adapter |
| \`backport\` | bring a newer technique to an older fixed target |
| \`compose\` | combine best-of-breed pieces from multiple candidates |
| \`reject\` | evidence shows the candidate is not a fit |
| \`unresolved\` | more evidence is genuinely needed |

## Evidence to capture
For load-bearing candidates record:
- source and provenance;
- version/date;
- license or explicit authorization status where relevant;
- compatibility with the exact target;
- capability/fidelity advantages;
- performance implications;
- maintenance/architecture fit;
- chosen decision and rationale.

## Reuse-before-rebuild rule
If an authorized mature implementation already solves the hard part better, do not recreate an inferior duplicate merely to avoid integration work.

Integration work is engineering work.

## Composition is first-class
Do not force a single winner when a stronger system can combine:
- one project's parser;
- another project's cache;
- another project's compatibility layer;
- another project's UI/UX behavior;
- local project-specific orchestration.

The target is the strongest coherent result, not loyalty to one upstream.

## Anti-research-stall rule
The challenger pass is bounded. Once:
- the high-value search space is covered;
- the likely best candidates are understood;
- target + edit/integration set are actionable;

cross into implementation.

Further read-only work requires a named correctness blocker.

## Acceptance
A challenger pass succeeds when it materially changes confidence, design, or implementation—or establishes with evidence that custom implementation is still the strongest route.

It does **not** succeed merely because many links were collected.
