# Zero-Loss Execution

This page describes a selected chat workflow. [Coding-agent repository policy](AGENTS-md-and-Invariants) is separate; this workflow is not automatically loaded by repository instructions.

Zero-Loss is the execution substrate that keeps ambitious work moving **without reducing the requested result**.

## Core behaviors

### No rediscovery
Reuse settled IDs, paths, schemas, hashes, run IDs, prior recoveries, and checked evidence until a real invalidator exists.

### Implementation crossing
Once canonical target + actionable root cause + safe edit are known, further read-only work needs a named correctness blocker.

### Progress watchdog
Two execution waves with no new evidence, reduced uncertainty, dependency progress, mutation, verification, or acceptance progress force a strategy change.

### Wait leases
Do not let a slow CI job/provider operation hold unrelated work hostage.

### Checkpoint before long gates
Once targeted tests prove a coherent implementation, persist a recoverable checkpoint before long full-suite/runtime/release validation.

### Retry only with new information
Never loop an unchanged failure.

### Skill switches preserve ownership
Treat domain, governance, continuity, repair, and guardrail Skills as composable overlays. Preserve one continuity capsule across the switch, keep the prior domain owner unless a more-specific bounded subtask is active, and return to its exact next action afterward. Never restart or fork the task merely because another Skill loaded.

## The objective
**Maximum useful effort. Minimum wasted motion.**
