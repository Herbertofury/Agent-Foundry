# Building a Skill

A high-quality Skill is a reusable operating system for one class of work.

## Minimal structure

\`\`\`text
skill-name/
├── SKILL.md
├── agents/openai.yaml
├── scripts/
├── references/
├── assets/
└── evals/
\`\`\`

## Design checklist
- precise trigger metadata;
- compact entrypoint;
- progressive loading;
- deterministic scripts for fragile operations;
- current source references where freshness matters;
- shared execution-constitution inheritance;
- real evals and regression fixtures;
- explicit artifact/package validation.

## Before inventing
Run a challenger pass for relevant Skills, frameworks, libraries, and workflows. Integrate mature superior work where authorized.

## Before publishing
Validate the Skill, remove scaffolding, test scripts, package the complete bundle, record provenance/checksum, and preserve the durable artifact.
