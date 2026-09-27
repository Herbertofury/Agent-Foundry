# Evaluation & Observability

## Evaluate the real harness

Agent Foundry prefers **with-change vs without-change** evaluations through the actual harness when practical.

For a Skill, that means testing:
- whether it triggered;
- whether task success improved;
- whether it stayed dormant for negative controls;
- what files/state actually changed;
- tool trajectory and retries;
- protected regressions;
- wall-clock/tokens/cost when useful.

One pretty answer is not enough evidence.

## Observe causally

Foundry prefers vendor-neutral OpenTelemetry-compatible traces so Phoenix, Langfuse, local collectors, or other tools can consume the same execution evidence.

A useful trace links:

<code>goal → run → action → policy decision → state mutation → verification → checkpoint</code>

Instrumentation should redact secrets and avoid turning the telemetry store into a duplicate project database.

Canonical standards:
- [EVALUATION_STANDARD.md](https://github.com/Herbertofury/Agent-Foundry/blob/main/EVALUATION_STANDARD.md)
- [OBSERVABILITY_STANDARD.md](https://github.com/Herbertofury/Agent-Foundry/blob/main/OBSERVABILITY_STANDARD.md)
