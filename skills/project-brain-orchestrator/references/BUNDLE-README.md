# AGENTS Workflow Bundle

This package includes two deployment styles and machine-enforcement tools.

## Recommended files

- `AGENTS.md` — complete standalone contract for agents that ignore referenced modules.
- `AGENTS.modular.md` plus `.agents/` — compact dispatcher and detailed modules for agents that reliably open referenced files.
- `.agents/PITFALLS.md` — approved evidence-backed failure patterns.
- `.agents/PITFALLS-QUARANTINE.md` — inactive candidates awaiting evidence and promotion.

## Governance tools

The portable export includes tools for policy compilation, integrity checks, compaction-resistant task state, machine-readable closeout receipts, repository probing, and UI audits. Run the AGENTS doctor before closeout or after instruction changes.

## Installation

For maximum compatibility, place the complete standalone contract at repository-root `AGENTS.md` and copy the `.agents/` directory beside it. Keep `AGENTS.modular.md` as an alternate dispatcher, not as a competing auto-loaded root file. Add project-specific commands, architecture, restricted paths, and known traps in nested `AGENTS.md` files near the relevant subsystem.

## Size and consistency

The standalone file is kept below the default 32 KiB project-instruction budget. `policies/policy-catalog.json` and the controlled learning ledgers are the structured sources; generated Markdown files must not drift. Use the compiler, doctor, tests, and export script rather than editing only one copy.

## Cross-project catalog

`tools/project_catalog.py` maintains a durable `project-catalog.json`, a human-readable `USER-PROJECTS-DATABASE.md`, and append-only events under `AGENTS_MEMORY_HOME` or `~/.agents-second-brain/`. Bootstrap from `memory/USER-PROJECTS-DATABASE.seed.md` only when no live catalog exists. The seed is never the current database. Reconcile project identities, versions, artifacts, repositories, relationships, checkpoints, confidence, and next actions before named project work; preserve old versions and validate/export the catalog for cross-chat handoff.

## Project second brain

For ongoing projects, initialize `.agents-memory/` with `tools/project_memory.py`. It records stable project identity, checkpoints, handoffs, decisions, research, tool choices, incidents, artifacts, and sessions while a user-level registry helps find the same project across directories or agents. `tools/research_memory.py` stores sourced, versioned, freshness-aware research. Run identity/resume checks before editing an existing or similarly named project. Export project memory at any time with `project_memory.py export`.


## Artifact library and storage manager

`tools/library_manager.py` maintains an organized local artifact vault plus a catalog for ChatGPT Library or other external entries. It tracks storage usage, warns at configurable thresholds, keeps project files in stable current/version/research/assets/bundles/memory/prompt/report folders, detects only hash-proven exact duplicates, generates cleanup plans, quarantines local files reversibly, and exports per-project bundles or the catalog. External ChatGPT Library deletion remains manual unless a supported delete action is available; never report deletion until it is confirmed.

## Export at any time

Run `scripts/export_bundle.py --output-dir <directory>` to create `AGENTS-workflow-bundle.zip`, `AGENTS-all-in-one.md`, and `AGENTS-modular.md` for Codex or other agents.

- Before resuming a project, perform a cross-chat delta sweep and reconcile same-name/new-content artifacts into `.agents-memory/` before editing.

## Feature Foundry source and object intelligence

The bundle includes capability-tested source-hub and object-intelligence seeds plus `scripts/asset_intelligence.py` to validate and render API/clipper/manual adapter truth, rights/fallback requirements, reversible object derivation, quality lanes, Blender isolation, and runtime candidates.
