# Runtime Stall Watchdog

Use this reference only for long, multi-step, interruption-prone, connector-heavy, CI/native-runtime, or already-stalled work. The watchdog is an execution governor, not another workflow owner.

## Purpose

Detect **lack of progress**, not merely elapsed time. A long compile/render/upload that emits meaningful milestones can be healthy; repeated unchanged observations, narration, rediscovery, or blocked orchestration are not.

## Four runtime signals

Track a compact progress signature:

1. latest new evidence or newly resolved uncertainty;
2. latest coherent mutation/deliverable change;
3. latest durable checkpoint or newly satisfied acceptance item;
4. current blocker plus the exact next action.

A wave is progressive if at least one of 1-3 changes or if a blocker is materially narrowed/invalidated. Merely restating status, repeating the same read/search, or observing an unchanged remote state does not count.

## Dead-man rule

After **two consecutive no-progress waves**, classify the current route as stalled. The very next wave must change strategy and produce one of:

- a coherent mutation;
- a targeted test/verification result;
- a durable checkpoint/recovery capsule;
- a stronger evidence route that resolves a named correctness blocker;
- a truthful external blocker with the exact preserved recovery identity.

Do not spend a third wave narrating, rediscovering, or polling the same state.

## Known-action mandate

Once canonical target + root cause + safe coherent edit are known, the task is forbidden from spending two additional waves only reading/explaining. Mutate, targeted-test, checkpoint, or name the exact blocker that prevents mutation.

## Wait leases / no-hostage rule

Every slow remote/process wait gets a finite **interactive lease**. The lease limits how long orchestration may be held hostage; it does not kill a healthy underlying CI/build/native job.

Default advisory leases when no provider-specific contract exists:

- connector/API/network request: 60 seconds;
- local subprocess expected to be interactive: 120 seconds;
- detached CI/build/native-runtime observation window: 120 seconds;
- user-auth/permission wait: do not poll; preserve state and surface the exact user action.

On lease expiry:

1. preserve exact run/job/PID/upload/session identity;
2. checkpoint coherent progress first when possible;
3. stop unchanged observation;
4. advance all independent acceptance work;
5. use a different evidence route or resume observation only after a real invalidator/milestone window.

Provider-required longer timeouts may be used, but they must not justify repeated blocking waits in the reasoning loop.

## Escalation ladder

Use this order instead of blind retries:

1. normal route;
2. same target with materially improved payload/batching/pressure;
3. alternate authoritative evidence/transport route;
4. preserve state + checkpoint + advance independent work;
5. recover/reconnect/relaunch using exact preserved identity;
6. truthful external blocker with one precise remaining action.

Never use `retry -> retry -> retry` as a strategy.

## Recovery capsule

Before compaction, handoff, long wait, risky tool transition, or closeout with an external blocker, preserve:

- acceptance items and completed items;
- canonical repo/file/Drive IDs and paths;
- loaded evidence/source versions/hashes;
- run/job/PID/session IDs;
- latest coherent mutation, test, and checkpoint;
- current blocker;
- no-repeat list (routes/queries/actions already disproven or completed);
- exact next action.

A continuation must restore this capsule and start from the exact next action. Skill activation or resume is not permission to rediscover settled state.

## Stall fingerprint

For a recovered stall, capture enough to learn from it:

- active skill stack and workflow owner;
- operation family/target;
- elapsed interval and progress signature before/after;
- repeated/duplicate actions;
- blocker and preserved identity;
- recovery strategy that produced progress;
- exact causal lesson.

Feed proven recurring fingerprints to the embedded Stall Brain evolution path. Do not universalize one-off backend slowness.

## Script

When code execution is available and the workflow is long enough to justify bookkeeping, use `scripts/watchdog.py` with one state file. The script is optional for short tasks; the behavioral contract above is always applicable.
