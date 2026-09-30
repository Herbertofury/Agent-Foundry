# Performance & Runtime Proof

## Performance: continuous zero-loss ratchet
Performance is an always-on objective for substantive runtime work. Agents perform a bounded free-speed pass on the affected path, integrate verified no-loss wins, and make each proven improvement the new baseline.

For explicit performance work, optimization must show:
- equivalent workload/result identity;
- a real target-metric or hot-path improvement; **and**
- no material regression in correctness, content, quantity, fidelity, compatibility, QoL, or any other relevant protected performance/resource dimension.

Faster by doing less is not optimization. Improving one metric by worsening another, moving cost elsewhere, or hiding it behind background work is a tradeoff—not a zero-loss win. Symptom-hiding workarounds such as feature removal, sleeps/delays, extra polling/retries, forced serialization/blocking, duplicated work, or cost-shifting do not count as completed fixes.

## Runtime proof
Use the strongest practical proof ladder:

1. syntax/schema
2. static analysis
3. unit tests
4. integration tests
5. build/package
6. real runtime launch
7. exact changed workflow
8. restart/reload persistence when relevant
9. challenge/regression pass

A successful compile is useful evidence. It is not automatically proof that the final user workflow works.

Canonical files:
- [PERFORMANCE_ACCEPTANCE.md](https://github.com/Herbertofury/Agent-Foundry/blob/main/PERFORMANCE_ACCEPTANCE.md)
- [RUNTIME_PROOF.md](https://github.com/Herbertofury/Agent-Foundry/blob/main/RUNTIME_PROOF.md)
