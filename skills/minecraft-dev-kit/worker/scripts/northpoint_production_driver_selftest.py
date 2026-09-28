#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import zipfile

from northpoint_production_driver import materialize_legacy_target
from northpoint_target_26_3 import ConversionBlock

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'scripts' / 'northpoint_job_runner.py'
DRIVER = ROOT / 'scripts' / 'northpoint_production_driver.py'


def write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def run_json(cmd: list[str], allowed: set[int] = {0}) -> dict:
    cp = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if cp.returncode not in allowed:
        raise AssertionError(f'command failed {cp.returncode}: {cp.stderr}\n{cp.stdout}')
    lines = [x.strip() for x in cp.stdout.splitlines() if x.strip()]
    if not lines:
        raise AssertionError(f'command emitted no JSON: {cp.stderr}')
    return json.loads(lines[-1])


def fixture(project: pathlib.Path) -> None:
    cfg = {
        'schema_version': 1,
        'mod_id': 'stoneproof',
        'build': {
            'mode': 'javac',
            'source_roots': ['src/main/java'],
            'compile_only_source_roots': ['qa-api/java'],
            'resource_roots': ['src/main/resources'],
        },
        'linkage': {
            'target_classes': '__compile_only__',
            'prefixes': ['net/fabricmc/'],
        },
        'runtime': {
            'required': True,
            'command': ['java', '-cp', '{artifact}{pathsep}{compile_only}', 'example.Smoke'],
            'stdout_contains': 'RUNTIME:',
            'timeout': 30,
        },
    }
    write(project / 'northpoint.project.json', json.dumps(cfg, indent=2) + '\n')
    write(project / 'qa-api/java/net/fabricmc/api/ModInitializer.java',
          'package net.fabricmc.api; public interface ModInitializer { void onInitialize(); }\n')
    write(project / 'src/main/java/example/ProofMod.java', '''package example;
import net.fabricmc.api.ModInitializer;
public final class ProofMod implements ModInitializer {
  public static boolean initialized;
  @Override public void onInitialize(){ initialized = true; }
}
''')
    write(project / 'src/main/java/example/Smoke.java', '''package example;
public final class Smoke {
  public static void main(String[] args){ new ProofMod().onInitialize(); if(!ProofMod.initialized) throw new IllegalStateException(); System.out.print("RUNTIME:"+Version.MC); }
}
''')
    write(project / 'src/main/resources/fabric.mod.json', json.dumps({
        'schemaVersion': 1,
        'id': 'stoneproof',
        'version': '1.0.0',
        'name': 'Stoneproof',
        'environment': '*',
        'entrypoints': {'main': ['example.ProofMod']},
        'depends': {'fabricloader': '>=0.15.0'},
    }, indent=2) + '\n')
    write(project / 'src/main/resources/assets/stoneproof/lang/en_us.json',
          json.dumps({'item.stoneproof.proof': 'Proof Item'}, indent=2) + '\n')
    write(project / 'src/main/resources/data/stoneproof/tags/items/proof.json',
          json.dumps({'replace': False, 'values': ['minecraft:stone']}, indent=2) + '\n')
    for mc in ('1.20.1', '1.21.1', '26.3'):
        write(project / f'overlays/version/{mc}/src/main/java/example/Version.java',
              f'package example; public final class Version {{ public static final String MC="{mc}"; }}\n')


def manifest(project: pathlib.Path) -> dict:
    return {
        'schema_version': 1,
        'project_root': str(project),
        'primary_cell': 'mc-1.21.1-fabric',
        'cells': [
            {'id': 'mc-1.21.1-fabric', 'minecraft': '1.21.1', 'loader': 'fabric', 'java': 21, 'support_state': 'stable', 'primary': True},
            {'id': 'mc-1.20.1-fabric', 'minecraft': '1.20.1', 'loader': 'fabric', 'java': 17, 'support_state': 'stable'},
            {'id': 'mc-26.3-fabric', 'minecraft': '26.3', 'loader': 'fabric', 'java': 25, 'support_state': 'stable'},
        ],
        'config': {'graduation': 'production-small-mod', 'zero_loss': True},
    }


def runtime_marker(jar: pathlib.Path) -> str:
    with zipfile.ZipFile(jar) as z:
        value = json.loads(z.read('fabric.mod.json'))
        assert value['id'] == 'stoneproof'
        assert 'assets/stoneproof/lang/en_us.json' in z.namelist()
        assert 'data/stoneproof/tags/items/proof.json' in z.namelist()
    return jar.name


