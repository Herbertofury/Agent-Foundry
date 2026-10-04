# Distribution and Sync

## Explicit chat Skill distribution
`tools/foundry_sync.py` implements desired-state plans, managed copy/symlink installs and drift status for selected Skill packages. Verify native harness directories before enabling targets. The draft adds local-edit conflict protection to managed copy updates. Existing releases retain their earlier behavior until updated.

Open Agent Skills format and pinned release provenance are the baseline. Popularity or pack membership is not trust; use the third-party security pipeline.

## Repository governance adoption
[Repository Governance Sync](Repository-Governance-Sync) is a separate proposed path with versioned snapshots, local-edit conflicts and preserved project-owned instructions. It does not activate chat Skills or copy root AGENTS.md across projects.

[Distribution standard](https://github.com/Herbertofury/Agent-Foundry/blob/main/DISTRIBUTION_STANDARD.md).
