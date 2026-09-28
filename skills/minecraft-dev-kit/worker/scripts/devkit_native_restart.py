#!/usr/bin/env python3
"""Independent-JVM save/restart proof for the version-pinned native test harness."""
from __future__ import annotations
from pathlib import Path
import shutil
import subprocess
import time
from northpoint_execution import atomic_json, run_logged

# Isolated adapter, not shipped mod logic. This constructor was checked against
# the exact Fabric 26.3 API and is compiled before any Minecraft launch.
METHODS = r'''
  // Test-framework cleanup only, after the actual menu and closed-world state
  // were asserted and captured. Never ship this class or modify mod settings.
  private static final class CleanupTitleScreen extends net.minecraft.client.gui.screens.TitleScreen {
    @Override public void init() { }
  }
  private static void finishOnTitleScreen(ClientGameTestContext context) {
    boolean customTitle = context.computeOnClient(client -> {
      if (client.player != null || client.level != null || client.getSingleplayerServer() != null)
        throw new AssertionError("native verification returned before its world/server closed");
      var screen = client.gui.screen();
      if (screen instanceof net.minecraft.client.gui.screens.TitleScreen) return false;
      if (!"aoba".equals("EXPECTED_MOD") || screen == null ||
          !"net.aoba.gui.screens.MainMenuScreen".equals(screen.getClass().getName()))
        throw new AssertionError("unexpected terminal screen: " + (screen == null ? "null" : screen.getClass().getName()));
      return true;
    });
    if (customTitle) {
      // Let deferred UI extraction/presentation complete before evaluating the menu.
      context.waitTicks(20);
      context.runOnClient(client -> {
        long buttons = client.gui.screen().children().stream()
            .filter(child -> child instanceof net.minecraft.client.gui.components.AbstractButton).count();
        if (buttons < 7) throw new AssertionError("custom title lost its menu controls: " + buttons);
      });
      context.takeScreenshot("devkit-EXPECTED_MOD-custom-title-" + System.getProperty("devkit.phase", "initial"));
      // Fabric's helper accepts Button/CycleButton, not arbitrary AbstractButton subclasses.
      context.runOnClient(client -> {
        var buttons = client.gui.screen().children().stream()
            .filter(child -> child instanceof net.minecraft.client.gui.components.AbstractButton)
            .map(child -> (net.minecraft.client.gui.components.AbstractButton) child)
            .filter(button -> "Singleplayer".equals(button.getMessage().getString())).toList();
        if (buttons.size() != 1 || !buttons.getFirst().active || !buttons.getFirst().visible)
          throw new AssertionError("custom Singleplayer control is missing, ambiguous or disabled");
        var button = buttons.getFirst();
        System.out.println("DEVKIT_CUSTOM_BUTTON:" + button.getX() + "," + button.getY() + "," + button.getWidth() + "," + button.getHeight());
        button.onPress(new net.minecraft.client.input.MouseButtonInfo(com.mojang.blaze3d.platform.InputConstants.MOUSE_BUTTON_LEFT, 0));
      });
      context.waitForScreen(net.minecraft.client.gui.screens.worldselection.SelectWorldScreen.class);
      context.waitTicks(5);
      context.takeScreenshot("devkit-EXPECTED_MOD-world-menu-" + System.getProperty("devkit.phase", "initial"));
      context.clickScreenButton("gui.back");
      context.waitFor(client -> client.gui.screen() != null &&
          "net.aoba.gui.screens.MainMenuScreen".equals(client.gui.screen().getClass().getName()));
      System.out.println("DEVKIT_NATIVE_CUSTOM_TITLE_INTERACTION:EXPECTED_MOD");
      System.out.println("DEVKIT_NATIVE_CUSTOM_TITLE_PRESERVED:EXPECTED_MOD");
      context.runOnClient(client -> client.gui.setScreen(new CleanupTitleScreen()));
    }
  }
  private static void recordRestart(TestWorldSave save, BlockPos marker) throws Exception {
    java.util.Properties state = new java.util.Properties();
    state.setProperty("artifact", "EXPECTED_SHA");
    state.setProperty("save", save.getSaveDirectory().toAbsolutePath().normalize().toString());
    state.setProperty("x", Integer.toString(marker.getX()));
    state.setProperty("y", Integer.toString(marker.getY()));
    state.setProperty("z", Integer.toString(marker.getZ()));
    state.setProperty("pid", Long.toString(ProcessHandle.current().pid()));
    try (var output = Files.newOutputStream(Path.of("devkit-restart.properties"))) {
      state.store(output, "Dev Kit isolated QA save; never a user world");
    }
  }
  private static void restart(ClientGameTestContext context) throws Exception {
    java.util.Properties state = new java.util.Properties();
    try (var input = Files.newInputStream(Path.of("devkit-restart.properties"))) { state.load(input); }
    if (!"EXPECTED_SHA".equals(state.getProperty("artifact"))) throw new AssertionError("stale restart state");
    long firstPid = Long.parseLong(state.getProperty("pid"));
    long currentPid = ProcessHandle.current().pid();
    if (firstPid == currentPid) throw new AssertionError("restart used the original JVM");
    Path directory = Path.of(state.getProperty("save")).toAbsolutePath().normalize();
    if (!directory.startsWith(Path.of("saves").toAbsolutePath().normalize()) || !Files.isRegularFile(directory.resolve("level.dat")))
      throw new AssertionError("restart save is missing or escapes isolated QA saves");
    BlockPos marker = new BlockPos(Integer.parseInt(state.getProperty("x")), Integer.parseInt(state.getProperty("y")), Integer.parseInt(state.getProperty("z")));
    TestWorldSave save = new net.fabricmc.fabric.impl.client.gametest.world.TestWorldSaveImpl(context, directory);
    try (TestSingleplayerContext world = save.open()) {
      world.getConnection().waitForChunksRender();
      world.getServer().runOnServer(server -> {
        if (!world.getConnection().getServerLevel().getBlockState(marker).is(Blocks.GOLD_BLOCK))
          throw new AssertionError("server lost the saved marker across JVM restart");
      });
      context.runOnClient(client -> {
        if (client.player == null || !client.level.getBlockState(marker).is(Blocks.GOLD_BLOCK))
          throw new AssertionError("client did not load the saved marker after JVM restart");
      });
      context.takeScreenshot("devkit-EXPECTED_MOD-process-restarted-world");
    }
    Files.writeString(Path.of("devkit-runtime-proof.json"), "{\"state\":\"runtime-smoke-verified\",\"artifact_sha256\":\"EXPECTED_SHA\",\"modid\":\"EXPECTED_MOD\",\"world_reopened\":true,\"client_server_sync\":true,\"process_restart\":true,\"first_process_id\":" + firstPid + ",\"restart_process_id\":" + currentPid + "}");
    System.out.println("DEVKIT_NATIVE_PROCESS_RESTARTED:EXPECTED_MOD");
    finishOnTitleScreen(context);
  }
'''


