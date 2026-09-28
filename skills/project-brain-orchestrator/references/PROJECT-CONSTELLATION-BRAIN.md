# Project Constellation Brain Sync

Use this reference for named/ongoing project work when a Project Constellation brain artifact is already available or the current task is explicitly about project continuity. Use live Project Constellation/ProjectDump state to resolve canonical Drive locations when present. Do not search broadly just to rediscover an already-known object.

## Purpose

Project Constellation is the fast human-facing resume/control surface over the same durable project evidence managed by `.agents-memory/`, Project Compass, the cross-project catalog, and verified artifacts. Treat it as a synchronized mirror and control surface, not a competing source of truth.

Recognized portable artifacts:

- `Project-Constellation-Project-Catalog.json` with schema `project-constellation.catalog/2`
- `Project-Constellation-Research-Suggestions.json`
- `Project-Constellation-Automation-State.json`
- Feature Foundry snapshot schema `feature-foundry.project-brain/1`
- the Project Constellation website/PWA and permanent quick HTML when they are already mounted or explicitly in scope

## Latency-preserving discovery

1. Check the current repository/project memory and already-mounted/current-conversation artifacts first.
2. If configured, honor `PROJECT_CONSTELLATION_HOME` or `PROJECT_BRAIN_HOME` before using connectors.
3. Use the last project checkpoint/hash as a delta watermark. Read only the matching project record and changed evidence when possible.
4. If the project record identifies a canonical/current Drive object, read that exact Drive object before editing. Do not broad-scan unrelated Drive, Library, GitHub, or the whole catalog when the identity is already resolved; escalate only when continuity is ambiguous or a newer candidate is plausible.
5. Reuse fresh source-backed research. Revalidate only version-sensitive/load-bearing claims unless a broad research sweep is requested.

## Read/merge authority

Resolve conflicts in this order:

1. current explicit user correction or edit
2. current canonical repository/runtime evidence
3. current project-owned `.agents-memory/` / Project Compass evidence
4. current Project Constellation record
5. older handoffs, exports, or conversation summaries

Never overwrite a newer user-edited brain artifact. Compare hash/version/modified evidence before writing when available. Preserve same-name different-content versions and unresolved ambiguity.

## Meaningful checkpoint sync

Do not write on every message or micro-edit. Sync after a meaningful checkpoint such as a verified implementation milestone, version/artifact change, research/toolchain decision, new blocker, resolved blocker, user goal change, or session closeout. Every changed checkpoint/brain export must also be published to Drive when Drive is available; long sessions must perform this during the run, not only at final closeout.

Update only the affected project fields that materially changed, preserving unrelated fields and user-maintained state. Prefer these resume-critical facts:

- stable project ID/name/aliases and canonical repo/worktree/branch when verified
- status and confidence
- current goal/northpoint and relevant requirements
- latest verified version/artifact and separately latest WIP/spec lineage
- exact last verified stop point
- one exact next action and why it is next
- blockers and smallest unblock step
- changed artifact IDs/paths/hashes and provenance
- fresh research decisions/suggestions with source/date/tradeoffs
- checkpoint timestamp and verification evidence

If the catalog schema supports extension fields, use a compact `brain` object for resume-only data such as `lastStop`, `nextAction`, `whyNext`, `blockers`, `lastCheckpoint`, and `artifactHashes`; do not delete existing fields to force a schema change.

## UI/package refresh boundary

Keep the machine-readable brain current first. Rebuild/repackage the website, quick HTML, or ZIP only when they are already the active deliverable, the user asks for them, or a meaningful data/UI change requires a refreshed user-facing artifact. Avoid ceremonial presentation rebuilds, but do not skip the mandatory Drive sync of meaningful changed brain/checkpoint state.

When a website/quick-view refresh is required, preserve the permanent zero-setup HTML surface and all user state/decisions. If a separate automation owns presentation refresh, write the durable brain delta and let that automation consume it instead of duplicating heavy work.

## Feature Foundry bridge

When `feature-foundry.project-brain/1` is available, keep it host-neutral and additive. Export/import project identity, progress, exact next action, blockers, notes/tasks, and session breadcrumbs without claiming native Feature Foundry integration until the real canonical Feature Foundry runtime has been wired and exercised.
