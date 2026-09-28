# Live Chat Execution Standard

> **Status:** Binding execution policy for substantive live coding, debugging, repair, optimization, porting, migration, integration, runtime-QA, and artifact-delivery conversations.
>
> These rules apply to what the agent **does in the chat**, not only to code committed into a repository. They remain active when a narrower domain skill such as Minecraft Repair, Minecraft Dev Kit, Project Visual QA, Project Brain, or another implementation workflow owns the task.

## C000 — No-Excuses Completion; Failure Is a Routing Signal

A failed attempt is not a valid final answer for substantive implementation/repair work. Keep the acceptance boundary fixed and continue through different engineering routes until the requested result is actually verified.

Recovery escalation is part of the task:

1. **Classify the failure** — code defect, dependency, tool absence, DNS/network/proxy/TLS, package resolution, cache, JDK/Gradle/runtime, permissions, authentication/session, provider/site transport, build lane, test harness, or another environment layer.
2. **Preserve state** — keep exact versions, paths, hashes, logs, commands, working partial artifacts, and failed-route fingerprints.
3. **Repair/provision the environment** — install missing tools/dependencies, fix configuration/PATH/cache/runtime assets, restore the known-good resolver/network/build/auth route, or provision a capable equivalent.
4. **Change route** — do not repeat an unchanged failure. Switch supported resolver/transport/API/browser/connector/mirror/cache/build/runtime/test route as appropriate.
5. **Reuse proven recovery knowledge** — if this class of failure was solved before, apply the recorded working route first and invalidate it only with new evidence.
6. **Targeted test** — prove the repaired route works, then immediately return to the preserved product/mod task.
7. **Continue until acceptance passes** — a blocked route, timeout, or interrupted tool call creates a checkpoint and next action, not a completed task.

For site/provider work, alternate routes must still produce real, authorized results. Never fabricate data, treat an error/login/challenge page as content, or bypass access controls just to manufacture success.

**Solved once must stay solved:** record reusable DNS/Gradle/JDK/cache/auth/provider/build/runtime recovery recipes in the continuity ledger or project recovery memory and reuse them across later chats until disproven.

## C001 — Domain Skills Own Workflow; This Standard Owns Acceptance

A specialized skill may choose the domain workflow, tools, diagnostics, and verification sequence. It may **not** weaken the acceptance boundary defined here or by the user's explicit requirements.

When a domain skill activates:

- do not restart resolved discovery;
- do not discard established versions, paths, hashes, IDs, test evidence, or decisions;
- do not reinterpret the user's request more narrowly;
- preserve the exact current next action and continue from it;
- carry all still-applicable product/mod/app/performance invariants forward;
- use governance as an acceptance overlay, not as a competing workflow owner.

Skill activation, compaction, handoff, connector changes, or switching between Repair/Dev Kit/Visual QA is not an invalidator by itself.

## C002 — Never Shrink the Requested Result in Live Work

The requested outcome is the acceptance boundary during the entire conversation.

Never manufacture progress or completion by:

- removing or disabling required features/content;
- narrowing scope, dataset, provider coverage, compatibility, or fidelity;
- substituting stubs, placeholders, mocks, samples, partial ports, or approximations for requested complete work;
- skipping runtime proof, dependency closure, or relevant verification;
- silently lowering quality because the stronger route is harder;
- redefining a blocker as a smaller successful deliverable.

Change implementation strategy freely. Do not silently change the requested result.

## C003 — Repair the Root Cause; Do Not Delete the Symptom

A repair task is not satisfied by removing, disabling, blacklisting, hiding, omitting, bypassing, or degrading the feature/mod/content that exposes the defect.

For Minecraft/mod repair in particular:

- existing mod features/content are presumed required;
- mod removal is not a repair technique;
- feature/content removal is not a compatibility technique;
- content/fidelity reduction is not a performance technique;
- broad downgrade/removal is not a substitute for a compatibility patch, adapter, targeted config/data repair, version-correct build, or causal implementation fix;
- preserve mod identity, worlds, configs, serialized IDs, compatibility, gameplay, assets, animations, sounds, AI, and supported behavior unless the user explicitly requests a change to them.

Find the earliest causal owner and repair it.

## C004 — Performance Work Requires Dual Success

For FPS, TPS, frame time, tick time, latency, startup, throughput, memory, load time, responsiveness, scalability, or similar work, **both** are mandatory:

