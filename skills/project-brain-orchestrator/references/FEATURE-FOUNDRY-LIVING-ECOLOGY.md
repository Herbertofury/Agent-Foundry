# Feature Foundry Living UI Ecology

**Registry version:** 3.5.5
**Verified:** 2026-08-04T12:32:00Z
**Review due:** 2026-11-04

This document is generated from the machine-readable living-ecology registry. It is a product contract and authoring specification, not a claim that the current application already implements every behavior.

## Northpoint

### One complete living world from potato hardware to cinematic hardware
Feature Foundry must preserve the same complete product, objects, cards, data, authoring power and theme identity on every supported machine while scaling only simulation and presentation fidelity. The interface should feel causally alive, intelligent and embodied at the efficient baseline, then grow into richer spatial, audio, physics and GPU-enhanced behavior as measured capability and user preference allow.

#### Non-negotiables

- No performance tier may hide cards, objects, data, tabs, authoring tools or supported workflows.
- No tier may reduce the correctness or quality of the user's actual task result.
- Every theme retains a recognizable material and interaction language at every tier.
- All speculative anticipation is visual or preparatory only and never commits state before the user action.
- Every effect is interruptible and user input always wins.
- GPU-enhanced modes are optional, capability-tested and paired with semantically equivalent fallbacks.
- Automatic adaptation is reversible, visible and overrideable by the user.

## Intent-aware anticipation

Prepare the world for the user's likely next action without moving the pointer, committing state, stealing focus or making the interface feel presumptuous.

### Signals

- pointer trajectory, velocity, acceleration and deceleration
- hover dwell and repeated approach/retreat
- coalesced and predicted pointer events when available
- pressure, tilt, twist and contact geometry for supported pen/touch devices
- drag payload type, apparent mass and current grab point
- keyboard focus direction and command history within the current task
- controller stick direction, trigger pressure and active navigation lane
- current workspace mode, selected tool, likely drop sockets and semantic action context

### Confidence bands

| Band | Range | Allowed behavior |
|---|---|---|
| `observe` | 0.00-0.39 | Collect short-lived local signals only; do not animate target preparation. |
| `hint` | 0.40-0.69 | Allow nearly imperceptible environmental readiness such as surface tension gathering, a sticker edge loosening or a target softly breathing. |
| `prepare` | 0.70-0.89 | Prewarm the likely transition/effect, reveal compatible sockets and prepare nearby materials without changing selection or data. |
| `strong-prepare` | 0.90-1.00 | Use the full authored anticipation pose, still without committing state; cancel on the next contradictory input sample. |

### Anticipation rules

- Predictions expire at the next confirmed pointer or navigation event.
- Use hysteresis so targets do not flicker when confidence crosses a boundary repeatedly.
- Never magnetically move the pointer or silently alter hit targets.
- Keep trajectory history local to the active interaction unless the user explicitly enables personalized learning.
- Anticipation must collapse in one frame when the user reverses direction, presses Escape, changes tool or starts another gesture.
- Repeated fast expert actions should reduce ceremony and prioritize speed.

## Ecology Director

Act as the authoritative conductor for semantic events, causal propagation, sensory budgets and stable settling across the entire living UI.

### World modes

- focused
- exploring
- playful
- authoring
- urgent
- background
- presentation

### Authoritative decision order

1. preserve input sovereignty and accessibility
2. commit the functional state change
3. select transition depth and world mode
4. resolve primary material response
5. traverse only eligible relationship and causal-field edges
6. enforce sensory and frame-time budgets
7. coordinate motion, deformation, light, shadow, audio, haptics and particles
8. record reversible causal history
9. settle or retain authored material memory

### Sensory and simulation budgets

- **Motion:** Limit simultaneous high-salience moving regions near active work.
- **Brightness:** Prevent competing flashes and keep status meaning readable without relying on color alone.
- **Particles:** Allocate by event importance and tier; never use particle count as the only signal.
- **Audio:** Limit concurrent voices, duck ambience around important cues and avoid repetitive samples.
- **Physics:** Bound awake bodies, contact depth, solver substeps and chain length without removing objects or data.
- **Causal Depth:** Default to local direct effects plus one or two meaningful propagated layers; deeper authored moments require cooldowns.

