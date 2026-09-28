# Bert's Cross-Chat Project Database

**Generated:** 2026-08-02  
**Purpose:** Recover, de-duplicate, and preserve the projects, versions, artifacts, plans, and open work found across available prior-chat context, uploaded files, File Library records, checklists, validation reports, and the current conversation.

> This is a recovery database, not a claim that every historical chat was accessible. Items are labeled by evidence strength. Nothing should be deleted or replaced merely because a newer artifact exists; preserve lineage until the canonical repository and latest-good state are verified.

## Status legend

- **ACTIVE** — current work or a current implementation directive exists.
- **VALIDATED ARTIFACT** — a packaged artifact passed the stated automated checks; live target testing may still be outstanding.
- **SPEC / PLAN** — substantial requirements or architecture exist, but implementation is not proven.
- **RESEARCH BASE** — reusable research, not necessarily a shipping product.
- **PRECURSOR / MERGED** — likely absorbed into a larger project; preserve until confirmed.
- **BLOCKED / NEEDS LIVE TEST** — automated or synthetic proof exists, but the intended real client/runtime has not been verified.
- **UNRESOLVED IDENTITY** — artifact found, but its project relationship or canonical source is unclear.

## Confidence legend

- **High** — exact artifact, version marker, validation report, or repository path recovered.
- **Medium** — repeated prior-chat context or strong artifact association, but canonical source was not opened here.
- **Low** — partial evidence only; do not mutate or discard anything based on it.

---

# 1. Executive project dashboard

| ID | Project / family | Current recovered state | Latest known version or artifact | Confidence | Immediate continuity action |
|---|---|---|---|---|---|
| PRJ-001 | Project Compass Orchestrator / project second brain | ACTIVE | Skill v3.3.0, artifact-library storage manager, master project/version catalog, portable AGENTS bundle, project-memory and cross-chat artifact reconciliation | High | Keep installed skill and portable bundle synchronized; export after every policy or memory-system change. |
| PRJ-002 | Feature Foundry | ACTIVE, major production rebuild | V11 production data platform and living-world directive; V11 database bundle validated | High | Locate the canonical app repository and reconcile it against V11 before any coding. |
| PRJ-003 | GameSync platform | ACTIVE, multiple hosts | Opera extension, extension-v2, desktop app; theme system and several game/runtime subprojects | High | Preserve the three host roots and make one host/version/parity ledger. |
| PRJ-004 | Aesthetic Media Companion / Living Room platform | PRECURSOR / MERGED | `master-living-room-aesthetic-plan-v3.md` | Medium | Treat as a Feature Foundry predecessor unless a separate canonical repo proves otherwise. |
| PRJ-005 | Mascot / Screenmate platform | ACTIVE umbrella | Shimeji engine, ACS engine, mascot runtime, desktop build, research base | High | Resolve which repository currently owns the shared mascot core. |
| PRJ-006 | ACS Agent parity runtime | SPEC / ACTIVE implementation track | `acs-agent-parity-checklist-generalized-v3.md` | High | Audit the current runtime against the checklist before claiming classic Microsoft Agent parity. |
| PRJ-007 | PF Magic Petz runtime integration | ACTIVE GameSync/Mascot subproject | `gamesync_petz_build_checklist.md`; PF Magic source path known | Medium | Keep one shared Petz core, then roll out GameSync v1 → v2 → desktop. |
| PRJ-008 | Mascot Games / sports and Golf flagship | ACTIVE design/implementation track | `mascotgames_master_agent_ordered_wxt_react_vite_v2_aligned_playable_contract_glorious_sports_golf_flagship.md` | Medium | Reconcile against current mascot repository and verify real playable flows. |
| PRJ-009 | Bert's Skill Atlas / Skill Guide | ACTIVE RuneLite project | QA Cockpit after Unified Cockpit; earlier Master plugin README recovered | Medium | Find the newest ZIP and repository, then record its hash and build status. |
| PRJ-010 | RuneLite FlipForge / Farm Material Ranker / No-Hitch / 117HD family | ACTIVE, release blocker | Multiple master prompts; known-good hitchless RuneLite JAR identity; Farm Material Ranker v1.1.0 | Medium | Prove external plugins load in the actual Jagex-launched client and persist after restart. |
| PRJ-011 | The Sims 4 Accelerator | SPEC / SCAFFOLD | `TS4_ACCELERATOR_AGENT_PLAN.md`; starter workspace README | High | Benchmark the exact game/mod setup before deeper hooks; preserve the real Mods folder. |
| PRJ-012 | Sims 4 native DX11 overlay mod | SPEC / possibly related to Accelerator | Native C++/DX11/Dear ImGui architecture prompt | Medium | Decide whether this is a TS4 Accelerator module or a separate repo before implementation. |
| PRJ-013 | Money App / AI Monetization Station | SPEC / PLAN | `money_app_plan_v38_no_meta_prompts.md` | Medium | Locate canonical plan and implementation repo; separate real working rooms from aspirational modules. |
| PRJ-014 | Grim Dawn Cairn Codex | ARTIFACT PRESENT | `Grim_Dawn_Cairn_Codex_Ultimate_v6_1.html` | Medium | Open the latest HTML, verify all navigation/state in-browser, and record a hash. |
| PRJ-015 | Bethesda Plugin Info for MO2 | VALIDATED ARTIFACT, live test pending | v1.5.3 shared drag/drop correction; v1.5.0 full validation available | High | Install in exact Windows MO2 and verify dedicated column, tooltips, warnings, categories, drag/drop, DPI, and restart. |
| PRJ-016 | Bethesda Creations Version Tracker for MO2 | VALIDATED ARTIFACT, live test pending | v2.4.3 shared drag/drop correction | High | Install in exact Windows MO2 and verify migration, metadata, conflicts, column behavior, and restart. |
| PRJ-017 | MO2 Image Column / MO2R image automation | ACTIVE, corrected build | Image Column v1.4.12; AI Automation Master Prompt | High | Verify v1.4.12 live with the complete plugin stack; do not regress image identity or drag/drop behavior. |
| PRJ-018 | MO2 Drag-and-Drop Line Restorer | VALIDATED ARTIFACT, live visual test pending | v1.1.0 | High | Run final visual/target smoke test in MO2 2.5.3 beta 12 with active theme and plugins. |
| PRJ-019 | MO2 Performance Accelerator | ACTIVE / corrected after crash | v4.0.1 | High | Replace v4.0.0, then live-test startup, drag, filtering, viewport restoration, and shutdown in Windows MO2. |
| PRJ-020 | Master Desktop Pet Research | RESEARCH BASE | Consolidated master containing v10, v14, v9, and v7 material | High | Append future verified research to the master rather than creating drifting numbered copies. |
| PRJ-021 | GX Slim | UNRESOLVED IDENTITY | `GX-Slim-1.0.0-FULL.zip`, SHA-256 sidecar recovered | Low | Find the ZIP/README and identify purpose, source repo, validation, and relationship to other projects. |
| PRJ-022 | Feral Unified Native Base | UNRESOLVED / Feature Foundry-generated base | `Feral_Unified_Native_Base.zip` | Medium | Determine whether this is a standalone product base or a generated Feature Foundry starter; validation was not run. |
| PRJ-023 | Feature Foundry Portable Feature Starter | GENERATED STARTER, not shippable | v0.1.0 starter ZIP | High | Keep as a template; its generated validation scenarios were not run and report `shippable: false`. |
| PRJ-024 | MO2 Drag/Column Compatibility Pack | VALIDATED COMPATIBILITY WORK | Image Column 1.4.12 + Bethesda Plugin Info 1.5.3 + Version Tracker 2.4.3 | High | Treat as a coordinated compatibility release and live-test all three together. |

