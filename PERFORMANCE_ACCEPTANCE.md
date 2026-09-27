# Performance Acceptance

Agent Foundry treats performance and preserved behavior as simultaneous requirements.

## Dual-success gate
A performance change passes only when:
1. the requested metric or hot path materially improves; and
2. protected behavior remains intact.

Protected behavior can include correctness, result count, content, visual fidelity, compatibility, determinism, data safety, feature coverage, and user-visible QoL.

## Invalid shortcuts
The following do not count as optimization:
- rendering fewer things without permission;
- silently reducing search breadth;
- dropping compatibility paths;
- lowering quality/fidelity;
- skipping validation;
- caching stale or wrong results;
- disabling expensive features rather than engineering them efficiently.

## Evidence
Prefer equivalent-work measurements:
- before/after timings;
- FPS/frame-time distributions;
- throughput;
- memory/CPU/GPU usage;
- launch/load latency;
- network/request counts;
- benchmark or trace evidence.

A preservation-only change with no measured gain is not a completed performance task. A faster result produced by doing less is also not complete.
