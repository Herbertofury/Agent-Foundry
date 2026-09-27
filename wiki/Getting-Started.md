# Getting Started

Agent Foundry works best when you think in **layers**, not one monolithic agent prompt.

## 1. Define protected behavior
Put non-negotiable user-visible behavior in a canonical invariant file.

Examples:
- no feature removal;
- exact supported versions;
- no sampling for exhaustive requests;
- performance and quality must improve together;
- runtime proof required before claiming completion.

## 2. Keep AGENTS.md lean
Use \`AGENTS.md\` as a routing and repository-behavior layer. Point it to canonical standards instead of copying every long rule into the root context.

## 3. Put procedure into Skills
A Skill should own a repeatable domain workflow: repair, porting, conversion, research, document generation, QA, publishing, etc.

## 4. Keep the shared acceptance boundary active
Ultimate Agent Governance protects the result across skill switches. Zero-Loss preserves continuity and prevents wasted motion.

## 5. Challenge before reinventing
For substantial new work, inspect mature challengers and integrations before building a weaker duplicate.

## 6. Prove the real path
When the real application/runtime/workflow exists, exercise it.

## Recommended reading order
1. [AGENTS.md & Invariants](AGENTS-md-and-Invariants)
2. [Architecture](Architecture)
3. [Zero-Loss Execution](Zero-Loss-Execution)
4. [Challenger & Integration](Challenger-and-Integration-Standard)
5. [Building a Skill](Building-a-Skill)