---

# 2. Project relationship map

```text
Project Compass Orchestrator / Second Brain
└── governs and exports continuity records for every project below

Feature Foundry
├── absorbs or supersedes Aesthetic Media Companion / Living Room plans
├── authors and exports themes/features to GameSync v1, GameSync v2, desktop, and future hosts
├── consumes Mascot, object, weather, soundtrack, overlay, and portable-feature systems
├── contains Aesthetic Explorer, Mixer, Asset Vault, Room Studio, Object Studio, Theme Studio
├── has generated starter bases such as Feature Foundry Portable Feature Starter
└── may have generated or influenced Feral Unified Native Base

GameSync
├── Opera extension (v1)
├── extension-v2
├── desktop app
├── living theme runtime and Theme Studio integration
├── game/mod search and source-finder subsystem
├── PF Magic Petz runtime integration
└── HyperBowl original reconstruction

Mascot / Screenmate platform
├── Shimeji-compatible engine
├── ACS / Microsoft Agent compatibility runtime
├── PF Magic Petz integration
├── Mascot Games / sports / Golf
├── browser extension runtime
└── future desktop runtime

RuneLite family
├── Bert's Skill Atlas / Skill Guide
├── FlipForge / FlipFore OSRS
├── Farm Material Ranker
├── No-Hitch RuneLite launcher/runtime
└── 117HD / RLHD integration track

MO2 plugin family
├── Bethesda Plugin Info
├── Bethesda Creations Version Tracker
├── Image Column / MO2R image automation
├── Drag-and-Drop Line Restorer
├── Performance Accelerator
└── coordinated drag/drop compatibility pack

Sims 4 family
├── TS4 Accelerator
└── native DX11 / Dear ImGui overlay track (relationship not yet resolved)
```

---

# 3. Detailed project records

## PRJ-001 — Project Compass Orchestrator / Cross-Chat Second Brain

**Status:** ACTIVE  
**Confidence:** High  
**Purpose:** Apply the full AGENTS execution contract across chats and agents, preserve project identity and progress, remember sourced research, prevent accidental restarts, and export a portable Codex/agent bundle.

### Latest recovered state

- Current-chat release: **v3.3.0 — Artifact Library and Storage Manager**.
- Trigger phrases include `agent`, `agent:`, direct agent requests, and substantive project work.
- Maintains all-in-one and modular AGENTS forms.
- Adds project-owned `.agents-memory/`, a durable cross-project catalog and Markdown database, an organized artifact-library vault, storage warnings, hash-proven duplicate cleanup, reversible quarantine, project bundle folders, identity checks, handoffs, research memory, artifact reconciliation, controlled learning, anti-poisoning, and export tools.
- Known handoff artifacts:
  - `skill.zip`
  - `AGENTS-workflow-bundle.zip`
  - `AGENTS-all-in-one.md`
  - `AGENTS-modular.md`
  - `Feature-Foundry-Project-Brain.zip`
  - `USER-PROJECTS-DATABASE.md`
  - `project-catalog.json` and portable catalog ZIP
  - `library-catalog.json`, `LIBRARY-DATABASE.md`, organized project bundles, and portable library catalog ZIP

