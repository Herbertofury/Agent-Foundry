# Skill Authoring in Agent Foundry

A strong Skill is a compact reusable operating manual, not a prompt dump.

## Structure
A typical Skill contains:

\`\`\`text
skill-name/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── scripts/
├── references/
├── assets/
└── evals/
\`\`\`

## Design rules

### Trigger precisely
The Skill description should make it obvious when the Skill owns the task.

### Keep the entrypoint lean
Put essential workflow in \`SKILL.md\`. Move long detail into references loaded only when needed.

### Use scripts for determinism
Fragile, repeatable, or machine-checkable operations should prefer tested scripts over long prose.

### Inherit the execution constitution
Substantive mutable skills must preserve the shared acceptance boundary: no blocker closeout, unknown-not-absent, full-result preservation, performance+quality, real proof, continuity, completeness, and challenger-before-reinventing.

### Preserve procedure ownership
A governance/guardrail skill adds acceptance constraints; it does not steal a narrower domain skill's procedure or restart its discovery.

### Evaluate real failure modes
Good evals include positive cases, negative controls, and regression fixtures from failures that actually happened.

## Challenger requirement
When creating a substantial new Skill, search for existing skills, libraries, agent frameworks, workflows, and tooling that can be integrated rather than duplicating a weaker implementation.

## Packaging
A published Skill should be validated, packaged, versioned/provenanced, and accompanied by a clear source/checksum lineage when a binary bundle is distributed.
