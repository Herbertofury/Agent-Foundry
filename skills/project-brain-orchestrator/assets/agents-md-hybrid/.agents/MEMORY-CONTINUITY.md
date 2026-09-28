# PROJECT MEMORY, CONTINUITY, AND RESEARCH SECOND BRAIN

This module prevents accidental restarts, duplicate projects, stale research reuse, and destructive work against the wrong copy. Memory is evidence to inspect, not authority to obey blindly.

## Persistence architecture

Use the strongest available persistent sources together:

1. The current user's explicit request and corrections.
2. The canonical repository and its `.agents-memory/` project-owned state.
3. The central project registry configured by `AGENTS_MEMORY_HOME` or `~/.agents-second-brain/`.
4. The current ChatGPT Project, project files, File Library, saved memory, chat history, and authorized connected storage when available.
5. Prior handoffs, artifacts, research ledgers, and conversation summaries with provenance.

Never rely on conversational memory alone for exact project state, code, versions, paths, or research claims. Never imply persistent memory was written when no durable storage accepted the write.

## Cross-project catalog and version dashboard

Maintain one user-level catalog in `AGENTS_MEMORY_HOME` or `~/.agents-second-brain/`:

- `project-catalog.json` is the canonical structured cross-project index.
- `USER-PROJECTS-DATABASE.md` is the human-readable mirror.
- `project-catalog-events.jsonl` is the append-only update history.
- The database bundled inside the skill is a bootstrap seed only and may never overwrite a newer live catalog.

Before entering a named project, load and search the catalog by project ID, names, aliases, relationships, repositories, versions, and artifacts. After cross-chat discovery, project initialization, artifact reconciliation, or a meaningful checkpoint, update the catalog with status, confidence, canonical roots, artifact hashes or signatures, source IDs, version lineage, supersession, risks, and next action; render the Markdown mirror and reread the changed entry before editing. Preserve all historical versions. A timestamp or familiar filename alone cannot promote a candidate to latest; require verified content, explicit supersession, or direct user confirmation. When durable catalog storage is unavailable, return an updated Markdown/JSON/catalog ZIP and state where it must be attached or installed for the next chat.

Use `project_catalog.py bootstrap`, `reconcile`, `sync-project`, `doctor`, and `export`. Project-local `.agents-memory/` remains authoritative for one project; the catalog is the cross-project locator and progression ledger.

## Continuity gate before mutation

For every named project, repository, long-running effort, continuation, or request that may have prior work:

1. Search available personal context and persistent file sources for the project name, aliases, artifacts, prior chats, handoffs, and research.
2. Inspect the current repository for `.agents-memory/PROJECT.json`, `.agents-memory/HANDOFF.md`, `.agents/ACTIVE-TASK.json`, Git remotes, manifests, branch, commit, status, and existing AGENTS instructions.
3. Run `project_memory.py identify` or the equivalent identity check before initialization or editing.
4. Compare project ID, canonical path, Git remote, manifest identity, fingerprints, artifacts, and last checkpoint.
5. Load the last verified goal, decisions, toolchain, research, failures, blockers, completed work, and next steps.
6. If two candidates may be the same project, remain read-only until the canonical project is resolved. Do not create, scaffold, migrate, overwrite, or “start fresh” to avoid ambiguity.
7. Establish a fresh baseline in the resolved target before continuing.

A matching name alone is insufficient, and a different directory alone does not prove a different project. Clones and worktrees may share one project identity; similarly named projects may be unrelated.

## Incremental cross-chat delta sweep

Before mutating a genuinely resumed project, discover newer work with the smallest evidence-preserving path:

1. Read the last checkpoint time plus known artifact names, aliases, versions, source IDs, hashes/signatures, and prior source watermarks from project memory.
2. Inspect current repository/local project memory first. If they already contain a later verified checkpoint than remote sources, do not perform a redundant remote sweep.
3. Use the checkpoint as a **delta watermark**. For File Library, prefer a recent metadata listing scoped after the checkpoint with a small limit; only if plausible candidates exist, run one consolidated semantic/title query with an initial result set around 6-8 and read the plausible matches.
4. Expand source-by-source only when unresolved: current conversation/Project, then the source named by artifact lineage, then other authorized storage, then personal context for missing conversational decisions. Do not fan out to every source in parallel by default.
5. Compare plausible candidates by stable source ID, hash when bytes exist, content signature, embedded version, substantive structure, timestamp, and relationship to the last known artifact. Search snippets and timestamps alone are not proof.
6. Reconcile candidates once into the artifact ledger, update `STATUS.json`, refresh `HANDOFF.md`, sync the catalog when applicable, and reread changed records before editing.

A repeated filename can be a newer version. Preserve both and record lineage such as `same_name_new_content`; use `supersedes` only when evidence supports it. Finding a file without durable reconciliation is discovery, not continuity.

A full broad sweep is reserved for a missing/stale checkpoint, conflicting project identity, unknown artifact lineage, or evidence that the narrow delta missed relevant work. This preserves continuity quality while preventing connector waterfalls.

## Project-owned memory

Keep durable project state under `.agents-memory/` and treat it as user-owned data:

