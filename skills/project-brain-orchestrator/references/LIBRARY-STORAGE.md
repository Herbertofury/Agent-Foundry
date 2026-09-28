# ARTIFACT LIBRARY, STORAGE, AND CLEANUP

This module governs ChatGPT Library inventory, local artifact vaults, organized project folders, bundles, storage warnings, duplicate review, cleanup, quarantine, and deletion. The goal is to reduce storage chaos without losing canonical work, project history, or reusable dependencies.

## Storage sources and truth

Use the strongest available source for storage state:

1. ChatGPT Library's Storage view or a supported platform API/connector.
2. A recent user-provided screenshot or exact reported used/remaining values.
3. A locally computed artifact-vault size.
4. A configured plan profile only as a fallback that must be revalidated when limits may have changed.

Never invent current usage, remaining quota, or plan limits. Record source and timestamp. Warn when usage reaches 70%, 85%, and 95%, and treat unknown usage as unknown rather than healthy. A rolling upload-rate limit is different from persistent storage and must not be misreported as the same quota.

## Durable library catalog

Maintain an artifact catalog under `AGENTS_LIBRARY_HOME` or `<AGENTS_MEMORY_HOME>/library`:

- `library-catalog.json` — machine-readable source of truth
- `LIBRARY-DATABASE.md` — human-readable mirror
- `library-events.jsonl` — append-only changes
- `cleanup-plans/` — reviewed cleanup plans and evidence

Each item should record project ID, name, kind, version, source type, source ID, path, SHA-256 or content signature, size, status, canonical/protected flags, references, lineage, supersession, and observation date. Update and reread the catalog after cross-chat discovery, new exports, version changes, cleanup, or bundle generation.

## Organized folder contract

Use a stable vault layout instead of scattering downloads and generated bundles:

```text
00-Inbox/
10-Projects/<project-id-name>/
  00-Current/
  10-Versions/
  20-Research/
  30-Assets/
  40-Bundles/
  50-Memory/
  60-Prompts/
  70-Reports/
  90-Archive/
20-Shared/
30-Reference/
40-Exports/
80-Archive/
90-Quarantine/
cleanup-plans/
```

Keep the canonical current artifact distinct from older versions. Store complete portable bundles in the project's `40-Bundles/` folder with a manifest, version, checksums, handoff/readme, required AGENTS files, project memory, and required dependencies. Do not scatter one bundle's supporting files across unrelated locations.

## Duplicate and version classification

Inventory before cleanup. Classify every candidate as one of:

- current/canonical
- protected or referenced dependency
- distinct version or lineage member
- exact duplicate
- near duplicate requiring review
- reproducible generated output
- archive candidate
- unknown/orphaned

Rules:

- Matching filenames, timestamps, titles, or visible content do not prove duplication.
- Exact SHA-256 equality is required for automatic duplicate quarantine.
- Same filename plus different hash or signature is a distinct version until proven otherwise.
- Never auto-delete canonical, current, protected, referenced, latest-good, unresolved, or uniquely sourced artifacts.
- Preserve project brains, AGENTS bundles, catalogs, manifests, checksums, handoffs, and source files needed to reproduce builds.
- Near duplicates, compressed variants, edited copies, and generated outputs require lineage and dependency review before cleanup.

## Cleanup and deletion safety

Use `scripts/library_manager.py` for local vault organization and cleanup.

1. Inventory and hash first.
2. Generate a cleanup plan that names the kept copy, every candidate, reason, source, size, and estimated recovery.
3. Require explicit confirmation for the exact plan.
4. Move local exact duplicates to `90-Quarantine/`; do not permanently delete during the first cleanup pass.
5. Keep quarantine for at least 30 days unless the user explicitly authorizes earlier permanent deletion.
6. Require a separate explicit purge confirmation for irreversible deletion.
7. Verify the kept copy, manifests, project references, bundles, and catalog after cleanup.
8. Preserve and report every skipped or ambiguous candidate.

For ChatGPT Library, use file search and Library metadata to build the inventory, but do not claim to have deleted files unless an actual supported delete action succeeded and was reread. When no delete tool is available, return an exact deletion checklist with filenames/source IDs and guide the user through Library deletion. Confirm the deletions in the catalog only after the user or platform reports success.

## Cross-chat and project integration

Before creating a new export or uploading another bundle, search the project catalog, library catalog, recent Library uploads, and project memory for an existing current artifact. Reuse or version it rather than creating an unexplained duplicate. After meaningful project work:

- ingest or catalog the new artifact in its project folder
- record version and lineage
- update the master project catalog and refresh the handoff
- publish/update the material artifact or changed project-brain checkpoint on connected Google Drive and verify it
- treat ChatGPT Library as an additional convenience copy, never the required durable substitute
- generate an organized bundle only when needed and record storage impact/warnings

When durable storage is unavailable, return a downloadable library-catalog export and organized project bundle instead of pretending the account Library was reorganized.

## Verification gate

Before claiming library cleanup or organization is complete, prove:

- usage and limit came from a named current source or are explicitly unknown
- all in-scope files were inventoried
- exact duplicates were hash-proven
- same-name different-content versions were preserved
- kept copies and project references still resolve
- local removals are recoverable from quarantine or an approved backup
- external deletions actually occurred or remain clearly marked manual
- the library doctor passes
- the Markdown mirror and event log reflect the final state
