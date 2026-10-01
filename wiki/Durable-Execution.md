# Durable Execution

Long-running agent work should survive runtime crashes, provider timeouts, human approval waits, and chat/session boundaries without replaying unsafe side effects.

## Foundry durable task contract

A durable task carries:
- stable identity;
- accepted requirements;
- durable checkpoint;
- lifecycle state;
- idempotency strategy;
- cancellation semantics;
- human-input state;
- exact next action;
- verified terminal result/error.

## Key rule

> **Persist before advertising durability.**

A resumable handle is not trustworthy until enough state exists to actually resume it.

MCP Tasks, Temporal, LangGraph-style checkpointers, Inspect checkpointing, or Project Brain can provide implementation mechanisms. Foundry standardizes the acceptance behavior, not one orchestration library.

## Remote checkpoint rule

For substantive project work, a resumable state is not fully durable until the latest coherent checkpoint has reached its required remotes: canonical GitHub/VCS source/history, connected Google Drive artifact/checkpoint storage when available, and the actual live GitHub Wiki when the project uses one. A chat, sandbox, or repo-side `wiki/` mirror is not enough by itself.

See **[Remote Continuity & Wiki Sync](Remote-Continuity-and-Wiki-Sync)** for the verification contract.

[Read DURABLE_EXECUTION_STANDARD.md](https://github.com/Herbertofury/Agent-Foundry/blob/main/DURABLE_EXECUTION_STANDARD.md)
