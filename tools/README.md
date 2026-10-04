# Agent Foundry Tooling

## foundry_sync.py

Desired-state multi-agent Skill synchronizer with three explicit phases:

- `plan` — read-only diff of intended installs/updates/conflicts.
- `apply` — reconciles only missing or previously Foundry-managed destinations.
- `status` — reports drift and exits nonzero when reconciliation is required.

It supports `symlink` and managed `copy` modes and refuses to clobber unmanaged destinations.

Start by copying `config/foundry-sync.example.json`, enabling only targets whose native Skill directory you have verified, then run:

```bash
python tools/foundry_sync.py plan --config config/foundry-sync.json
python tools/foundry_sync.py apply --config config/foundry-sync.json
python tools/foundry_sync.py status --config config/foundry-sync.json
```

## validate_skill_tree.py

Fast deterministic local source/package guard. CI also performs pinned upstream Agent Skills compatibility validation.

## package_skills.py

Builds reproducible per-Skill `skill.zip` files plus machine-readable release receipts. Release CI attaches GitHub provenance attestations to the produced archives.

## repository_governance.py

Separate versioned repository-policy adoption; never installs chat Skills. `check` verifies canonical digests. `plan`/`status --target <isolated-project>` are read-only. Explicit `apply` preserves existing AGENTS.md and refuses edited/unmanaged snapshots. [Adoption guide](../docs/REPOSITORY-GOVERNANCE.md).

`manifest --version <major.minor.patch>` generates the source release manifest; changed policy requires a higher version. Adopt reviewed source commits through scoped project PRs. No automatic project discovery, broad pushes or recurring automation is configured.
