# Minecraft Dev Kit v8: managed setup and native runtime

Use the complete isolated worker, not the historical top-level Northpoint scripts.

## First run

On Windows launch `devkit.cmd`. It reuses Python 3.12+ when suitable, otherwise verifies and provisions private Python 3.13.15 from python.org. Do not modify global PATH or request administrator access. On Linux/macOS run `sh devkit.sh` with Python 3.12+; the guided workflow selects and provisions a matching private Temurin JDK. Validate explicit JDKs by checking both java and javac.

## Production workflow

Use `convert --project SOURCE --minecraft 26.3 --loader fabric --workspace SEPARATE_WORKSPACE --verify`. Continue with `resume --workspace SEPARATE_WORKSPACE`, inspect with `status`, and deliver with `package --workspace SEPARATE_WORKSPACE --output RELEASE.zip`.

Use `dependencies --help` for nested/transitive Fabric dependency installation, explicit provider mappings, audit-only and offline reuse. Use `verify --help` to test an existing Fabric 26.3 production JAR. Keep every locked dependency alongside the candidate; do not remove or rewrite embedded original JARs. Report optional dependencies rather than silently adding them.

## Evidence and scope

The native probe validates the candidate SHA-256 inside Fabric, renders an integrated world, checks server-to-client block synchronization, saves/closes/reopens that save, exits the JVM, starts a second JVM, reopens the same save, verifies persistence, and captures each phase. Preserve and capture custom mod title screens before test-framework cleanup. Inspect native-result.json, phase evidence, screenshots, dependency-lock.json, and process receipts. Do not promote startup, a screenshot alone, compilation, or a simulated receipt into complete runtime proof.

This automatic native adapter is Fabric 26.3. Retain older Forge/NeoForge and other loader-specific tools for their intended runtime workflows; do not imply this adapter covers all loaders or exhaustive mod gameplay. The isolated Fabric test profile does not certify authenticated multiplayer. Software rendering does not certify RTX hardware performance.

## Regression loop

Run the implicated devkit self-test first. Run workbench/resume/QoL tests at convergence; preserve canonical CI and native run IDs. Retain shader, water-overlay, mouse-invoker, chunk-packet, and independent-restart regressions. Update checksum pins atomically with module bytes. Do not rerun already-green conversion builds unless input, worker or proof dependencies change.

The v7 guide and evidence remain historical; this guide and evidence/v8 describe the current worker.

## Rendering ABI regression

For 26.3 transparent-but-compiling custom UI, inspect inline DynamicTransforms layouts against DynamicGpuData.Transform.write. The exact legacy four-field order is migrated by northpoint_shader_rules.py without changing shader math. Run devkit_shader_selftest.py and inspect the actual native menu before and after a separate JVM restart. A passing compiler or successful button callback does not prove visible controls.
