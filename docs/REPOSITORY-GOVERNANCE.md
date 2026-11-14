# Shared instruction adoption

Agent-Foundry owns the reusable engineering mindset. Every consumer owns its setup, commands, constraints, domain procedures and scoped instructions. Never sync private or project-specific content back into the shared core.

The implementation selectively reconciles the repository-governance tooling from earlier PR #3 onto current main; it does not replace newer standards with that branch's historical copies. Existing `foundry_sync.py` continues to manage explicitly selected skills separately.

## Plan, reconcile, verify

Use a reviewed, clean pinned Agent-Foundry checkout:

```sh
python tools/repository_governance.py check
python tools/repository_governance.py plan --target /path/to/project
python tools/repository_governance.py apply --target /path/to/project
python tools/repository_governance.py status --target /path/to/project
```

`plan`/`status` are read-only. `apply` pins canonical standards and one concise core under `.agents/foundry/`, recording version, source commit and SHA-256/LF digests in `.agent-foundry/governance-lock.json`. It refuses unmanaged/edited/deleted snapshots and linked destinations before writing. Local AGENTS.md, overrides, nested instructions and existing CLAUDE.md remain untouched. Missing root AGENTS.md gets a thin router; missing CLAUDE.md gets `@AGENTS.md`. Existing routers/imports needing integration return `review`, not false success. Review local precedence and conflicts explicitly before adding references. A root router never receives a stale copy of the entire shared core.

For a shared edit, update the canonical template/standard and publish a higher explicit manifest version with `manifest --version X.Y.Z`. Reconcile pinned copies on isolated consumer branches; review local instructions, run target checks, publish and verify remote blobs. Hash equality proves synchronization, not agent quality. Never automatically push to discovered repositories or grant persistent access. Existing local extensions never flow outward. Retiring migration sources are excluded from rollout; route their work to Athena.

## Current practice and evidence

- [Codex AGENTS discovery](https://developers.openai.com/codex/guides/agents-md/): inspect overrides and nested scope; leave ample room within its default 32 KiB combined budget for useful local instructions.
- [Claude memory](https://code.claude.com/docs/en/memory): use the documented `@AGENTS.md` import, especially when CLAUDE.md shadows native discovery. Imports avoid brittle Windows symlinks but do not eliminate context cost.
- [Agent Skills specification](https://agentskills.io/specification): small entrypoints, on-demand scripts/references and explicit task applicability, not every skill preloaded.
- [Evaluating AGENTS.md](https://arxiv.org/abs/2602.11988): more instructions are not automatically better; reported benefits and costs depend on task and content. Do not claim this core is empirically superior until target trials demonstrate it.

The design choice is a compact shared core plus local detail, with deterministic synchronization checks rather than a huge universal prompt. Important safeguards belong in executable tests as well as prose.

## Acceptance matrix

Compare baseline/minimal/candidate instructions on real bug repair, UI/native workflow, data migration, stale-command recovery and concurrent-edit tasks. Record correctness, scope preservation, native acceptance, false blocks, unrelated churn, token/tool/time cost and truthful completion. Synthetic synchronizer tests prove overwrite protection and reproducibility, not generalized agent intelligence. No native harness behavioral superiority is claimed by this release.
