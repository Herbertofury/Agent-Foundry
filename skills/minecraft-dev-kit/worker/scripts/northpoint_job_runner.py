#!/usr/bin/env python3
from __future__ import annotations
import argparse, concurrent.futures, hashlib, json, os, pathlib, re, shutil, subprocess, sys, tempfile, threading, time
from dataclasses import dataclass
from northpoint_compose import inventory
from northpoint_execution import new_run_id, run_logged, workspace_lock

STATE_SCHEMA = 1
FINAL_STATES = {'passed', 'blocked', 'runtime-unverified', 'failed', 'cancelled'}
REUSABLE_STATES = {'passed', 'blocked', 'runtime-unverified'}


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path: pathlib.Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=str(path.parent))
    os.close(fd)
    try:
        pathlib.Path(tmp).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        os.replace(tmp, path)
    finally:
        pathlib.Path(tmp).unlink(missing_ok=True)


def now() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def load_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def normalized_cell(cell: dict) -> dict:
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', str(cell['id'])):
        raise ValueError('unsafe cell id: ' + str(cell['id']))
    return {
        'id': str(cell['id']),
        'minecraft': str(cell['minecraft']),
        'loader': str(cell['loader']),
        'java': int(cell.get('java') or 0),
        'java_path': str(cell.get('java_path') or ''),
        'support_state': str(cell.get('support_state') or 'stable'),
        'primary': bool(cell.get('primary')),
    }


def driver_probe(driver: pathlib.Path, cell: dict, project: pathlib.Path, work_root: pathlib.Path, timeout: int) -> dict:
    probe_root = work_root / '.probe' / str(cell['id'])
    probe_root.mkdir(parents=True, exist_ok=True)
    cell_file = probe_root / 'cell.json'
    cell_file.write_text(json.dumps(cell, indent=2) + '\n', encoding='utf-8')
    if driver.suffix.lower() == '.py':
        cmd = [sys.executable, str(driver), '--probe', '--cell-json', str(cell_file), '--project', str(project)]
    else:
        cmd = [str(driver), '--probe', '--cell-json', str(cell_file), '--project', str(project)]
    try:
        cp = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=min(timeout, 45))
    except Exception as exc:
        return {'protocol': 1, 'available': False, 'probe_error': type(exc).__name__}
    if cp.returncode != 0:
        # Backward-compatible drivers simply do not participate in environment
        # invalidation; their file hash still remains part of the fingerprint.
        return {'protocol': 0, 'available': False}
    lines = [line.strip() for line in cp.stdout.splitlines() if line.strip()]
    if not lines:
        return {'protocol': 0, 'available': False}
    try:
        value = json.loads(lines[-1])
    except Exception:
        return {'protocol': 0, 'available': False}
    return value if isinstance(value, dict) else {'protocol': 0, 'available': False}


