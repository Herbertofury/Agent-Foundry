# AGENTS Second Brain

The durable project source of truth lives in `.agents-memory/` inside each project. A user-level registry, defaulting to `~/.agents-second-brain/registry.json`, only helps locate projects; it does not replace repository evidence.

Use `project_memory.py init` once per real project, `identify` before mutating an unfamiliar or resumed project, `checkpoint` after meaningful progress, `resume` in a new session, `doctor` before closeout, and `export` to create a portable project-memory ZIP.

Use `research_memory.py` for sourced, versioned, freshness-aware research. A remembered claim is not automatically current truth. Revalidate stale or version-sensitive records before using them.

Never store credentials, private keys, access tokens, passwords, or unrelated personal data in project memory.

## Cross-chat delta reconciliation

Before resuming a named project, search the current ChatGPT Project, File Library, personal context, connected storage, current uploads, and repository handoffs for artifacts created or changed after the last checkpoint. Open plausible candidates before trusting them. A later artifact may reuse the same filename, so filename equality is never proof of identical content.

Write a temporary JSON manifest containing the discovered candidates, then reconcile it:

```bash
python .agents/tools/project_memory.py reconcile-artifacts . --input cross-chat-artifacts.json
python .agents/tools/project_memory.py list-artifacts . --json
```

Each candidate should provide a stable `source_id`, content SHA-256, or content signature plus its name, source type, timestamps, explicit version when known, and notes. The reconciler preserves same-name versions, records lineage and supersession, updates `STATUS.json`, refreshes `HANDOFF.md`, and refuses duplicate identities. Never overwrite an older artifact merely because a new chat reused its filename.

## Cross-project catalog

The project-local `.agents-memory/` state answers “what is true about this project?” The user-level project catalog answers “which projects exist, what are their latest known versions, and where should work resume?”

Initialize the catalog once from the bundled recovery database:

```bash
python .agents/tools/project_catalog.py bootstrap --seed .agents/memory/USER-PROJECTS-DATABASE.seed.md
```

The default durable files under `AGENTS_MEMORY_HOME` or `~/.agents-second-brain/` are:

- `project-catalog.json` — canonical machine-readable registry
- `USER-PROJECTS-DATABASE.md` — human-readable project/version database
- `project-catalog-events.jsonl` — append-only update history

Before working on a named project, search the catalog, perform the cross-chat delta sweep, open plausible newer artifacts, and reconcile the evidence. Do not silently promote a timestamp-only candidate to latest. Promotion requires verified content, explicit supersession, or direct user confirmation.

After every project-memory initialization, checkpoint, or artifact reconciliation, synchronize the project into the master catalog:

```bash
python .agents/tools/project_catalog.py sync-project .
python .agents/tools/project_catalog.py doctor
```

When the durable catalog cannot be shared directly, export it:

```bash
python .agents/tools/project_catalog.py export --output USER-PROJECTS-CATALOG.zip
```

The seed file bundled with the skill is a recovery starting point, not the live database. Never overwrite a newer user catalog with the immutable seed.

## Organized artifact library

Use `library_manager.py` alongside project memory so files are not scattered across chats, downloads, and repeated exports.

```bash
python .agents/tools/library_manager.py init
python .agents/tools/library_manager.py ingest <files...> --project-id PRJ-001 --project-name "Project Name" --kind bundle --version v1
python .agents/tools/library_manager.py record-usage --plan plus --used-bytes <bytes>
python .agents/tools/library_manager.py plan-cleanup
python .agents/tools/library_manager.py doctor
```

The default library vault is `<AGENTS_MEMORY_HOME>/library` or `~/.agents-second-brain/library`. It keeps current files, versions, research, assets, bundles, memory, prompts, reports, archive, quarantine, a machine-readable catalog, a Markdown database, and append-only events. Exact SHA-256 equality is required for automatic duplicate quarantine. Same-name different-content files are preserved as versions. External ChatGPT Library deletions remain manual unless a supported delete action is available and verified.

## Project Compass and interaction ecology

Use `PROJECT-COMPASS.template.json` and `project_compass.py` to preserve project northpoints, goals, feature pillars, principles, wants, guardrails, acceptance signals, and publication targets. For living or highly themed interfaces, record a complete theme-native interaction ecology: distinct press/drag/placement/collision/transformation languages, bounded cross-element causality, material/scale/velocity-aware behavior, subtle-but-unmistakable feedback, and immediate user-input sovereignty.

`FEATURE-FOUNDRY-COMPASS.seed.json` is the project-local reference implementation. It intentionally contains product-specific Frutiger Aero, liminal, and graffiti-world examples that must not be copied into universal policy.

`FEATURE-FOUNDRY-LIVING-ECOLOGY.seed.json` is the machine-readable living-world contract. It defines intent-aware anticipation, the Ecology Director, transition levels 0-5, persistent chronological/use/authored memory, semantic materials, spatial audio, object relationships, theme-native AI presence, environmental data embodiments, microclimates, causal undo/replay, behavior genomes, an always-expanding professional authoring studio, cross-device capability, and an Efficient-to-Cinematic performance ladder that preserves full feature/data parity. Validate and render it with `living_ecology.py`.
## Feature Foundry asset intelligence

`FEATURE-FOUNDRY-SOURCE-HUBS.seed.json` is the capability-tested source-adapter registry. It distinguishes official/public/OAuth APIs, oEmbed, browser clipping, manual import, launchers, and legacy-client-only access while preserving authentication, rate-limit, attribution, rights, moderation, caching, fallback, and freshness requirements.

`FEATURE-FOUNDRY-OBJECT-INTELLIGENCE.seed.json` defines the immutable-original, reversible fifteen-stage derivation graph; instant, draft, and high-fidelity quality lanes; truthful representation ladder; candidate segmentation/depth/3D/Blender/optimization runtimes; and reviewable uncertainty rules.

Validate and render both catalogs with:

```bash
python .agents/tools/asset_intelligence.py validate
python .agents/tools/asset_intelligence.py render
```

Validate and render the living-ecology registry with:

```bash
python .agents/tools/living_ecology.py validate
python .agents/tools/living_ecology.py render
```