### Preservation rules

- Installed skill packages do not silently update themselves; regenerate and reinstall after changes.
- Repository/project memory is separate from the installed skill.
- Never claim cross-chat persistence unless a durable store accepted and reread the update.
- Always preserve version lineage when same-name artifacts are replaced.

### Open work

- Keep the master project and artifact-library catalogs synchronized after every checkpoint, artifact reconciliation, rename, merge, version change, cleanup, or bundle export.
- Revalidate ambiguous latest-version claims before promotion and preserve every prior version.
- Export the catalog whenever the live durable store cannot be shared with another chat or agent.

---

## PRJ-002 — Feature Foundry

**Status:** ACTIVE — production application not yet proven complete  
**Confidence:** High  
**Aliases:** Theme Home, Theme Lab, living aesthetic worlds, Feature Foundry Theme Studio

### Mission

A professional, deeply moddable authoring application for living theme worlds, UI skins, rooms, objects, weather, time, soundtracks, UI sounds, mascots, interactions, assets, research, mixing, packaging, and exports to multiple hosts.

### Current canonical document

- `feature-foundry-aesthetic-worlds-codex-master-directive.md`
- Internal revision marker: **V11**, researched 2026-08-02.
- The V11 directive calls itself the single canonical implementation contract.
- The final implementation directive says the standalone HTML is not the finished product and the real application must implement and persist the workflows.

### Version and artifact lineage

1. Early standalone living-world HTML concept.
2. V4 standalone HTML.
3. V7 HTML.
4. V8 HTML.
5. V9 HTML.
6. V10 production-stack directive.
7. **V11 production data platform and bundle reference**.

Current V11 artifacts recovered:

- `feature-foundry-aesthetic-worlds-codex-master-directive.md`
- `feature-foundry-codex-final-implementation-directive-v11.md`
- `feature-foundry-aesthetic-world-guide-v11.md`
- `feature-foundry-living-world-prototype-v11-bundle-reference.html`
- `V11-VALIDATION-REPORT.md`
- Object Atlas SQLite database
- Theme Worlds SQLite database

### V11 validation facts

The V11 validation report records **61 passed, 0 failed** for the supplied data/schema bundle, including:

- 178 object archetypes and families
- 52 materials
- 178 behavior profiles
- 12 affordances
- 17 themes and versions
- 72 districts
- 17 room presets
- 51 weather profiles
- 17 soundtrack profiles
- 17 mascot profiles
- 170 object-pool members
- database integrity, foreign keys, FTS, RTree, cross-database references, manifest hashes

**Critical boundary:** the report explicitly does **not** claim that final artwork, production runtime integration, Blender conversion, provider authentication, or the complete app is implemented.

### Approved theme set

V11 preserves **17 full themes**:

1. Frutiger Aero
2. Utopian Scholastic
3. Wacky Pomo
4. Contempo Eclectic
5. Vaporwave
6. Neo-Y2K
7. Liminal Leisure
8. Diner Kitsch
9. Cassette Futurism
10. Googie Kitsch
11. French Synthpop
12. Memphis
13. Ethereal CGI
14. Divine Machinery
15. Dark Fantasy
16. Atomic Age
17. Jazz / Solo Jazz

The broader aesthetics guide is research-only and must not silently promote every entry to a shipping theme.

### Major subsystems

- Professional application surface
- Living left/right worlds
- Focused Full UI
- Performance Mode
- Theme Studio
- Aesthetic Explorer and Mixer
- Asset Vault
- World Studio and Room Studio
- Object Studio and semantic affordance/rig system
- Weather, time, lighting, soundtrack, UI sound, mascot and interaction studios
- Package/export system
- Object Atlas and Theme Worlds databases
- Opera-style multi-provider Music Hub
- GameSync migration and host adapters

### Current failure/repair focus

- Room Studio is currently documented as an unconvincing mostly empty scene with pasted objects and weak editing tools.
- Aesthetic Explorer is documented as generic, flat, and not a real mixing/research workflow.
- Asset Vault is documented as an empty or underbuilt drawer rather than a real asset operating system.
- The desired Aesthetic Explorer/media base may be a branch before v23; do not assume the numerically highest old branch is the latest-good base.

### Canonical repository

**Not yet recovered in this chat.** Do not edit the prototypes or initialize a new project in their place. Locate the existing Feature Foundry repo/worktree/branch first.

### Related artifacts

- `ui-theme-agent-spec.md` and historical v48/v49/v51 variants
- `FEATURE_FOUNDRY_CODEX_MASTER_PROMPT.md`
- `LIVE_DEVELOPMENT_WORKBENCH.md`
- `TECH_STACK_PHYSICS_RENDERING_ATLAS.md`
- `Feature_Foundry_Portable_Feature_Starter.zip`
- visual targets for Frutiger Aero, Wacky Pomo, and Neo-Y2K

### Immediate next checkpoint

1. Locate canonical repo and branch.
2. Hash and import the V11 bundle without overwriting newer repository data.
3. Reproduce the current Room Studio/Explorer/Vault failures.
4. Build a migration ledger from current implementation to V11.
5. Establish exact production/runtime proof rather than relying on database validation or HTML prototypes.

---

