# Minecraft Dev Kit v8

A durable workbench for building, converting, recovering, testing and packaging Minecraft mod projects through Enderloom's existing Northpoint engine.

## Start here

**Windows:** extract the complete package and double-click `devkit.cmd`. The guided menu selects a source project, detects its metadata, chooses a target, provisions its JDK, and retains the result in a separate workspace. When Python is missing, the launcher downloads a checksum-pinned private Python runtime from python.org. It does not require administrator access, install globally or modify your system PATH.

**Linux/macOS:** use `sh devkit.sh` with Python 3.12 or newer installed. The same menu and managed JDK setup are available. Use `sh devkit.sh doctor` for a noninteractive prerequisite check.

Already use a terminal? The minimal Windows conversion command is:

```powershell
.\devkit.cmd convert --project "C:\Mods\MyMod" --minecraft 26.3 --loader fabric --workspace "C:\DevKit-Runs\MyMod-26.3" --verify
```

`--java` and `--java-path` are optional. The kit selects the required Java major, reuses an appropriate installed JDK or provisions a private verified Temurin JDK. An explicitly supplied JDK must actually contain matching `java` and `javac` binaries.

## Everyday commands

```powershell
.\devkit.cmd doctor
.\devkit.cmd setup --minecraft 26.3
.\devkit.cmd status --workspace "C:\DevKit-Runs\MyMod-26.3"
.\devkit.cmd resume --workspace "C:\DevKit-Runs\MyMod-26.3"
.\devkit.cmd package --workspace "C:\DevKit-Runs\MyMod-26.3" --output "C:\DevKit-Releases\MyMod-candidate.zip"
```

Do not run `convert` over a nonempty workspace: use `resume`. Exact unchanged candidate hashes are reused; changed source, missing files or corruption invalidates reuse. Previous attempts and compiler failures remain inspectable.

## Real native verification

For an already built Fabric 26.3 candidate:

```powershell
.\devkit.cmd verify --jar "C:\Mods\MyMod.jar" --workspace "C:\DevKit-Runs\MyMod-native"
```

The native route fetches and records the exact official Fabric template revision, closes required mod dependencies, builds an independent test probe, and starts the **packaged candidate in production Minecraft**. It checks the loaded candidate's SHA-256 from inside Fabric, creates an integrated world, synchronizes a server-owned block to the client, captures the real rendered world, saves/closes it, reopens it, and checks persistence on both sides. Fresh logs, screenshots, dependency locks and proof are retained.

This automated native probe currently targets **Fabric 26.3**. Other versions and loaders retain their existing build and runtime-adapter routes; selecting them is not a promise that this particular probe supports them. A native world smoke test is not exhaustive mod gameplay, multiplayer or hardware-GPU performance certification.

The first native run needs network access for the official template, Gradle, game libraries/assets and required mods. On headless Linux it also needs Xvfb, Mesa/OpenGL, OpenAL and the narrator's native libraries. The repository's native CI workflow provisions these prerequisites. On a normal Windows desktop it uses the available graphics driver. This test fixture is not a substitute for a normal licensed gameplay account or launcher.

## Required dependencies without source surgery

```powershell
.\devkit.cmd dependencies --jar "C:\Mods\MyMod.jar" --minecraft 26.3 --loader-version 0.19.5 --output "C:\DevKit-Runs\MyMod-dependencies"
```

The resolver reads nested Fabric JARs, evaluates required version predicates using Fabric's semantics, queries exact target-compatible Modrinth releases, verifies provider SHA-512/SHA-256, and resolves transitive requirements. Provider hash metadata can expose an old bundled library whose broad metadata incorrectly suggests newer compatibility. Compatible external versions are installed in a separate managed directory; original mod and embedded JAR bytes are not edited or deleted.

Use every dependency listed in the resulting lock when installing the candidate. Optional recommendations are reported, not silently installed. A missing provider identity, incompatible explicit top-level mod, unsupported constraint or unresolved dependency remains a visible failure. Supply `--projects mapping.json` with exact mod-ID-to-Modrinth-project-ID mappings when provider names differ. `--audit-only` reads metadata without downloading. This is a Fabric resolver, not an unverified Forge/NeoForge metadata translator.

## Offline, integrity and recovery

`setup --offline` reuses a previously verified installed/private JDK without network access. `dependencies --offline` uses verified lockfile bytes. Native `--offline` additionally requires a cached `--template` and already populated Gradle/game caches. `convert --offline` prevents JDK provisioning; source-owned build tools may still perform their normal dependency resolution.

Private JDKs live under `~/.minecraft-dev-kit/cache` (override `DEVKIT_CACHE`). Private Windows Python lives under `%LOCALAPPDATA%\MinecraftDevKit` (override `DEVKIT_BOOTSTRAP_CACHE`). Set `DEVKIT_OFFLINE=1` to prevent the Windows bootstrap from downloading Python. No broad Java-process termination, global package installation or background watchdog is installed.

Candidate/evidence ZIPs are created exclusively rather than overwritten. Packaging re-hashes candidate and runtime dependency bytes. `VERIFICATION.json` distinguishes build-only `runtime-unverified`, separately scoped `native_runtime`, failed and stale proof states. Full command logs can contain project-specific text emitted by your own build tools; review them before sharing publicly.

## Tests and source

The canonical worker is `tools/minecraft-dev-kit` in [Enderloom](https://github.com/Herbertofury/Enderloom). In the complete skill bundle, `worker/` isolates this import graph from the preserved model, animation, server-asset, mapping, caching and older runtime tools in `scripts/` and `references/`.

Run `python scripts/devkit_qol_selftest.py` and `python scripts/devkit_workbench_selftest.py` from the repository kit, or replace `scripts/` with `worker/scripts/` in the skill bundle. The workbench fixture uses a real compiler/JVM but explicitly does **not** count as Minecraft. `devkit_setup_selftest.py` performs real provider downloads; the native CI executes real Minecraft independently.
