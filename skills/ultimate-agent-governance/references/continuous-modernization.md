# Continuous Modernization and Fix-Forward Standard

> **Status:** Binding cross-domain engineering policy
> **Scope:** Apps, mods, tools, libraries, integrations, provider adapters, build systems, runtimes, migrations, ports, repairs, tests, release pipelines, and live implementation chats.

## Prime rule

**The engineering baseline must continuously move forward. Do not let a project remain stale merely because the current version, tool, API, architecture, or workflow already works. For every substantive task, perform a bounded freshness pass, seek the strongest current method, adopt materially better technology fully, and fix forward through migration breakage instead of retreating to stale versions for convenience.**

The default posture is:

`current evidence -> freshest/best viable candidate -> full integration -> equivalent-work comparison -> dissect mixed regressions -> fix forward -> runtime/performance proof -> promoted new baseline`

Stability does not mean stagnation. Modernization does not permit regressions. The goal is a newer, stronger baseline that preserves or improves the complete requested result.

---

## MZ001 — Every Substantive Task Gets a Freshness Pass

Before finalizing substantive implementation, identify the load-bearing technology that could materially affect the result and verify whether a newer or better approach exists.

Examples include:

- runtimes and language versions;
- loaders, mappings, APIs, SDKs, frameworks, libraries, plugins, Gradle/Maven/npm/Cargo tooling, compilers, bundlers, packagers, renderers, and test harnesses;
- provider APIs, authentication flows, transport options, browser automation APIs, site-adapter techniques, and data schemas;
- performance primitives, native APIs, concurrency models, caching/indexing approaches, serialization formats, GPU/runtime capabilities, and platform facilities;
- current upstream releases, migration guides, deprecations, compatibility changes, and known replacements.

When freshness matters, use current primary sources such as official documentation, release notes, tags/releases, migration guides, source repositories, issue trackers, and authoritative package metadata. Do not rely on stale model memory for version-sensitive implementation decisions.

Keep the pass bounded to the actual task and load-bearing stack; do not turn freshness into ceremonial ecosystem-wide scanning.

**Acceptance:** Did the implementation use current evidence for the parts of the stack where newer methods or versions could materially improve the result?

---

## MZ002 — Latest Production-Worthy Version Is the Default Baseline

Use the newest production-worthy version of a dependency, runtime, toolchain, library, plugin, SDK, API, or platform component by default when it is compatible with the required product target.

Do not retain an older version as the final state merely because:

- its API is already familiar;
- the migration takes work;
- the newer version requires source changes;
- tests need updating;
- mappings or schemas changed;
- the build script needs repair;
- the old version happens to compile today.

If a newer version introduces breakage, that breakage becomes migration work. Fix forward by updating code, mappings, adapters, schemas, configs, build logic, tests, assets, serialization, compatibility shims, or integration boundaries.

An older version may be used temporarily for bisecting or diagnosis, but **diagnostic rollback is not a modernization-complete final state**.

If the newest tagged release contains a verified upstream defect that materially blocks the task, prefer a fixed newer commit/nightly, a maintained fork, a local patch, or a compatibility shim when that is the strongest verifiable route. Do not automatically freeze indefinitely on an obsolete release just because upstream has a bug.

**Acceptance:** Is the final baseline as current as the required target permits, with upgrade breakage repaired rather than avoided?

---

## MZ003 — Explicit Target Envelopes Must Be Preserved and Modernized Within

An explicit compatibility target is part of acceptance and must not be upgraded away without user approval.

Examples:

- Minecraft Forge 1.20.1;
- NeoForge 1.21.1;
- a specific OS/application API floor;
- a required Java/.NET/Node ABI;
- a plugin host or game version;
- a binary/protocol compatibility requirement.

When an exact target is required:

1. preserve that target;
2. update everything that can safely be updated within it;
3. backport or adapt newer algorithms, fixes, tooling patterns, performance techniques, APIs, or architecture when the modern upstream approach is outside the target envelope;
4. build compatibility layers when necessary instead of using the target as an excuse for stale implementation quality.

**A target version is a compatibility boundary, not a staleness exemption.**

**Acceptance:** Was the required target preserved while the implementation around it advanced as far as technically supportable?

---

## MZ004 — Bleeding-Edge Better Methods Must Be Evaluated and Adopted When They Win

Do not stop at the first conventional or familiar solution. When the task materially benefits from newer techniques, compare the current best available approaches.

The latest stable release is the minimum freshness floor, not automatically the ceiling. Evaluate newer preview/nightly/commit-level capabilities when they provide a material advantage and can be verified safely in the project.

Examples:

- new native APIs that eliminate an expensive compatibility layer;
- a newer renderer or data pipeline that materially improves FPS/TPS without fidelity loss;
- new incremental/indexed filesystem APIs that replace full rescans;
- newer concurrency/runtime primitives that remove serial bottlenecks;
- a maintained successor library replacing an abandoned one;
- a better provider/API integration path replacing brittle scraping;
- a new build/test/runtime tool that gives stronger proof or dramatically better iteration speed.

Adopt based on measured capability, maintainability, compatibility, and evidence—not novelty theater. But do not reject a superior current method merely because the old method is already implemented.

**Acceptance:** Was the strongest current practical method considered and, when materially better, adopted rather than dismissed for migration convenience?

---

## MZ005 — Integrate Superior Tools Fully, Not as Decorative Sidecars

When a materially better tool, library, subsystem, adapter framework, profiler, renderer, database/index, build system, test harness, or integration is adopted, connect it to the real production path.

Full integration means, as applicable:

- real workflows route through it;
- existing state/data/configuration is migrated safely;
- auth/session/caching/telemetry/error semantics are integrated;
- UI and background jobs use the same canonical owner;
- old bypass paths are migrated or removed after parity is proven;
- tests, diagnostics, runtime proof, documentation, and release pipelines know about the new path;
- relevant capabilities of the new tool are actually used rather than installing it and continuing through the legacy implementation.

Do not create dead architecture, optional-looking wrappers, or parallel implementations that leave the old weaker path authoritative.

**Acceptance:** Did the new tool/method become the canonical production path with real end-to-end capability, rather than another unused dependency or bolt-on demo?

---

## MZ006 — Fix Forward Through Upgrade Breakage

**An upgrade causing errors is not evidence that the upgrade should be abandoned. It is evidence that the migration is incomplete.**

When modernization breaks something:

`capture exact failure -> identify old/new contract delta -> update causal owner -> migrate state/config/data -> targeted test -> runtime proof -> continue`

Typical fix-forward work includes:

- API/signature migrations;
- loader/mapping changes;
- compiler/runtime changes;
- build-plugin or manifest updates;
- schema/data migrations;
- auth/permission changes;
- serialization/network protocol compatibility;
- renamed/removed configuration keys;
- rendering or lifecycle changes;
- dependency graph updates;
- replacement of deprecated APIs;
- test fixture and harness updates;
- source/binary compatibility shims.

Do not use downgrade as the default permanent repair merely because fixing forward takes more work. Patch, fork, shim, port, adapt, or migrate until the newer baseline is real and verified.

**Acceptance:** Were modernization-induced failures repaired forward at their causal owner instead of being used to justify a stale final baseline?

---

## MZ007 — Modernization Must Preserve Full Product Value

Continuous updating is subordinate to the full-result, preservation, runtime-proof, and dual-success performance invariants.

Modernization must not silently lose:

- features or content;
- data/configuration/history;
- fidelity or visual/audio quality;
- compatibility or supported workflows;
- provenance/identity;
- performance;
- accessibility/QoL;
- security boundaries;
- deterministic behavior or evidence quality.

When a newer tool/version changes behavior, migrate the product so the old required value survives unless the user explicitly requested the behavior change.

**Latest is not permission for regression. The required result must move forward with the stack.**

**Acceptance:** Did the update leave the product at least as complete, correct, compatible, performant, and usable as before while gaining the modernization benefit?

---

## MZ008 — Every Improvement Becomes the New Reusable Baseline

Do not repeatedly rediscover a better method project by project or chat by chat.

When a modernization proves useful:

- promote reusable logic into shared libraries/components/adapters/scripts/templates;
- update canonical build/runtime recipes;
- record the new version/tool/method and migration knowledge;
- add regression fixtures/tests for the old failure mode;
- update skills/governance/reference material when the lesson is cross-project;
- invalidate the older baseline in recovery/continuity memory where appropriate;
- carry the newer baseline into analogous future features and projects.

This is a ratchet: once a stronger approach is proven, future work should start there unless newer evidence supersedes it.

**Acceptance:** Will the next analogous task inherit the improvement automatically instead of relearning it from scratch?

---

## MZ009 — Staleness Is a Defect When a Better Verified Route Exists

Treat known avoidable staleness as engineering debt to resolve, not neutral background state.

Examples:

- deprecated API still in active production code despite a proven replacement;
- old dependency retained only because migration was postponed;
- a one-off scraper retained after a stronger provider API/adapter path exists;
- full rescans retained after a proven incremental/indexed path exists;
- legacy serial code retained after a safe parallel pipeline is proven;
- obsolete build/test/runtime tooling retained despite a stronger supported replacement;
- older recovery recipes kept authoritative after a newer route is proven better.

Do not churn working code for meaningless version-number cosmetics. Modernize when the newer route materially improves support, correctness, performance, capability, reliability, maintainability, security, developer velocity, or user experience.

