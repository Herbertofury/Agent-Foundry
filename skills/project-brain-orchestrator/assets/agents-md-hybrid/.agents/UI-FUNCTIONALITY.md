# FUNCTIONAL UI AND CONTEXTUAL ACTIONS

## Functional UI contract: no fake controls or feature theater

Every visible control is a promise and must perform its stated job. Navigation must open its real destination; active styling alone is dead UI.

- Never ship no-op handlers, placeholders, `TODO` or `Coming soon` flows, demo-only behavior, hardcoded results, fake progress or success, console-only actions, empty modals, decorative controls, or disconnected UI.
- Every primary or secondary navigation control must open the distinct real destination it names, with the correct tools, data, selection, and active state. Verify direct entry, navigation history, reload, and restart where supported. Styling changes, logs, toasts, renamed headers, empty shells, or leaving the same view visible do not count.
- Wire every path end-to-end: **action -> validation -> real domain/service logic -> required storage/backend/provider -> observable result -> persistence or refresh where applicable**. A panel, button, or firing handler is not completion.
- Keep a ledger for each control: **control -> promise -> handler -> owner -> result -> evidence**. Unmapped fails.
- Use every affected control in the production build. Verify success, truthful failure feedback, repeat use, cancel/undo, state persistence, and relevant logs.
- Never show success before completion or swallow failure. Build or repair missing backend/dependency wiring; never leave pretend UI.
- Before closeout, inventory and exercise every actionable control in scope. One dead, misleading, disconnected, or partial control fails the task.

## Theme-native interaction ecology

For any living, highly themed, spatial, or game-like interface, treat interaction feedback as a coherent world system rather than isolated hover or click animation.

- Define a distinct per-theme interaction grammar for press, hold, release, drag, reorder, resize, drop, placement, collision, transfer, absorption/ejection or equivalent transformation, cancel/undo, keyboard, controller, and assistive activation.
- Propagate meaningful actions through a bounded reaction chain across the touched element and only the relevant nearby UI, objects, lighting, sound, particles, mascots, or scenery. Reactions must be theme-native and material-, scale-, velocity-, direction-, and context-aware; never reuse a generic pulse or particle clip as proof.
- Make feedback subtle but unmistakable: it must not obscure work, yet the theme's tactile identity should be obvious without relying on color.
- User input always wins. Effects must be immediately interruptible and may never delay state changes, steal focus, corrupt pointer capture, block controls, alter hit testing incorrectly, or prevent grab, cancel, undo, redirect, keyboard, controller, or assistive operation.
- Verify an interaction-language matrix and representative cause-and-effect chains for every theme in the real runtime, including reduced-motion, muted, Performance Mode, and interruption-at-every-phase tests.
- Model living feedback as a bounded causal world: anticipation, contact, follow-through, material memory/recovery, cross-modal timing, salience/attention budgets, semantic cooldowns, and stable settling must arise from one traceable event rather than unrelated clips. Rare moments must be contextual and non-repeating.
- For imported image/GIF/video/3D/Blender objects, preserve immutable originals and use a reversible derivation graph with visible uncertainty, editable masks/parts/depth/materials/pivots/sockets/colliders/rigs/affordances, progressive quality lanes, and the simplest truthful representation. Never hide hallucinated geometry or treat an inference as verified fact.

## Contextual action fidelity: no generic or half-complete destinations

- A contextual action must complete its exact promise. A control that claims to open, show, continue, guide, locate, download, inspect, or edit something may not land on a generic home screen, root view, search page, unrelated tab, empty state, or leave the user to finish the navigation manually.
- Resolve and preserve the exact destination state required by the current context, including the target entity, workflow step, route, selection, coordinates or identifier, viewport, tab, version, filters, and authorization state as applicable.
- If the underlying platform cannot deep-link directly, implement the bridge, route state, selection transfer, generated link, or deterministic navigation sequence needed to land on and visibly identify the exact target. Never present a generic destination as a working implementation.
- Exercise every relevant contextual path from the production UI and confirm the final visible state matches the initiating context. If the user must search, reselect, infer, translate, or manually finish what the control promised, the feature is incomplete.
