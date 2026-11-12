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

## Review and evidence rules

Review date: **2026-11-12**. This is a comparison agenda, not a benchmark result or proof of superiority. Official-source capability descriptions and our proposed experiments are separate. Pin actual versions and licenses before reuse; record publication date separately from the date checked. Retain failed comparisons and rejected candidates.

During recurring reviews, inspect upstream releases, breaking changes, security notices and relevant issue reports; add a dated change note only for a meaningful change. Reuse the existing catalogs instead of creating another disconnected list. A missing observation is **unknown**, not unsupported. No new feature is silently authorized merely by appearing here.

For each proposed adoption, record baseline revision, candidate revision, identical workload, required outputs, correctness/security/compatibility checks, latency distribution, memory and reproducible raw evidence. Never make a target-project superiority claim from a synthetic microbenchmark. Keep private assets and traces out of public evidence.

## Publication status

This repository document is the canonical comparison entry point for this addition. A repository-backed wiki page can link to it without duplicating its tables. Native GitHub Wiki publication must be verified separately; a wiki-enabled setting or a source mirror is not publication proof.