## PRJ-003 — GameSync Platform

**Status:** ACTIVE  
**Confidence:** High

### Known canonical roots

- Opera/v1 extension: `C:\Users\Owner\Desktop\GameSync\opera-extension`
- v2 extension: `C:\Users\Owner\Desktop\GameSync\apps\extension-v2`
- Desktop app: `C:\Users\Owner\Desktop\GameSync\apps\desktop`

### Main tracks

#### A. Core GameSync product and theme runtime

The current theme checklist documents:

- original 16-theme registration and world packs
- theme engine, interactions, sounds, object ecology, collectibles, weather, timeflow, media surfaces, library interactions, districts, and Spotify architecture
- v1 and v2 parity work
- Feature Foundry editors and portable theme packages

Treat the checklist as claimed implementation history, not proof that every feature works in the current loaded build. The newer Feature Foundry V11 contract supersedes the theme catalogue with 17 themes and stronger production requirements.

#### B. Search, source finder, and entity resolution

Recovered goals:

- game and mod title search
- source discovery
- strong identity and anti-normalization matching
- Typesense and Meilisearch exploration
- SQL-centered extension data
- direct source links
- append-only upgrade behavior

Known hotspots from prior work:

- `background/background.js`
- title normalization and fuzzy match functions
- `src/modsources/discovery.js`
- AutoNotes
- FolderMonitor
- ModAuthors

Known artifacts:

- `checklist-updated.md`
- `opera-extension-analyzed.zip`

#### C. HyperBowl original reconstruction

- Original assets are expected under `C:\Users\Owner\Desktop\GameSync\hyperbowl\HYPERBOWL ORGINAL`.
- Original assets are read-only reference material.
- Unity extracts are not the canonical behavior source.
- Control work should follow `HYPERBOWL_ORIGINAL_RECONSTRUCTION_MASTER.md` when found.

#### D. Petz / PF Magic runtime

See PRJ-007.

### Preservation risks

- Three hosts can drift.
- Feature Foundry theme exports and GameSync theme implementations can diverge.
- Old checked boxes may not match current runtime.
- Generated or copied extensions can be mistaken for canonical source.

### Immediate next checkpoint

Create a host matrix:

`feature/version -> Opera v1 -> extension-v2 -> desktop -> Feature Foundry source -> evidence -> parity gap`

---

## PRJ-004 — Aesthetic Media Companion / Living Room Platform

**Status:** PRECURSOR / MERGED candidate  
**Confidence:** Medium

### Latest known plan

- `master-living-room-aesthetic-plan-v3.md`

### Scope

- room runtime
- asset vault
- aesthetic catalogue/explorer
- media companion
- mystery/progression
- world orchestration

### Recovered technical direction

- Rapier2D
- PixiJS v8
- ECS
- Web Animations + GSAP
- local-first persistence with JSON export/import

### Relationship decision

Most of this scope now appears inside Feature Foundry. Preserve the v3 plan as source history and research. Do not maintain a parallel implementation unless a distinct repository and product identity are confirmed.

---

## PRJ-005 — Mascot / Screenmate Platform

**Status:** ACTIVE umbrella  
**Confidence:** High

### Purpose

A shared browser/desktop mascot runtime combining Shimeji-style packs, classic ACS agents, screenmates, desktop companions, Petz-style creatures, overlays, voices, interactions, games, and future Feature Foundry/GameSync integrations.

### Known systems

- Real Shimeji pack ingestion
- XML action graphs
- anchors, borders, frame durations, velocities and hotspots
- carry/throw behavior
- wall and ceiling traversal
- graph-driven animation reuse
- WXT + React + Vite migration track
- browser extension and future desktop build
- ACS compatibility runtime
- Petz runtime integration
- mascot games and sports

### Latest broad implementation artifact

- `mascotgames_master_agent_ordered_wxt_react_vite_v2_aligned_playable_contract_glorious_sports_golf_flagship.md`

### Critical preservation rule

Do not replace authentic pack/state/action semantics with a generic sprite animation system. Preserve current smooth dragging, browser safety, existing pack conversion, and working runtime behavior while adding parity.

### Canonical repository

Not recovered. Resolve before any new scaffold.

---

## PRJ-006 — ACS Agent Parity Runtime

**Status:** SPEC / ACTIVE track  
**Confidence:** High

### Latest artifact

- `acs-agent-parity-checklist-generalized-v3.md`

### Mission

Restore classic Microsoft Agent, Office Assistant, MASH/TMAFE, and Double Agent behavior across the whole mascot runtime without regressing modern browser improvements.

### Existing foundation documented in the checklist

- ACS parser
- ACS-to-runtime conversion
- spritesheets and audio export
- `pack.acsAgent` metadata
- state and return maps
- voice and balloon metadata
- queued playback, movement, speech, dragging and idle transitions
- Shimeji compatibility

### Primary gaps documented

- true `GestureAt()` direction selection
- true `Think()` path
- request objects and queue semantics such as Wait/Interrupt/StopAll/Get
- classic popup/Commands/CommandsWindow/Voice Commands Window parity
- speech recognition/voice grammar
- deeper state semantics
- lip-sync/audio timing
- local AI, local STT/TTS and voice switching
- inspector, parity scoring and authoring tools

### Version note

Multiple same-name v3 copies exist. The latest content-rich version includes Phases 0–6, local packaged intelligence/voices, page-element attachment, browser/app reactions, and desktop readiness. Preserve all copies until their content hashes are reconciled.

