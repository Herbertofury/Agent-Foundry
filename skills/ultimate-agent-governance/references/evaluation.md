# Evaluating Agent Rules and Skills

The purpose of an eval is to determine whether the instruction changes real behavior in the intended direction without causing unrelated regressions.

## Minimum suite

For an important rule/skill, create:

- one **positive case** where it must apply;
- one **negative control** where it must not add unnecessary behavior;
- one **regression case** for a real past failure when available.

## Assertions

Prefer deterministic assertions such as:

- expected file exists/changed;
- forbidden file remains unchanged;
- test command passes;
- generated link equals an exact canonical URL;
- implementation uses the shared component/helper;
- no fabricated fallback appears;
- build artifact is fresh.

Use LLM grading only for behavior that cannot be checked deterministically.

## Compare against baseline

When practical, run with and without the skill/rule. Track acceptance first; token/time/tool counts are secondary.

A rule that lowers cost but weakens acceptance is a regression.
## Performance dual-success controls

For performance governance, include both failure directions:

- reject a candidate that is faster because it removes, caps, disables, or degrades required behavior;
- reject a candidate that preserves behavior but does not improve the requested FPS/TPS/latency/throughput/hot path when the task explicitly requires a performance gain.

Also include a case where the first optimization route conflicts with preservation. The expected behavior is to change implementation strategy and continue, not to remove content and not to close the task unchanged.



## Live execution cases

When the skill is used as a live execution overlay, evaluate composition rather than governance-file authoring. Positive cases should prove that a narrower domain skill keeps workflow ownership while full-result preservation, no-removal repair, performance dual-success, continuity/no-reset, runtime proof, and evidence-bound completion remain active. Negative controls should reject skill-triggered rediscovery, feature removal as repair, preservation-only performance closeout, and build-only completion when real runtime proof is available.
