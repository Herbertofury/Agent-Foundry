#!/usr/bin/env python3
"""Real provider downloads and private setup; run only in the explicit network CI lane."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from devkit_toolchains import ensure_jdk, sha256_file


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix='devkit-setup-proof-', dir=os.environ.get('RUNNER_TEMP'))).resolve()
    before_path, before_home = os.environ.get('PATH'), os.environ.get('JAVA_HOME')
    first = ensure_jdk(25, root=root / 'jdk', managed_only=True)
    second = ensure_jdk(25, root=root / 'jdk', managed_only=True, offline=True)
    assert first['java_sha256'] == second['java_sha256'] and second['source'] == 'managed-cache'
    assert os.environ.get('PATH') == before_path and os.environ.get('JAVA_HOME') == before_home
    receipt = {'managed_java': first, 'offline_cache': second, 'global_environment_unchanged': True}
    if os.name == 'nt':
        kit = Path(__file__).resolve().parents[1]
        bootstrap = kit / 'bootstrap.ps1'
        env = dict(os.environ, DEVKIT_BOOTSTRAP_FORCE='1', DEVKIT_BOOTSTRAP_CACHE=str(root / 'python cache'))
        command = ['powershell.exe','-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',str(bootstrap),'doctor']
        first_run = subprocess.run(command, env=env, text=True, capture_output=True, timeout=180)
        (root / 'bootstrap-first.stdout.txt').write_text(first_run.stdout)
        (root / 'bootstrap-first.stderr.txt').write_text(first_run.stderr)
        assert first_run.returncode == 0, (first_run.stdout, first_run.stderr)
        env['DEVKIT_OFFLINE'] = '1'
        cached = subprocess.run(command, env=env, text=True, capture_output=True, timeout=45)
        assert cached.returncode == 0, (cached.stdout,cached.stderr)
        info = json.loads(cached.stdout)
        runtime = Path(info['python_executable'])
        assert runtime.is_relative_to(root / 'python cache'), info
        assert info['python'] == '3.13.15'
        pth = runtime.parent / 'python313._pth'; original = pth.read_bytes()
        pth.write_bytes(original + b'\n# corrupted fixture\n')
        rejected = subprocess.run(command,env=env,text=True,capture_output=True,timeout=45)
        assert rejected.returncode != 0, 'tampered private Python accepted while offline'
        pth.write_bytes(original)
        cp = subprocess.run([str(runtime), str(kit / 'scripts/devkit_workbench_selftest.py')],
                            text=True,capture_output=True,env=env,timeout=150)
        (root / 'private-python-workbench.log').write_text(cp.stdout + '\n' + cp.stderr)
        assert cp.returncode == 0, (cp.stdout,cp.stderr)
        receipt.update(python=info, private_python_sha256=sha256_file(runtime),
                       private_python_real_workbench=True, bootstrap_tamper_rejected=True)
    (root / 'SETUP-PROOF.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps({'status':'PASS','evidence':str(root),**receipt},indent=2))
    return 0
if __name__ == '__main__':raise SystemExit(main())
