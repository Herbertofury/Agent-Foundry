# Agent Foundry Product Invariants

These are non-negotiable behavior guarantees for substantive Agent Foundry workflows.

## 1. Preserve the complete result
Never manufacture success through hidden caps, sampling, truncation, placeholders, removed features, reduced fidelity, weakened compatibility, or skipped verification.

## 2. Blockers do not close work
A failed route is a routing signal. Repair the environment, dependency, auth, provider state, implementation, build path, or workflow; otherwise preserve the exact unresolved checkpoint.

## 3. Unknown is not absent
Search/API/parser/provider misses stay <code>unresolved-active</code> until alternate authoritative routes establish the result or absence is genuinely proven.

## 4. Challenge before reinventing
Before substantial invention, look for mature challengers and integration opportunities. Prefer authorized adoption, merge, port, wrapping, backporting, or composition when it produces a stronger result than rebuilding from scratch.

## 5. Performance and quality improve together
Equivalent-work performance tasks require a measured improvement in the target metric or hot path and preservation of correctness, content, quantity, fidelity, compatibility, and user-visible QoL.

## 6. Real proof outranks structural proof
When the actual runtime or workflow is available, exercise the final artifact and affected user path.

## 7. Continuity is mandatory
Preserve accepted requirements, canonical IDs/paths, evidence, hashes/run IDs, checkpoints, failed-route history, prior verified recoveries, and exact next action across handoffs, timeouts, skill switches, connectors, and retries.

## 8. Never suffer the same failure twice
Reuse prior verified recovery knowledge before rediscovery. Convert nontrivial verified fixes into reusable incident knowledge and regression protection.

## 9. Modernize and fix forward
Use current production-worthy compatible methods when freshness matters. Treat upgrades as candidates until comparative evidence proves the gain.

## 10. Evidence-bound completion
A completion claim may not outrun observed proof.

## 11. One truth, many thin adapters
Long policy has one canonical source. Skills, agent files, wiki pages, and tool-specific adapters point to it instead of forking copies that drift.

## 12. Maximum useful effort, minimum wasted motion
Optimize orchestration waste, repeated discovery, redundant polling, and avoidable serialization—not quality, reasoning depth, verification, capability, or requested breadth.

## 13. Root-cause fixes over regression workarounds
**Rule.** Solve the causal defect or bottleneck; do not manufacture a pass by making the product do less or by moving the cost somewhere less visible.

**Scope.** Repair, optimization, compatibility, migration, integration, refactor, reliability, and performance work.

**Required behavior.** Do not remove or disable features, reduce scope/coverage/fidelity, add sleeps/delays/polling/retries, force serialization/blocking, duplicate work, or shift expensive work to another path when that materially worsens protected behavior, end-to-end latency, throughput, resource use, responsiveness, UX, or maintainability. A workaround with such regressions is temporary containment only, remains `unresolved-active`, and may not be called the fix unless the user explicitly accepts the tradeoff.

**Architecture requirement.** Identify the earliest causal owner, repair it at the appropriate shared layer, and compare equivalent work end-to-end so costs cannot be hidden by relocation.

**Regression requirements.** Preserve feature and behavior contracts and compare the relevant before/after performance or resource metrics. Add a focused regression check when the failure mode is repeatable.

**Acceptance test.** Did the solution remove the causal failure while preserving the complete result and avoiding material performance/QoL regressions or hidden cost-shifting?
