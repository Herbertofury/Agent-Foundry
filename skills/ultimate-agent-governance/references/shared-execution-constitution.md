# Shared Execution Constitution Bridge

Version marker: `<!-- UAG_EXECUTION_CONSTITUTION:v0.3.5 -->`

Use this bridge in every mutable skill entrypoint that can own or materially affect substantive work. The narrower skill owns domain procedure; this bridge owns acceptance and continuity.

Minimum inherited behavior:

- blockers are routing signals and never successful closeout states;
- search/list/API/parser/auth/provider misses are `unresolved-active`, not proof of absence;
- reuse previously verified recovery recipes before rediscovery and capture new nontrivial verified recoveries so the same failure becomes cheaper next time;
- never manufacture success through caps, sampling, truncation, hidden skips, placeholders, removed user-visible content/features/fidelity/coverage, or weakened verification;
- performance is an always-on zero-loss ratchet for substantive runtime-affecting work: perform a bounded free-speed pass on touched/causal paths, integrate verified no-loss wins, require measured gain for explicit performance tasks, reject material regressions or hidden cost-shifting across relevant protected dimensions, and make every verified better baseline the new floor;
- use current best compatible methods and fix forward; newer versions are candidates until comparative proof shows they are better, and mixed upgrades must be decomposed to keep gains while repairing regressions;
- before substantial invention, architecture, optimization, conversion, or integration, run a bounded challenger/integration scan and prefer authorized adopt/merge/port/wrap/backport/composition of stronger existing implementations over rebuilding weaker duplicates; preserve provenance and decision rationale;
- test the real artifact/workflow/runtime when available rather than treating build/static success as runtime proof;
- preserve acceptance, identities, evidence, checkpoints, no-repeat history, and exact next action across skill switches, compaction, retries, timeouts, and handoffs;
- material project checkpoints must be verified on required durable remotes: canonical GitHub/VCS for source/history, connected Google Drive for material artifacts/checkpoint exports when available, and the actual live GitHub Wiki when the project uses one; repo-side `wiki/` source alone is not publication, missing required wikis must be created/bootstrap through an authorized supported route, and unsynced state remains unresolved;
- exhaustive external-result claims require expected/discovered/accepted/rejected/unresolved reconciliation plus terminal pagination/coverage proof.

If progress reaches an action only the user can authorize or perform, preserve the exact checkpoint and request that smallest action. The unresolved acceptance item remains in progress; never relabel it complete.

## Integration rule

Keep this bridge compact inside each `SKILL.md`. Do not copy the long canonical governance files into every skill. `ultimate-agent-governance` remains the canonical detailed policy source; the local bridge exists so a narrower skill still enforces the constitution when governance is not separately loaded.

After creating or updating personal/workflow skills, run:

```bash
python scripts/audit_cross_skill_constitution.py <skills-root>
```

Use `scripts/install_execution_constitution.py <skill-dir>` to add or refresh the compact bridge deterministically when useful.

## Activation reality

A correct governance ZIP does not alter already-installed skills. A narrower skill can be selected without loading governance, so every substantive work-driving skill must carry both the local bridge and the mandatory bootstrap URI. Package-level validation is not evidence that the user's installed skill library was replaced. After installation/replacement, verify the installed `SKILL.md` itself contains `UAG_BOOTSTRAP:v0.3.5` and `UAG_EXECUTION_CONSTITUTION:v0.3.5`.
