# Repository governance and adoption

## Two separate instruction surfaces

The nine flagship components are chat workflows selected in ChatGPT or another compatible chat harness. `skills/` is their source mirror, and `catalog/SKILLS.md` describes their invocation. A skill containing coding scripts or `agents/openai.yaml` is still a chat workflow; packaging metadata does not make its entire prompt repository policy.

Coding agents use project-owned `AGENTS.md`, applicable scoped instructions and approved shared standards. They do not automatically activate Ultimate Agent Governance, Zero-Loss Chat Accelerator, Project Brain Orchestrator, or the other chat skills. Their adapters preserve the same accepted product invariants without importing chat orchestration, catalogs, watchdogs or a per-chat build/export ceremony.

## Canonical policy and versions

`PRODUCT_INVARIANTS.md` retains the 18 existing numbered invariants. Root standards supply their detailed gates. `registry/repository-governance.json` versions an explicit set of shared policy files and the thin repository adapter, with SHA-256 over UTF-8/LF text. `tools/repository_governance.py check` rejects stale digests; changing the shared set requires an explicit higher semantic version.

Use a reviewed commit/tag of Agent-Foundry as the source. The consumer lock records its source commit, version, file digests and whether the source working tree was dirty. A clean pinned source is required for a reproducible published adoption. Digest agreement proves file parity, not semantic compliance or agent quality.

## Adoption without overwriting customization

```sh
python tools/repository_governance.py check
python tools/repository_governance.py plan --target /path/to/isolated-consumer
python tools/repository_governance.py apply --target /path/to/isolated-consumer
python tools/repository_governance.py status --target /path/to/isolated-consumer
```

`plan` and `status` are read-only and never enumerate projects. An explicit `apply` writes policy snapshots under `.agents/foundry/` and `.agent-foundry/governance-lock.json`. It creates a small root router only when `AGENTS.md` is absent. Existing root/nested instructions remain project-owned. If the root has no Foundry reference, status reports `review`; add a reviewed reference to `.agents/foundry/AGENTS-adapter.md` at the appropriate local scope. Until then, the files are available but adoption is not active.

Missing snapshots can be created. A managed snapshot can update only when its current digest matches the prior lock. Unmanaged, edited, removed or linked destinations stop the entire apply before writes. Local exceptions belong in project-owned instructions; review conflicts rather than replacing them. For existing adopted roots, the root references the managed adapter so its version can update without replacing local commands. No tool changes permissions, activates chat skills, discovers targets or pushes repositories.

For updates, read the version diff, preserve project-specific restrictions and stronger acceptance requirements, run a plan, reconcile in an isolated clean branch, inspect the diff, run project checks and publish a scoped PR. Do not fan out a fresh root `AGENTS.md` to every repository. No recurring sync or broad rollout is configured here.

## Layering and context discipline

Follow the actual harness's discovery and precedence rules; user/developer/system authority outranks repository files. Root guidance should contain setup, commands, a short routing map and non-obvious local rules. Keep domain detail scoped or load it when needed. Reuse unchanged instructions/evidence within a run; refresh when scope, files, authority or context changes. Do not preload every standard or duplicate standalone and modular contracts.

[OpenAI documents Codex discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md.md), including `AGENTS.override.md`, directory layering and a default combined project-document budget of 32 KiB. Other harnesses can differ. Being just below that budget is not a quality target: leave room for real project instructions.

The Project Brain all-in-one/modular exports remain legacy chat-oriented compatibility material. Its installer defaults to this thin repository adoption path. Legacy modes require an explicit opt-in and refuse to replace any existing installation. They are not the cross-project source of truth.

## Bounded audit, 2026-10-04

Read-only GitHub default-branch tree/root checks found no adoption lock or shared invariant snapshot in these four repositories. No files, settings, branches or wikis were changed there.

| Repository | Observed default-branch commit | Instruction surface |
|---|---|---|
| MediaForge | `23b7e2c572eb341560e54747d06f89d26d787201` | No tracked root AGENTS.md or Foundry adoption lock found |
| JetSetCraft | `46269e017dcc7d7b4237cd0ba99b09d9d2795c29` | No tracked root AGENTS.md or Foundry adoption lock found |
| Project-Constellation | `a3d9cc8a8da4ec03e97e3124ebda02d2dcf28dd4` | Project-owned root and recovery-scoped AGENTS.md; no Foundry adoption lock |
| Travel-Softball-Team | `626c57d87e9ee25b8f7a928a131a7d281437776b` | Project-owned root AGENTS.md with product/UI/privacy rules; no Foundry adoption lock |

This establishes unversioned adoption, not proof of behavioral violation. GameSync repositories/copies and Enderloom were excluded entirely. Future adoption should select named inactive repositories and review their local exceptions before any writes.