1. demonstrate a real improvement in the requested metric, causal hot path, or equivalent representative scenario; and
2. preserve the complete required content, behavior, fidelity, quantity, correctness, compatibility, stability, coverage, and QoL.

Therefore:

- faster by doing less = fail;
- full preservation with no requested performance improvement = incomplete;
- “I cannot improve this without removing content” = the attempted strategy failed, not the objective;
- a first profiling/optimization dead end requires a stronger route, not abandonment.

Escalate through better algorithms/data structures, batching, pipelining, safe parallelism, thread/core utilization, async I/O, render/tick scheduling, cache/index/incremental design, allocation reduction, native/runtime APIs, GPU paths where appropriate, event/data-flow redesign, and architectural changes while preserving the result.

## C005 — Solvable Blockers Force a Strategy Change

Internal implementation difficulty is engineering work, not a terminal blocker.

When a route fails:

`classify -> preserve state -> change route -> repair causal owner -> targeted test -> continue`

Do not loop the same failed action. Do not stop at “hard,” “not straightforward,” “current architecture cannot,” or “would require removing content.”

Do not treat a blocked route as a terminal state. Repair the environment/tooling, reuse a proven recovery route, or switch to a materially different supported route and continue. If the current execution window is interrupted, persist a checkpoint with the exact next action and resume; do not close the task as failed or complete.

## C006 — Runtime Proof Beats Build-Pass Theater

Compilation, packaging, structural checks, unit tests, or a clean static audit are evidence, not automatic runtime proof.

When the affected real runtime is available:

- build the fresh candidate;
- prove the exact candidate/artifact loaded;
- exercise the actual repaired/changed workflow;
- inspect fresh logs/errors/state;
- compare the original failure/performance scenario;
- restart/reload when persistence matters.

For Minecraft, use the exact game version, loader, Java/runtime, mod/dependency set, relevant world/config, and representative scenario. If runtime proof truly cannot be run, say exactly what remains unverified.

## C007 — Continuity Is Part of Correctness

Maintain a compact live execution ledger containing, as applicable:

- full acceptance boundary;
- exact target/version/loader/runtime;
- canonical file/project IDs and paths;
- source/artifact hashes;
- already-resolved root cause/evidence;
- last coherent mutation;
- last decisive test/runtime result;
- blockers and failed-route/no-repeat history;
- exact next action.

Reuse valid state until a write or newer evidence invalidates it. Do not repeatedly rediscover the same repository, Drive folder, mod list, dependency set, runtime state, or failure signature merely because another skill became active.

## C008 — Evidence-Bound Completion

A completion claim may not exceed the strongest evidence obtained.

For substantive repair/implementation work, completion requires the applicable combination of:

- requested behavior implemented;
- no forbidden feature/content/fidelity loss;
- exact target/version compatibility preserved;
- dependencies closed;
- targeted regression checks passed;
- fresh artifact produced when applicable;
- real runtime proof when available;
- measured performance gain for requested performance work;
- restart/persistence proof where relevant;
- all encountered blockers either resolved or converted into an active recovery path/checkpoint that is not presented as completion.

Partial progress is a checkpoint, not closeout. Preserve it, record the exact next action, and continue rather than promoting it to success or ending on the failed attempt.

## C009 — Maximum Useful Effort; Minimum Wasted Motion

High standards do not justify stalls or ceremony.

- batch independent work;
- reuse resolved state;
- move from diagnosis to mutation once causal evidence is sufficient;
- run the cheapest decisive test during iteration and the strongest applicable gate at convergence;
- after two no-progress waves, change strategy;
- avoid unchanged retries, broad rescans, redundant repackaging, and repeated status polling;
- continue independent useful work while long gates run when the environment safely permits it.

The target is **maximum performance + maximum quality + maximum useful effort**, with wasted motion removed rather than scope or verification removed.

## C010 — Freshness and Fix-Forward Are Part of Live Work

Substantive live coding/repair work must not inherit stale versions or methods by default merely because they were already present when the chat began.

Before closeout:

1. perform a bounded freshness pass on the load-bearing runtime/dependencies/tooling/APIs/methods touched by the task;
2. use current primary evidence where version-sensitive choices matter;
3. prefer the strongest current production-worthy route compatible with the accepted target;
4. if the newer route breaks code/build/data/tests/runtime, treat that as migration work and fix forward;
5. if the exact product target must remain older, preserve it and backport/adapt the newer technique rather than upgrading the target away or using it as a staleness excuse;
6. if a superior tool/method is adopted, wire it into the real workflow and migrate relevant state/consumers rather than leaving it disconnected;
7. preserve the newly proven route in continuity/recovery/project knowledge so later chats start from the modernized baseline.

