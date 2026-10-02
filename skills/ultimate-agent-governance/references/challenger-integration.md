# Challenger and Integration Discovery Standard

> **Status:** Binding cross-domain execution policy for substantive implementation, architecture, optimization, ports/converters, integrations, tooling, and platform work.

## Prime invariant

**The goal is not merely to avoid reinvention; it is to start from the strongest credible existing baseline and build something measurably stronger for the user.** Challenger discovery feeds a beat-the-baseline plan: reuse/compose superior authorized pieces, preserve protected dimensions, and seek a real advantage rather than shipping a weaker clone.


**Challenge the proposed implementation before reinventing it.** Search for stronger existing implementations and complementary integrations, prefer authorized reuse when it produces a better result, compose best-of-breed pieces when appropriate, and invent only where the evidence leaves a real gap.

This is the generalized form of the Enderloom workflow: do not assume the project you already know is the ceiling. Deliberately look for challengers that can raise the ceiling.

## 1. Define the capability boundary first

Capture the exact capability or bottleneck being solved, protected behavior, target/platform/version envelope, performance/quality constraints, and user authorization boundaries. This prevents a superficially impressive project from winning while failing the real task.

## 2. Search the challenger space

Use current evidence when the ecosystem can change. Cover the highest-yield relevant surfaces rather than repeating one search engine:

- official/upstream implementations and maintained forks;
- GitHub, GitLab, Codeberg, package/plugin registries, and domain-specific indexes;
- reference clients, SDK examples, standards implementations, compatibility layers, migration/conversion tools, profilers, renderers, parsers, adapters, and reusable libraries;
- authorized internal/commercial code or installed applications when the user explicitly has permission to inspect/integrate them.

Search by **capability**, not only by the incumbent project's name. Use synonyms, competing architectures, successor projects, forks, and adjacent tools that solve only one valuable subproblem.

## 3. Build a decision ledger, not a link pile

For each credible challenger, record whether it is the **baseline-to-beat**, a component to reuse/port/wrap, a source of a technique to backport, or a rejected candidate. Record the comparison dimensions and the evidence required before claiming the final result is superior.


For each serious candidate record:

- name, source, exact version/tag/commit;
- what it does better and what it lacks;
- compatibility with the accepted target;
- performance, fidelity, correctness, maintenance, and ecosystem evidence as applicable;
- license/provenance/authorization status;
- integration cost/risk;
- disposition: `adopt`, `merge`, `port`, `wrap`, `backport`, `compose`, `reject`, or `unresolved`;
- concise reason.

A rejection needs a real reason such as incompatibility, worse evidence, stale/unmaintained code, missing required capability, unacceptable regression, or permission/license conflict. “Already have our own” is not enough.

## 4. Prefer reuse-before-rebuild

When a candidate is materially stronger and authorized, integrate it into the actual production path. Do not merely mimic its surface behavior if direct reuse/porting/wrapping is allowed and gives a stronger result.

Allowed outcomes include:

- adopt one challenger wholesale;
- merge or port its best subsystem;
- wrap it behind the project's canonical API;
- backport a newer algorithm/architecture into an older target;
- compose multiple challengers where each owns a different best capability;
- retain the incumbent only where comparative evidence shows it is still stronger.

Preserve provenance and required notices. Authorization to inspect or integrate one source does not imply permission for unrelated sources.

## 5. Integration must be real

A selected challenger is not “integrated” until real workflows use it, state/config migration is handled, error/auth/cache/telemetry semantics are coherent where applicable, tests cover it, and bypass paths no longer leave the weaker implementation authoritative.

## 6. Bound the search so it cannot stall implementation

The challenger pass is complete enough when:

1. the obvious incumbent/upstream path is checked;
2. multiple plausible alternative families or ecosystems have been considered where they exist;
3. serious candidates have dispositions with evidence;
4. remaining unknowns are explicit; and
5. the implementation decision is actionable.

At that point, implement. Reopen challenger discovery only when new evidence, a blocker, a failed benchmark, a missing capability, or a material ecosystem update invalidates the decision.

## 7. Make the result reusable

Preserve the winning combination, rejected-route reasons, exact versions/commits, migration notes, and comparative proof in project continuity/governance. A later analogous task should begin from the proven challenger map instead of restarting discovery.

Use `scripts/challenger_gate.py` to validate a JSON challenger receipt when the decision is important enough to make mechanically checkable.

## Minimal receipt example

```json
{
  "scope": "mod conversion pipeline",
  "coverage_complete": true,
  "searched_sources": ["upstream", "GitHub", "Codeberg", "package ecosystem"],
  "candidates": [
    {
      "name": "candidate-a",
      "source": "https://example.invalid/project",
      "version": "v1.2.3",
      "disposition": "merge",
      "reason": "best parser, compatible target",
      "permission": "compatible license / user-authorized",
      "evidence": ["fixture parity", "benchmark"]
    }
  ],
  "decision": "Merge candidate-a parser and keep incumbent renderer",
  "implementation_ready": true
}
```
