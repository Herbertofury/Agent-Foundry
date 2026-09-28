# Compaction recovery contract

Preserve execution-critical state, not conversational filler.

After compaction, before further work:
1. Reload every applicable AGENTS.md from repository root to the current target and every required `.agents/` module.
2. Read `.agents/ACTIVE-TASK.json`, `.agents-memory/PROJECT.json`, `.agents-memory/STATUS.json`, and `.agents-memory/HANDOFF.md` when present. Preserve the exact request, project ID, canonical target, requirements, decisions, sourced research, toolchain choices, completed work, artifacts, remaining work, failed approaches, blocker evidence, and verification obligations.
3. Reconcile the current repository and runtime state with the saved state. Never assume a command, edit, test, or build occurred unless evidence is present.
4. Continue from the first incomplete requirement. Do not restart completed work or repeat a failed approach without new evidence.
5. Before closeout, validate `.agents/CLOSEOUT-RECEIPT.json`, checkpoint and validate project memory, and run the AGENTS doctor.
