# Flagship Skill Source Policy

The directories below are the browsable source mirrors for Agent Foundry-owned flagship Skills.

Included:
- SKILL.md entrypoints and agent metadata;
- scripts and tests;
- references and schemas;
- reusable assets/templates/configuration;
- eval fixtures and source-side documentation.

Excluded from the canonical source mirror:
- generated runtime evidence such as screenshots and one-off execution logs;
- cache directories and compiled bytecode;
- secrets, credentials, machine-specific state, and private user data.

Generated evidence may be preserved separately as release/QA artifacts when it is useful, but it is not treated as source code.

The mirror is normalized through Ultimate Agent Governance before promotion so child Skills inherit the current shared execution constitution without restarting their domain-specific workflow ownership.
