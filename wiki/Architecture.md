# Architecture

Agent Foundry separates **acceptance ownership** from **procedure ownership**.

\`\`\`mermaid
flowchart TD
    U[User Goal] --> I[Product Invariants]
    I --> G[Ultimate Agent Governance]
    G --> Z[Zero-Loss Chat Accelerator]
    Z --> D[Domain Skill]
    D --> C[Challenger / Integration Pass]
    C --> M[Implementation]
    M --> V[Targeted Verification]
    V --> R[Runtime Proof]
    R --> P[Project Brain / Durable Publication]
    R --> F[Failure Intelligence]
    F --> G
\`\`\`

## Acceptance ownership
Governance answers: **what may not be lost, weakened, faked, or forgotten?**

## Procedure ownership
The narrowest relevant Skill answers: **how do we actually do this task?**

## Continuity ownership
Zero-Loss and Project Brain preserve:
- requirements;
- canonical IDs/paths;
- evidence freshness;
- hashes/run IDs;
- checkpoints;
- failed-route history;
- exact next action.

## Mechanical enforcement
Important rules should graduate from prose into:
- tests;
- audit scripts;
- schemas;
- eval cases;
- completion receipts;
- performance gates;
- runtime proof.