## Transition depth ladder

| Level | Mode | Purpose | Representative use |
|---:|---|---|---|
| 0 | **Instant / Focus** | Commit the new workspace immediately with only a static state cue or extremely short opacity/material confirmation. | No travel animation; the selected tab state, lighting and semantic label update immediately. |
| 1 | **Ambient Echo** | The destination is immediate while the world acknowledges it through a restrained environmental response. | Grass waves, water trembles, distant signage shifts, a faint light route travels or a small graffiti accent lands. |
| 2 | **Local Material Journey** | The touched tab, card or panel and its nearby material field transform while the larger workspace remains stable. | A card glides through a shallow water wake, peels into a sticker layer or sinks through soft liminal depth. |
| 3 | **Shared-Element Continuity** | Selected cards, objects, mascots and authored landmarks physically continue into the destination instead of disappearing and respawning. | A selected asset travels from the Vault into the World editor and becomes the same placed object. |
| 4 | **Workspace Recomposition** | Panels, architecture, terrain and environmental systems reorganize into the new workspace while preserving spatial identity and task continuity. | A room unfolds, drains, rotates, peels or reassembles around persistent cards and objects. |
| 5 | **Full World Traversal** | The user travels through a complete authored world transformation with camera, climate, architecture, audio, lighting and shared objects acting as one causal sequence. | The current environment floods into a Frutiger Aero transit channel, carries the selected object forward and emerges as the destination workspace. |

### Transition selection and adaptation

- global transition-depth preference
- per-theme maximum
- per-action override
- per-workspace override
- Auto mode driven by measured performance and current intent
- temporary Focus and Cinematic commands

- Repeated navigation within a short period automatically favors levels 0-2 unless the user pins a higher level.
- First entry, major milestones and presentation moments may use higher authored levels when allowed.
- The functional destination state is committed independently from visual duration so cancellation never loses work.
- Prewarm likely destination assets and shaders opportunistically without blocking the current action.
- Every level uses the active theme's own material and sonic grammar rather than a shared generic transition.

## Persistent world and material memory

### Content Age Patina
**Source:** Domain data such as last played, last updated, last edited, release age, installation age or user-selected date field.

- An unplayed game card slowly gathers theme-native age cues.
- A mod that has not been updated in a long time shows restrained material weathering without changing its factual update status.
- A recently refreshed asset appears clean, active or newly energized.

### Use and Handling Patina
**Source:** Optional local interaction history such as moves, opens, edits, grabs, collisions and authoring sessions.

- Frequently handled edges become subtly polished.
- Repeated sticker placement creates believable adhesive wear.
- A favorite object develops gentle theme-native signs of care rather than damage.

### World Event Memory
**Source:** Explicit project events, milestones, repairs, damage, mascot relationships and user-authored story state.

- A repaired crack remains as a tasteful seam.
- A mascot remembers a favorite resting object.
- A workspace milestone permanently unlocks an environmental detail.

### Memory controls

- Enable or disable each memory channel independently.
- Preview any date or usage intensity without committing.
- Reset one object, one property, one workspace or the entire world.
- Keep factual timestamps and status labels visible and unchanged by decorative patina.
- Export and import memory state with project provenance.

### Memory guardrails

- Patina must never obscure title, status, controls, accessibility contrast or task-critical imagery.
- Interaction history remains local and project-scoped unless the user explicitly exports it.
- Age and usage channels never silently change sorting, compatibility or update decisions.
- All derived wear is reversible and has a pristine reference.

## Semantic material intelligence

### Material properties

- mass, density, center of mass and scale
- softness, elasticity, plasticity and damping
- friction, adhesion, stickiness and peel strength
- wetness, absorbency, buoyancy and surface tension
- temperature, conductivity, emissive response and heat memory
- thickness, transparency, translucency and internal volume
- damage threshold, repair behavior and recovery curve
- theme reinterpretation, sound family and attention cost

### Material rules

- Material behavior is data-driven and editable rather than hardcoded per asset.
- The same object may receive a theme-specific material interpretation while retaining identity and user-authored overrides.
- Fallback tiers preserve the material story with cheaper motion, shading and audio rather than replacing it with a generic pulse.
- Generated material claims expose confidence and can be corrected independently.