---

## PRJ-007 — PF Magic Petz Runtime Integration

**Status:** ACTIVE subproject  
**Confidence:** Medium

### Known source

- `C:\Users\Owner\Desktop\GameSync\PF Magic`

### Goal

Build a fully playable Petz/Dogz/Catz/Oddballz-compatible runtime integrated with the shared mascot system.

### Rollout order

1. GameSync v1
2. GameSync v2
3. Desktop app

### Architecture rule

One shared core engine with host adapters, not three divergent reimplementations.

### Known artifacts

- `gamesync_petz_build_checklist.md`
- earlier `pf_petz_playable_methods.md`

### Continuity risks

- PF Magic source and extracted assets must remain preserved.
- Petz behavior should not be flattened into ordinary mascot animation.
- GameSync, mascot, and Feature Foundry object/room systems may overlap; define ownership explicitly.

---

## PRJ-008 — Mascot Games / Golf and Sports

**Status:** ACTIVE design/implementation track  
**Confidence:** Medium

### Latest known artifact

- `mascotgames_master_agent_ordered_wxt_react_vite_v2_aligned_playable_contract_glorious_sports_golf_flagship.md`

### Direction

- Golf as flagship
- sports experiences playable in popup, panel, and full view
- aligned with the WXT/React/Vite v2 mascot runtime
- real playable loops, not decorative sports screens

### Needed reconciliation

Locate the repository and verify what is implemented versus specified. Keep the sports game layer modular so it does not corrupt the core mascot runtime.

---

## PRJ-009 — Bert's Skill Atlas / Skill Guide

**Status:** ACTIVE RuneLite plugin family  
**Confidence:** Medium

### Recovered lineage

1. `Bert's Skill Guide Master`
2. `bert-skill-guide-master.zip`
3. `bert-skill-atlas-ultra.zip`
4. `bert-skill-atlas-unified-cockpit.zip`
5. `bert-skill-atlas-qa-cockpit.zip`

### Known earlier Master plugin scope

- RuneLite sidebar guide
- all 24 current skills including Sailing
- multiple routes and steps
- money-making tabs
- object/NPC/tile/inventory/bank/equipment highlights
- Wiki and Prices actions
- data-driven `GuideRepository.java`

### Prior-chat recovered counts

The Unified Cockpit was described as preserving:

- 24 skills
- 144 routes
- 404 money-makers
- 211 quest entries
- 4,877 quest steps

The QA Cockpit added True Content QA and consolidated guide/prep/map/money/settings workflows.

### Build status warning

An earlier artifact explicitly had not been locally built. Do not assume later ZIPs compile or load until the latest package is found and tested in RuneLite developer mode.

### Immediate next checkpoint

Find the newest QA Cockpit ZIP, compute SHA-256, extract cleanly, run Gradle build/tests, launch RuneLite developer mode, and verify sidebar, routes, overlays, links, and persistence.

---

## PRJ-010 — RuneLite FlipForge / Farm Material Ranker / No-Hitch / 117HD

**Status:** ACTIVE, external-plugin loading is a release blocker  
**Confidence:** Medium

### Components

- `flipfore-osrs` / user-facing FlipForge naming
- Farm Material Ranker
- Rust dashboard/bridge
- No-Hitch RuneLite launcher/runtime
- 117HD / RLHD integration

### Farm Material Ranker

Latest known standalone version: **v1.1.0**.

Recovered features:

- searchable sidebar
- OSRS/GE pricing
- item icons
- sorting
- monster metadata
- shortest-path routing

Artifact: `farm-material-ranker.zip`

### Known-good hitchless reference identity

- Artifact: `hitchless-runelite-main.jar`
- SHA-256: `80d99e72d82ad28a5fe7779d7325450b487edb2c9c1f617b2e75acfa39f61d89`
- Size: 57,842,944 bytes
- Main class: `com.bertsplugins.hitchless.HitchlessRuneLiteMain`
- Embedded RuneLite: 1.12.29.1
- Commit: `68ff80e`

### Main unresolved release gate

The actual Jagex-launched client must prove that both external plugins are visible, enabled, functional, and persistent after restart. A build, JAR inspection, or developer-mode load is not enough.

---

## PRJ-011 — The Sims 4 Accelerator

**Status:** SPEC / STARTER SCAFFOLD  
**Confidence:** High

### Latest recovered plan

- `TS4_ACCELERATOR_AGENT_PLAN.md`
- Updated plan variants from 2026-04-20 through 2026-04-27
- Starter `README.md`

### Mission

A Windows-only TS4 performance project targeting:

1. large Mods/Overrides startup cost
2. zone-load hitching and asset warmup
3. DX11 frame pacing and render-thread overhead

### Architecture

- Rust launcher/control plane
- C++23 provider and injected telemetry/acceleration DLL
- ProjFS first, WinFsp fallback, staged/hardlink fallback
- SQLite manifests and baselines
- ETW, PresentMon and Tracy
- Detours/MinHook
- DBPF and `.ts4script` optimization
- libdeflate/zlib-ng only after profiling proves a decompression bottleneck

### Strict rules

- Measure before internal patching.
- Preserve the real Mods library.
- Start with pass-through projection and externalized bottlenecks.
- Benchmark DX9/DX11 and Memory Boost states where relevant.
- Stop if projection is slower, content compatibility breaks, or the DLL crashes with hooks disabled.

