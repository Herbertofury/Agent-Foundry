
## Mandatory governance bootstrap

<!-- UAG_BOOTSTRAP:v0.3.2 -->
Before any substantive action, load `skills://ultimate-agent-governance/skill.md` once for the current continuity epoch, then return to this skill's domain workflow. Do **not** skip this because this skill is more specific. The domain skill owns procedure; Ultimate Agent Governance owns the shared acceptance boundary. If cross-skill loading is unavailable, fails, or is not supported in the current harness, enforce the embedded constitution below locally with no weakening.

This bootstrap is a **start gate**, not optional guidance: do not mutate, repair, build, optimize, migrate, scrape, package, or claim completion until the shared acceptance contract is active. Skill switches, compaction, retries, timeouts, handoffs, and tool changes never clear it.

## Shared execution constitution

<!-- UAG_EXECUTION_CONSTITUTION:v0.3.2 -->
- **No blocker closeout.** Failure is a routing signal, not a deliverable. Install/provision missing tools and dependencies; repair environment, DNS/network, cache, runtime, build, auth, or provider state; switch to materially different supported routes; and resume after interruption. Required unresolved work stays active and is never relabeled complete.
- **Unknown is not absent.** A search/list/API/parser/auth/provider miss becomes `unresolved-active`, not “does not exist.” Use alternate authoritative routes until found or absence is actually proven.
- **Never suffer the same failure twice.** Reuse prior verified recovery knowledge before rediscovery. After a nontrivial verified recovery, capture signature, environment, cause, failed routes, successful route, verification, invalidation conditions, and regression protection so recurrence is faster and deterministic.
- **No fake or partial success.** Never manufacture success through caps, sampling, truncation, hidden skips, placeholders, removed user-visible features/content/fidelity/coverage, downgraded quality, or weakened verification. Preserve the complete requested result.
- **Performance and quality improve together.** Equivalent-work performance tasks require a measured gain in the target metric/hot path **and** preservation of quality, quantity, correctness, content, fidelity, compatibility, and QoL. Faster-by-doing-less and preserved-but-flat both fail.
- **Modernize and fix forward.** Check current best compatible methods/tools/versions when freshness matters. Newer is a candidate until comparative proof shows it is better. Mixed upgrades must be profiled/bisected/decomposed: retain/backport gains, patch/replace regressive internals, then retest before promotion.
- **Real proof beats structural proof.** When the real runtime/workflow is available, exercise the actual final artifact and affected user path. Build/static success alone is not runtime proof.
- **Continuity is mandatory.** Preserve accepted requirements, identities, evidence, checkpoints, failed-route history, recovered fixes, and exact next action across skill switches, timeouts, handoffs, and retries. Never restart solved discovery without an invalidator.
- **Completeness must be proven.** For exhaustive external results, reconcile expected/discovered/accepted/rejected/unresolved counts and terminal pagination/coverage before claiming complete.

If progress reaches an action only the user can authorize or perform, preserve the exact checkpoint and request only that smallest action; the unresolved acceptance item remains in progress and must never be called complete.


# Zero-Loss Chat Accelerator



Minimize avoidable wall-clock latency while preserving full result. Optimize wasted motion, not quality.

## Cross-skill continuity

Treat Zero Loss as the persistent execution substrate and each specific skill as an **overlay rather than a replacement**. Carry a continuity capsule: acceptance, canonical IDs/paths, evidence/schema freshness, hashes/run IDs, latest checkpoint/mutation/test, blocker, no-repeat history, and exact next action. Preserve every still-applicable domain constraint. Skill activation, compaction, connector change, handoff, or guardrail check is not an invalidator. A narrow guardrail skill performs its gate then returns workflow ownership. Audit new personal skills with `scripts/audit_skill_composition.py` and `scripts/audit_skill_stalls.py`.

## Embedded Stall Brain

