# Minecraft Dev Kit v7 - durable workbench

Use the same production conversion engine as Enderloom from a persistent command-line workspace. The package also retains the complete pre-existing model, animation, asset-conversion, mapping, caching and runtime-QA tools.

## Run on Windows

Install Python 3.13 and the JDK for the selected Minecraft target. Then open a terminal in the extracted folder:

```powershell
.\devkit.cmd doctor
.\devkit.cmd convert --project "C:\Mods\MyMod" --minecraft 26.3 --loader fabric --java 25 --java-path "C:\Java\jdk-25\bin\java.exe" --workspace "C:\DevKit-Runs\MyMod-26.3"
.\devkit.cmd status --workspace "C:\DevKit-Runs\MyMod-26.3"
.\devkit.cmd resume --workspace "C:\DevKit-Runs\MyMod-26.3"
.\devkit.cmd package --workspace "C:\DevKit-Runs\MyMod-26.3" --output "C:\DevKit-Releases\MyMod-candidate.zip"
```

Use `sh devkit.sh` on Linux/macOS. The standalone CLI uses an installed JDK; Enderloom's existing native managed-JDK path is unchanged. Official setup: [Python](https://www.python.org/downloads/), [Temurin](https://adoptium.net/temurin/releases/), [Git](https://git-scm.com/downloads).

## What is retained

Candidate JARs, immutable source intake, exact target manifest, complete command stdout/stderr, process IDs/timing, build/static/runtime receipts, previous attempt workspaces, per-cell states and SHA-256s. `resume` reuses intact unchanged candidates; corruption or changed inputs invalidates reuse. Workspaces are protected by OS-owned locks. Timeouts stop the owned process tree, not arbitrary Java processes.

## Supported routes and verification

The embedded worker's inferred migration route is same-loader legacy Fabric/NeoForge to 26.3. Conventional same-version builds and explicit Northpoint overlays retain their existing routes. Cross-loader conversions need their appropriate explicit adapter; choosing a target is not proof that every arbitrary mod is already supported.

`runtime-unverified` means a retained build candidate, NOT a certified playable Minecraft release. Configured JVM fixtures do not count as native Minecraft. Real client/server/integrated-server, Mixin, assets/gameplay and restart gates remain required for the relevant mod changes. `package` preserves that status instead of relabelling a candidate.

Exit 0 passes configured gates; exit 2 means a primary cell is blocked, failed or runtime-unverified; exit 3 means unresolved secondary cells. `status` can exit 0 while accurately reporting an unresolved conversion. Read the actual JSON state.

The package command excludes source trees and Gradle/account caches from candidate bundles. Full logs may contain project-specific values printed by build tools; review them before external sharing.

## Where the tools live

- `worker/`: exact repository-owned Northpoint engine and regression tests.
- `scripts/`, `references/`, `assets/`: complete existing Dev Kit tools and guidance, preserved rather than overwritten by the worker's differently versioned import graph.
- `evidence/`: observed test results and source/retention manifests.
- `SKILL.md`: workflow entrypoint for ChatGPT/Codex.

Run the workbench regression with `python worker/scripts/devkit_workbench_selftest.py`. It exercises actual javac, JAR packaging, JVM execution, cache reuse, corruption, compiler-error recovery and package integrity; its API fixture is explicitly not Minecraft.