**Acceptance:** Is any known materially inferior legacy path still authoritative only because nobody wanted to finish the migration?

If yes, modernization is incomplete.

---

## MZ010 — Upgrades Must Earn Promotion Through Comparative Proof

A newer version, tool, dependency, runtime, API, renderer, compiler, library, plugin, provider route, or implementation method is a **candidate baseline**, not an automatic winner.

Before promotion, compare the proven baseline and candidate on representative equivalent work. Use the strongest practical combination of:

- unit/integration/regression tests;
- real runtime workflows;
- output/content/fidelity/capability identity checks;
- compatibility and persistence checks;
- FPS/TPS/frame-time/latency/throughput/startup measurements;
- memory/CPU/GPU/I/O/resource measurements;
- reliability/error-rate evidence;
- user-critical responsiveness and QoL behavior.

Promotion requires:

1. **material improvement evidence** in at least one intended dimension; and
2. **no unacceptable regression** in protected dimensions affected by the upgrade.

Do not promote an upgrade because its version number is newer, its changelog sounds better, it compiles, or one isolated benchmark improved while another important dimension became worse.

Use `scripts/upgrade_gate.py` when numeric A/B evidence is practical. The gate preserves workload/result/capability identity and rejects candidates that gain speed by doing less.

**Acceptance:** Did the candidate prove that it is genuinely better for this product/target under equivalent representative work before becoming authoritative?

---

## MZ011 — Mixed Upgrades Must Be Decomposed; Keep the Gains and Excise the Regressions

When an upgrade contains both valuable improvements and harmful regressions, do not choose between two weak outcomes: blindly accepting the regressions or permanently abandoning all of the upgrade's useful work.

Treat the mixed candidate as a decomposition problem, and enter this loop proactively rather than asking the user to choose between a worse upgrade and a stale downgrade:

`baseline vs candidate diff -> profile/bisect -> identify winning and losing changes -> preserve/backport winning changes -> patch/replace/reconfigure losing internals -> rebuild -> equivalent-work retest -> promote synthesized baseline`

Useful techniques include:

- commit/change bisection;
- feature/config/default isolation;
- profiler-guided hot-path comparison;
- dependency or transitive-dependency decomposition;
- selective cherry-pick/backport;
- local patch/fork/shim;
- replacing a newly regressive subsystem while retaining unrelated upgrade gains;
- restoring a proven fast code path behind the newer API/ABI;
- disabling/removing only dead, redundant, debug/telemetry, duplicate work, wasteful defaults, obsolete compatibility baggage, or harmful **internal implementation** that is not required product behavior;
- rewriting the regressive implementation while keeping the newer public contract and useful capabilities.

**Do not interpret “remove harmful pieces” as permission to remove user-visible features, content, fidelity, compatibility, supported behavior, or requested capability.** The target is a synthesized upgraded baseline that keeps the useful new pieces and eliminates the harmful implementation cost.

If a new renderer/API/library improves capability but adds lag, the job is not “choose capability or speed.” Keep the capability, locate the lag source, and repair/replace that source until the newer baseline is at least as good as the old one on protected dimensions and better on the intended dimensions.

**Acceptance:** When the full upgrade was mixed, did the final promoted result retain the upgrade's useful gains while removing/repairing the actual regressive implementation rather than giving up or sacrificing product value?

---

## Freshness evidence and continuity

For substantial version-sensitive work, preserve enough evidence to avoid repeating stale decisions:

- versions/tags/commits evaluated;
- primary-source release/migration references;
- exact selected version/commit/tool;
- compatibility target/envelope;
- migration or fix-forward notes;
- artifact/build identity after migration;
- runtime/benchmark evidence;
- baseline/candidate comparison evidence and protected dimensions;
- mixed-upgrade decomposition/bisection notes when applicable;
- date/freshness point when relevant;
- known superseded routes that should no longer be retried by default.

Freshness evidence belongs in the execution/continuity ledger, project docs, lockfiles, manifests, migration notes, or completion receipt as appropriate.

---

## Closeout gate

Before substantive closeout, ask:

1. Did we check the load-bearing stack for a newer materially better method/version?
2. Are we on the newest production-worthy baseline compatible with the required target?
3. If a newer version broke something, did we fix forward rather than permanently retreat?
4. If the project has an explicit historical/compatibility target, did we preserve it while backporting/adapting modern improvements?
5. If we adopted a better tool, does the real production path use it fully?
6. Did modernization preserve all required behavior/data/fidelity/compatibility/performance/QoL?
7. Did the proven improvement become reusable baseline knowledge for future work?
8. Did the candidate earn promotion through equivalent-work comparison rather than version-number trust?
9. If the upgrade was mixed, did we decompose it and preserve the useful pieces while repairing/removing only the harmful internal implementation?

If a required answer is no, the modernization work is not complete.
