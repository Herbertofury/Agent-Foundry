# Repository Governance Sync

## Current behavior

The 18 accepted product invariants remain canonical in Agent-Foundry. The nine flagship components are chat workflows, separate from coding-agent instructions. Existing `tools/foundry_sync.py` distributes explicitly selected Skill packages; it does not synchronize repository AGENTS.md. Source code now includes a local-edit conflict guard for managed copy updates; reviewed source updates remain supported.

## Versioned repository adoption

The repository provides `registry/repository-governance.json` and `tools/repository_governance.py`. They version an explicit shared policy set, verify UTF-8/LF SHA-256 digests, and provide read-only `plan`/`status` plus explicit `apply` to a named consumer.

```sh
python tools/repository_governance.py check
python tools/repository_governance.py plan --target /path/to/isolated-project
python tools/repository_governance.py status --target /path/to/isolated-project
```

Apply writes snapshots to `.agents/foundry/` and a lock to `.agent-foundry/governance-lock.json`. Existing root/nested instructions remain project-owned. If the root lacks a Foundry reference, status reports a required integration review. Unmanaged, locally edited, removed or linked snapshot destinations stop the entire apply before writes. The lock records version, digests, source commit and dirty-source state.

The repository code and safe installer default are available on main through PR #3. Published release packages have not changed. No consumer repository is enrolled or updated, and no recurring sync exists. The wiki footer links the canonical source and merge review.

## Bounded audit and adoption policy

Read-only default-branch checks on 2026-10-04 found no adoption lock in MediaForge, JetSetCraft, Project-Constellation or Travel-Softball-Team. The latter two have project-owned AGENTS.md; the former two have no tracked root AGENTS.md. This establishes unversioned adoption, not a behavioral violation. GameSync and Enderloom were entirely excluded.

A future rollout should select named inactive repositories, reconcile local requirements, pin a reviewed Foundry commit/version, plan in isolation, inspect the diff, run project checks and publish a scoped PR. Do not copy a universal root file across projects.

[Detailed source guide](https://github.com/Herbertofury/Agent-Foundry/blob/main/docs/REPOSITORY-GOVERNANCE.md).
