# Connector + Project Fast Path

## Contents

- Canonical restore boundary
- Tree/diff/snapshot first
- Source fan-in
- Restricted runner networking
- Read/audit/mutation barrier
- CI observation
- Persistence fast path
- Port example

Use this reference for GitHub/Drive/project continuation, code ports, CI-heavy tasks, or environments with restricted outbound networking.

## Canonical restore boundary

Perform mandatory canonical restores once, and do independent canonical sources in the same wave when tooling allows. Retain a compact state tuple:

`repo, branch, head_sha/tree_sha, drive_project_folder_id, checkpoint_id/version, relevant workflow/run IDs`

Do not re-search the same canonical state until an invalidator occurs:

- external change is explicitly reported or materially plausible;
- user gives a newer source/checkpoint;
- this run changes the repository/Drive state;
- freshness requirement explicitly demands revalidation.

For self-authored GitHub changes, returned commit/tree SHA becomes the cached HEAD. For Drive writes, returned file ID/revision/version becomes the cached Drive state. Do not run broad continuity searches merely to learn identifiers the mutation already returned.

## Tree/diff/snapshot first

Before fetching many bodies, check whether the provider can return an authoritative tree, manifest, compare/diff, release file list, revision map, or content-addressed archive.

Use it to build the read set:

1. identify changed paths by hash/revision/compare data;
2. fetch all changed files plus any cross-file dependencies needed for semantic validation;
3. trust unchanged status only when backed by authoritative version/hash evidence;
4. for very many files, prefer one practical repository snapshot/archive materialization over hundreds of scalar reads when supported.

This is especially valuable for ports and upgrades where most scaffold files are already correct.

## Source fan-in

When comparison still needs many files:

- collect the complete path set first;
- use batch read/fetch endpoints when available;
- otherwise invoke independent reads in the broadest safe **critical-path-aware** wave; in a barriered runtime, do not let a very slow unrelated read delay a fast gateway read whose result unlocks a longer downstream chain;
- keep sequential reads only for dependency-driven discovery (for example file B path is learned from file A);
- use targeted follow-up reads for ambiguous regions instead of rereading every file.

Audit after fan-in. Patch only confirmed deltas instead of repeatedly alternating read/edit/read/edit.

## Restricted code-runner networking

A deterministic error such as DNS resolution failure, network unreachable, or documented no-outbound access is a capability result, not a reason to retry blindly.

After one conclusive failure:

1. mark the route unavailable for the current environment;
2. switch to GitHub/Drive/native connector reads;
3. use the local runner only for computation/building against already-materialized content;
4. retry outbound access only if the environment changes or evidence indicates transience.

## Discovery-to-mutation circuit breaker

Once `repo/Drive identity + requested delta + enough source context to edit safely` are known, freeze that restore state and cross into implementation. One additional read-only wave is allowed only for a named correctness blocker. Two same-family searches that do not change the canonical tuple are sufficient evidence to stop rediscovery; switch to direct ID fetch/list, local materialized bytes, or the best authoritative state already held.

A progress update does not satisfy this boundary. Count only a concrete source/artifact mutation, changed-path validation, or durable implementation checkpoint as implementation progress. When a user reports a stall, do not reopen broad history/version discovery; checkpoint recovered inputs and make the smallest coherent advancing change first.

## Read/audit/mutation barrier

Prefer this sequence:

`restore -> tree/diff -> fan-in -> local/in-memory audit -> complete patch -> local preflight -> one atomic/coherent mutation -> CI`

Before remote mutation, use base SHA/revision/write-control tokens when supported. This catches concurrent edits without a full continuity resweep.

Benefits without quality loss:

- fewer connector round trips;
- fewer intermediate broken remote states;
- fewer CI runs;
- one coherent review state;
- easier rollback;
- precise conflict detection.

Do not force one commit when independent commits are a correctness/review requirement.

## Exact-head evidence discipline

For expensive acceptance, conversion, or repair CI, keep one authoritative evidence head at a time.

- Capture `branch + exact head SHA + run ID + job ID + current acceptance boundary` when the run starts.
- Freeze that exact head until the run is decisive. Do not contaminate an evidence run with unrelated polish/tooling commits.
- If a connector sequence exposes an incomplete intermediate commit, label it non-authoritative immediately; reconcile to one coherent head and trust only the replacement run.
- A later commit invalidates only evidence that depends on changed state. Preserve independent proofs (for example a separately sealed foundation runtime) unless the new change can affect them.

Use a causal advancement ladder:

`already-proven gates -> earliest new failure -> owning layer -> narrow repair -> replacement exact-head run`

Do not restart from project-wide uncertainty after every failure.

## Artifact/runtime visibility split

When a downstream dev run reports a missing class, resource, mixin service, or dependency from an upstream local JAR, do not assume the release is malformed.

