# Optional lifecycle-hook adapter

`agent_hook.py` is a runtime-neutral enforcement adapter for lifecycle events equivalent to session start, prompt submission or post-compaction refresh, pre-tool use, post-tool use, and stop/closeout.

Agent hook schemas and configuration keys change. Verify the installed agent's current official documentation, then map its event payloads to the adapter's `event`, `repository`, and optional `command` fields. Do not paste unverified hook syntax into a live configuration.

The adapter can run the AGENTS, project-memory, and artifact-library doctors at session start; require the handoff and library catalog before mutation or new exports; remind the agent to refresh `ACTIVE-TASK.json`; reject a narrow set of destructive commands; request evidence and memory checkpoints after tool use; and block closeout when the receipt, initialized project memory, or library catalog is invalid.
