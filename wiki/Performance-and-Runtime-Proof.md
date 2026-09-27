# Performance & Runtime Proof

## Performance: dual-success
Optimization must show:
- a real target-metric improvement; **and**
- preserved correctness, content, quantity, fidelity, compatibility, and QoL.

Faster by doing less is not optimization.

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