def extend_probe(java: str, gradle: str) -> tuple[str, str]:
    anchor = '      AtomicReference<BlockPos> marker = new AtomicReference<>();'
    if java.count(anchor) != 1 or java.count('      Files.writeString(Path.of("devkit-runtime-proof.json")') != 1:
        raise ValueError('native Java probe changed; reconcile the restart adapter')
    java = java.replace(anchor, '      if ("restart".equals(System.getProperty("devkit.phase"))) { restart(context); return; }\n' + anchor)
    java = java.replace('      Files.writeString(Path.of("devkit-runtime-proof.json")',
                        '      recordRestart(save, marker.get());\n      Files.writeString(Path.of("devkit-runtime-proof.json")')
    marker = '      System.out.println("DEVKIT_NATIVE_PROOF_COMPLETE:EXPECTED_MOD");'
    if java.count(marker) != 1:
        raise ValueError('native completion marker changed; reconcile custom-title cleanup')
    java = java.replace(marker, marker + '\n      finishOnTitleScreen(context);')
    end = java.rfind('}')
    java = java[:end] + METHODS + java[end:]
    anchor = '  jvmArgs.add("-Dfabric.client.gametest")'
    if gradle.count(anchor) != 1:
        raise ValueError('native Gradle task changed; reconcile the restart adapter')
    gradle = gradle.replace(anchor, anchor + '\n  jvmArgs.add("-Ddevkit.phase=" + providers.gradleProperty("devkitPhase").getOrElse("initial"))')
    return java, gradle


def valid_restart(proof: dict, digest: str) -> bool:
    first, second = proof.get('first_process_id'), proof.get('restart_process_id')
    return (proof.get('artifact_sha256') == digest and proof.get('world_reopened') is True
            and proof.get('client_server_sync') is True and proof.get('process_restart') is True
            and type(first) is int and type(second) is int and first > 0 and second > 0 and first != second)


def run_phases(command: list[str], *, run: Path, probe: Path, env: dict[str, str], timeout: float) -> subprocess.CompletedProcess:
    """Retain complete evidence for both processes; startup is never restart proof."""
    started = time.monotonic()
    process = run_logged(command, directory=run / 'commands', name='native-initial', cwd=probe, env=env, timeout=timeout)
    if process.returncode:
        return process
    game = probe / 'run/devkit-native'
    first = game / 'devkit-runtime-proof.json'
    state = game / 'devkit-restart.properties'
    if not first.is_file() or not state.is_file():
        raise ValueError('initial native process exited without its proof and restart state')
    evidence = run / 'phase-evidence'; evidence.mkdir()
    shutil.copyfile(first, evidence / 'initial-proof.json')
    if (game / 'logs/latest.log').is_file():
        shutil.copyfile(game / 'logs/latest.log', evidence / 'initial-client.log')
    first.unlink()  # Delete only disposable initial evidence after archiving it.
    remaining = timeout - (time.monotonic() - started)
    if remaining <= 0:
        raise TimeoutError('native verification budget exhausted before independent JVM restart')
    atomic_json(run / 'phase.json', {'state': 'restart-running', 'initial_returncode': process.returncode})
    restarted = run_logged(command + ['-PdevkitPhase=restart'], directory=run / 'commands', name='native-restart',
                           cwd=probe, env=env, timeout=remaining)
    if restarted.returncode == 0 and not first.is_file():
        raise ValueError('restarted process returned success without fresh runtime proof')
    atomic_json(run / 'phase.json', {'state': 'completed' if restarted.returncode == 0 else 'restart-failed',
                                    'initial_returncode': process.returncode, 'restart_returncode': restarted.returncode})
    return restarted
