# Competing approaches and challenger workflows

Foundry is a governance and reusable-skill system, not a replacement for every agent framework. Extend the [existing challenger sweep](research/CHALLENGER_SWEEP_2026-09-27.md) and follow the [integration standard](CHALLENGER_INTEGRATION_STANDARD.md); do not replace their adoption decisions with a popularity ranking.

| Comparator and primary source | Documented role | Foundry question / proposed test |
|---|---|---|
| [Inspect AI](https://inspect.aisi.org.uk/) | Evaluation framework with tasks, scoring, tools and analysis | Compare an identical tool-using task with and without a Foundry skill. Grade actual state changes, false completion and permission handling, not just prose. |
| [Temporal](https://docs.temporal.io/) | Durable execution platform | Inject interruption around a side effect and human approval wait. Compare recovery evidence, duplicate side effects, cancellation and operational cost. |
| [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview) | Stateful agent orchestration, persistence and interrupts | Evaluate whether a thin adapter preserves Foundry task identity and approval boundaries better than a bespoke coordinator. |
| Existing Phoenix / Langfuse and OPA / Cedar lanes | Observability and authorization comparators already cataloged in the sweep | Keep tracing separate from canonical truth, and policy enforcement separate from model persuasion. Extend the existing test lane instead of adding duplicate frameworks. |

## Improvement backlog, not accepted results
- [ ] Publish a small reproducible failure corpus: lost acceptance criteria, interrupted write, stale checkpoint, denied tool, duplicate handoff.
- [ ] Compare recoverability and completed user outcomes at fixed permissions and budget.
- [ ] Capture versioned adapter contracts and rejected alternatives; require an actual workflow before adding an adapter.
- [ ] Test provenance and revocation when third-party skills change. A scanner pass is not a trust guarantee.


## Potential foundations, reuse and integration decisions

These are **evaluation proposals**, not new adoption decisions. The existing challenger standard remains authoritative.

| Potential foundation | Specific reuse to investigate | Improve rather than clone | Integration boundary and empirical gate |
|---|---|---|---|
| Inspect evaluation components | Task/scorer interfaces and retained tool trajectories | Grade preserved user requirements, truthful completion and side-effect state, not eloquent reports | Export sanitized Foundry evaluation receipts; replay the same failure corpus with and without the skill and compare false-success rate at fixed budget. |
| Temporal or LangGraph, evaluated separately | Checkpoint/interrupt/resume semantics behind a thin adapter | Retain permission decisions and task identity across recovery without duplicate writes | Use a sandboxed toy side effect first. Kill/restart before and after commit and during human wait; require exactly one authorized effect and complete cancellation evidence. |
| Existing protocol standards | Versioned schemas and conformance tests rather than a new proprietary protocol | Preserve native cancellation, identity and streaming instead of flattening everything into text | Exchange only scoped task/evidence records with Atlas or Athena; their data stores and permissions remain independent. |
| Existing Foundry invariants and incident catalog | The current canonical standards and recovery receipts | Make important invariants mechanically testable; eliminate duplicated adapter policy | Link shared standards from each project instead of copying drifting policy blocks. Require target-specific evaluation before claiming benefit. |

**Licensing/compatibility gate:** inspect each exact pinned upstream revision, LICENSE, dependency licenses, redistribution/notice requirements and supported runtime before code reuse. A public documentation page does not grant permission to copy its implementation. Keep provider credentials and private trajectories outside shared adapters.

**Current evidence:** only documented capability and proposed experiments in this section. No new framework was installed, no adapter was integrated, and no comparative execution result is claimed. Reject a candidate if recovery duplicates effects, erases permission state or raises operating cost without a protected user benefit.

## Review and evidence rules

Review date: **2026-11-12**. This is a comparison agenda, not a benchmark result or proof of superiority. Official-source capability descriptions and our proposed experiments are separate. Pin actual versions and licenses before reuse; record publication date separately from the date checked. Retain failed comparisons and rejected candidates.

During recurring reviews, inspect upstream releases, breaking changes, security notices and relevant issue reports; add a dated change note only for a meaningful change. Reuse the existing catalogs instead of creating another disconnected list. A missing observation is **unknown**, not unsupported. No new feature is silently authorized merely by appearing here.

For each proposed adoption, record baseline revision, candidate revision, identical workload, required outputs, correctness/security/compatibility checks, latency distribution, memory and reproducible raw evidence. Never make a target-project superiority claim from a synthetic microbenchmark. Keep private assets and traces out of public evidence.

## Publication status

This repository document is the canonical comparison entry point for this addition. A repository-backed wiki page can link to it without duplicating its tables. Native GitHub Wiki publication must be verified separately; a wiki-enabled setting or a source mirror is not publication proof.
