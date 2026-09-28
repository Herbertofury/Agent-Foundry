# Workflow Selection

Choose the smallest workflow that preserves correctness. Do not force every task through the heaviest process.

## Tiny/local task

Use for a spelling fix, one-file config correction, or obvious low-risk change.

`inspect target -> edit -> targeted check -> finish`

Do not create an ExecPlan merely because one exists in the repository.

## Bug repair

Use when behavior is broken.

`reproduce/observe -> isolate earliest causal owner -> scoped fix -> regression test -> targeted runtime proof -> convergence check`

Do not patch only the visible symptom when the same shared cause affects multiple surfaces.

## Feature / meaningful behavior change

Use a lightweight spec-driven loop:

`define observable acceptance -> resolve architecture -> task/edit sequence -> implement -> converge against acceptance`

Add clarification/checklists only when ambiguity materially threatens correctness.

## Cross-cutting / migration / long-running change

Use an ExecPlan conforming to `PLANS.md` (or the repository equivalent). Preserve checkpoints, latest test evidence, blockers, rejected routes, and exact next action.

## Research/decision task

Keep facts, alternatives, evidence, and the chosen decision separate. Use primary/current sources for version-sensitive choices. Do not turn research into implementation unless the task calls for it.

## Principle

The process should remove uncertainty and preserve continuity. If the process itself becomes the main work, it is too heavy for the task.


## Live domain-skill execution

When this skill is active as an execution overlay rather than governance authoring, do not force the governance-authoring workflow. Load `live-chat-execution.md`, keep the narrower domain skill in control, preserve the continuity capsule, and enforce the acceptance boundary without restarting resolved work.
