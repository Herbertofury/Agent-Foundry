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