### Current status

The README explicitly describes the workspace as a **blueprint and scaffold, not a finished optimizer**.

---

## PRJ-012 — Sims 4 Native DX11 Overlay Mod

**Status:** SPEC / relationship unresolved  
**Confidence:** Medium

### Recovered requirements

- native C++
- DirectX 11 overlay
- Dear ImGui
- F11 toggle
- architecture, folder structure, build, hooking, input, configuration and runtime variables
- explicitly excludes XML, Python, HTML, CAS and a separate app

### Relationship question

This may be:

- a UI/telemetry module within TS4 Accelerator, or
- a separate native mod project.

Do not merge repositories or duplicate hooks until the original prompt/artifact is located and the user intent is reconciled.

---

## PRJ-013 — Money App / AI Monetization Station

**Status:** SPEC / PLAN  
**Confidence:** Medium

### Latest known plan

- `money_app_plan_v38_no_meta_prompts.md`

### Recovered version lineage

v9 → v17 → v19 → v25 → v26 → v27 → v28 → v36 → v37 → **v38**

### Scope in v38

An interconnected creation and monetization station with rooms/pipelines such as:

- Game Asset Foundry
- Mod Garage
- Music Foundry
- Logo Lab
- Etsy
- Fiverr
- TikTok
- YouTube
- Vault
- Patreon
- SubscribeStar
- Boosty
- Afdian
- OnlyFans
- Bandcamp
- BeatStars
- ecommerce and automation pipelines

### Status boundary

The plan is substantial, but current implementation, repository, integrations, credentials, and real revenue workflows were not recovered. Treat it as a plan until proven in a runtime.

---

## PRJ-014 — Grim Dawn Cairn Codex

**Status:** ARTIFACT PRESENT; functional status unverified  
**Confidence:** Medium

### Latest known artifact

- `Grim_Dawn_Cairn_Codex_Ultimate_v6_1.html`

### Recovered characteristics

- standalone HTML guide/codex
- quest and area data
- localStorage schema associated with Cairn Codex Ultimate v5
- legacy v4/v3 migration awareness

### Immediate next checkpoint

Open the v6.1 artifact in a browser, test every navigation/filter/state path, verify save/migration/reload behavior, inspect console errors, and record the file hash.

---

# 4. Mod Organizer 2 project family

## PRJ-015 — Bethesda Plugin Info

**Status:** VALIDATED ARTIFACT; final Windows MO2 test pending  
**Confidence:** High

### Version lineage recovered

v1.0.0 → v1.1.0 → v1.2.0 → v1.3.0 → v1.4.0 → v1.5.0 → v1.5.1/v1.5.2 patch work → **v1.5.3 compatibility correction**

### Strongest full validation recovered

v1.5.0:

- 69 automated tests passed
- clean ZIP and release hygiene
- dedicated column, header movement, resize safety, branch restoration, selection/model preservation
- rich and classic tooltip modes
- warning and category behavior
- 22 ICO + 22 PNG assets
- no networking, subprocesses, per-mod sidecars, game Data or Overwrite writes

### Latest correction

The shared drag/drop root-cause report records Bethesda Plugin Info **v1.5.3** with native-column-zero drop capability and paint-barrier corrections. It retained 76 tests plus four subtests in that compatibility pass.

### Final live test needed

- exact Windows MO2 2.5.3 beta 12 or compatible build
- installed theme and DPI
- full plugin stack
- dedicated column and native columns
- drag/drop insertion indicator
- tooltips
- enable warning
- categories
- restart persistence

---

## PRJ-016 — Bethesda Creations Version Tracker

**Status:** VALIDATED ARTIFACT; final Windows MO2 test pending  
**Confidence:** High

### Version lineage recovered

v2.0.0 → v2.1.0 → v2.2.0 → v2.3.0 → v2.3.1 → v2.4.0 → v2.4.1 → v2.4.2 patch → **v2.4.3 compatibility correction**

### Important migration history

v2.3.1 stopped creating `.bethesda-creation-sorter.json` in every Creation mod, migrated ownership to MO2 metadata/central plugin data, quarantined corrupt legacy marker data, and preserved user metadata.

### Latest correction

The shared root-cause report records v2.4.3 with the same dedicated-column drop flag and repaint corrections as the other synthetic-column plugins.

### Final live test needed

Verify migration, metadata, version/source data, dedicated column behavior, no false conflicts, drag/drop, and persistence inside the real Windows MO2 installation.

---

## PRJ-017 — MO2 Image Column / MO2R Image Automation

**Status:** ACTIVE corrected build  
**Confidence:** High

### Version lineage recovered

- restored v1.4.10 base
- rejected/avoided v1.4.11 delegate-substitution path for final compatibility fix
- **v1.4.12** shared drag/drop correction

### Related master prompt

- `MO2R_Image_Column_AI_Automation_Master_Prompt.md`

### Major requirements

- exact image identity and duplicate isolation
- local/remote source resolution
- bounded caching and invalidation
- context-aware repair actions
- no mod-list state regression
- preserve scroll, selection, separators, column state, search/filter, profile and drag/drop
- compact row height by default

### Final live test needed

Verify v1.4.12 with Bethesda Plugin Info and Version Tracker installed together, including insertion line, download-to-mod-list drag, thumbnails, tooltips, identity matching, scrolling and separator preservation.

