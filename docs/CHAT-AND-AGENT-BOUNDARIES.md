# Chat skills and agent execution

## Chat-facing catalog

Ultimate Agent Governance, Zero-Loss Chat Accelerator, Project Brain Orchestrator, Minecraft Dev Kit, Minecraft Repair, Project Visual QA Showcase, Artifact Browser Companion, Revenue Operator, and Skill Creator are **chat-facing reusable skills**. Their historical names are preserved; they are not independent agents and do not grant an execution environment, credentials, model access, or background processing.

Load a relevant skill when its procedure helps the current chat. Do not require every chat to load every component. The Minecraft Dev Kit's chat workflow and code-engineering boundary remain documented in [the existing Dev Kit boundary guide](MINECRAFT_DEV_KIT_CHAT_AND_CODE_BOUNDARY.md).

## Repository and agent layer

- `AGENTS.md`: short repository routing and non-obvious execution rules.
- `PRODUCT_INVARIANTS.md`: one canonical acceptance contract.
- `agents/`: explicit adapters for supported execution contexts.
- `evals/`, tests and runtime receipts: evidence that behavior improved.

Do not paste the full chat skill catalog into every agent. Read only relevant references, preserve model-native tool/permission semantics, and avoid redundant instructions that consume context or weaken capabilities. No prompt can grant permissions that the host has not provided.

## To-do workflow

At project start, quickly check the canonical hub/issues and internal to-dos. Keep the requested task first; handle sensible authorized adjacent work, avoid collisions with active workers, and update completion only after the relevant checks pass. See [product invariant 19](../PRODUCT_INVARIANTS.md#19-project-to-do-awareness-without-task-drift).