def main() -> int:
    with tempfile.TemporaryDirectory(prefix='northpoint-production-driver-') as td:
        root = pathlib.Path(td)
        project, state = root / 'project', root / 'state'
        fixture(project)

        # An inferred 26.3 request must never build an ambiguous legacy source unchanged.
        ambiguous = root / 'ambiguous-source'
        write(ambiguous / 'build.gradle', "plugins { id 'net.fabricmc.fabric-loom' version '1.17-SNAPSHOT' }\n")
        write(ambiguous / 'src/main/resources/fabric.mod.json', json.dumps({
            'schemaVersion': 1, 'id': 'ambiguous', 'version': '1.0.0', 'name': 'Ambiguous',
            'depends': {'fabricloader': '>=0.19.5'},
        }, indent=2) + '\n')
        try:
            materialize_legacy_target(
                ambiguous,
                {'id': 'mc-26.3-fabric', 'minecraft': '26.3', 'loader': 'fabric', 'java': 25},
                root / 'ambiguous-work',
            )
            raise AssertionError('ambiguous source version incorrectly received an unchanged 26.3 pass')
        except ConversionBlock as exc:
            assert 'source Minecraft version could not be determined exactly' in str(exc), exc

        manifest_file = root / 'manifest.json'
        manifest_file.write_text(json.dumps(manifest(project), indent=2) + '\n', encoding='utf-8')
        cmd = [sys.executable, str(RUNNER), '--manifest', str(manifest_file), '--driver', str(DRIVER), '--state-dir', str(state), '--max-workers', '2', '--timeout', '90']
        first = run_json(cmd, {3})
        assert first['status'] == 'PARTIAL', first
        assert first['run']['built'] == ['mc-1.20.1-fabric', 'mc-1.21.1-fabric', 'mc-26.3-fabric'], first
        assert first['run']['blocked'] == ['mc-26.3-fabric'], first
        assert first['run']['failed'] == [], first
        release = state / 'release'
        jars = sorted(release.glob('mc-*.jar'))
        assert [p.name for p in jars] == ['mc-1.20.1-fabric.jar', 'mc-1.21.1-fabric.jar'], jars
        for jar in jars:
            runtime_marker(jar)

        session = json.loads((state / 'session.json').read_text(encoding='utf-8'))
        for cid in ('mc-1.20.1-fabric', 'mc-1.21.1-fabric'):
            rec = session['cells'][cid]
            assert rec['state'] == 'passed', rec
            ev = json.dumps(rec.get('evidence') or [])
            assert 'content-parity' in ev and 'packaged-linkage' in ev and 'runtime-command' in ev, rec
        assert session['cells']['mc-26.3-fabric']['state'] == 'blocked'
        assert 'Java 25 required' in session['cells']['mc-26.3-fabric']['reason']

        second = run_json(cmd, {3})
        assert second['run']['built'] == [], second
        assert second['run']['reused'] == ['mc-1.20.1-fabric', 'mc-1.21.1-fabric', 'mc-26.3-fabric'], second
        assert second['run']['blocked'] == ['mc-26.3-fabric'], second

        # Version-local change must rebuild only the affected cell; the latest
        # Java-25 block remains cached until environment/toolchain evidence changes.
        v20 = project / 'overlays/version/1.20.1/src/main/java/example/Version.java'
        v20.write_text('package example; public final class Version { public static final String MC="1.20.1"; }\n// local change\n', encoding='utf-8')
        third = run_json(cmd, {3})
        assert third['run']['built'] == ['mc-1.20.1-fabric'], third
        assert third['run']['reused'] == ['mc-1.21.1-fabric', 'mc-26.3-fabric'], third

        matrix = json.loads((release / 'release-matrix.json').read_text(encoding='utf-8'))
        states = {r['cell_id']: r['state'] for r in matrix['cells']}
        assert states == {'mc-1.20.1-fabric': 'passed', 'mc-1.21.1-fabric': 'passed', 'mc-26.3-fabric': 'blocked'}, states
        print(json.dumps({
            'status': 'PASS',
            'first': first['run'],
            'resume': second['run'],
            'version_local_edit': third['run'],
            'matrix': states,
        }, indent=2))
    print('Northpoint production driver self-test: PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())