def input_fingerprint(project: pathlib.Path, cell: dict, driver: pathlib.Path, config: dict, probe: dict | None = None) -> str:
    inv = inventory(project, cell)
    driver_sha = sha256_file(driver)
    artifact_fingerprint = str((probe or {}).get('artifact_fingerprint') or '')
    payload = {
        'compose': inv['sha256'],
        'driver_sha256': driver_sha,
        'artifact_fingerprint': artifact_fingerprint,
        'cell': normalized_cell(cell),
        'config': config,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def environment_fingerprint(probe: dict) -> str:
    return hashlib.sha256(json.dumps(probe, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def artifact_ok(record: dict, release_dir: pathlib.Path) -> bool:
    artifact = record.get('artifact') or {}
    rel = artifact.get('file')
    expected = artifact.get('sha256')
    if not rel or not expected:
        return False
    path = (release_dir / rel).resolve()
    return path.is_relative_to(release_dir.resolve()) and path.is_file() and sha256_file(path) == expected


def load_runtime_proofs(path: pathlib.Path | None) -> dict[str, dict]:
    if path is None or not path.is_file():
        return {}
    try:
        value = load_json(path)
    except Exception:
        return {}
    rows = value.get('proofs') if isinstance(value, dict) else None
    if not isinstance(rows, list):
        return {}
    out = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        cell_id = str(row.get('cell_id') or '')
        if cell_id:
            out[cell_id] = row
    return out


def apply_runtime_proofs(state: dict, release_dir: pathlib.Path, proofs: dict[str, dict]) -> list[str]:
    promoted: list[str] = []
    for cid, proof in proofs.items():
        rec = state.get('cells', {}).get(cid)
        if not rec or rec.get('state') != 'runtime-unverified' or proof.get('passed') is not True:
            continue
        artifact = rec.get('artifact') or {}
        expected = str(artifact.get('sha256') or '')
        if not expected or str(proof.get('artifact_sha256') or '') != expected:
            continue
        if not artifact_ok(rec, release_dir):
            continue
        rec['state'] = 'passed'
        rec['reason'] = None
        rec['updated_at'] = now()
        evidence = list(rec.get('evidence') or [])
        evidence.append({
            'kind': 'external-runtime-proof',
            'artifact_sha256': expected,
            'verified_at': proof.get('verified_at'),
            'evidence': proof.get('evidence') or [],
        })
        rec['evidence'] = evidence
        promoted.append(cid)
    return promoted


def load_state(path: pathlib.Path, manifest: dict) -> dict:
    if path.exists():
        state = load_json(path)
        if state.get('schema_version') == STATE_SCHEMA:
            return state
    return {
        'schema_version': STATE_SCHEMA,
        'created_at': now(),
        'updated_at': now(),
        'primary_cell': manifest['primary_cell'],
        'cells': {},
        'runs': [],
    }


def driver_command(driver: pathlib.Path, cell_file: pathlib.Path, project: pathlib.Path, work: pathlib.Path, output: pathlib.Path) -> list[str]:
    if driver.suffix.lower() == '.py':
        return [sys.executable, str(driver), '--cell-json', str(cell_file), '--project', str(project), '--work', str(work), '--output', str(output)]
    return [str(driver), '--cell-json', str(cell_file), '--project', str(project), '--work', str(work), '--output', str(output)]


def run_driver(driver: pathlib.Path, cell: dict, project: pathlib.Path, work_root: pathlib.Path, release_dir: pathlib.Path, timeout: int) -> dict:
    cid = cell['id']
    work = work_root / cid
    if work.exists():
        history = work_root / 'history' / cid / new_run_id()
        history.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(work), str(history))
    work.mkdir(parents=True, exist_ok=True)
    cell_file = work / 'cell.json'
    cell_file.write_text(json.dumps(cell, indent=2) + '\n', encoding='utf-8')
    raw_output = work / 'driver-output'
    raw_output.mkdir(parents=True, exist_ok=True)
    command = driver_command(driver, cell_file, project, work, raw_output)
    if driver.name == 'northpoint_production_driver.py':
        command += ['--timeout', str(timeout)]
    cp = run_logged(command, directory=work, name='driver', timeout=timeout + 15)
    if cp.returncode in {124, 130}:
        return {'state': 'failed' if cp.returncode == 124 else 'cancelled',
                'reason': f'driver timed out or was interrupted (exit {cp.returncode}); full evidence: {work}',
                'evidence': [{'kind': 'process-failure', 'exit': cp.returncode, 'workspace': str(work)}]}
    if cp.returncode != 0:
        return {'state': 'failed', 'reason': (cp.stderr.strip() or cp.stdout.strip() or f'driver exited {cp.returncode}')[-12000:], 'evidence': []}
    lines = [line.strip() for line in cp.stdout.splitlines() if line.strip()]
    if not lines:
        return {'state': 'failed', 'reason': 'driver emitted no JSON receipt', 'evidence': []}
    try:
        result = json.loads(lines[-1])
    except Exception as exc:
        return {'state': 'failed', 'reason': f'driver receipt invalid JSON: {exc}: {lines[-1][:500]}', 'evidence': []}
    atomic_json(work / 'receipt.json', result)
    state = str(result.get('state') or 'failed')
    if state not in FINAL_STATES:
        return {'state': 'failed', 'reason': f'unknown driver state: {state}', 'evidence': []}
    artifact_name = result.get('artifact')
    if state not in {'passed', 'runtime-unverified'}:
        return {'state': state, 'reason': result.get('reason') or f'driver returned {state}', 'evidence': result.get('evidence') or [], 'conversion': result.get('conversion')}
    if state == 'runtime-unverified' and not artifact_name:
        return {'state': state, 'reason': result.get('reason') or 'runtime verification is pending', 'evidence': result.get('evidence') or [], 'conversion': result.get('conversion')}
    artifact = pathlib.Path(str(artifact_name or ''))
    if not artifact.is_absolute():
        artifact = raw_output / artifact
    artifact = artifact.resolve()
    root = raw_output.resolve()
    if artifact != root and root not in artifact.parents:
        return {'state': 'failed', 'reason': 'driver artifact escaped output root', 'evidence': []}
    if not artifact.is_file():
        return {'state': 'failed', 'reason': f'driver artifact missing: {artifact}', 'evidence': []}
    release_dir.mkdir(parents=True, exist_ok=True)
    suffix = ''.join(artifact.suffixes) or '.bin'
    name = f"{cid}{suffix}"
    tmp = release_dir / (name + '.tmp')
    shutil.copy2(artifact, tmp)
    final = release_dir / name
    os.replace(tmp, final)
    return {
        'state': state,
        'reason': None if state == 'passed' else (result.get('reason') or 'runtime verification is pending'),
        'artifact': {'file': name, 'sha256': sha256_file(final), 'size': final.stat().st_size},
        'evidence': result.get('evidence') or [],
        'conversion': result.get('conversion'),
        'driver_stdout_tail': '\n'.join(lines[-20:]),
    }


def write_release_outputs(state: dict, release_dir: pathlib.Path) -> None:
    rows = []
    sums = []
    for cid, rec in sorted(state['cells'].items()):
        artifact = rec.get('artifact') or {}
        row = {
            'cell_id': cid,
            'state': rec.get('state'),
            'fingerprint': rec.get('fingerprint'),
            'environment_fingerprint': rec.get('environment_fingerprint'),
            'artifact': artifact,
            'conversion': rec.get('conversion'),
            'reason': rec.get('reason'),
        }
        rows.append(row)
        if rec.get('state') == 'passed' and artifact.get('file') and artifact.get('sha256'):
            sums.append(f"{artifact['sha256']}  {artifact['file']}")
    atomic_json(release_dir / 'release-matrix.json', {'schema_version': 1, 'generated_at': now(), 'cells': rows})
    (release_dir / 'SHA256SUMS.txt').write_text('\n'.join(sums) + ('\n' if sums else ''), encoding='utf-8')


def main() -> int:
    p = argparse.ArgumentParser(description='Run a resumable Northpoint target-first conversion matrix.')
    p.add_argument('--manifest', type=pathlib.Path, required=True)
    p.add_argument('--driver', type=pathlib.Path, required=True)
    p.add_argument('--state-dir', type=pathlib.Path, required=True)
    p.add_argument('--max-workers', type=int, default=0)
    p.add_argument('--timeout', type=int, default=180)
    p.add_argument('--runtime-proofs', type=pathlib.Path)
    args = p.parse_args()
    if args.timeout <= 0:
        raise SystemExit('--timeout must be positive')
    manifest = load_json(args.manifest.resolve())
    project = pathlib.Path(manifest['project_root']).resolve()
    state_dir = args.state_dir.resolve()
    if state_dir == project or state_dir.is_relative_to(project) or project.is_relative_to(state_dir):
        raise ValueError('state directory and source project must be disjoint')
    with workspace_lock(state_dir):
        return run_manifest(args, manifest)


def run_manifest(args: argparse.Namespace, manifest: dict) -> int:
    project = pathlib.Path(manifest['project_root']).resolve()
    driver = args.driver.resolve()
    state_dir = args.state_dir.resolve()
    if state_dir == project or state_dir.is_relative_to(project) or project.is_relative_to(state_dir):
        raise ValueError('state directory and source project must be disjoint')
    release_dir = state_dir / 'release'
    work_root = state_dir / 'work'
    state_path = state_dir / 'session.json'
    cells = {str(c['id']): normalized_cell(c) for c in manifest['cells']}
    if len(cells) != len(manifest['cells']):
        raise ValueError('duplicate cell ids are not allowed')
    primary_id = str(manifest['primary_cell'])
    if primary_id not in cells:
        raise SystemExit('primary_cell is not in cells')
    cells[primary_id]['primary'] = True
    state = load_state(state_path, manifest)
    config = manifest.get('config') or {}
    runtime_proofs = load_runtime_proofs(args.runtime_proofs.resolve() if args.runtime_proofs else None)
    promoted = apply_runtime_proofs(state, release_dir, runtime_proofs)
    if promoted:
        state['updated_at'] = now()
        atomic_json(state_path, state)
    run = {'started_at': now(), 'built': [], 'reused': [], 'failed': [], 'blocked': [], 'runtime_promoted': sorted(promoted)}

    probes = {cid: driver_probe(driver, cell, project, work_root, args.timeout) for cid, cell in cells.items()}
    fps = {cid: input_fingerprint(project, cell, driver, config, probes[cid]) for cid, cell in cells.items()}
    env_fps = {cid: environment_fingerprint(probes[cid]) for cid in cells}
    for cid, cell in cells.items():
        rec = state['cells'].setdefault(cid, {
            'state': 'pending', 'attempts': 0, 'fingerprint': None,
            'environment_fingerprint': None, 'artifact': None, 'evidence': [], 'conversion': None, 'reason': None,
        })
        if rec.get('fingerprint') != fps[cid]:
            rec.update({
                'state': 'stale' if rec.get('state') == 'passed' else 'pending',
                'fingerprint': fps[cid],
                'environment_fingerprint': env_fps[cid],
                'reason': 'inputs changed',
                'artifact': rec.get('artifact'),
                'conversion': None,
            })
        elif rec.get('state') in {'blocked', 'runtime-unverified'} and rec.get('environment_fingerprint') != env_fps[cid]:
            rec.update({
                'state': 'pending',
                'environment_fingerprint': env_fps[cid],
                'reason': 'conversion environment changed',
            })
        elif rec.get('state') == 'passed' and not artifact_ok(rec, release_dir):
            rec.update({'state': 'stale', 'reason': 'promoted artifact missing or hash mismatch'})
    state['updated_at'] = now()
    atomic_json(state_path, state)

    state_lock = threading.RLock()

    def execute(cid: str) -> tuple[str, dict, bool]:
        rec = state['cells'][cid]
        if rec.get('fingerprint') == fps[cid] and rec.get('state') in REUSABLE_STATES:
            artifact = rec.get('artifact') or {}
            if not artifact or artifact_ok(rec, release_dir):
                return cid, rec, False
        with state_lock:
            rec['state'] = 'building'; rec['attempts'] = int(rec.get('attempts') or 0) + 1; rec['reason'] = None
            state['updated_at'] = now()
            atomic_json(state_path, state)
        result = run_driver(driver, cells[cid], project, work_root, release_dir, args.timeout)
        with state_lock:
            rec.update(result)
            rec['fingerprint'] = fps[cid]
            rec['environment_fingerprint'] = env_fps[cid]
            rec['updated_at'] = now()
            atomic_json(state_path, state)
        return cid, rec, True

    cid, rec, built = execute(primary_id)
    (run['built'] if built else run['reused']).append(cid)
    atomic_json(state_path, state)
    if rec.get('state') != 'passed':
        (run['blocked'] if rec.get('state') in {'blocked', 'runtime-unverified'} else run['failed']).append(primary_id)
        run['finished_at'] = now(); state['runs'].append(run); state['updated_at'] = now(); atomic_json(state_path, state); write_release_outputs(state, release_dir)
        print(json.dumps({'status': 'FAILED_PRIMARY', 'run': run, 'state_file': str(state_path), 'release_dir': str(release_dir)}))
        return 2

    secondaries = [cid for cid in sorted(cells) if cid != primary_id]
    auto_workers = max(1, min(8, max(1, (os.cpu_count() or 2) - 1)))
    workers = args.max_workers if args.max_workers > 0 else auto_workers
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(execute, cid): cid for cid in secondaries}
        for fut in concurrent.futures.as_completed(futures):
            cid, rec, built = fut.result()
            (run['built'] if built else run['reused']).append(cid)
            if rec.get('state') == 'passed':
                pass
            elif rec.get('state') in {'blocked', 'runtime-unverified'}:
                run['blocked'].append(cid)
            else:
                run['failed'].append(cid)
            with state_lock:
                atomic_json(state_path, state)

    run['built'].sort(); run['reused'].sort(); run['failed'].sort(); run['blocked'].sort(); run['finished_at'] = now()
    state['runs'].append(run); state['updated_at'] = now(); atomic_json(state_path, state)
    write_release_outputs(state, release_dir)
    status = 'PASS' if not run['failed'] and not run['blocked'] else 'PARTIAL'
    print(json.dumps({'status': status, 'run': run, 'state_file': str(state_path), 'release_dir': str(release_dir)}))
    return 0 if status == 'PASS' else 3

if __name__ == '__main__':
    raise SystemExit(main())