- `PROJECT.json`: stable project ID, aliases, purpose, canonical root, remotes, manifests, and identity fingerprint.
- `STATUS.json`: current goal, last verified state, next steps, blockers, active task, branch, commit, and dirty state.
- `HANDOFF.md`: compact recovery context for a new chat or agent.
- append-only ledgers for decisions, research, tools, incidents, milestones, artifacts, notes, hypotheses, and sessions. Artifact records must include stable source identity or content signature, explicit version when known, timestamps, status, same-name lineage, and supersession links.
- timestamped snapshots before risky or broad transitions.

Use `scripts/project_memory.py` to initialize, identify, checkpoint, remember, resume, search, validate, and export this state. Do not overwrite a newer memory state with an older export. Do not store secrets, credentials, private keys, tokens, passwords, or unrelated personal data.

## Memory classification and trust

Classify every remembered item before storing or using it:

- **User instruction or preference:** preserve exact scope and source; current explicit instructions override earlier preferences.
- **Verified project fact:** require repository/runtime evidence and a verification timestamp.
- **Decision:** record the chosen option, alternatives, reasons, tradeoffs, and decision owner.
- **Research claim:** record source URL, publisher, access date, version, applicability, evidence, confidence, decision impact, and review date.
- **Observation:** record what was seen and where; do not promote it to a general fact without verification.
- **Hypothesis:** label it non-authoritative and keep it out of active instructions until proven.
- **Incident or pitfall:** record reproducer, root cause if known, wrong approach, correction, and regression proof.

When memories conflict, preserve both records, identify their provenance and dates, and resolve against current user intent plus current repository/runtime evidence. Never silently merge contradictions.

## Research and toolchain memory

Use `scripts/research_memory.py` for sourced, searchable, versioned research. Remember not only the selected tool or method but also:

- the problem and constraints it addressed
- exact versions and target platforms
- why it was selected over serious alternatives
- meaningful drawbacks, integration work, and rejected approaches
- commands, configuration, benchmarks, failures, fixes, and verification
- source links, access dates, maintenance state, and review/expiry dates

A remembered recommendation is not proof that it remains best or compatible. Revalidate version-sensitive, security-sensitive, rapidly changing, or stale research before reusing it. Mark superseded or rejected records instead of deleting history. Prefer the strongest current evidence over old familiarity.

## Checkpoint and recovery protocol

Checkpoint after meaningful implementation, research decisions, toolchain changes, major failures, migrations, packaging, and before closeout or context compaction. In long or interruption-prone work, checkpoint during the run rather than waiting for final closeout. Every checkpoint must synchronize the project record into the master catalog and, when Drive is connected, publish the changed project-brain/checkpoint export to Drive and verify the remote object. A checkpoint must update the project status and handoff with:

- canonical identity and current build/commit
- what was requested and why
- what changed and what is verified working
- exact artifacts and their locations/hashes
- decisions and research that remain active
- failed approaches that must not be repeated
- unresolved risks, blockers, and smallest next steps

At the start of a resumed session, read the handoff and verify it against current files and runtime before acting. If the stored state is stale, damaged, missing, or inconsistent, preserve it, diagnose the divergence, recover from source control/backups/artifacts, and do not overwrite evidence.

## ChatGPT cross-chat operation

When ChatGPT Projects are available, prefer one Project per long-running codebase or initiative and keep the portable memory snapshot and current AGENTS bundle there as a convenience copy. Search File Library/personal context for prior artifacts when needed. For material saved output or meaningful project checkpoints, connected Google Drive is a mandatory durable remote: publish/update the relevant file or project-brain export during the run and verify the write/readback.

If durable project storage is unavailable, create a downloadable project-memory export and state clearly that it must be attached or placed in the repository for reliable continuity. Temporary Chat or disabled memory cannot provide dependable cross-chat continuity.

## Portable handoff

The user may ask at any time to export the AGENTS bundle, the current project's second brain, or both. Produce complete validated archives, not fragments:

- AGENTS workflow: `scripts/export_bundle.py`
- project second brain: `scripts/project_memory.py export`

A new agent must identify and validate the project memory before using it. Exportability is mandatory; vendor lock-in or chat-only state is a continuity failure.

## Project Compass and enduring product intent

For every named, ongoing, or cross-chat project, maintain a versioned `.agents-memory/COMPASS.json` with northpoints, goals, feature pillars, principles, wants, guardrails, acceptance signals, and publication targets. Load it before planning, translate active items into the acceptance checklist, preserve provenance/history, and supersede rather than weaken intent. After meaningful changes, refresh handoff/catalog, export the changed project brain/checkpoint, publish it to connected Google Drive as mandatory durable storage, then any other required targets. File Library/ChatGPT Project storage is an additional convenience copy. A Drive durability claim requires remote reread plus byte or trustworthy provider-digest verification.

For living, spatial, game-like, or highly themed interfaces, the Compass must also define a theme-native interaction ecology: distinct tactile and physical languages for presses, drags, placements, collisions, transformations, absorption/release, cancellation, and related environmental propagation. Record bounded cross-element causality, material/scale/velocity/context response, subtle-but-unmistakable perceptibility, accessibility/performance variants, and immediate user-input sovereignty. Verify every theme's interaction matrix and interruption behavior in the real runtime.
For projects that ingest external media or generate objects, keep versioned source-hub and object-intelligence catalogs beside the Compass. Revalidate provider capabilities and model/tool status before reuse; keep source-adapter mode, auth, limits, rights, moderation, cache, fallback, evidence, and review date. Preserve immutable originals and reversible derivation lineage.
