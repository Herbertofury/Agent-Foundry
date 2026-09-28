# Minecraft Dev Kit layout and discovery

## Canonical Drive root

When Google Drive is connected, prefer the user's canonical Dev Kit first:

`https://drive.google.com/drive/folders/1LJ12tL6n__IEf6UdB0iyVx3V3gF1VCeG`

Do not ask the user to re-upload a tool that is already present and readable there. Inspect the relevant subfolder directly rather than broad-scanning all Drive content.

Established high-level layout:

- `00 Documentation & Index`
- `01 Toolchains & SDKs`
- `02 Build & Port Frameworks`
- `03 Launchers & Test Harnesses`
- `04 Reference Runtime Mods`
- `05 Asset & Content Tools`
- `06 Reverse Engineering & Bytecode`
- `07 Profiling, Diagnostics & Rendering`
- `08 Orchestration & Automation`
- `05 Asset & Content Tools/Vanilla Feature Atlas` (version lineage, registries, sounds, data/resources, asset-index provenance, provider inventories)
- `AI Dev Tools`
- `Projects`

Important reusable components include Java toolchains, Gradle distributions, loader MDKs/caches, decompilers, Blockbench/Blender, RenderDoc, profiling tools, FFmpeg/ImageMagick, native Linux headless runtime packages, and project-specific QA toolkits.

## Orchestrator

Prefer the newest verified `mmv-devkit` release in `08 Orchestration & Automation`. Known 2.3.0 capabilities include:

- `validate`
- `check`
- `sync`
- `watch`
- `sources`
- `heritage`
- `port-guard`
- `adopt-tools`
- `cache-doctor`
- `cache-reassemble`
- `archive-split`
- `client-assets`
- `client-natives`
- `world-qa-enable`
- `vanilla-atlas verify|query|sound-status|diff|providers|plan-backport` (2.6.0+; 2.6.3+ enforces base-port-first explicit opt-in authorization)

Use `--help` on the installed version before assuming newer flags.

## Minecraft 26.3 readiness profile

Keep a Java 25 toolchain lane available for Minecraft 26.3. The 26.3 port skill fast path uses `references/minecraft-26.3-porting.md` as the dated loader matrix and these deterministic tools:

- `scripts/port_intake.py` — source/JAR identity, loader/build/content inventory and migration-risk scan;
- `scripts/port_scaffold_26_3.py` — loader-native Fabric/NeoForge target scaffold;
- `scripts/port_26_3_pipeline.py` — safe new workspace with intake evidence and initial ledger;
- `scripts/port_guard.py` — static target/toolchain/risk/inventory gate before runtime QA;
- `scripts/port_26_3_selftest.py` — fixture regression covering source/JAR intake, both loader scaffolds, blocker detection and the initial unresolved-ledger failure;
- `scripts/prewarm_mc_26_3_toolchains.py`, `scripts/Prewarm-Minecraft-26.3-Toolchains.ps1` + `references/minecraft-26.3-toolchain-lock.json` — checksum-verified Java 25 / Gradle cache prewarm on a networked machine.

Current profile snapshot (2026-09-17): Java 25; Fabric Minecraft 26.3 + Loader 0.19.5 + Loom 1.17-SNAPSHOT + Fabric API 0.160.6+26.3 + Gradle 9.6.0; NeoForge Minecraft 26.3 + NeoForge 26.3.0.1-beta + ModDevGradle 2.0.147 + Gradle 9.2.1. Revalidate these pins against official loader sources before a fresh port, especially while the NeoForge pin is beta.

## Reuse before download

Before fetching a new JDK, Gradle, loader, mapping, native, model tool, profiler, or dependency cache:

1. Check the canonical Dev Kit folder.
2. Validate the candidate by embedded version/hash/runtime launch, not filename alone.
3. Reuse exact compatible artifacts.
4. Download current official artifacts only when the Dev Kit lacks a compatible copy or the task explicitly requires a newer version.
5. Put genuinely reusable new tools back into the correct Dev Kit subfolder and record provenance/version/checksum.

## Missing-tool behavior

If a missing runtime/tool materially blocks correctness, speed, fidelity, or verification, tell the user exactly what is missing and include a direct official download/use link. Never request credentials, launcher sessions, Microsoft/Minecraft tokens, cookies, or account files for development QA.
