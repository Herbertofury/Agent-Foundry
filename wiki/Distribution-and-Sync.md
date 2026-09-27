# Distribution & Sync

Agent Foundry should be installable across agent harnesses without inventing a proprietary Skill format.

## Baselines

- Open Agent Skills <code>SKILL.md</code> format
- Open <code>AGENTS.md</code> repository instruction convention
- Git as canonical source
- pinned/digested releases for durable installs

## Ecosystem compatibility

The <code>skills</code> CLI and skills.sh provide useful discovery/install/update compatibility across many agent harnesses.

For multi-agent machines and teams, Foundry prefers a **desired-state** approach:

<code>declare → plan → sync → status</code>

Botfile is a strong challenger pattern: one curated source fans out into agent-native directories using a plan-first, non-clobbering model.

## Trust is separate

Popularity, install count, or inclusion in a pack does not equal trust. Distribution feeds the third-party Skill security pipeline.

[Read DISTRIBUTION_STANDARD.md](https://github.com/Herbertofury/Agent-Foundry/blob/main/DISTRIBUTION_STANDARD.md)
