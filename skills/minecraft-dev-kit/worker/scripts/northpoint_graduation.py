#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'

LEVELS = {
    'smoke': ['northpoint_job_runner_selftest.py'],
    'semantic': ['northpoint_semantic_migration_selftest.py'],
    'fast': ['northpoint_job_runner_selftest.py', 'northpoint_semantic_migration_selftest.py'],
    'production': ['northpoint_production_driver_selftest.py'],
    'release': ['northpoint_job_runner_selftest.py', 'northpoint_semantic_migration_selftest.py', 'northpoint_production_driver_selftest.py'],
    'full': ['northpoint_job_runner_selftest.py', 'northpoint_semantic_migration_selftest.py', 'northpoint_production_driver_selftest.py', 'northpoint_target_26_3_selftest.py', 'port_26_3_selftest.py'],
}


def run_script(name: str, timeout: int) -> dict:
    started = time.monotonic()
    cp = subprocess.run(
        [sys.executable, str(SCRIPTS / name)],
        cwd=str(ROOT), text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=timeout,
    )
    elapsed = round(time.monotonic() - started, 3)
    stdout = cp.stdout or ''
    stderr = cp.stderr or ''
    marker = next((line.strip() for line in reversed(stdout.splitlines()) if line.strip().endswith(': PASS')), None)
    return {
        'script': name,
        'ok': cp.returncode == 0 and bool(marker),
        'exit': cp.returncode,
        'seconds': elapsed,
        'marker': marker,
        'stdout_tail': '\n'.join(stdout.splitlines()[-30:]),
        'stderr_tail': '\n'.join(stderr.splitlines()[-30:]),
    }


def main() -> int:
    p = argparse.ArgumentParser(description='Run bounded Northpoint conversion graduation levels.')
    p.add_argument('--level', choices=sorted(LEVELS), default='fast')
    p.add_argument('--per-test-timeout', type=int, default=180)
    p.add_argument('--json-out', type=pathlib.Path)
    args = p.parse_args()
    results = []
    for name in LEVELS[args.level]:
        try:
            row = run_script(name, args.per_test_timeout)
        except subprocess.TimeoutExpired as exc:
            row = {
                'script': name, 'ok': False, 'exit': None,
                'seconds': float(args.per_test_timeout), 'marker': None,
                'stdout_tail': (exc.stdout or '')[-12000:] if isinstance(exc.stdout, str) else '',
                'stderr_tail': (exc.stderr or '')[-12000:] if isinstance(exc.stderr, str) else '',
                'reason': 'timeout',
            }
        results.append(row)
        if not row['ok']:
            break
    status = 'PASS' if len(results) == len(LEVELS[args.level]) and all(r['ok'] for r in results) else 'FAIL'
    report = {
        'schema_version': 1,
        'level': args.level,
        'status': status,
        'tests': results,
        'total_seconds': round(sum(float(r.get('seconds') or 0) for r in results), 3),
    }
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    print(f'Northpoint {args.level} graduation: {status}')
    return 0 if status == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())