## Spatial micro-audio

Make interactions feel physically located and materially believable while remaining quiet, optional and non-repetitive.

### Features

- theme-native material families for press, drag, scrape, peel, splash, impact, absorption, release, repair and settling
- screen/world-position panning with optional HRTF spatialization
- distance attenuation, occlusion, room tone and surface-dependent reflection
- procedural or multi-sample variation to prevent machine-gun repetition
- velocity, mass, pressure, contact area and material-driven timbre
- priority-based voice stealing and ambience ducking
- per-category volume, mute, preview, captions/text equivalents and complete audio-off operation
- AudioWorklet path for advanced synthesis with built-in-node or sample fallback

### Guardrails

- Never start sound before a required user gesture or violate platform autoplay policy.
- Do not use sound as the only confirmation or warning.
- Repeated expert actions compress or omit decorative sounds automatically.
- Focus mode and reduced sensory modes preserve meaning with minimal or no audio.

## Object relationships and social physics

### Relationship edge types

- attracts
- repels
- supports
- contains
- absorbs
- transfers-energy
- conducts
- illuminates
- stains
- wets
- dries
- charges
- shields
- awakens
- comforts
- frightens
- uses
- repairs
- breaks
- teaches
- follows

### Authoring

- Visual relationship graph with direction, strength, range, conditions, cooldowns and priorities.
- Conflict resolver for competing relations and material rules.
- Live sandbox that previews one edge or the entire local network.
- Mascot affordance editor for sitting, carrying, climbing, using, avoiding and sharing objects.
- Deterministic trace showing why every relationship fired or was suppressed.

### Guardrails

- Relationship chains are bounded by distance, semantic relevance, cost and authored stop conditions.
- No relationship may steal a grabbed object or override direct user control.
- Ambient relationship activity yields immediately to focused work.

## Theme-native AI presence

Let assistance inhabit the world without hiding what the AI knows, what it is proposing or what action will occur.

### Embodiments

- environmental guidance through theme-native light, water, signage, stickers, terminals, mascots or architecture
- spatial previews that point to the exact object, property, graph node or transition being discussed
- editable generated graphs, materials, behaviors and transitions instead of opaque one-click magic
- explanations and confidence attached to every inferred object property or automated authoring decision

### Truthfulness

- Every environmental cue has an equivalent explicit text/status representation.
- Suggestions are visually distinct from committed changes.
- The user sees the exact diff, affected entities and undo scope before destructive or broad actions.
- The AI never claims a world reaction, asset conversion or adapter succeeded when only a preview or fallback exists.

## Environmental data embodiment

### Examples

- A healthy workspace settles into stable balanced motion and lighting.
- A queue may accumulate as an authored conveyor, shelf, current or skyline while exact counts remain visible.
- A successful completion can restore, bloom, fill, illuminate or repair a local world element.
- An error creates a localized disturbance tied to the affected object instead of a global red flash.
- Storage pressure may crowd a vault shelf while exact storage metrics and actions remain explicit.
- Background processing animates a machine or environment only while real work is occurring.

### Rules

- Every metaphor is backed by a real state field and traceable data adapter.
- Ordinary labels, percentages, warnings and controls remain available.
- Decorative intensity scales with severity but never exaggerates or invents state.
- Data embodiments are theme-specific and author-editable.

## Living time and microclimates

### Systems

- per-workspace time-of-day and lighting state
- theme-native weather, airflow, humidity, water level, dust, fog, temperature and soundscape
- activity-generated microclimates around busy or idle regions
- seasonal, milestone and project-phase transformations
- rare authored events with semantic prerequisites and long cooldowns
- idle settling and gentle reawakening

### Controls

- real time, project time, authored timeline, frozen time or manual scrub
- per-workspace climate presets and rule graphs
- global intensity, accessibility and performance overrides
- deterministic seeds for replay and collaborative consistency

### Guardrails

- Climate never hides controls or changes data meaning.
- Rare events cannot repeat on short loops or interrupt focused work.
- All climate systems have low-cost equivalents and pause safely when inactive.

