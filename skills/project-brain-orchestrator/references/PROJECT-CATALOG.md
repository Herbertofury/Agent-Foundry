# Cross-Project Catalog and Version Ledger

Use the cross-project catalog before entering any named, resumed, or possibly existing project. It complements project-local `.agents-memory/`; it does not replace repository evidence.

## Durable locations

The default catalog home is `AGENTS_MEMORY_HOME` or `~/.agents-second-brain/`:

- `project-catalog.json` — canonical structured catalog
- `USER-PROJECTS-DATABASE.md` — human-readable mirror
- `project-catalog-events.jsonl` — append-only catalog history

The bundled `assets/memory/USER-PROJECTS-DATABASE.seed.md` is a bootstrap snapshot only. Never treat the immutable copy inside an installed skill as the current live catalog.

## Required workflow

1. Bootstrap the catalog once with `project_catalog.py bootstrap` when no durable catalog exists.
2. Before project work, search the catalog by exact name, aliases, known versions, artifacts, repositories, and related project families.
3. Run the cross-chat delta sweep, open plausible newer artifacts, and compare content signatures, hashes, source IDs, embedded versions, timestamps, and substantive structure.
4. Reconcile the discovered project/version/artifact changes with `project_catalog.py reconcile` before editing.
5. Resolve the canonical repository and then use `project_memory.py` for project-local identity, handoff, research, decisions, and checkpoints.
6. After each meaningful checkpoint or artifact reconciliation, sync project memory into the catalog with `project_catalog.py sync-project`.
7. Run `project_catalog.py doctor` before closeout and export the catalog when the live durable location cannot be written or shared.

## Version and artifact rules

- Preserve every known version and artifact; do not overwrite history.
- A same-name file may be a new version. Compare content, not filenames alone.
- Do not replace the current latest version merely because a newer timestamp exists. Promotion to latest requires explicit evidence, a verified supersession relationship, or direct user confirmation.
- Record status, confidence, source, source ID, hash or signature, observed time, canonical path, next action, and unresolved ambiguity.
- Record project relationships such as parent, subproject, precursor, merge, generated starter, host, shared runtime, or compatibility release.
- When identity or latest-good state is ambiguous, remain read-only.

## Cross-chat fallback

When the platform cannot write the durable catalog, generate and return an updated `USER-PROJECTS-DATABASE.md`, `project-catalog.json`, and a validated catalog ZIP. State that the export must be attached to the next chat, placed in the relevant ChatGPT Project, or copied into the configured catalog home. Discovery without durable reconciliation is not continuity.
