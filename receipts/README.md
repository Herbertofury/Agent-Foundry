# Foundry Receipts

Receipts turn important governance claims into structured, reviewable evidence.

## Schemas

- [Challenger receipt](../schemas/challenger-receipt.schema.json) — what was searched, what was compared, and why the chosen route won.
- [Skill trust receipt](../schemas/skill-trust-receipt.schema.json) — provenance, digest, capabilities, scan/review evidence and trust state.
- [Eval case](../schemas/eval-case.schema.json) — trigger expectation, protected invariants, observable assertions and cleanup.
- [Release receipt](../schemas/release-receipt.schema.json) — artifact/source identity, digest, validation and provenance links.

## Principle

A receipt is **evidence metadata**, not a substitute for the evidence itself.

Do not mark a field “passed” merely because the intended check exists. Link or identify the observed result that actually passed.
