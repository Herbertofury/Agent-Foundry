# Embedded Stall Brain

This is Zero Loss's self-contained memory of proven chat-stall failure modes. It exists so anti-stall behavior does not depend on Project Brain, another skill, a prior chat, or a connector being active.

Do not preload this file on ordinary healthy tasks. Load it when any of these is true:

- the user reports that the chat stalled, looped, repeated itself, or burned the conversation without advancing;
- the progress heartbeat fails across two execution waves;
- a skill transition, compaction, resume, or connector handoff risks losing the exact next action;
- a long remote process, upload, CI run, runtime, or publication path becomes the blocking dependency;
- `audit_trace.py` or `audit_skill_stalls.py` finds a stall-risk signal;
- a repeated failure suggests a new general anti-stall lesson.

The machine-readable rule catalog is `stall-patterns.json`. Use `scripts/stall_brain.py search` or `diagnose` when code execution is available. The Markdown below is the human control plane.

## Core diagnosis order

When progress stalls, diagnose in this order instead of immediately adding more work:

1. **State loss:** Did a skill/connector/compaction transition drop the acceptance ledger, canonical IDs, evidence, blocker, or exact next action?
2. **Observation loop:** Are we rereading, rediscovering, polling, rerendering, or rerunning unchanged validation?
3. **Waiting mistake:** Are we synchronously waiting on a long process that can be identified and observed by milestones, or using huge retry/socket budgets?
4. **Critical-path mistake:** Did a slow low-priority sibling block a fast gateway, or did heavyweight concurrent jobs contend for the same runner/cache?
5. **Ownership mistake:** Did a guardrail/subskill become a workflow owner, or did a domain subroutine re-baseline the parent task?
6. **Persistence ceremony:** Are Drive/GitHub/status/handoff/catalog steps being repeated on unchanged bytes/state rather than at coherent checkpoints?
7. **Recovery mistake:** Are we repeating the same failed route without an invalidator, hammering a rate limit, or restarting after truncation instead of continuing?
8. **Implementation avoidance:** Is the actionable fix already known but we keep reading, planning, narrating, or broadening research instead of mutating and testing?

## Learned stall rules

### 1. Skill transition resets execution state
Preserve the continuity capsule across every skill transition: acceptance, canonical paths/IDs, loaded evidence and schema freshness, hashes/run IDs, latest durable checkpoint/mutation/test, blocker, no-repeat history, and exact next action. A new skill overlays the state; it does not start a fresh workflow.

### 2. Guardrail or subskill steals workflow ownership
Narrow guardrails perform one bounded decision and return control. Repair, visual QA, document, spreadsheet, research, and publication helpers act as bounded subroutines unless the user's task itself makes them the primary owner. Returning from a subskill must resume the parent's preserved exact next action without re-baselining.

### 3. Activation triggers broad enumeration
Do not list a whole skill directory, connector surface, repository tree, Drive tree, history, or project catalog merely because a skill activated. Read the exact known target/reference first. Broad discovery is reserved for unresolved identity or a named acceptance gap.

### 4. Hot-path instruction bloat
Keep always-loaded skill entrypoints compact. Put cold QA, provider, benchmark, porting, and troubleshooting detail in references loaded only when its trigger is met. Extra control-plane text is itself latency and context pressure.

### 5. Repeated read/discovery of unchanged state
Single-flight equivalent reads/searches/discovery. Reuse versioned evidence until a write, explicit freshness need, newer user input, or plausible external change invalidates it. After your own write, trust the write response and update the ledger rather than rediscovering the state you just created.

### 6. Read-only discovery continues after the fix is actionable
Use the implementation crossing and read-only circuit breaker. Once identity, root cause, and a safe coherent edit set are known, permit at most one more read-only wave for a named correctness blocker; then mutate, targeted-test, or checkpoint.

### 7. Same-family search repetition
After two searches in the same family add no material fact, change strategy: use a stronger source, inspect the exact artifact, narrow to the unresolved gap, or implement/test what is already known. Cosmetic query rewrites are not progress.

### 8. Polling an unchanged job/run/state
Do not exceed two unchanged observations of the same run/job/state in one active wait unless an explicit transition window requires it. Preserve the exact run/PID/job identity, observe meaningful milestones, and advance independent work instead of busy-waiting.

