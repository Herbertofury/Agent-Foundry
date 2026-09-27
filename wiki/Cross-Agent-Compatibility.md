# Cross-Agent Compatibility

Agent Foundry is built around **canonical policy + thin adapters**.

## The goal
The same high-level acceptance behavior should survive across:
- ChatGPT Skills;
- Codex/coding agents;
- repository AGENTS.md systems;
- domain-specific agents;
- connected tool workflows;
- future agent runtimes.

## The rule
Do not maintain large independent copies of the same policy for every harness.

Instead:
1. keep one canonical standard;
2. expose a short bridge/adapter in each harness;
3. mechanically audit parity where the rule is critical.

This reduces context waste and policy drift while preserving behavior.
