# Mandatory Google Drive Persistence

Use this reference whenever a run creates or modifies a material file/artifact, changes durable project state, resumes a Drive-backed artifact, or is long enough that losing the current chat would lose meaningful progress.

## Non-negotiable rule

Google Drive is a required durable remote whenever an authorized Drive connector/API path is available. Do not treat Drive publication as an optional delivery preference or wait until the end of a long run to begin persistence.

A material save includes:

- any user-visible file or reusable artifact created or modified for the task;
- documents, spreadsheets, slides, PDFs, images when saved as files, archives, builds, installers, exports, generated datasets, prompts/specifications saved as files, manifests, and recovery bundles;
- project-brain/checkpoint exports that preserve an idea, requirement, decision, blocker, next action, research conclusion, version/artifact change, schedule change, or exact repository state needed for another chat to continue.

Ordinary transient reasoning, disposable scratch files, caches, build intermediates, and every individual repository source file do not need separate Drive copies. For repository work, preserve source in the canonical repository and publish a Drive checkpoint/export that records the exact repository, branch, commit, dirty state, verified artifact/build, and next action. Upload any distributable artifact produced by the run.

## Start/resume workflow

1. Resolve the project/artifact from the current request, Project Constellation/ProjectDump state, project memory, or direct Drive identity. Never hardcode a repository inventory or Drive folder ID into universal skill rules.
2. If the continuing artifact has a known canonical Drive file ID or exact Drive location, read that current object before editing and compare it with repository/project-memory evidence. User edits and newer verified content win.
3. Avoid broad Drive scans when the exact object is already known. Search only when identity, lineage, or latest-good state is unresolved.
4. Prefer the existing project Drive folder and existing canonical same-artifact file.

## Checkpoint cadence

Persist to Drive in the same run:

- after each meaningful implementation or research milestone in long/multi-step work;
- after a material idea/requirement/decision/blocker/next-action change that affects continuity;
- after producing a coherent build/package/export;
- before context compaction, handoff, interruption-prone transitions, or closeout;
- once before closeout for a short single-step task that produced a material file.

Do not upload after every micro-edit. The invariant is continuous meaningful checkpointing, not connector spam.

## Update versus create

- When a canonical Drive file exists and the connector supports replacement/update, update that file in place so its stable file ID remains the canonical identity.
- For native Docs/Sheets/Slides, use the dedicated native edit/update action instead of replacing them with raw bytes when supported.
- When an in-place update is not supported, create an explicit versioned object, preserve the prior object, and record lineage/supersession.
- Never create unexplained same-name duplicates.

## Required verification

After each required Drive publication:

1. Record the local/intended artifact identity, size, and SHA-256 when raw bytes exist.
2. Record the returned Drive file ID and observed location/link.
3. Read back remote metadata.
4. Compare exact size and provider digest when available.
5. If no trustworthy digest is exposed and byte identity matters, reread/redownload the complete remote object and compare SHA-256.
6. Record verification time and result in the project/artifact ledger when applicable.

An upload acknowledgement alone is not verification. Do not claim Drive synchronization when the remote object was not checked.

## Project state and ProjectDump

For named project work, keep the layers complementary:

- project repository: canonical source and project-owned `.agents-memory/`;
- ProjectDump/Project Constellation: cross-project catalog, recovery, relationships, handoffs, publication receipts, and discovery;
- Google Drive: mandatory durable copy of material user artifacts and project-brain/checkpoint exports;
- ChatGPT Library/sandbox/memory: convenience only.

After a meaningful checkpoint, update the project-owned state and Project Constellation/ProjectDump as applicable, then publish the resulting changed checkpoint/export to Drive and record the verified Drive identity. GitHub/ProjectDump synchronization does not satisfy the Drive requirement by itself.

## Failure recovery

If Drive publication fails:

1. Retry transient connector/provider failures with backoff.
2. Re-resolve the target folder/file ID and permissions.
3. Recover/reconnect the supported Drive integration when available.
4. For size limits, prepare verified multipart or resumable uploads instead of repeatedly retrying the same oversized transfer.
5. Preserve local bytes, checksums, manifests, and pending publication state until remote verification succeeds.
6. If Drive remains genuinely unavailable after realistic supported recovery paths, return the complete local artifact and exact blocker, but state clearly that Drive durability is still outstanding.

Never silently downgrade to ChatGPT Library as the durable substitute.

## Closeout gate

Before closing any run that created or modified material saved output, verify all applicable statements:

- every material user file/artifact has a Drive copy or verified in-place Drive update;
- every meaningful project-state change has a Drive-backed checkpoint/export;
- long work was checkpointed during the run rather than only at the end;
- repository work records the exact repository/branch/commit in the Drive-backed project checkpoint;
- generated builds/packages are present on Drive;
- remote IDs, sizes/digests, and verification evidence were recorded when available;
- ProjectDump/GitHub and other required destinations were also updated when applicable;
- no completion claim relies only on sandbox, Library, or conversational memory.

If any applicable item is missing and Drive is available, continue working.