---

## PRJ-018 — MO2 Drag-and-Drop Line Restorer

**Status:** VALIDATED ARTIFACT; visual live test pending  
**Confidence:** High

### Latest version

- **v1.1.0**
- SHA-256: `615b3b05e081ce6c529b4e9e117dbdc207f30e0dca5c858c31739a0981da7b56`

### Function

A visual-only overlay that restores an always-visible MO2 drop indicator without accepting, rejecting, rerouting or executing drag/drop.

### v1.1.0 additions

- exact MO2 native renderer mode
- Enhanced v1 and Fully Custom modes
- live preview
- presets
- target tests
- native indicator positioning

### Automated evidence

Offscreen tests passed for native/custom rendering, model/view discovery, safety, settings, drag event non-interference, performance, ZIP layout and compilation.

### Final live test needed

Exact appearance and insertion target in Windows MO2 with the active theme and full plugin stack.

---

## PRJ-019 — MO2 Performance Accelerator

**Status:** ACTIVE / corrected after a reproduced crash  
**Confidence:** High

### Version lineage

v2.0.0 → v3.0.0 → v4.0.0 → **v4.0.1**

### v4 design

- event-driven only
- no recurring workers or scans
- transactional proxy updates
- drag fast path
- lossless filter batching
- viewport/separator preservation
- passive reversible tuning

### v4.0.0 failure

A deleted `QTabWidget` wrapper could enter the discovery path and raise `RuntimeError: wrapped C/C++ object ... has been deleted`.

### v4.0.1 fix

- removed generic discovery implementation
- binds only after `setParentWidget()`
- exact `modList` targeting
- exception containment and circuit breaker
- no workers, recurring timers, filesystem traversal or arbitrary view binding
- synthetic benchmark showed about 8.3–8.6× for the targeted proxy recomputation pattern, not a promise for whole MO2 performance

### Final live test needed

Install v4.0.1, not v4.0.0. Verify startup, drag, filtering, sorting, viewport/separators, fail-safes, restoration and shutdown in the real Windows process.

---

## PRJ-024 — MO2 Drag/Column Compatibility Pack

**Status:** VALIDATED COMPATIBILITY WORK; live stack test pending  
**Confidence:** High

### Coordinated versions

- Image Column 1.4.12
- Bethesda Plugin Info 1.5.3
- Bethesda Creations Version Tracker 2.4.3

### Root cause corrected

1. Synthetic columns inherited drag/drop flags from the wrong native column.
2. Queued plugin repaints could erase native insertion feedback and add drag-path work.

### Required live proof

All three plugins loaded together in the exact MO2 build with:

- installed-mod moves
- separator moves
- download-to-list drags
- top/bottom auto-scroll
- full insertion-line visibility
- unchanged native drop behavior

---

# 5. Research and supporting projects

## PRJ-020 — Master Desktop Pet Research

**Status:** RESEARCH BASE  
**Confidence:** High

### Canonical master

- `master desktop pet research.md`
- Primary consolidation date: 2026-04-01

### Consolidated content

- exhaustive ecosystem catalogue
- host map
- creator/linktree/hub research
- Discord/community map
- Microsoft Agent / ACS / Bonzi / Peedy / Clippy / XP Search branch
- KinitoPET addendum
- embedded v10 and v14 passes
- retained v9 and v7 appendices

### Rule

Append future verified passes to this master rather than creating unrelated numbered files, unless a snapshot is intentionally versioned.

---

## PRJ-021 — GX Slim

**Status:** UNRESOLVED IDENTITY  
**Confidence:** Low

### Recovered artifact

- `GX-Slim-1.0.0-FULL.zip`
- SHA-256: `5ad8aa6d13a898af1ead4d50b7922829ec94d427199475f17522b2ed1a4a9717`

### Missing

- README/purpose
- canonical source repository
- validation report
- relationship to Opera GX, GameSync, Feature Foundry or another project

Do not guess or merge it until the archive is found and inspected.

---

## PRJ-022 — Feral Unified Native Base

**Status:** UNRESOLVED / generated base  
**Confidence:** Medium

### Recovered artifact

- `Feral_Unified_Native_Base.zip`

### Evidence

The archive contains Feature Foundry-style App DNA, mod-cartridge, preview-runtime, validation, promotion, and golden-fleet structures. Generated validation scenarios were marked not run and `shippable: false`.

### Needed decision

Determine whether Feral is:

- a standalone application project,
- a generic native app base,
- a generated Feature Foundry experiment,
- or a precursor to another product.

---

## PRJ-023 — Feature Foundry Portable Feature Starter

**Status:** GENERATED STARTER / TEMPLATE  
**Confidence:** High

### Version

- package version `0.1.0`

### Stack and capabilities recovered

- Vite
- Vue 3 in the recovered package manifest
- Tauri 2
- TypeScript
- Vitest
- Playwright
- Biome
- portable feature capsule operations
- upgrade, rollback, validation and golden-fleet scaffolding

### Validation boundary

The included validation report had zero scenarios run and `shippable: false`. Preserve it as a starter/template, not a completed application.

---

# 6. Changelog and version-reconciliation rules

## 6.1 Never overwrite history silently

For each project, keep:

- stable project ID
- aliases
- canonical repository/path
- artifact filename
- embedded version
- content hash
- source chat/file location
- created/recovered date
- predecessor and successor links
- validation status
- live-runtime status
- known regressions
- next action