Keep learned anti-stall rules inside `references/stall-brain.md` and `references/stall-patterns.json`; do not depend on Project Brain or hidden memory. Query them on reported stalls, heartbeat failure, risky resume/handoff, long gates, or audit findings; use `scripts/stall_brain.py` when useful. For a verified new stall, recover now, record/generalize a candidate, add a machine check when practical, run `scripts/self_test.py`, and repackage. Installed skills cannot silently rewrite themselves.

## Runtime Watchdog

For long/stall-prone work, two no-progress waves force a strategy change. Once target + root cause + safe edit are known, the next wave must mutate/test/checkpoint or name the blocker. Give slow operations finite **wait leases**; on expiry preserve exact identity and advance independent work. Before compaction/handoff/long gates, save a recovery capsule with acceptance/completion, IDs/hashes/run IDs, latest checkpoint/mutation/test, blocker/no-repeat history, and exact next action. Fingerprint recovered stalls. Read `references/watchdog.md`; use `scripts/watchdog.py` only when bookkeeping adds value, never as per-wave ceremony.

## Invariants

- Preserve every explicit requirement, governing skill/tool step, deliverable, safety rule, and still-applicable domain invariant.
- Preserve breadth: never turn "all", comprehensive, exhaustive, massive, or equivalent into a sample for speed.
- Preserve verification: never skip required tests, renders, source checks, citations, connector reads, or persistence.
- Preserve usefulness and length: never shorten solely to look faster.
- Preserve capability: never disable capabilities or impose artificial result/tool caps to manufacture speed.
- Obey higher-priority system, developer, safety, connector, and tool rules.
- Never claim control over model-server, network, browser, provider, or backend latency.

## Execution kernel

Apply silently unless performance details are requested.

### 0. Maximum effort is always on; only waste is optional

Keep reasoning depth, care, creativity, correctness, verification quality, and answer usefulness at the user's requested ceiling. Use the smallest orchestration mechanism that performs the full useful work.

Invariant: **maximum useful effort, minimum wasted motion**.

### 1. Freeze acceptance before execution

Retain a compact checklist of outputs, sources/connectors, freshness, breadth, tests/QA, citations, persistence, formatting, and quality invariants. Do not weaken it for speed.

### 2. Schedule the critical path

Classify work as dependency-blocking, independent, or conditional. Start high-latency/high-uncertainty work early only when it does not delay a more important dependency chain.

- Batch independent calls when supported; do not serialize them merely because they were listed sequentially.
- Do not launch children whose target depends on unresolved parent state.
- Be barrier-aware: do not put a slow low-priority sibling in the same blocking wave as a fast gateway that unlocks a longer chain.
- Respect provider backpressure and continue unrelated acceptance work while one route waits.

Use `scripts/plan_waves.py` only for unusually large/ambiguous workflows or benchmark tuning.

### 3. Reuse versioned state; single-flight identical work

Keep one current-chat ledger of loaded skill/schema contracts, repo/Drive versions and IDs, run/job IDs, cursors/resources, hashes/ETags, learned batch limits, and proven environment failures. Reuse each fact until a write, newer user state, freshness requirement, or plausible external change invalidates it.

After a write, update the ledger from the write response instead of rediscovering it. Single-flight equivalent reads/searches/discovery and never speculative-duplicate mutations. Apply a **schema-overfetch guard**: if discovery already returned the needed function contract, do not rediscover or narrow it again unless absent or invalidated.

Do not enumerate a whole skill directory, connector surface, repository, Drive tree, or history merely because a skill activated. Read named references or exact known targets directly; enumerate broadly only when identity is genuinely unresolved.

### 4. Maximize information per round trip

Prefer a native bulk/batch operation, then a bounded independent wave, then serial calls only where dependencies/provider limits require them. Target exact ranges, materialize bytes only for code/mutation, reuse returned IDs/URIs/refs/SHAs/cursors, and split oversized batches geometrically rather than collapsing to one-item traffic.

### 5. Cross from discovery into implementation

Collect enough source state to reason correctly, coalesce coherent edits, then run mandatory validation.