## Causal undo, replay, and inspection

### Architecture

- Event-sourced semantic command history with inverse transactions.
- Functional state rollback occurs immediately; visual reversal catches up without delaying control.
- Each causal record stores source event, rules, participants, parameters, deterministic seed, outputs and stop condition.
- Undo reverses propagated reactions in dependency order where physically appropriate.
- Replay supports step, scrub, slow motion, normal speed and stress speed.

### Tools

- causal DAG inspector
- why-did-this-react trace
- material state timeline
- input and pointer-capture debugger
- transition frame scrubber
- audio and haptic event lanes
- performance cost per causal branch
- recording export for bug reports and regression tests

### Guardrails

- Undo never depends on playing an animation to completion.
- Replays are deterministic unless the author explicitly chooses nondeterministic variation.
- The inspector can disable one effect layer without changing the underlying command result.

## Object behavior genome

### Fields

- identity and provenance
- semantic parts and hierarchy
- materials and confidence
- mass, center of mass and collision proxies
- grabbable regions, handles, sockets and snap planes
- joints, flexible regions and detachable parts
- interaction verbs and affordance conditions
- theme-specific behavior variants
- audio, lighting, particle and haptic families
- damage, wear, repair and recovery states
- chronological, interaction and authored memory channels
- mascot relationships and safe-use lanes
- attention cost and allowed propagation depth
- performance variants and fallback representation
- user overrides, locked fields and uncertainty

### Generation rules

- Generate editable proposals rather than opaque final behavior.
- Keep geometry, material, affordance, physics and theme in separately replaceable nodes.
- Allow the user to demonstrate an interaction and convert it into an editable rule graph.
- Preserve approved fields when another field is regenerated.
- Export the genome with the object and validate it on reimport.

## Ecology Authoring Studio

Authoring capability must continuously expand because Feature Foundry exists to help users create, inspect, improve and reuse sophisticated features rather than merely consume presets.

### Transition Choreographer

- level 0-5 transition designer
- shared-element mapper
- world topology editor
- camera and climate lanes
- per-theme variants
- interrupt/cancel authoring
- repeat-navigation behavior

### Interaction Recorder

- record a gesture or object interaction
- infer editable intent and causal rules
- clean curves
- map pressure/tilt/touch
- generate test cases

### Material Laboratory

- material property editor
- stress test
- absorption and peel lab
- damage/repair editor
- theme reinterpretation preview
- potato fallback preview

### Ecology Graph

- semantic event graph
- causal fields
- relationship edges
- attention budgets
- cooldowns
- stop conditions
- director arbitration

### Spatial Audio Lab

- material sound families
- procedural layers
- position/occlusion preview
- voice budget
- ducking
- mute and accessibility equivalents

### World Memory Editor

- age patina mapping
- usage patina mapping
- milestone memory
- pristine references
- time scrub
- selective reset

### Ai Presence Designer

- theme embodiment
- suggestion vs committed-state styling
- confidence display
- action diffs
- accessible text equivalents

### Device And Tier Simulator

- mouse/touch/pen/controller simulation
- reduced-motion preview
- potato/balanced/high/ultra simulation
- frame and input budgets
- GPU unavailable fallback

### Causal Debugger

- deterministic replay
- DAG trace
- frame scrub
- layer isolation
- event coalescing view
- cost heatmap
- automated regression capture

### Optimization Compiler

- batching and atlas suggestions
- shader/material simplification
- worker partitioning
- effect equivalence checks
- asset prewarm plan
- automatic tier variants

### Authoring Version Control

- hot reload
- branch and compare
- visual diff
- presets and inheritance
- rollback
- shareable packages
- schema migration

### Extension Sdk

- documented schemas
- custom material nodes
- custom adapters
- custom transition types
- custom authoring panels
- validation hooks
- safe sandboxing

### AI-assisted authoring

- Natural-language authoring creates editable nodes, curves and test cases, not hidden proprietary behavior.
- The assistant proposes optimizations and shows the visual/semantic difference before applying them.
- The assistant continuously identifies missing authoring tools from repeated manual work and records proposals in the Project Compass.
- Generated tools must integrate with undo, versioning, accessibility, profiling and export.

