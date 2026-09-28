#!/usr/bin/env python3
"""Deterministic lifecycle regressions; no Minecraft runtime claims."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from northpoint_execution import contained_file, run_logged, stop_process_tree, workspace_lock


def main() -> int:
    with tempfile.TemporaryDirectory(prefix='northpoint-execution-test-') as raw:
        root = Path(raw).resolve()
        cp = run_logged([sys.executable, '-c', 'import sys; print("x"*2000000); print("ERR-END", file=sys.stderr)'],
                        directory=root / 'complete', name='large', timeout=15)
        assert cp.returncode == 0 and len(cp.stdout) == 2000001 and 'ERR-END' in cp.stderr
        assert (root / 'complete/large.stdout.txt').stat().st_size >= 2000001
        cp = run_logged([str(root / 'does-not-exist')], directory=root / 'missing', name='missing', timeout=5)
        assert cp.returncode != 0 and 'launch-failed' in (root / 'missing/missing.process.json').read_text()
        cp = run_logged([sys.executable, '-c', 'import time; time.sleep(30)'],
                        directory=root / 'timeout', name='tree', timeout=0.5)
        assert cp.returncode == 124
        receipt = json.loads((root / 'timeout/tree.process.json').read_text())
        assert receipt['state'] == 'timed-out' and receipt['returncode'] == 124
        marker, ready = root / 'child-ran', root / 'parent-ready'
        child_code = f'import time; from pathlib import Path; time.sleep(4); Path({str(marker)!r}).write_text("orphan")'
        parent_code = ('import subprocess,sys,time; from pathlib import Path; '
                       'subprocess.Popen([sys.executable,"-c",' + repr(child_code) + ']); '
                       f'Path({str(ready)!r}).write_text("ready"); time.sleep(30)')
        parent = subprocess.Popen([sys.executable, '-c', parent_code], start_new_session=os.name != 'nt')
        try:
            deadline = time.monotonic() + 15
            while not ready.exists() and parent.poll() is None and time.monotonic() < deadline:
                time.sleep(0.02)
            assert ready.exists(), 'child cleanup fixture never reached readiness'
        finally:
            stop_process_tree(parent)
        time.sleep(4.2)
        assert not marker.exists(), 'stopped process left a running child'
        with workspace_lock(root / 'locked'):
            try:
                with workspace_lock(root / 'locked'):
                    raise AssertionError('second writer entered a live workspace')
            except RuntimeError:
                pass
        with workspace_lock(root / 'locked'):
            pass
        (root / 'artifact.jar').write_bytes(b'jar')
        assert contained_file(root, 'artifact.jar') == root / 'artifact.jar'
        for path in ('../escape.jar', '.', str(root.parent / 'escape.jar')):
            try:
                contained_file(root, path)
                raise AssertionError('invalid artifact path was accepted: ' + path)
            except ValueError:
                pass
    print(json.dumps({'status': 'PASS', 'cases': ['complete-large-logs', 'launch-failure-evidence',
          'timeout-process-tree', 'workspace-exclusion', 'lock-recovery', 'artifact-path-containment']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