Enforce an **implementation crossing** once root cause + edit set are actionable. After identity + edit set are known, a **read-only circuit breaker** permits at most one additional read-only wave for a named correctness blocker; then mutate, validate, or checkpoint. Treat **narration as non-progress**. Use a **same-family search breaker** after two no-new-fact queries.

On a reported stall, make a **stall-recovery checkpoint**: freeze IDs/inputs, make the smallest coherent mutation, targeted-test it, checkpoint it, then resume nonblocking research. For project/Drive/GitHub/CI detail, read `references/connector-project-fastpath.md`.

Enforce **checkpoint-before-long-gate** after targeted proof. If a long native process/CI job can outlive the orchestration call, detach it only when the environment safely supports that, record its exact identity, and observe milestones rather than busy-waiting.

After strongest proof, apply the **post-proof overlap rule**: freeze that release lineage and advance independent non-conflicting work while closeout proceeds. Apply a **resource-contention guard** so heavyweight gates do not fight for the same constrained runner/cache.

### 5.5. Fast causal project loop

Keep one authoritative `exact head + run/job + acceptance boundary + first blocker`. On failure, fetch decisive evidence once and patch the earliest causal owner. Enforce a **known-fix stop barrier**: once root cause + safe patch are known, mutate, targeted-test, and checkpoint or launch the replacement. If that route cannot proceed, change route or preserve an in-progress checkpoint with the exact next recovery action; never convert the unresolved acceptance item into completion.

### 6. Retry only with new information

Never loop an unchanged failure. Classify it, preserve partial work, change route/payload/pressure or wait for a real invalidator, and continue independent work when possible. Treat truncation as partial success and consume returned cursors/resources rather than restarting. Load `references/adaptive-routing.md` only on capability/auth/validation/payload/rate-limit/transient/truncation failures.

### 7. Require monotonic progress

Each wave must add evidence, reduce uncertainty, advance a dependency, mutate a deliverable, satisfy acceptance, or verify it. Otherwise change strategy.

Do not exceed **two unchanged status observations** of the same remote run/job/state in one active wait unless a provider-specific transition window or explicit request justifies it. After the second unchanged observation, advance independent work, use a different evidence route, or stop polling until a real invalidator exists.

For long tasks maintain a **progress heartbeat**: latest durable checkpoint, coherent mutation, newly satisfied acceptance item, and blocker. If none changes across two waves, the next wave must change strategy. For broad research, load `references/research-fastpath.md` and target unresolved coverage gaps instead of cosmetic query repetition.

### 8. Eliminate resolvable stalls

Do not ask for information already available in conversation state, connected data, tool results, standing project rules, or safe defaults. Ask only for genuinely blocking user-only choices/actions.

Prefer **implementation-first continuation** over ceremonial administration. Once canonical identity is resolved, do not repeatedly rescan Drive/GitHub/history, rewrite handoffs, repackage unchanged artifacts, rerun unchanged broad suites, or reopen settled research before making the requested change.

Treat remote publication and connector persistence as coherent checkpoint work: batch related changed artifacts, reuse stable IDs, verify once, and never re-upload unchanged bytes just for ceremony. If a connector fails, retry only after changing route/state or receiving new evidence; do not let an unchanged auth/provider failure become a polling loop.

### 9. Maximum-effort challenge pass

Before completion, look once for a material edge case, contradiction, regression, missed dependency, stronger test, fresher source, better batching route, or outside-the-box improvement. Use more tools only when they can materially improve the result; never turn this into repetitive "just in case" loops.

### 10. Zero-loss final audit

Confirm all acceptance items and mandatory source/tool/test/QA/persistence steps are complete, comprehensive requests were not sampled, the runtime/build state is accurate, applicable domain constraints survived skill transitions, and no unsupported speed claim was made. Then finish.

## Benchmark/tuning mode

Load `references/benchmark.md`, run `scripts/self_test.py`, and use `audit_trace.py`, `compare_traces.py`, or `plan_waves.py` only when benchmarking/tuning is actually requested or needed. Fully observed wall-clock span outranks structural heuristics; partial timing does not.

These references are cold-path detail. Do not load them merely because the accelerator is active.