1. Inspect the exact upstream artifact recursively, including nested JAR-in-JAR entries.
2. Prove whether the missing class/resource exists in the packaged runtime.
3. Compare real loader behavior with the dev toolchain's local-file dependency/classpath behavior.
4. If the release is correct but the dev harness cannot expand nested metadata, restore only the missing development-runtime visibility; do not duplicate or weaken the packaged dependency contract.
5. Add a cheap gate that checks both package reachability and downstream dev-runtime reachability when this seam is reusable.

This distinction prevents correct releases from being "repaired" into incorrect or duplicated packages merely because Loom/Gradle local-file dependencies lost transitive/nested runtime metadata.

## Proof-tail overlap and stall recovery

Treat post-proof closeout as a separate lane once implementation behavior is already proven. A common stall pattern is: native behavior gate passes -> package -> fresh extraction -> rebuild -> second native smoke -> publication -> round-trip, all serially, while the next independent batch waits. That preserves quality but wastes the critical path.

Split the work instead:

- **Release lane:** freeze the exact proven source/artifact/hash. Complete packaging, fresh-extraction/install proof, redundant smoke required by the acceptance contract, publication, and byte/digest verification without mutating the frozen lineage.
- **Next-batch lane:** branch/copy from that proven source and immediately perform bounded source fan-in, implementation, and targeted preflight for the next independent coherent batch. Do not consume or modify the release lane's evidence files.
- **Promotion barrier:** do not call the release fully promoted until its required tail gates pass. If a tail gate fails, invalidate only the state it can causally invalidate; do not erase independent next-batch research or implementation by default. Rebase/reconcile only when the failure changes a source or dependency the next batch actually inherited.
- **No duplicate proof monopoly:** a second full native run from a fresh package may still be mandatory, but it must not become the sole active workstream after an equivalent frozen source has already passed the behavior gate.
- **Resource-contention guard:** overlap logical lanes, not blindly heavyweight processes. If two Minecraft/Gradle/native gates share a constrained JVM host, Gradle cache, memory budget, display, port range, or other scarce runtime resource, serialize those heavy gates and overlap each with non-heavy source/audit/packaging/persistence work. A daemon/process killed under contention is scheduling evidence, not an implementation regression.

This is a scheduling rule, not a QA reduction. Every required closeout test still runs; the fix is overlapping independent work and preserving exact-lineage isolation.

## Waiting-window work

After the authoritative run ID is known, do not spend the entire wait path polling. Safe independent work includes:

- inspect already-produced evidence/artifacts;
- update durable checkpoint/repair-brain records with proven state;
- build/test generic QA helpers locally without mutating the frozen evidence head;
- preflight the next dependency or conversion lane;
- prepare the next narrow patch hypothesis, but do not commit it until current evidence justifies it.

Prefer this over repeated run-list reads. The next CI observation should normally occur after useful work or a meaningful expected transition.

## CI observation

CI is a state machine, not a busy-wait loop.

Default pattern:

1. confirm run creation and capture exact run/check ID;
2. continue independent analysis, docs, packaging, or persistence preparation;
3. query that known run ID after useful work or a meaningful expected transition;
4. on failure, fetch failing job/logs first;
5. make one coherent corrective implementation commit if needed, which legitimately creates a new run;
6. verify final required state.

Avoid broad workflow-list rediscovery after a run ID is known. Avoid fixed rapid polling. Never re-run Drive/GitHub continuity discovery just to see whether the known CI run changed.

## Persistence fast path

Persistence remains mandatory whenever the governing workflow/user requires it.

For each required checkpoint/final delivery:

- batch compatible files in one destination mutation when supported;
- reuse known destination folder/file IDs;
- compute local hashes once and reuse them for verification/reporting;
- use authoritative write response metadata when sufficient;
- if round-trip verification is explicitly required, perform it, but do not rediscover the folder or file by name first when the returned ID is already known.

## Example: Ranged Weapon API-style port

Slow pattern:

`continuity -> file A -> edit A -> CI -> poll xN -> file B -> edit B -> CI -> poll xN -> continuity again -> ...`

Fast zero-loss pattern:

`Drive+GitHub restore wave -> tree/compare -> source fan-in -> audit existing scaffold -> patch missing deltas -> local preflight -> one coherent commit -> one active CI run -> useful parallel work -> failing-log-only diagnosis if needed -> milestone/final CI check -> batched verified persistence`

## Known-fix stop barrier

A newly identified root cause is not progress until it crosses into state change. Once the owning cause and a narrow safe patch are known, do not end a turn, update, or execution slice at language such as "preparing the fix", "next I will patch", or "about to rerun" when no user-only or external blocker exists.

Required crossing before stopping:

`known root cause -> coherent mutation -> targeted validation -> durable checkpoint OR replacement exact-lineage run launch`

If a tool/session limit threatens interruption, prioritize applying and persisting the patch over more narration, research, packaging, or unrelated scouting. Preserve the failed evidence, patch only the causal owner, and leave an exact restartable command/receipt. A status message is not a substitute for the crossing. If the live worktree is at risk of disappearance, restore from the newest byte-verified checkpoint first, then mutate immediately.