### 9. Broad CI rediscovery after exact run identity is known
Once the exact run/job ID is known, query that run. Do not repeatedly list recent runs/workflows to rediscover it. Replace the exact identity only when new evidence proves a replacement run exists.

### 10. Retry without an invalidator
Never repeat an unchanged failure on the same route merely because time passed. Retry only after a changed payload, route, pressure level, authentication state, provider recovery signal, retry window, or other real invalidator.

### 11. Rate-limit hammering
Honor `Retry-After` or a conservative backoff. Do not immediately retry the same provider under the same pressure. Continue unrelated work while waiting when possible.

### 12. Unbounded waits, socket timeouts, or retry budgets
Interactive skill scripts must have finite subprocess/network timeouts and small default retry ceilings. Prefer resumable operations and checkpointed progress over one call that can hold the chat for minutes. A timeout must preserve partial state and exact recovery identity.

### 13. Full validation suite repeated on unchanged state
Use changed-path/targeted tests during iteration. Run the broad required suite at convergence, after a material state change, or when a specific cross-cutting risk requires it. Do not rerun a full suite simply for reassurance.

### 14. Build/status ceremony displaces the usable artifact
For implementation work, protect the build-first invariant: get a current usable artifact/build after the coherent implementation state, then perform concise status/handoff/catalog closeout. Do not spend the remaining session on reports while the runnable result is stale or missing.

### 15. Entire gate stack reruns after every edit
Do not rerun static + server + client + render + package stacks after every micro-edit. Select the smallest gate that can disprove the current change, then run the full applicable release gate once the edit set converges.

### 16. Re-rendering unchanged visual states
Reuse source inventory, render configuration, deterministic frames, and existing proof when source/state is unchanged. Render only changed/risky states and required final coverage.

### 17. Re-enumerating canonical sources after a file-format subskill returns
A spreadsheet/document/PDF helper may transform or inspect a known source, but returning from it must not trigger a full source discovery pass. Reuse canonical IDs/hashes and process only changed sources.

### 18. Re-reading an entire repair/history brain every iteration
Perform one targeted knowledge lookup keyed to the failure signature/version. Reuse the loaded result until the failure signature or relevant version changes. Do not reread full history after each patch.

### 19. Re-refreshing market/pipeline state without a freshness need
Reuse a fresh sourced snapshot for candidate generation and scoring. Refresh only the exact opportunity immediately before an irreversible/send/apply action. Do not repeatedly poll an unchanged market or pipeline.

### 20. Duplicate or fragmented mutations
Never duplicate send/apply/delete/publish mutations speculatively. Coalesce coherent repository or artifact writes where the provider permits it. Record write responses so a follow-up does not repeat the mutation.

### 21. Re-uploading or republishing unchanged bytes
Batch related changed artifacts at coherent checkpoints, reuse stable remote IDs, and verify once. Do not re-upload identical bytes or re-list the same destination for ceremony. A failed connector route must not become a blind retry loop.

### 22. Checkpoint is delayed until after a long gate
After targeted proof of a coherent implementation state, create a recoverable checkpoint before a long CI/native-runtime/package/publication gate. Do not leave all useful progress only in ephemeral state while waiting.

### 23. Heavyweight gates compete for the same constrained runner/cache
Do not overlap Gradle/Minecraft/native-client/build jobs that contend for the same CPU/RAM/cache merely to appear parallel. Overlap a heavyweight gate with non-heavy independent work instead.

### 24. Slow low-priority sibling blocks a gateway
Be barrier-aware. If the runtime waits for every sibling in a wave, do not put a slow optional/low-priority call beside a fast gateway whose result unlocks a long downstream chain. Split the wave to minimize end-to-end makespan.

### 25. Truncation causes a restart
Treat truncation as partial success. Consume returned cursors/resources/ranges and continue from the boundary. Do not restart the same expensive extraction/search just to obtain a prettier complete response.

### 26. Resolved user information is asked again
Do not ask for facts already available in current conversation state, connected data, tool results, standing project rules, or safe defaults. Ask only for genuinely blocking user-only decisions/actions.

