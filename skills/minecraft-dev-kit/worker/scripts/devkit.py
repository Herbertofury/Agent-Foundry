#!/usr/bin/env python3
"""Minecraft Dev Kit workbench, using the canonical Northpoint production engine."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

from devkit_toolchains import ensure_jdk, java_pair, target_java
from northpoint_execution import atomic_json, new_run_id, run_logged, sha256_file, workspace_lock
from northpoint_production_driver import java_major, javac_major
from northpoint_source_intake import inspect_project

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
RUNNER = SCRIPTS / 'northpoint_job_runner.py'
DRIVER = SCRIPTS / 'northpoint_production_driver.py'


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError(f'expected a JSON object: {path}')
    return value


def status(root: Path) -> dict:
    manifest = load(root / 'manifest.json')
    state_path = root / 'state' / 'session.json'
    state = load(state_path) if state_path.is_file() else {}
    cells = []
    for cell in manifest['cells']:
        record = state.get('cells', {}).get(cell['id'], {})
        artifact = dict(record.get('artifact') or {})
        if artifact:
            path = (root / 'state' / 'release' / artifact['file']).resolve()
            if not path.is_relative_to((root / 'state' / 'release').resolve()):
                raise ValueError('saved artifact escapes release directory')
            artifact.update(path=str(path), integrity_verified=path.is_file() and sha256_file(path) == artifact['sha256'])
        cells.append({'id': cell['id'], 'minecraft': cell['minecraft'], 'loader': cell['loader'],
                      'state': record.get('state', 'pending'), 'attempts': record.get('attempts', 0),
                      'artifact': artifact or None, 'reason': record.get('reason')})
    def native_for(cell):
        directory=root/'native' if len(cells)==1 else root/'native'/cell['id']
        receipt=directory/'native-result.json'
        if not receipt.is_file():return None
        value=load(receipt)
        artifact=cell.get('artifact') or {}
        value['artifact_match']=bool(artifact.get('integrity_verified') and artifact.get('sha256')==value.get('artifact_sha256'))
        if not value['artifact_match']:value['state']='stale-proof'
        elif value.get('state') == 'runtime-smoke-verified':
            from devkit_native import reusable_proof
            configured = next(row for row in manifest['cells'] if row['id'] == cell['id'])
            java = Path(configured.get('java_path') or '')
            if not java.is_file() or reusable_proof(directory, Path(artifact['path']), java) is None:
                value['state'] = 'stale-proof'
        return value
    native_rows={cell['id']:native_for(cell) for cell in cells}
    if len(cells)==1:
        native=native_rows[cells[0]['id']]
    elif any(native_rows.values()):
        matched=all(row and row.get('artifact_match') for row in native_rows.values())
        verified=matched and all(row.get('state')=='runtime-smoke-verified' for row in native_rows.values())
        native={'state':'runtime-smoke-verified' if verified else 'incomplete','artifact_match':matched,'cells':native_rows}
    else:native=None
    all_passed = bool(cells) and all(c['state'] == 'passed' and c['artifact'] and c['artifact']['integrity_verified'] for c in cells)
    if manifest.get('native_verify'):
        all_passed = all_passed and bool(native and native.get('artifact_match') and native.get('state') == 'runtime-smoke-verified')
    return {'schema_version': 1, 'workspace': str(root), 'project': manifest['project_root'],
            'cells': cells, 'last_run': (state.get('runs') or [None])[-1], 'native_runtime': native,
            'all_passed': all_passed}


def run_workspace(root: Path, timeout: int, *, proofs: Path | None = None, offline: bool = False) -> int:
    with workspace_lock(root):
        manifest = load(root / 'manifest.json')
        source = Path(manifest['project_root']).resolve()
        if not source.is_dir():
            raise ValueError(f'source project is unavailable; saved work was preserved: {source}')
        for cell in manifest['cells']:
            pinned = Path(cell['java_path']) if cell.get('java_path') else None
            jdk = ensure_jdk(int(cell['java']), explicit=pinned if pinned and pinned.is_file() else None, offline=offline)
            cell['java_path'] = jdk['java_path']
        atomic_json(root / 'manifest.json', manifest)
        run_id = new_run_id()
        command = [sys.executable, str(RUNNER), '--manifest', str(root / 'manifest.json'),
                   '--driver', str(DRIVER), '--state-dir', str(root / 'state'), '--timeout', str(timeout)]
        if proofs:
            command += ['--runtime-proofs', str(proofs.resolve())]
        atomic_json(root / 'active.json', {'run_id': run_id, 'state': 'running', 'command': command})
        print(f'Workspace: {root}', flush=True)
        print(f'Live evidence: {root / "runs" / run_id}', flush=True)
        cp = run_logged(command, directory=root / 'runs' / run_id, name='runner',
                        timeout=(timeout + 75) * max(1, len(manifest['cells'])))
        result = status(root)
        result.update(run_id=run_id, runner_exit=cp.returncode)
        atomic_json(root / 'active.json', {'run_id': run_id, 'state': 'finished', 'runner_exit': cp.returncode})
        atomic_json(root / 'result.json', result)
        print(json.dumps(result, indent=2))
        if cp.returncode not in {0, 2, 3}:
            print(cp.stderr, file=sys.stderr)
        return cp.returncode


def package(root: Path, output: Path) -> dict:
    """Package only explicit release/evidence paths, not caches, account files or secrets."""
    output = output.resolve()
    if output.is_relative_to(root.resolve()):
        raise ValueError('package output must be outside its workspace')
    with workspace_lock(root):
        snapshot = status(root)
        rows = [row for row in snapshot['cells'] if row['artifact'] and
                row['state'] in {'passed', 'runtime-unverified'}]
        if not rows or any(not row['artifact']['integrity_verified'] for row in rows):
            raise ValueError('no intact candidate artifact is available to package')
        files = set()
        for row in rows:
            files.add(Path(row['artifact']['path']))
        for name in ['manifest.json', 'result.json', 'intake.json', 'state/session.json',
                     'state/release/release-matrix.json', 'state/release/SHA256SUMS.txt', 'runtime-proofs.json', 'toolchain.json']:
            path = root / name
            if path.is_file():files.add(path)
        for cell in snapshot['cells']:
            work = root / 'state' / 'work' / cell['id']
            for name in ['cell.json', 'receipt.json', 'driver.stdout.txt', 'driver.stderr.txt', 'driver.process.json']:
                path = work / name
                if path.is_file():files.add(path)
            if (work / 'evidence').is_dir():
                files.update(p for p in (work / 'evidence').rglob('*') if p.is_file())
        native = root / 'native'
        if native.is_dir():
            for name in ['native-result.json', 'dependencies/dependency-lock.json', 'dependencies/provider-compatibility.json']:
                path = native / name
                if path.is_file():files.add(path)
            for dependency_lock in native.rglob('dependency-lock.json'):
                files.add(dependency_lock)
                for row in load(dependency_lock).get('downloads', []):
                    path = dependency_lock.parent / 'mods' / row['file']
                    if not path.is_file() or sha256_file(path) != row['sha256']:
                        raise ValueError('runtime dependency changed or missing: ' + row['file'])
                    files.add(path)
            for receipt_name in ['native-result.json','provider-compatibility.json']:
                files.update(native.rglob(receipt_name))
            for path in native.rglob('*'):
                if path.is_file() and ('commands' in path.parts or
                    path.name in {'latest.log','debug.log','devkit-runtime-proof.json','devkit-restart.properties','phase.json','initial-proof.json','initial-client.log','template-origin.json'} or
                    ('devkit-' in path.name and path.suffix == '.png')):
                    files.add(path)
        for path in files:
            if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
                raise ValueError(f'unsafe package input: {path}')
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
            hashes = []
            for path in sorted(files):
                rel = path.relative_to(root).as_posix()
                archive.write(path, rel)
                hashes.append(f'{sha256_file(path)}  {rel}')
            archive.writestr('PACKAGE-SHA256SUMS.txt', '\n'.join(hashes) + '\n')
            archive.writestr('VERIFICATION.json', json.dumps(snapshot, indent=2) + '\n')
            archive.writestr('READ-ME.txt',
                'Minecraft Dev Kit candidate and evidence bundle.\n'
                'Use VERIFICATION.json for the actual verification state of every cell.\n'
                'runtime-unverified means build evidence only; it is NOT a tested Minecraft release.\n'
                'native_runtime records separately scoped world/render/sync/save-reopen/independent-JVM-restart proof, not exhaustive gameplay.\n'
                'Install the candidate with ALL JARs in native/dependencies/mods for the recorded target.\n'
                'Original embedded dependencies are preserved; Fabric selects the compatible external versions.\n'
                'Private source projects, account data and Gradle caches are not included.\n')
        return {'package': str(output), 'sha256': sha256_file(output), 'size': output.stat().st_size,
                'file_count': len(files), 'all_passed': snapshot['all_passed']}


def verify_workspace(root: Path, timeout: int, *, offline: bool=False) -> int:
    """Finish the existing build/verify/promote route without source surgery or rebuild."""
    from devkit_native import verify, reusable_proof
    from northpoint_job_runner import now
    manifest=load(root/'manifest.json')
    order=[manifest['primary_cell']]+[row['id'] for row in manifest['cells'] if row['id']!=manifest['primary_cell']]
    proofs=[]
    for index,cid in enumerate(order):
        snapshot=status(root)
        cell=next(row for row in snapshot['cells'] if row['id']==cid)
        artifact=cell.get('artifact') or {}
        if cell['state'] not in {'passed','runtime-unverified'} or not artifact.get('integrity_verified'):return 2
        if cell['minecraft']!='26.3' or cell['loader']!='fabric':
            print('Native client automation requires its loader-specific adapter; candidate and prior evidence are retained.',file=sys.stderr)
            return 2
        native=root/'native' if len(order)==1 else root/'native'/cid
        configured=next(row for row in manifest['cells'] if row['id']==cid)
        java=Path(configured['java_path'])
        result=reusable_proof(native,Path(artifact['path']),java)
        if result is None:
            result=verify(Path(artifact['path']),native,timeout=timeout,offline=offline,java_path=java)
        if result['state']!='runtime-smoke-verified':
            atomic_json(root/'result.json',status(root));print(json.dumps(result,indent=2));return 2
        proofs.append({'cell_id':cid,'artifact_sha256':artifact['sha256'],'passed':True,
                       'verified_at':now(),'evidence':[{'scope':result['coverage'],'not_proven':result['not_proven'],
                         'receipt':str(native/'native-result.json'),'receipt_sha256':sha256_file(native/'native-result.json')}]})
        proof_file=root/'runtime-proofs.json';atomic_json(proof_file,{'proofs':proofs})
        if index==0 and len(order)>1:
            code=run_workspace(root,timeout,proofs=proof_file,offline=offline)
            if code not in {0,2,3}:return code
    code=run_workspace(root,timeout,proofs=root/'runtime-proofs.json',offline=offline)
    return 0 if code==0 and status(root)['all_passed'] else code or 2


def wizard() -> int:
    """Interactive front door over the same tested CLI operations."""
    print('Minecraft Dev Kit | Build, recover, verify and package')
    print('1. Convert a source project   2. Resume a workspace   3. Set up Java   4. Inspect prerequisites')
    try:
        choice = input('Choose [1]: ').strip() or '1'
        if choice == '4':return main(['doctor'])
        if choice == '3':
            target = input('Minecraft version [26.3]: ').strip() or '26.3'
            return main(['setup', '--minecraft', target])
        if choice == '2':
            workspace = Path(input('Saved workspace folder: ').strip().strip('"')).expanduser().resolve()
            return main(['resume', '--workspace', str(workspace)])
        if choice != '1':raise ValueError('Choose 1, 2, 3 or 4')
        project = Path(input('Source project folder (you may drag it here): ').strip().strip('"')).expanduser().resolve()
        info = inspect_project(project)
        print('Detected:', info.get('mod_id') or project.name, '|', info.get('loader') or 'unknown loader', '| Minecraft', info.get('minecraft'))
        target = input('Target Minecraft version [26.3]: ').strip() or '26.3'
        suggested = info.get('loader') or 'fabric'
        loader = input(f'Target loader [{suggested}]: ').strip() or suggested
        workspace = Path.home() / '.minecraft-dev-kit/runs' / new_run_id()
        arguments = ['convert', '--project', str(project), '--minecraft', target, '--loader', loader,
                     '--workspace', str(workspace)]
        if loader == 'fabric' and target == '26.3':
            if (input('Also run native Minecraft, resolve dependencies and verify save/reopen? [Y/n]: ').strip().lower() or 'y') in {'y','yes'}:
                arguments.append('--verify')
        print('Your original source will remain untouched. Workspace:', workspace)
        code = main(arguments)
        snapshot = status(workspace)
        if any(c.get('artifact') and c['artifact']['integrity_verified'] for c in snapshot['cells']):
            output = workspace.parent / (workspace.name + '-candidate-and-evidence.zip')
            print(json.dumps(package(workspace, output), indent=2))
        return code
    except (EOFError, KeyboardInterrupt):
        print('Cancelled. Any already-created workspace is preserved.')
        return 130


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    doctor = sub.add_parser('doctor', help='Inspect installed build prerequisites without changing them')
    doctor.add_argument('--java-path', type=Path)
    setup = sub.add_parser('setup', help='Provision and verify a private JDK; no administrator or PATH changes')
    setup.add_argument('--minecraft', default='26.3')
    setup.add_argument('--java', type=int)
    setup.add_argument('--offline', action='store_true')
    setup.add_argument('--managed-only', action='store_true')
    setup.add_argument('--refresh', action='store_true')
    deps = sub.add_parser('dependencies', help='Audit or install the exact-target required Fabric dependency closure')
    deps.add_argument('--jar', type=Path, action='append', required=True)
    deps.add_argument('--minecraft', required=True)
    deps.add_argument('--java', type=int)
    deps.add_argument('--loader-version', required=True)
    deps.add_argument('--output', type=Path, required=True)
    deps.add_argument('--audit-only', action='store_true')
    deps.add_argument('--offline', action='store_true')
    deps.add_argument('--projects', type=Path, help='JSON map of mod IDs to exact Modrinth project IDs')
    verify_parser = sub.add_parser('verify', help='Launch the exact Fabric 26.3 JAR; verify world, network and save/reopen')
    verify_parser.add_argument('--jar', type=Path, required=True)
    verify_parser.add_argument('--workspace', type=Path, required=True)
    verify_parser.add_argument('--template', type=Path)
    verify_parser.add_argument('--java-path', type=Path)
    verify_parser.add_argument('--offline', action='store_true')
    verify_parser.add_argument('--timeout', type=int, default=900)
    convert = sub.add_parser('convert', help='Build/convert through the real production engine; retain all evidence')
    convert.add_argument('--project', type=Path, required=True)
    convert.add_argument('--minecraft', required=True)
    convert.add_argument('--loader', choices=['fabric', 'forge', 'neoforge', 'quilt'], required=True)
    convert.add_argument('--java', type=int, help='Inferred from Minecraft when omitted')
    convert.add_argument('--offline', action='store_true')
    convert.add_argument('--java-path', type=Path)
    convert.add_argument('--workspace', type=Path)
    convert.add_argument('--timeout', type=int, default=600)
    convert.add_argument('--verify', action='store_true', help='Also run the native Fabric 26.3 world and persistence gate')
    resume = sub.add_parser('resume', help='Reuse exact-hash candidates; rebuild only invalidated inputs')
    resume.add_argument('--workspace', type=Path, required=True)
    resume.add_argument('--timeout', type=int, default=600)
    resume.add_argument('--runtime-proofs', type=Path)
    resume.add_argument('--offline', action='store_true')
    resume.add_argument('--verify', action='store_true', help='Verify and remember the native runtime gate for future resumes')
    inspect = sub.add_parser('status', help='Read actual state and re-hash the saved candidate')
    inspect.add_argument('--workspace', type=Path, required=True)
    pack = sub.add_parser('package', help='Package real candidates, hashes and evidence without caches')
    pack.add_argument('--workspace', type=Path, required=True)
    pack.add_argument('--output', type=Path, required=True)
    sub.add_parser('wizard', help='Guided conversion, resume and setup without memorizing commands')
    args = parser.parse_args(argv)
    if hasattr(args, 'timeout') and args.timeout <= 0:parser.error('--timeout must be positive')
    if args.command == 'wizard':return wizard()
    if args.command == 'verify':
        from devkit_native import verify
        result = verify(args.jar, args.workspace, template=args.template, java_path=args.java_path,
                        timeout=args.timeout, offline=args.offline)
        print(json.dumps(result, indent=2))
        return 0 if result['state'] == 'runtime-smoke-verified' else 2
    if args.command == 'setup':
        jdk = ensure_jdk(args.java or target_java(args.minecraft), offline=args.offline,
                         managed_only=args.managed_only, refresh=args.refresh)
        print(json.dumps(dict(jdk, status='READY', minecraft=args.minecraft), indent=2))
        return 0
    if args.command == 'dependencies':
        from devkit_dependencies import audit, resolve
        version = args.java or target_java(args.minecraft)
        if args.audit_only:
            result = audit(args.jar, minecraft=args.minecraft, java=version, loader_version=args.loader_version)
            atomic_json(args.output.resolve() / 'dependency-audit.json', result)
        else:
            result = resolve(args.jar, args.output, minecraft=args.minecraft, java=version,
                             loader_version=args.loader_version, offline=args.offline,
                             projects=load(args.projects) if args.projects else None)
        print(json.dumps(result, indent=2))
        return 0 if result['state'] == 'complete' else 2
    if args.command == 'doctor':
        java = args.java_path or (Path(shutil.which('java')) if shutil.which('java') else None)
        pair = java_pair(java) if java else None
        print(json.dumps({'python': sys.version.split()[0], 'python_executable': sys.executable,
                          'jdk': pair, 'git': shutil.which('git'), 'production_driver': str(DRIVER),
                          'production_driver_sha256': sha256_file(DRIVER),
                          'next_action': None if pair else 'Run devkit setup --minecraft <target>'}, indent=2))
        return 0 if pair else 2
    if args.command == 'convert':
        project = args.project.resolve()
        if not project.is_dir():parser.error(f'project does not exist: {project}')
        root = args.workspace.resolve() if args.workspace else (Path.home() / '.minecraft-dev-kit' / 'runs' / new_run_id())
        if root == project or root.is_relative_to(project) or project.is_relative_to(root):
            parser.error('workspace and source project must be disjoint')
        if root.exists() and any(root.iterdir()):parser.error(f'workspace already contains data; use resume: {root}')
        root.mkdir(parents=True, exist_ok=True)
        major = args.java or target_java(args.minecraft)
        jdk = ensure_jdk(major, explicit=args.java_path, offline=args.offline)
        atomic_json(root / 'toolchain.json', jdk)
        cell = {'id': f'mc-{args.minecraft}-{args.loader}', 'minecraft': args.minecraft, 'loader': args.loader,
                'java': major, 'java_path': jdk['java_path'], 'primary': True}
        from northpoint_job_runner import normalized_cell
        cell = normalized_cell(cell)
        atomic_json(root / 'intake.json', inspect_project(project))
        atomic_json(root / 'manifest.json', {'schema_version': 1, 'project_root': str(project),
                    'primary_cell': cell['id'], 'cells': [cell], 'config': {'zero_loss': True}, 'native_verify':args.verify})
        code = run_workspace(root, args.timeout, offline=args.offline)
        if args.verify:return verify_workspace(root,args.timeout,offline=args.offline)
        return code
    root = args.workspace.resolve()
    if args.command == 'resume':
        manifest=load(root/'manifest.json')
        if args.verify:
            manifest['native_verify']=True;atomic_json(root/'manifest.json',manifest)
        code=run_workspace(root,args.timeout,proofs=args.runtime_proofs,offline=args.offline)
        if manifest.get('native_verify'):return verify_workspace(root,args.timeout,offline=args.offline)
        return code
    if args.command == 'status':
        print(json.dumps(status(root), indent=2))
        return 0
    if args.command == 'package':
        print(json.dumps(package(root, args.output), indent=2))
        return 0
    return 2


if __name__ == '__main__':
    try:raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print(json.dumps({'status': 'ERROR', 'reason': str(exc)}, indent=2), file=sys.stderr)
        raise SystemExit(1)
