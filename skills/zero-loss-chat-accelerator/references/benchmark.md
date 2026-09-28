# Zero-Loss Benchmark Protocol

## Contents

- Goal and measures
- A/B method and pass criteria
- Trace annotations
- Priority scenarios
- Report format

Use only when the user asks to test, benchmark, validate, or tune the accelerator.

## Goal

Verify lower avoidable orchestration critical path while holding acceptance scope, correctness, validation, citations, persistence, and result breadth constant.

## Measure

When observable compare:

- total tool events / serial round trips;
- fully observed trace span when every event has start/end timing;
- dependency-only critical-path estimate, emitted barrier-wave makespan, and exact optimized barrier schedule for timed plans up to 16 tasks;
- duplicate/equivalent and overlapping single-flight calls;
- repeated schema discovery;
- repeated continuity sweeps while canonical state is unchanged;
- serial independent source reads;
- body reads that could be replaced by authoritative tree/diff/snapshot evidence;
- fragmented repository writes that could be atomic;
- broad CI rediscovery after an exact run ID is known;
- CI poll count and rapid unchanged polls;
- retries through a route already proven unavailable;
- rate-limit hammering / unchanged pressure after 429;
- repeated full-resource reads;
- repeated expensive validation cycles before a coherent edit boundary;
- mandatory verification completion;
- acceptance-criteria completion;
- maximum-effort quality invariants such as full scope/breadth, no artificial caps, and challenge-pass completion when annotated.

Prefer fully timed observed wall-clock span over heuristic flag counts when available. Partial timing is diagnostic only and must not be treated as ground truth. Do not claim precise server/network latency gains unless externally measured.

## A/B method

### Baseline

Use a real prior trace when available. Otherwise create a structural baseline; do not intentionally waste live user time running a bad workflow.

### Accelerated

Use the same acceptance contract and source coverage. Change only orchestration.

### Pass criteria

Pass only if:

1. acceptance and requested outputs are unchanged;
2. maximum-effort quality invariants are unchanged;
3. mandatory tool/skill/QA/citation/persistence steps remain;
4. breadth and quantity are unchanged;
5. fully observed wall-clock span does not regress when comparable timing is available, and avoidable critical path, serial calls, duplicate work, fragmented writes, poll storms, dead-route retries, or backpressure mistakes decrease;
6. no unsupported latency claim is made.

Call it neutral if governing constraints make the critical path irreducible.

## Trace annotations

`audit_trace.py` accepts normal call fields plus optional annotations that make the diagnosis more accurate:

- `id`, `tool`, `op`, `target`, `fingerprint`, `status`;
- `depends_on`, `start_ms`, `end_ms`;
- `category`, `repo`, `branch`, `run_id`, `route`;
- `version`, `revision`, `sha`, `etag`, `head_sha`, `state_version`;
- `satisfies`: acceptance requirement IDs satisfied by the event;
- `quality_satisfies`: quality-invariant IDs such as `maximum_effort`, `full_scope`, `full_breadth`, `no_artificial_caps`, `challenge_pass`;
- `intentional_boundary`: true for deliberately separate repo writes;
- `invalidator`: reason a repeated continuity/read operation became necessary;
- `http_status`, `retry_after_ms`, `error`, `message`.

Use `compare_traces.py` for structural A/B comparison. Acceptance parity is only automatically testable when `satisfies` tags are present, and quality parity only when `quality_satisfies` tags or `--require-quality` guards are present; otherwise report the corresponding dimension as manual review. Run `scripts/self_test.py` before packaging or after modifying the accelerator itself.

## Priority scenarios

Choose the scenarios relevant to the complaint; do not inflate testing with unrelated cases.

### Connector/project + CI

Expected optimized behavior:

- one continuity restore per unchanged state;
- Drive/GitHub restore in the same independent wave when possible;
- tree/diff/snapshot before many body reads when authoritative;
- batch/parallel source fan-in;
- known no-outbound route cached after conclusive failure;
- one atomic/coherent implementation commit where supported;
- one active CI run for that state;
- exact run-ID observation rather than broad CI rediscovery;
- milestone/final polling rather than tight repeated checks;
- batch checkpoint persistence using known destination IDs.

### Web research

Diverse queries batched early; deduplicate sources; only evidence-driven follow-ups; no duplicate broad searches.

### File/artifact

Semantic/targeted reads first; materialize only when bytes needed; coalesce edits before expensive mandatory render/test cycles; mandatory render/test/QA preserved.

### Failure recovery

Classify the failure; change route/pressure/payload once; preserve partial work; continue unrelated work.

## Report

Keep compact:

- **Quality parity**: pass/fail/manual-review, including maximum-effort/no-cap invariants when annotated.
- **Coverage parity**: pass/fail/manual-review.
- **Mandatory verification**: pass/fail.
- **Observed wall-clock span**: before -> after when timing coverage is complete.
- **Critical path / barrier makespan**: before -> after when declared dependencies/timings are available.
- **Continuity reuse**: before -> after.
- **Source acquisition**: body-by-body -> tree/diff + fan-in where applicable.
- **Repository writes**: fragmented -> atomic/coherent.
- **CI observation**: broad/polling -> exact-ID milestones.
- **Dead-route retries**: before -> after.
- **Rate-limit hammering**: before -> after.
- **Avoidable round trips removed**: exact or conservative estimate.
- **Remaining latency**: external/backend vs orchestration.
- **Verdict**: pass / neutral / needs tuning.