### 27. Wrong target or stale artifact causes rework
Resolve canonical repo/worktree/branch/file/build identity once, preserve it in the capsule, and prove the runtime loaded the new artifact. A familiar filename or newer timestamp alone is not enough.

### 28. Missing tooling becomes either a terminal blocker or an install loop
Recover missing required tooling when a realistic supported route exists, but do it once on the critical path. Reuse the recovered environment state; do not repeatedly reinstall/re-probe the same toolchain.

### 29. Narration substitutes for progress
Progress text is not a mutation, evidence gain, dependency advance, or verification result. If two waves only narrate/restate, the next wave must change strategy and produce a real state transition.

### 30. Status/handoff/catalog files are rewritten on every micro-edit
Checkpoint meaningful coherent state, not every keystroke. Write concise deltas after useful implementation/build progress. Reuse the current project identity instead of rehydrating every governance artifact on each turn.

### 31. Broad research restarts instead of advancing the frontier
Keep a coverage ledger. Search unresolved gaps, stronger primary sources, or the top candidate deeply. Do not restart the same ecosystem sweep because the task resumed or another skill returned.

### 32. Compaction/resume loses the exact next action
Before compaction, long waits, or handoff, persist the compact continuity capsule and exact next action. On resume, restore from that watermark and search only deltas/newer candidates before continuing.

### 33. One slow operation holds the whole workflow hostage
Give slow remote/process waits finite interactive leases. Lease expiry preserves the exact run/job/PID/session identity, checkpoints coherent progress, and releases unrelated acceptance work instead of blocking the whole project.

### 34. Wall-clock grows without a progress signature
Long work is healthy only when meaningful milestones/evidence/state keep changing. Two consecutive waves with no new evidence, mutation, checkpoint, acceptance, or materially changed blocker force a strategy change.

### 35. Known action is delayed by more reading/explaining
When canonical target + root cause + safe edit are known, apply the known-action mandate. Within the next wave mutate, targeted-test, checkpoint, or identify the exact blocker preventing mutation.

### 36. Risky boundary has no recovery capsule
Before compaction, handoff, long blocking wait, or interruption-prone gate, preserve acceptance/completion state, canonical IDs/hashes, run IDs, latest mutation/test/checkpoint, blocker, no-repeat history, and exact next action.

### 37. Expired wait lease keeps getting polled
When the orchestration lease expires, stop unchanged observation. Preserve identity, advance independent work, and resume only after a real invalidator or meaningful milestone window.

### 38. Recovered stall is not fingerprinted
Capture the active skill stack/owner, operation/target, elapsed interval, repeated actions, blocker, recovery that worked, and causal lesson. Promote only proven recurring/generalizable causes.

### 39. Anti-stall enforcement relies only on global/user memory
Memory can be missing, stale, or not loaded. Zero Loss itself remains the enforceable source of truth; persistent memory/custom instructions are redundant reinforcement only.

### 40. Watchdog becomes its own ceremony
Apply watchdog behavior silently. Run the deterministic watchdog script only for long/interruption-prone/already-stalled work where it materially reduces risk; never add per-wave bookkeeping just to prove the watchdog exists.

## Evolution protocol

Zero Loss should improve from proven incidents without turning one odd failure into a universal rule.

1. Apply the immediate recovery to the active task.
2. Record a candidate only when there is an explicit user correction, objective reproduction, repeated independent incident, or authoritative specification plus observed behavior.
3. Generalize away project names/paths while preserving the causal trigger, forbidden loop, required replacement, and verification.
4. Check for duplicate/contradictory rules before adding anything.
5. During a Zero Loss skill update, add/promote the rule in `stall-patterns.json`, update this Markdown only if the human control plane changes, extend a regression test/auditor when machine detection is realistic, run the full Zero Loss self-test, then repackage the complete skill.
6. Outside a skill-update working copy, never pretend the installed skill silently rewrote itself. Preserve the candidate in a durable external ledger/checkpoint if persistence is required and carry it into the next skill update.

The objective is a monotonic anti-stall system: every verified lesson should reduce a known class of wasted motion without reducing scope, quality, safety, QA, or required persistence.