## Cross-device embodiment

### Capabilities

- mouse hover, buttons, wheel and high-frequency movement
- touch contact area, multi-touch stretch/twist/squeeze and gesture cancellation
- pen pressure, tilt, altitude, azimuth, twist and barrel controls
- keyboard spatial navigation, commands and repeat behavior
- controller sticks, triggers, buttons and optional haptics
- device orientation and motion for opt-in subtle parallax or world response
- future XR/spatial input as an enhancement layer

### Rules

- Detect capabilities at runtime and never infer them from a product name alone.
- No core feature or authoring action may require a particular device.
- Every device-specific enhancement has keyboard and accessible equivalents.
- Sensor and orientation use is opt-in, local and easy to disable.
- Haptics are restrained, theme-native and never the only signal.

## Performance capability ladder

Offer Auto plus explicit user-pinned levels. Auto uses measured frame time, interaction latency, long-animation-frame attribution, thermal/power hints when available, current theme cost and recent stability rather than trusting a static hardware label.

| Tier | Target | Behavior | GPU path |
|---|---|---|---|
| **Efficient** | Potato-class and battery-sensitive devices | Full data, objects, cards, tabs and authoring tools; theme-native CSS/WAAPI/Canvas responses, low-cost shared-element transitions, static or short material cues, event-driven settled physics and compact audio. | Not required |
| **Balanced** | Default broad hardware | Richer local deformation, particles, shadows, material memory, spatial audio and transition levels 0-3 with measured budgets. | WebGL/Canvas acceleration when available |
| **High** | Strong integrated or discrete graphics | Workspace recomposition, higher-resolution materials, more active relationships, advanced audio, richer soft-body/fluid approximations and transition levels 0-4. | Accelerated path preferred |
| **Ultra** | High-end hardware with stable measured headroom | WebGPU-enhanced compute, dense but bounded particles, fluid/gel/paint simulation, volumetric lighting, richer climate and full transition levels 0-5. | Opt-in WebGPU or strongest supported GPU path |
| **Cinematic Lab** | Explicit authoring, capture and presentation sessions | Maximum authored fidelity, offline precomputation where useful, deterministic capture and expensive debug overlays; never silently enabled for routine work. | Explicit opt-in |

### Adaptive controller

- Measure frame time, input-to-paint latency, long animation frames, render cost and dropped audio/physics work per subsystem.
- Use hysteresis and cooldowns so quality does not oscillate.
- Lower the most expensive effect dimension first instead of globally flattening the world.
- Upgrade gradually after sustained headroom and prewarm resources before switching.
- Show the active tier, reason for adaptation and exact differences; allow pinning and per-system overrides.
- Respect reduced motion, reduced transparency, reduced data and user-defined sensory settings independently from hardware tier.

### Implementation patterns

- one authoritative frame scheduler and semantic event bus
- event-driven simulation and sleeping settled bodies rather than per-object endless loops
- fixed-step physics with interpolated rendering and bounded catch-up
- workers and OffscreenCanvas for eligible simulation/render preparation
- batched draw calls, instancing, texture atlases and compressed textures
- shader and transition prewarming based on likely intent
- pooled particles and audio voices
- transform/opacity-first DOM animation and scoped view transitions
- incremental authoring recompilation and cached deterministic derivatives
- quality variants generated by the authoring compiler rather than hand-maintained forks

### Hard performance guardrails

- Never use viewport culling, hidden-card removal, quantity caps, data truncation or inaccessible deferred content as a performance shortcut.
- Never remove features, authoring tools, object relationships or supported workflows at lower tiers.
- Never lower export, inference or task-result correctness to make the UI faster.
- Only visual/audio/physics fidelity, resolution, sample count, simulation substeps and transition depth may scale.
- All objects remain selectable and their state remains fully available even when settled simulation is asleep.
- A fallback must preserve semantic timing and theme identity, not become a generic fade or pulse.

## Acceptance tests

