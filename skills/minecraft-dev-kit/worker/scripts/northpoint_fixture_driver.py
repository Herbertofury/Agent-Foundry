#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, pathlib, shutil, subprocess, zipfile
from northpoint_compose import compose


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    cp = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    if cp.returncode:
        raise RuntimeError((cp.stderr or cp.stdout or f'command failed: {cmd}').strip())
    return cp


def metadata(loader: str, mc: str) -> dict[str, str]:
    if loader == 'fabric':
        return {'fabric.mod.json': json.dumps({'schemaVersion': 1, 'id': 'northpoint_fixture', 'version': '1.0.0', 'name': 'Northpoint Fixture', 'environment': '*'}, indent=2) + '\n'}
    if loader == 'neoforge':
        return {'META-INF/neoforge.mods.toml': f'modLoader="javafml"\nloaderVersion="[1,)"\nlicense="MIT"\n[[mods]]\nmodId="northpoint_fixture"\nversion="1.0.0"\ndisplayName="Northpoint Fixture"\n'}
    if loader == 'forge':
        return {'META-INF/mods.toml': f'modLoader="javafml"\nloaderVersion="[1,)"\nlicense="MIT"\n[[mods]]\nmodId="northpoint_fixture"\nversion="1.0.0"\ndisplayName="Northpoint Fixture"\n'}
    return {'northpoint-loader.json': json.dumps({'loader': loader, 'minecraft': mc}) + '\n'}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--cell-json', type=pathlib.Path, required=True)
    p.add_argument('--project', type=pathlib.Path, required=True)
    p.add_argument('--work', type=pathlib.Path, required=True)
    p.add_argument('--output', type=pathlib.Path, required=True)
    args = p.parse_args()
    cell = json.loads(args.cell_json.read_text(encoding='utf-8'))
    project = args.project.resolve(); work = args.work.resolve(); out = args.output.resolve()
    composed = work / 'composed'
    inv = compose(project, cell, composed, clean=True)
    java_files = sorted((composed / 'java').rglob('*.java')) if (composed / 'java').exists() else []
    if not java_files:
        raise RuntimeError('fixture has no Java sources')
    classes = work / 'classes'; classes.mkdir(parents=True, exist_ok=True)
    java = int(cell.get('java') or 0)
    current = run(['java', '-version']).stderr
    # javac --release can target older Java bytecode, but never a future release.
    major_text = run(['javac', '-version']).stdout.strip().split()[-1].split('.')[0]
    current_major = int(major_text)
    if java > current_major:
        print(json.dumps({'state': 'blocked', 'reason': f'Java {java} required; runner has Java {current_major}', 'evidence': ['toolchain-java-block']}))
        return 0
    run(['javac', '--release', str(java), '-d', str(classes), *map(str, java_files)])
    expected = f"{cell['minecraft']}|{cell['loader']}|" + ('fabric-cell' if cell['id'] == 'mc-1.21.1-fabric' else cell['loader'])
    actual = run(['java', '-cp', str(classes), 'example.HelloMod']).stdout.strip()
    if actual != expected:
        raise RuntimeError(f'composed behavior mismatch: expected={expected!r} actual={actual!r}')
    for rel, text in metadata(cell['loader'], cell['minecraft']).items():
        target = classes / rel; target.parent.mkdir(parents=True, exist_ok=True); target.write_text(text, encoding='utf-8')
    out.mkdir(parents=True, exist_ok=True)
    jar = out / 'northpoint-fixture.jar'
    with zipfile.ZipFile(jar, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for file in sorted(p for p in classes.rglob('*') if p.is_file()):
            z.write(file, file.relative_to(classes).as_posix())
        z.writestr('META-INF/northpoint-cell.json', json.dumps({'cell': cell, 'compose_sha256': inv['sha256'], 'runtime_output': actual}, sort_keys=True))
    print(json.dumps({'state': 'passed', 'artifact': jar.name, 'evidence': ['javac', 'java-runtime', 'loader-metadata', f'compose:{inv["sha256"]}']}))
    return 0

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({'state': 'failed', 'reason': str(exc), 'evidence': []}))
        raise SystemExit(0)