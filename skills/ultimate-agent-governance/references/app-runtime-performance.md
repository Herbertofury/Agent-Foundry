# Application Runtime and Performance Governance

Use this reference when governance work needs binding rules for interactive applications, runtime verification, or performance acceptance.

## Separate app-domain policy

Keep interactive-application rules in a canonical `APP_INVARIANTS.md` rather than bloating root `AGENTS.md`.

High-value app invariants include:

- UI/persisted/filesystem/runtime/reported state must converge on truth.
- No fake production data, progress, success, or capability.
- Stale asynchronous work cannot overwrite newer user intent.
- Important mutations are atomic or recoverable.
- Durable state survives process restart.
- Search/sort/filter/count/bulk actions preserve complete logical-dataset semantics under virtualization/pagination.
- First useful render does not wait on nonessential enrichment.
- Heavy work stays off the UI thread and preserves responsiveness.
- Prefer incremental invalidation/change tracking over unnecessary full rescans.
- Errors identify the real failed operation and practical recovery.
- Cancellation/backpressure/single-flight prevent concurrency from becoming duplication/races.
- Installed/updated/downloaded/completed states require artifact-level evidence.
- Desktop interactions should behave like native desktop interactions: keyboard/focus/selection/context menus/file operations/window behavior must match the affordance presented.
- No dead architecture: new services, queues, caches, workers, repositories, providers, feature flags, or compatibility layers must be wired into a real production path before they count as implemented.
- Apps should feel alive and companion-like: perform a companion pass for substantial features, adding obvious directly related QoL, contextual next actions, meaningful update awareness, recovery, persistence, and multi-source ecosystem coverage instead of stopping at the literal minimum.
- Ecosystem products should use provider/source registries and normalized provenance/capability metadata rather than assuming one provider is the whole domain. Cover major legitimate official/community/self-hosted/repository/marketplace/author/user-authorized paid sources relevant to the accepted product purpose.
- Track meaningful change types when reliable source data permits (content added/removed, dependency/compatibility changes, public-release transitions, stable-release transitions, source migrations) rather than only version-string changes.
- Product agency is bounded: it does not authorize unrelated scope creep, purchases, hidden subscriptions, destructive actions, access-control/paywall bypass, or leaked/stolen-content acquisition.
- Authenticated integrations are first-class product state: provide a connection/account surface, preflight auth before dependent work, persist authorized sessions securely where permitted, reuse one canonical connection owner, and transition expired/revoked sessions to reconnect-required instead of retrying login walls indefinitely.
- Prefer official OAuth/API/device flows when supported; otherwise use legitimate user-authorized browser/session flows. Never store passwords/tokens/sensitive cookies in plaintext or automate around CAPTCHA/paywall/access-control challenges.
- Background provider jobs should suspend only the affected authenticated provider/account while preserving subscriptions/tracked state, then resume after successful reconnection.
- Provider/site integrations should be routed to a separate canonical `SITE_ADAPTERS.md` policy and a shared adapter platform; see `references/site-adapter-platform.md`.

## Continuous modernization / fix-forward

For substantive app/runtime/performance governance, also apply `references/continuous-modernization.md`. Require a bounded freshness pass on the load-bearing stack, current primary evidence for version-sensitive decisions, newest production-worthy compatible baselines, full production-path integration of materially superior tools, and fix-forward migration rather than permanent rollback for convenience. Preserve explicit target envelopes and backport/adapt newer techniques when the target itself must remain fixed.

## Root runtime-proof gate

Root `AGENTS.md` should state plainly that a passing build is not runtime proof. Put detailed steps in `RUNTIME_PROOF.md` so the root remains concise.

When runtime execution is available, require:

1. fresh build identity;
2. proof the current artifact was launched;
3. exercise of the actual changed workflow;
4. observed result;
5. relevant runtime log/error inspection;
6. restart/reload persistence when applicable.

When runtime cannot be exercised, require an explicit unverified acceptance blocker rather than a false completion claim.

## Performance acceptance

Treat performance as an **always-on zero-loss ratchet** alongside result quality/completeness across apps, mods, tools, and integrations. For substantive runtime-affecting work, run a bounded free-speed pass on the touched or causal path even when the user did not explicitly label the task an optimization. Actively pursue the strongest practical speed/snappiness/throughput using profiling, better algorithms/data structures, batching, fewer round trips, safe concurrency, available CPU threads/cores, async I/O, caching/indexing/incremental state, allocation reduction, native fast paths, and hardware acceleration where useful, without sacrificing capability, fidelity, coverage, correctness, verification, or another relevant performance/resource dimension. Verified no-loss wins become the new baseline. Solvable blockers are engineering work, not permission to ship a degraded result.

A performance task has a **dual-success gate**: (1) show a material improvement in the requested metric, causal hot path, or representative scenario, and (2) preserve or improve the complete intended result. Passing only preservation is incomplete; passing only speed by reducing content/quality is a failure. If the first safe optimization route cannot deliver both, profile deeper, repair/provision the environment or toolchain if necessary, and change algorithms, scheduling, data flow, runtime/native paths, transport/build lanes, or architecture until both are achieved. A failed route is unresolved work, not closeout.

Performance gates must first establish workload/result equivalence. Reject a faster candidate if it truncates results, reduces fidelity, disables work, changes semantics, weakens verification, or materially worsens another relevant protected dimension.

### Multi-dimensional performance protection
Protect the relevant vector, not just one headline number: p50/p95/p99 latency, first-useful and full-completion time, FPS/frame time, TPS/tick time, throughput, cold/warm startup, memory, allocations/GC, CPU, GPU, disk I/O, network requests/bytes, and power/thermal behavior where relevant. Improving one by materially worsening another is a tradeoff, not a zero-loss win. Any nonzero regression tolerance must be explicit and justified as measurement noise or an accepted budget rather than silently granted.

Every verified better equivalent-work candidate ratchets the baseline forward. Do not compare future work against an older slower baseline merely because it is easier to pass.

Measure first-useful-result latency separately from full completion for interactive workflows.

For parallelizable work, evaluate effective concurrency up to hardware/workload limits rather than enforcing a tiny fixed thread count or unbounded thread creation.

Useful mechanisms include safe worker pools, batching, pipelining, asynchronous I/O, cancellation, single-flight, bounded queues, caching, incremental indexing, native/bulk filesystem enumeration, and background enrichment.

## Completion evidence

For substantial work, use a machine-checkable receipt that maps:

`requirement -> implementation -> verification -> observed result -> status`

A receipt marked complete must not contain blockers, failed requirements, or missing required runtime/performance/modernization proof. Modernization proof should record the freshness scope, current baseline, selected baseline, fix-forward/full-integration work, and observed result.