- **`anticipation-reversal`:** Approach a target rapidly, reverse before contact and confirm every speculative cue cancels within one frame without selection or hit-target change.
- **`anticipation-device-parity`:** Repeat an authored interaction with mouse, touch, pen, keyboard and controller; each uses available signals while reaching the same functional result.
- **`director-causal-trace`:** For a card placement, inspect the director trace and verify one source event, bounded participants, budgets, stop condition and deterministic replay.
- **`transition-level-matrix`:** Execute the same tab change at levels 0 through 5 and verify increasing world depth without changing destination state, focus, selection or data.
- **`transition-repeat-compression`:** Switch rapidly between tabs and verify Auto reduces ceremony while a pinned level remains honored.
- **`shared-object-continuity`:** Move a selected asset between Asset Vault and World and verify identity, selection, state, undo and spatial continuity persist.
- **`spatial-audio-material`:** Trigger the same impact with different mass, velocity, material and screen position; verify location and timbre vary while audio-off retains equivalent visible feedback.
- **`relationship-bounds`:** Create a dense local relationship graph and verify only eligible edges fire, chains stop, grabbed objects remain controlled and focus mode suppresses ambient activity.
- **`ai-truthfulness`:** Request an AI-authored behavior and verify suggestion/commit states, confidence, editable graph, exact diff, undo and accessible text are all present.
- **`data-metaphor-truth`:** Change a real queue or error state and verify the environment matches exact underlying data while labels and controls remain explicit.
- **`microclimate-determinism`:** Replay a seeded workspace timeline twice and verify identical climate events, cooldowns and settling.
- **`physical-undo`:** Undo an interaction during its reaction; confirm logical rollback is immediate and every propagated visual/audio state reverses or settles correctly.
- **`patina-channels`:** Enable age patina only, usage patina only, both and neither; verify separate provenance, reset, preview and unchanged factual status.
- **`behavior-genome-roundtrip`:** Export and reimport an object with genome, theme variants, memory and user locks; verify no approved field or lineage is lost.
- **`authoring-to-runtime`:** Record an interaction, convert it to an editable graph, test across themes and tiers, package it and verify the production runtime uses the authored result.
- **`potato-feature-parity`:** Run the efficient tier with a full large workspace and verify every card, object, authoring tool, relationship and workflow remains available without viewport caps or quantity loss.
- **`adaptive-quality-stability`:** Inject sustained frame pressure and verify the controller lowers the responsible effect dimension with hysteresis, reports why, preserves semantics and later restores quality after stable headroom.
- **`gpu-fallback-equivalence`:** Disable WebGPU/GPU acceleration and verify fluid, gel, paint, climate and transitions retain recognizable theme-native equivalents and exact functional state.
- **`reduced-motion-equivalence`:** Enable reduced motion/transparency and verify state, causality and theme identity remain understandable through replacement cues rather than merely slower animation.

## Official technical sources

- **pointer-events-3** — https://www.w3.org/TR/pointerevents3/ — predicted events, coalesced events, pressure, tilt, twist, contact geometry
- **view-transitions-2** — https://drafts.csswg.org/css-view-transitions-2/ — scoped transitions, nested groups, transition types, shared-element continuity, cross-document transitions
- **web-audio-1-1** — https://www.w3.org/TR/webaudio-1.1/ — audio graphs, AudioWorklet, spatial processing, low-latency synthesis
- **webgpu** — https://www.w3.org/TR/webgpu/ — GPU rendering, compute, advanced opt-in effects
- **long-animation-frames** — https://www.w3.org/TR/long-animation-frames/ — jank attribution, adaptive quality, main-thread congestion
- **event-timing** — https://www.w3.org/TR/event-timing/ — interaction latency, input-to-paint measurement
- **media-queries-5** — https://www.w3.org/TR/mediaqueries-5/ — reduced motion, reduced transparency, reduced data, contrast preferences
- **offscreen-canvas** — https://html.spec.whatwg.org/multipage/canvas.html#the-offscreencanvas-interface — worker rendering, off-main-thread preparation
- **gamepad** — https://www.w3.org/TR/gamepad/ — controller input, optional haptics
- **device-orientation** — https://www.w3.org/TR/orientation-event/ — opt-in orientation, motion-responsive environments
- **webxr** — https://www.w3.org/TR/webxr/ — future spatial input enhancement
