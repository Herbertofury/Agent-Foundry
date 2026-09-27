# Evaluations

Important behavior should be tested, not merely described.

Canonical standard: [EVALUATION_STANDARD.md](../EVALUATION_STANDARD.md)

## Preferred coverage

- baseline **without** the Skill/change;
- candidate **with** the Skill/change;
- real harness when the target is a real harness;
- repeated runs for stochastic cases;
- positive trigger cases;
- negative trigger controls;
- deterministic workspace/state-delta checks;
- trajectory/tool-call inspection;
- protected-regression assertions;
- failure injection and recovery;
- time/token/tool/cost evidence where useful;
- holdout cases for important reusable Skills.

## Eval rule

A Skill does not pass merely because the final prose looks better. The evaluation should detect whether it:
- triggered correctly;
- changed real task success;
- avoided unnecessary work;
- preserved protected behavior;
- recovered from failures;
- used the intended tools/state;
- left the expected workspace/artifact state.

Real incidents should become regression fixtures when replayable.