## 6.2 Version trust order

Use this order when deciding the latest usable state:

1. Current explicit user correction.
2. Current canonical repository and runtime evidence.
3. Embedded version and changelog inside the artifact.
4. Content hash and verified lineage.
5. Validation report tied to the exact artifact hash.
6. File Library upload time.
7. Filename alone.

A higher filename number does not automatically beat a known-good branch or artifact.

## 6.3 Required statuses per artifact

Use separate fields:

- **Discovered**
- **Preserved**
- **Parsed/inspected**
- **Build passed**
- **Automated tests passed**
- **Packaged**
- **Fresh extraction passed**
- **Installed in target**
- **Real workflow passed**
- **Restart persistence passed**
- **Canonical/latest-good confirmed**

Do not collapse these into one “done” checkbox.

## 6.4 Append-only project changelog template

```markdown
### YYYY-MM-DD — Project name — version/artifact

- Project ID:
- Canonical repo/worktree/branch:
- Previous version/hash:
- New version/hash:
- Source chat/file:
- What changed:
- What was preserved:
- What was removed intentionally:
- Automated checks:
- Real-runtime checks:
- Known regressions or risks:
- Latest-good status:
- Next exact step:
```

---

# 7. Highest-priority organization work

1. **Create canonical IDs and paths** for Feature Foundry, GameSync, Mascot, RuneLite, MO2, TS4, Money App, Grim Dawn and GX Slim.
2. **Find and hash the latest artifact** for every Medium/Low confidence record.
3. **Separate project families from subprojects** so one subsystem is not restarted as a new app.
4. **Preserve latest-good builds before changes**, especially Feature Foundry Explorer/media work, MO2 v4.0.1, RuneLite hitchless reference, and GameSync hosts.
5. **Add a per-project `PROJECT.md` and `.agents-memory/` folder** to every active repository.
6. **Checkpoint after each meaningful chat** with what changed, artifact hashes, current blockers and next exact steps.
7. **Re-run this cross-chat inventory periodically** and append deltas instead of regenerating an unrelated list.

---

# 8. Source evidence index

This database was assembled from available current-chat files, File Library search results and prior-chat personal context. Key recovered source documents include:

## Feature Foundry

- `feature-foundry-aesthetic-worlds-codex-master-directive.md` — V11 canonical marker
- `feature-foundry-codex-final-implementation-directive-v11.md`
- `feature-foundry-aesthetic-world-guide-v11.md`
- `feature-foundry-living-world-prototype-v11-bundle-reference.html`
- `V11-VALIDATION-REPORT.md`
- `ui-theme-agent-spec.md`
- `ui-theme-agent-spec-v48.md`, `v49.md`, `v51.md`
- `aesthetics-guide.md`
- `Feature_Foundry_Portable_Feature_Starter.zip`

## GameSync and Mascot

- `AGENTS.md` records for GameSync
- `acs-agent-parity-checklist-generalized-v3.md`
- `mascot_engine_rebuild_directive (2).md`
- `master desktop pet research.md`
- `gamesync_petz_build_checklist.md`
- `pf_petz_playable_methods.md`
- mascot games Golf/sports master directive

## RuneLite

- `README.md` for Bert's Skill Guide Master
- Bert's Skill Atlas prior-chat artifacts
- `RuneLite_Master_Prompt_Smart_No_BS.md`
- `RuneLite_Codex_Master_Prompt_No_Logging.md`
- `runelite_flipping_codex_master_prompt(4).md`
- `RuneLite_External_Plugins_Codex_Prompt_CLEANED(7).md`

## Sims 4

- `TS4_ACCELERATOR_AGENT_PLAN.md`
- TS4 Accelerator `README.md`
- prior-chat native DX11 overlay architecture prompt

## MO2

- Bethesda Plugin Info validation reports v1.0.0 through v1.5.0
- Bethesda Creations Version Tracker validation/hash records
- `MO2-Drag-Drop-Audit-and-Fix-Report.md`
- `MO2-Drag-Drop-Root-Cause-and-Fix-Report.md`
- `MO2-Drag-Drop-Line-Restorer-v1.1.0-README.md`
- `MO2-Drag-Drop-Line-Restorer-v1.1.0-TEST-REPORT.md`
- `MO2-Performance-Accelerator-v4.0.1-TEST-REPORT.md`
- `MO2R_Image_Column_AI_Automation_Master_Prompt.md`

## Other

- `money_app_plan_v38_no_meta_prompts.md`
- `Grim_Dawn_Cairn_Codex_Ultimate_v6_1.html`
- `GX-Slim-1.0.0-FULL.zip.sha256`
- `Feral_Unified_Native_Base.zip`

---

# 9. Known gaps in this recovery

- Chat history is not exposed as one complete export, so some one-off or unnamed projects may be missing.
- Several latest artifacts were recovered from prior-chat context but not rediscovered as current File Library files.
- Canonical repository paths are known only for GameSync and the PF Magic source branch.
- “Implemented” checklists may describe repository work that has not been revalidated in the current runtime.
- Some version relationships are inferred from explicit changelog/report text but still need artifact hashes and repository confirmation.
- GX Slim and Feral Unified Native Base need identity reconciliation.

**Do not treat these gaps as permission to start over. Search, identify, preserve and reconcile first.**
