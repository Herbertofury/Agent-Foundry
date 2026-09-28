# Changelog

## 5.1.2 - 2026-08-30

- Added stall-safe workflow ownership so narrower domain skills remain the task owner while Project Brain supplies continuity/persistence without re-enumerating project state.
- Bounded connector/publication retries, backoff, socket waits, and local helper subprocesses to prevent multi-minute interactive stalls while preserving resumable Drive/GitHub publication and byte verification.
- Tightened validation/publication scheduling: changed-path tests during iteration, one convergence pass, coherent batched remote checkpoints, exact run identity, and no unchanged polling loops.
- Reduced the always-loaded Project Brain entrypoint from 13,991 to 12,242 bytes while preserving the project, Drive, build-first, and maximum-improvement contracts.

## 5.1.1 - 2026-08-30

- Added mandatory composition with `zero-loss-chat-accelerator` so Project Brain reuses the existing acceptance ledger, canonical identities, evidence, checkpoints, blockers, and exact next action instead of restarting discovery when skill routing changes.
- Promoted P-017, `Skill transition resets execution state`, as an explicit universal regression rule with a machine-verifiable cross-skill continuity acceptance test.

## 5.1.0 - 2026-08-20

- Made Google Drive a mandatory durable remote for every material file/artifact and meaningful cross-chat checkpoint whenever Drive is available.
- Broadened implicit activation so the skill applies whenever ChatGPT creates, modifies, saves, packages, checkpoints, or delivers reusable material output, not only named coding projects.
- Added continuous mid-session Drive checkpointing for long/interruption-prone work, canonical Drive read-before-edit behavior, update-in-place preference, and remote verification requirements.
- Kept repository source canonical in GitHub while requiring a Drive-backed project-brain/checkpoint export plus generated builds/packages, avoiding wasteful duplication of every source file.
- Made ChatGPT Library/sandbox/memory explicitly non-authoritative convenience layers and aligned Project Constellation, Compass, AGENTS policy mirrors, verification, and closeout rules with the Drive invariant.

## 5.0.0 - 2026-08-15

- Consolidated AGENTS Workflow Enforcer, Project Compass Orchestrator, and Reliable Artifact Publisher into one `project-brain-orchestrator` skill.
- Kept Project Compass Orchestrator as the execution/governance base because it already contains the newer fast-path, continuity, Project Constellation, policy, and verification stack.
- Added deterministic artifact preparation, multipart recovery, resumable upload, GitHub Release, Drive, HTTPS publication, and byte-verification tooling from Reliable Artifact Publisher.
- Reworked the entrypoint as a compact progressive-loading control plane so ordinary chats do not preload every governance, continuity, research, and publishing reference.
- Added collision avoidance so this consolidated skill does not compose with the three legacy skills when active.
- Preserved the Project Constellation meaningful-checkpoint delta model and user-edit precedence.
