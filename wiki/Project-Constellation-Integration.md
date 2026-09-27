# Project Constellation Integration

Project Constellation is the human-facing continuity/control layer around long-running work.

Agent Foundry complements it by defining **how project state should behave**.

## Preserve
- project identity;
- canonical repo/file/Drive IDs;
- exact branch/commit;
- latest verified artifact;
- accepted requirements;
- blockers;
- failed routes not to repeat;
- exact next action.

## Handoff rule
A continuation resumes from the last verified checkpoint. It does not restart discovery simply because the chat, model, skill, or tool changed.

## Publication
Material checkpoints and distributable artifacts should be durably persisted to the project's canonical destinations and verified after write.
