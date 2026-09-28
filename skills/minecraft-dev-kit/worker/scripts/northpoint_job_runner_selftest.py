#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib, shutil, subprocess, sys, tempfile, zipfile

from northpoint_job_runner import input_fingerprint

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'scripts' / 'northpoint_job_runner.py'
DRIVER = ROOT / 'scripts' / 'northpoint_fixture_driver.py'


def write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text, encoding='utf-8')


def run_json(cmd: list[str]) -> dict:
    cp = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if cp.returncode:
        raise AssertionError(f"command failed {cp.returncode}: {cp.stderr}\n{cp.stdout}")
    lines = [x for x in cp.stdout.splitlines() if x.strip()]
    return json.loads(lines[-1])


def fixture(project: pathlib.Path) -> None:
    write(project / 'src/common/java/example/HelloMod.java', '''package example; public class HelloMod { public static void main(String[] a){ System.out.print(Version.NAME+"|"+Platform.NAME+"|"+Flavor.NAME); } }\n''')
    write(project / 'src/common/java/example/Flavor.java', 'package example; public class Flavor { public static final String NAME="common"; }\n')
    for loader in ('fabric', 'forge', 'neoforge'):
        write(project / f'src/loader/{loader}/java/example/Platform.java', f'package example; public class Platform {{ public static final String NAME="{loader}"; }}\n')
        write(project / f'src/loader/{loader}/java/example/Flavor.java', f'package example; public class Flavor {{ public static final String NAME="{loader}"; }}\n')
    for mc in ('1.20.1', '1.21.1'):
        write(project / f'src/version/{mc}/java/example/Version.java', f'package example; public class Version {{ public static final String NAME="{mc}"; }}\n')
    write(project / 'src/cell/mc-1.21.1-fabric/java/example/Flavor.java', 'package example; public class Flavor { public static final String NAME="fabric-cell"; }\n')


def manifest(project: pathlib.Path) -> dict:
    return {
      'schema_version': 1,
      'project_root': str(project),
      'primary_cell': 'mc-1.21.1-fabric',
      'cells': [
        {'id':'mc-1.21.1-fabric','minecraft':'1.21.1','loader':'fabric','java':21,'support_state':'stable','primary':True},
        {'id':'mc-1.21.1-neoforge','minecraft':'1.21.1','loader':'neoforge','java':21,'support_state':'stable'},
        {'id':'mc-1.20.1-fabric','minecraft':'1.20.1','loader':'fabric','java':17,'support_state':'stable'},
        {'id':'mc-1.20.1-forge','minecraft':'1.20.1','loader':'forge','java':17,'support_state':'stable'}
      ],
      'config': {'fixture':'simple-mod','zero_loss':True}
    }


def jar_runtime_marker(jar: pathlib.Path) -> str:
    with zipfile.ZipFile(jar) as z:
        return json.loads(z.read('META-INF/northpoint-cell.json'))['runtime_output']


def main() -> int:
    with tempfile.TemporaryDirectory(prefix='northpoint-job-selftest-') as td:
        base = pathlib.Path(td); project = base / 'project'; state = base / 'state'
        fixture(project)
        manifest_value = manifest(project)
        probe_cell = manifest_value['cells'][0]
        fp_a = input_fingerprint(project, probe_cell, DRIVER, manifest_value['config'], {'artifact_fingerprint': 'engine-a'})
        fp_b = input_fingerprint(project, probe_cell, DRIVER, manifest_value['config'], {'artifact_fingerprint': 'engine-b'})
        assert fp_a != fp_b, 'artifact-engine changes must invalidate reusable passed artifacts'
        mf = base / 'manifest.json'; mf.write_text(json.dumps(manifest_value, indent=2), encoding='utf-8')
        cmd = [sys.executable, str(RUNNER), '--manifest', str(mf), '--driver', str(DRIVER), '--state-dir', str(state), '--max-workers', '4']
        first = run_json(cmd)
        assert first['status'] == 'PASS', first
        assert first['run']['built'] == ['mc-1.20.1-fabric','mc-1.20.1-forge','mc-1.21.1-fabric','mc-1.21.1-neoforge'], first
        release = state / 'release'
        jars = sorted(release.glob('mc-*.jar'))
        assert len(jars) == 4, jars
        markers = {p.stem: jar_runtime_marker(p) for p in jars}
        assert markers['mc-1.21.1-fabric'] == '1.21.1|fabric|fabric-cell', markers
        second = run_json(cmd)
        assert second['run']['built'] == [], second
        assert len(second['run']['reused']) == 4, second
        fabric = project / 'src/loader/fabric/java/example/Platform.java'
        fabric.write_text('package example; public class Platform { public static final String NAME="fabric"; }\n// fingerprint-only fixture edit\n', encoding='utf-8')
        third = run_json(cmd)
        assert third['run']['built'] == ['mc-1.20.1-fabric','mc-1.21.1-fabric'], third
        assert third['run']['reused'] == ['mc-1.20.1-forge','mc-1.21.1-neoforge'], third
        matrix = json.loads((release / 'release-matrix.json').read_text(encoding='utf-8'))
        assert sum(1 for r in matrix['cells'] if r['state']=='passed') == 4
        sums = [line for line in (release / 'SHA256SUMS.txt').read_text().splitlines() if line.strip()]
        assert len(sums) == 4
        print(json.dumps({'status':'PASS','first':first['run'],'resume':second['run'],'fabric_edit':third['run'],'markers':markers}, indent=2))
    print('Northpoint resumable job runner self-test: PASS')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())