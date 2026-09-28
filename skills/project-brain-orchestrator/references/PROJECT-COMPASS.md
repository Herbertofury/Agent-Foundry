# Project Compass, Northpoints, Wants, and Publication

Use one versioned **Project Compass** for every long-running or cross-chat project. It preserves what the project is trying to become, not merely what happened last.

## Durable files

Keep these under `.agents-memory/`:

- `COMPASS.json` — canonical structured northpoints, goals, feature pillars, principles, wants, guardrails, acceptance signals, and publication targets.
- `PROJECT-COMPASS.md` — generated human-readable mirror.
- `compass-events.jsonl` — append-only history of additions, changes, supersession, and retirement.
- `publications.jsonl` — provider, remote ID/link, local and remote size, SHA-256, verification state, and timestamp.

## Meaning and precedence

- **Northpoint:** enduring product outcome that guides tradeoffs.
- **Goal:** concrete result that advances a northpoint.
- **Feature pillar:** major capability family required by the product identity.
- **Principle:** reusable design or engineering rule.
- **Want:** user-requested addition not yet promoted to a foundational rule.
- **Guardrail:** behavior that must not regress while pursuing goals.
- **Acceptance signal:** observable evidence that proves the idea exists in the real product.

Current explicit user instructions override stored Compass content. Never silently dilute, delete, or rewrite foundational entries. Supersede them with provenance and preserve history. Convert examples into general project-local acceptance criteria while retaining the examples as test cases.

## Living and themed interface interaction ecology

For a living, spatial, game-like, or highly themed interface, the Compass must define the world's **interaction ecology**, not merely colors and ambient decoration. Record it through northpoints, feature pillars, principles, guardrails, wants, and acceptance signals.

- Define a distinct interaction grammar per theme for press, hold, release, drag, reorder, resize, drop, placement, collision, transfer, transformation, absorption/ejection or equivalent behavior, cancel/undo, keyboard, controller, and assistive activation.
- Make reactions coherent across the touched element and only the relevant surrounding UI, objects, lighting, sound, particles, mascots, and scenery. Treat those responses as one bounded cause-and-effect chain rather than unrelated canned animations.
- Make material behavior respond to apparent material, scale, mass, velocity, direction, contact depth, surface, and surrounding medium. A single generic pulse, color wash, stock particle burst, or shared clip is not sufficient.
- Make the theme identity **subtle but unmistakable**: effects remain refined and non-obstructive while the interaction character is immediately perceptible without relying on color alone.
- Preserve **input sovereignty**. Users may seize, yank, redirect, cancel, undo, or continue an object at every phase. Effects may never delay state changes, steal focus, corrupt pointer capture, alter hit testing incorrectly, block controls, or force the user to wait.
- Verify every theme with an interaction-language matrix, representative cross-element reaction chains, material/scale/velocity variations, interruption at multiple phases, reduced-motion alternatives, muted operation, and Performance Mode.

Keep product-specific examples in the project's Compass seed or local memory. Treat each example as a required test case for the broader interaction law.

## Mandatory workflow

1. Before planning named project work, load `COMPASS.json`, its event history, current handoff, and publication ledger.
2. Reconcile new user requests into the narrowest correct category. Deduplicate semantically; link related items instead of creating wording variants.
3. Translate aspirational northpoints into measurable acceptance signals and add them to the active task checklist.
4. After meaningful work, update status, evidence, affected Compass entries, handoff, and cross-project catalog.
5. Export the changed project brain/checkpoint and publish it to connected Google Drive as a mandatory durable copy after meaningful work. Publish to other required targets too; File Library/ChatGPT Project storage is an additional chat-native convenience layer, not a substitute for Drive.
6. Never claim publication until the remote object was reread and its bytes or trustworthy provider digest were verified. Record failures and retry/fallback state truthfully.

Use `scripts/project_compass.py` to initialize, add, supersede, render, validate, record publication, and export. The Feature Foundry seed demonstrates project-specific living-world goals without contaminating universal policy.
