# Codex integration pack

Copy `compact-prompt.md`, `ACTIVE-TASK.template.json`, and the portable tools into the repository `.agents/` directory. Keep the compact root `AGENTS.md` plus the modular `.agents/*.md` files. Retain `AGENTS-all-in-one.md` as a fallback for agents that ignore module loading, but do not leave competing instruction files in locations automatically loaded by Codex.

`config.toml.example` is intentionally conservative. Confirm configuration keys against the installed Codex version before applying them. The bundle itself remains below the default project-document limit and does not depend on the larger optional budget.

For long-running work, install `project_memory.py`, `project_catalog.py`, `research_memory.py`, and `library_manager.py`; initialize `.agents-memory/` only after identity checks; and set `AGENTS_MEMORY_HOME` to a persistent user-owned vault. Keep organized artifacts under `<AGENTS_MEMORY_HOME>/library` or `AGENTS_LIBRARY_HOME`, with complete bundles in project folders and cleanup routed through reviewed plans and quarantine. On every Codex session, resume from `.agents-memory/HANDOFF.md` and verify it against the current Git state before editing.
