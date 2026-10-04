# Legacy chat workflow exports

Standalone and modular contracts here are compatibility exports for explicitly selected chat workflows. They include chat orchestration, catalogs and remote-artifact continuity detail. They are not the default cross-project coding-agent contract.

## Repository installation
Use the canonical Agent-Foundry checkout and `scripts/install_agents_bundle.py <isolated-target> --dry-run`. Default `repository` mode delegates to `tools/repository_governance.py`: versioned shared-policy snapshots plus a thin router, preserving local instructions and reporting integration review. It does not initialize chat memory, catalogs, hooks or Skills. See `docs/REPOSITORY-GOVERNANCE.md` in Agent-Foundry.

## Legacy compatibility
`--mode all-in-one`, `modular` or `hybrid` requires explicit `--legacy-chat-contract`. These modes refuse existing instruction/module destinations. A standalone export consumes about 30 KiB, leaving little room under common instruction budgets. Keep long workflows as selected references. Do not load standalone and modular contracts together.

`policies/policy-catalog.json` and controlled learning ledgers remain the source for these legacy outputs. Use compiler, doctor, tests and export tooling to keep representations synchronized. Their version is separate from repository adoption and published Skill releases.
