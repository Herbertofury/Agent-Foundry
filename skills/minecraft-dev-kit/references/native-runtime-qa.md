# Native Minecraft runtime QA

## Goal

Prove the changed mod in the real target Minecraft runtime. Native QA is not a screenshot generator; it is an executable release gate with visual/log/state evidence.

## General sequence

1. Build the exact project artifact with the intended Java + loader toolchain.
2. Prepare a disposable deterministic QA save from a known-good world or create a purpose-built test world.
3. Enable commands/op-level QA only in the disposable test save.
4. Normalize time/weather/camera and control natural spawning.
5. Extract platform-correct LWJGL natives.
6. Start the actual client under a real or virtual display.
7. Wait for authoritative readiness: the integrated player joins and the changed mod is loaded.
8. Drive the workflow from deterministic in-game mechanisms whenever possible.
9. Assert authoritative server/client state for each phase.
10. Capture the real window and preserve logs/markers.
11. Close Minecraft cleanly, then post-process evidence.
12. Restart when state/config persistence matters.

## Headless Linux Forge pattern

A proven Linux path uses:

- Java 17 for Minecraft 1.20.1 Forge 47.x;
- Gradle/ForgeGradle cache compatible with the project;
- Xvfb virtual display;
- Mesa software rendering via `LIBGL_ALWAYS_SOFTWARE=1`;
- Linux LWJGL native libraries extracted from verified classifier JARs;
- OpenAL Soft null backend (`ALSOFT_DRIVERS=null`) when no audio device exists;
- FFmpeg X11 capture with mouse drawing disabled under bare Xvfb;
- deterministic Quick Play singleplayer save;
- integrated-server log markers as source of truth.

Example environment shape:

```bash
export DISPLAY=:99
export LIBGL_ALWAYS_SOFTWARE=1
export ALSOFT_DRIVERS=null
export JAVA_TOOL_OPTIONS="${JAVA_TOOL_OPTIONS:-} -Dorg.lwjgl.librarypath=$NATIVES -Djava.library.path=$NATIVES"
Xvfb "$DISPLAY" -screen 0 1280x720x24 -nolisten tcp &
ffmpeg -nostdin -f x11grab -draw_mouse 0 -video_size 1280x720 -framerate 30 -i "$DISPLAY.0" ...
gradle --offline --no-daemon runClient "--args=--width 1280 --height 720 --quickPlaySingleplayer QA-World"
```

Adapt the exact command to the project's loader and Gradle run configuration.

## World invariants

Do not trust a copied server QA world blindly. Validate:

- `allowCommands=1` when commands/datapack QA needs operator permissions;
- intended difficulty;
- game mode and player permissions;
- deterministic seed/world type;
- datapack enabled state;
- no corrupted/truncated `level.dat`;
- natural spawning policy.

If the test subject is a MONSTER-category custom entity, do **not** use Peaceful simply to suppress random mobs. Use Normal/Easy/Hard plus `doMobSpawning=false`; otherwise Minecraft can delete the intended QA entity after a successful summon.

## Deterministic phase driver

Prefer a scheduled datapack or mod-owned QA command that:

- clears only prior QA-tagged entities;
- spawns exact entities/states at fixed coordinates;
- sets `NoAI`, persistence, invulnerability, labels, and orientation where appropriate;
- logs an authoritative phase marker with expected counts;
- waits long enough to sample the full animation/action;
- advances through every required phase;
- cleans up and logs final removal count.

Use X11/keyboard automation only for camera/focus/clean-close assistance, not as the correctness source of truth.

## Visual evidence

For entity/model/animation work, capture:

- baseline front/three-quarter/side/back when practical;
- rest/pose variants;
- representative early/mid/late animation frames;
- charged/emissive/alternate state;
- motion strips or short clips for loops/actions;
- a contact sheet for at-a-glance review;
- full client log and phase markers.

Use the actual project texture/model/runtime code. Never substitute generated imagery for a native screenshot.

## Failure classification

### Entity command says success but subject is missing

Check difficulty/despawn category, state synchronization, chunk position, kill/clear selectors, render distance, and server-side live entity count before blaming the renderer.

### Shadow/particles remain but model vanishes over time

Suspect a render transform accumulator. Check custom root/parent `ModelPart`s that vanilla `setupAnim`/`resetPose` does not reset. Restore bind pose before applying additive transforms each frame.

### First native run works, next run fails in early Forge window/config

Inspect generated `run/config/fml.toml` or equivalent for truncation from prior hard kills. Repair/regenerate the disposable runtime config; do not mutate user gameplay config without reason.

### `liblwjgl.so` missing or platform shows Windows on Linux

Inspect cached native classifier JARs rather than trusting a platform-specific generated POM copied from another OS. Extract Linux natives and set `org.lwjgl.librarypath` + `java.library.path` explicitly.

### Long capture appears to hang in an agent/container

Check the wrapper execution timeout. Run Minecraft detached and poll readiness/phase markers. Do not interpret the orchestration tool killing a foreground command as a Minecraft hang.

### Full Mojang asset object cache unavailable

If testing sound/resource completeness, block and populate the full cache. If only testing model/texture rendering, allow a visual-only fallback only after proving the mapped client JAR contains the required vanilla texture resources; state that external sound objects remain unverified.

## Packaged Forge client escalation

When a failure can depend on production SRG names, direct Mixin member names, reflection strings, or lambda/SAM linkage, escalate beyond `runClient` / `forgeclientuserdev` to the real packaged `forgeclient` path. Read `forge-production-client-qa.md` before constructing that harness.

For restored/offline client QA, verify the asset index and every referenced object, restore platform-correct natives, and keep launcher/profile artifacts as immutable provenance. If client execution must outlive the orchestration command, launch detached, record the exact PID, poll milestones only, and clean up only that PID/window.