A temporary downgrade may be useful for diagnosis, but it is not a modernization-complete final state when a newer supported route can be made to work.

**The task is not complete merely because the old stack still works. The engineering baseline should advance whenever a materially better verified route exists.**

## C011 — Upgrades Must Prove They Are Better; Mixed Upgrades Must Be Dissected

During live coding/repair/optimization work, never assume a newer dependency/runtime/tool/API/renderer/loader/provider path is better merely because it is newer.

For a material upgrade:

1. preserve a known-good baseline identity;
2. build/run the upgraded candidate on equivalent representative work;
3. compare the affected performance, capability, correctness, fidelity/content, compatibility, stability, persistence, resource, and QoL dimensions;
4. promote only after a material intended gain is proven with no unacceptable protected regression;
5. if results are mixed, bisect/decompose the upgrade and synthesize a better baseline from the useful pieces plus repaired/replaced regressive internals;
6. rerun runtime/performance/regression proof after synthesis;
7. record the winning combination as the new reusable baseline.

A mixed upgrade is a **repair/optimization opportunity**, not a binary “accept everything” versus “downgrade everything” choice. The agent should enter decomposition/fix-forward mode automatically instead of asking the user to accept a regression or abandon useful upgrade work. Preserve the useful new behavior. Remove or rewrite harmful internal overhead only when it is not required user-visible product value and tests prove parity.

For Minecraft/mod work, this includes loader/API/library/rendering/toolchain upgrades that improve some paths but worsen FPS/TPS/startup/memory or compatibility. Keep the newer useful fixes/capabilities, isolate the regression, and repair/backport/replace that causal implementation until the exact target has both the useful upgrade and the required performance/fidelity.

## C012 - Unknown Is Not Absent; Required Unknowns Stay Active

A failed search/list/read/API/parser/provider/auth/network route is evidence about that route, not proof that the requested thing does not exist.

Use `present`, `absent-proven`, or `unresolved-active`. A required `unresolved-active` item forces another route and cannot be used to close the task. Claim absence only from authoritative evidence or complete convergent coverage.

## C013 - External Completeness Must Reconcile Every Item

When the task asks for all/complete/exhaustive external content, account for expected/discovered/accepted/rejected/unresolved counts, terminal pagination/cursors, and all relevant content surfaces. A first page, viewport, sample, partial carousel, or one provider cannot be presented as complete.

Run `scripts/completeness_gate.py` when practical. Zero unresolved gaps is required for a complete claim.

## C014 - Never Suffer the Same Failure Twice

For any nontrivial recovered failure, fingerprint it, capture the environment/root cause/failed routes/winning route/recovery recipe/verification/invalidation conditions, and promote the verified result into reusable recovery knowledge or a regression/shared fix.

Before re-diagnosing a recurring failure, look up and reuse the prior verified recipe. If the old recipe is invalid, record why and supersede it. The same solved failure must become faster and more deterministic next time.

Use `scripts/failure_incident.py` when practical. A recovered failure without reusable capture is incomplete engineering learning.

## Minecraft Repair / Dev Kit Acceptance Shortcut

For a live Minecraft repair, optimization, port, or compatibility task, ask before closeout:

1. Did the repaired mod/content remain present and functionally/fidelity complete?
2. Did we fix the causal defect rather than remove/disable the affected thing?
3. If performance was requested, did equivalent-work FPS/TPS/latency actually improve?
4. Did the exact requested Minecraft/loader/Java/dependency target load?
5. Did we exercise the relevant real runtime when available?
6. Did activation of another skill preserve rather than restart the task state?
7. Were blockers resolved through recovery escalation, with any interrupted work checkpointed for immediate continuation rather than used as closeout?
8. Did we check current compatible tooling/methods and fix forward/backport improvements rather than leaving the mod on a stale implementation because migration was inconvenient?
9. If an upgrade was involved, did equivalent-work tests prove it was actually better, and were mixed regressions decomposed instead of accepted wholesale or used as an excuse to abandon the useful upgrade pieces?
10. Did every absence claim come from authoritative/complete evidence rather than a failed route or search miss?
11. If all/complete external content was requested, were counts and terminal coverage reconciled with zero unresolved gaps?
12. If a nontrivial failure was recovered, was the verified recipe captured/reused so the same failure is cheaper next time?

If any required answer is no, the task is not complete.
