#!/usr/bin/env python3
"""Exercise the normal CLI with actual javac, JAR packaging, JVM execution and recovery."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import zipfile
from northpoint_production_driver_selftest import fixture

SCRIPTS = Path(__file__).resolve().parent
CLI = SCRIPTS / 'devkit.py'


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hash(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): digest(p) for p in root.rglob('*') if p.is_file()}


def run(argv: list[str], allowed: set[int] = {0}, *, env=None) -> float:
    start = time.monotonic()
    cp = subprocess.run([sys.executable, *argv], text=True, capture_output=True, env=env, timeout=120)
    if cp.returncode not in allowed:
        raise AssertionError(f'code={cp.returncode}: {argv}\n{cp.stdout}\n{cp.stderr}')
    return time.monotonic() - start


def main() -> int:
    base = os.environ.get('NORTHPOINT_TEST_ROOT')
    root = Path(tempfile.mkdtemp(prefix='workbench-', dir=base)).resolve()
    project, workspace = root / 'project', root / 'session'
    fixture(project)
    original = source_hash(project)
    command = [str(CLI), 'convert', '--project', str(project), '--minecraft', '1.21.1',
               '--loader', 'fabric', '--java', '21', '--workspace', str(workspace), '--timeout', '90']
    first_seconds = run(command)
    result = read(workspace / 'result.json')
    cell = result['cells'][0]
    assert result['all_passed'] and cell['attempts'] == 1, result
    artifact = Path(cell['artifact']['path'])
    assert artifact.is_file() and cell['artifact']['integrity_verified']
    with zipfile.ZipFile(artifact) as archive:
        assert read(workspace / 'intake.json')
        assert json.loads(archive.read('fabric.mod.json'))['id'] == 'stoneproof'
        assert 'example/ProofMod.class' in archive.namelist()
    resume_cmd = [str(CLI), 'resume', '--workspace', str(workspace), '--timeout', '90']
    resume_seconds = run(resume_cmd)
    resumed = read(workspace / 'result.json')
    assert resumed['last_run']['built'] == [] and resumed['cells'][0]['attempts'] == 1, resumed
    assert resumed['cells'][0]['artifact']['sha256'] == cell['artifact']['sha256']
    assert source_hash(project) == original, 'normal build changed original source'
    artifact.write_bytes(artifact.read_bytes() + b'corrupt')
    run([str(CLI), 'package', '--workspace', str(workspace), '--output', str(root / 'bad.zip')], {1})
    run(resume_cmd)
    assert read(workspace / 'result.json')['cells'][0]['attempts'] == 2
    history = workspace / 'state/work/history/mc-1.21.1-fabric'
    assert any(history.glob('*/receipt.json')), 'previous attempt evidence was deleted'
    source = project / 'src/main/java/example/ProofMod.java'
    good = source.read_text()
    source.write_text('not valid Java')
    run(resume_cmd, {2})
    failed = read(workspace / 'result.json')
    assert not failed['all_passed'] and failed['cells'][0]['state'] == 'failed'
    errors = list((workspace / 'state/work/mc-1.21.1-fabric/evidence/commands').glob('*.stderr.txt'))
    assert any('error' in p.read_text().lower() for p in errors), 'compiler failure evidence lost'
    source.write_text(good)
    run(resume_cmd)
    assert read(workspace / 'result.json')['all_passed']
    package_path = root / 'candidate-and-evidence.zip'
    run([str(CLI), 'package', '--workspace', str(workspace), '--output', str(package_path)])
    with zipfile.ZipFile(package_path) as archive:
        assert archive.testzip() is None
        assert json.loads(archive.read('VERIFICATION.json'))['all_passed']
        for line in archive.read('PACKAGE-SHA256SUMS.txt').decode().splitlines():
            expected, path = line.split('  ', 1)
            assert hashlib.sha256(archive.read(path)).hexdigest() == expected
    smoke = root / 'smoke'
    run([str(SCRIPTS / 'northpoint_public_mod_smoke.py'), '--project', str(project), '--minecraft', '1.21.1',
         '--loader', 'fabric', '--java', '21', '--workspace', str(smoke), '--timeout', '90'])
    summary = read(smoke / 'summary.json')
    assert Path(summary['artifact_path']).is_file() and (smoke / 'receipt.json').is_file()
    assert digest(Path(summary['artifact_path'])) == summary['sha256']
    # Unconfigured actual-game verification must remain explicitly unverified.
    config = read(project / 'northpoint.project.json')
    config['runtime'] = {'required': True}
    (project / 'northpoint.project.json').write_text(json.dumps(config))
    pending = root / 'pending-runtime'
    run(command[:command.index('--workspace')] + ['--workspace', str(pending), '--timeout', '90'], {2})
    pending_result = read(pending / 'result.json')
    assert not pending_result['all_passed'] and pending_result['cells'][0]['state'] == 'runtime-unverified'
    run([str(CLI), 'resume', '--workspace', str(pending), '--timeout', '90'], {2})
    assert read(pending / 'result.json')['last_run']['built'] == []
    run([str(CLI), 'package', '--workspace', str(pending), '--output', str(root / 'runtime-unverified.zip')])
    with zipfile.ZipFile(root / 'runtime-unverified.zip') as archive:
        assert not json.loads(archive.read('VERIFICATION.json'))['all_passed']
    print(json.dumps({'status': 'PASS', 'workspace': str(root), 'real_javac_and_jvm': True,
                      'minecraft_runtime': 'NOT_TESTED_BY_THIS_FIXTURE',
                      'initial_seconds': round(first_seconds, 4), 'resume_seconds': round(resume_seconds, 4),
                      'resume_rebuilt_cells': 0, 'cases': ['durable-cli-artifact', 'exact-hash-resume',
                       'source-immutability', 'corruption-rebuild', 'history-retention', 'compiler-failure-recovery',
                       'package-integrity', 'durable-public-smoke', 'runtime-unverified-preserved']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
