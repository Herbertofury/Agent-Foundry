#!/usr/bin/env python3
"""Exercise restart orchestration with two real OS processes (not Minecraft)."""
from pathlib import Path
import json
import os
import sys
import tempfile
from devkit_native_restart import run_phases, valid_restart


def main():
    from devkit_native import JAVA
    assert JAVA.count('finishOnTitleScreen(context);') == 2
    assert 'screen instanceof net.minecraft.client.gui.screens.TitleScreen' in JAVA
    assert 'net.aoba.gui.screens.MainMenuScreen' in JAVA
    assert '@Override public void init() { }' in JAVA
    assert JAVA.index('devkit-EXPECTED_MOD-custom-title-') < JAVA.index('client.gui.setScreen(new CleanupTitleScreen())')
    assert 'client.player != null || client.level != null || client.getSingleplayerServer() != null' in JAVA
    assert 'enableCustomTitle' not in JAVA, 'probe must not disable the user-visible custom menu'
    assert 'context.waitTicks(20);' in JAVA and 'buttons < 7' in JAVA
    assert 'button.onPress(new net.minecraft.client.input.MouseButtonInfo' in JAVA
    assert 'buttons.size() != 1' in JAVA and '.active' in JAVA and '.visible' in JAVA
    assert 'DEVKIT_NATIVE_CUSTOM_TITLE_INTERACTION' in JAVA
    with tempfile.TemporaryDirectory(prefix='devkit-restart-test-') as td:
        root=Path(td); probe=root/'probe';probe.mkdir()
        script=probe/'protocol.py'
        script.write_text('''import json,os,sys
from pathlib import Path
p=Path('run/devkit-native');p.mkdir(parents=True,exist_ok=True)
r='-PdevkitPhase=restart' in sys.argv
state=p/'devkit-restart.properties';proof=p/'devkit-runtime-proof.json'
if r:
    assert not proof.exists(), 'stale first proof survived'
    if os.environ.get('FAIL_RESTART'):raise SystemExit(9)
    first=int(state.read_text())
    proof.write_text(json.dumps({'artifact_sha256':'a'*64,'state':'runtime-smoke-verified','world_reopened':True,'client_server_sync':True,'process_restart':True,'first_process_id':first,'restart_process_id':os.getpid()}))
else:
    state.write_text(str(os.getpid()))
    proof.write_text(json.dumps({'artifact_sha256':'a'*64,'state':'runtime-smoke-verified','world_reopened':True,'client_server_sync':True}))
print('PHASE='+('restart' if r else 'initial'),flush=True)
''')
        for case in ['good','bad']:
            run=root/case;run.mkdir()
            env=dict(os.environ)
            if case=='bad':env['FAIL_RESTART']='1'
            cp=run_phases([sys.executable,str(script)],run=run,probe=probe,env=env,timeout=15)
            assert cp.returncode==(0 if case=='good' else 9)
            assert (run/'phase-evidence/initial-proof.json').is_file()
            assert (run/'commands/native-initial.process.json').is_file()
            assert (run/'commands/native-restart.process.json').is_file()
            final=probe/'run/devkit-native/devkit-runtime-proof.json'
            if case=='good':
                proof=json.loads(final.read_text());assert valid_restart(proof,'a'*64)
                assert not valid_restart(dict(proof,restart_process_id=proof['first_process_id']),'a'*64)
                assert not valid_restart(proof,'b'*64)
                assert not valid_restart(dict(proof,process_restart=False),'a'*64)
            else:assert not final.exists(),'failed restart reused the initial proof'
    print('Independent-process restart orchestration, fresh proof, failure retention and distinct-PID controls PASS (not a Minecraft test)')
    return 0

if __name__=='__main__':raise SystemExit(main())
