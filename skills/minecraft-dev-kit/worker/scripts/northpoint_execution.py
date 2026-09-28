#!/usr/bin/env python3
"""Durable process evidence and safe artifact operations for real Northpoint runs."""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import uuid
from typing import Any, Iterator


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def contained_file(root: Path, value: str) -> Path:
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()) or path == root.resolve():
        raise ValueError(f'artifact escapes output directory: {value}')
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f'artifact is missing or empty: {path}')
    return path


def _descendants(pid: int) -> list[int]:
    """Snapshot only the current process tree before stopping its owner."""
    parents: dict[int, int] = {}
    if Path('/proc').is_dir():
        for item in Path('/proc').iterdir():
            if not item.name.isdigit():
                continue
            try:
                # comm can contain spaces and parentheses; split after the last ).
                tail = (item / 'stat').read_text().rsplit(')', 1)[1].split()
                parents[int(item.name)] = int(tail[1])
            except (OSError, ValueError, IndexError):
                continue
    else:
        try:
            rows = subprocess.run(['ps', '-axo', 'pid=,ppid='], capture_output=True,
                                  text=True, timeout=5, check=True).stdout.splitlines()
            parents = {int(row.split()[0]): int(row.split()[1]) for row in rows}
        except (OSError, ValueError, IndexError, subprocess.SubprocessError):
            return []
    found, todo = [], [pid]
    while todo:
        parent = todo.pop()
        children = [child for child, ppid in parents.items() if ppid == parent and child not in found]
        found.extend(children)
        todo.extend(children)
    return found


def stop_process_tree(process: subprocess.Popen) -> None:
    """Stop only this launched process and its descendants, including Gradle children."""
    if process.poll() is not None:
        return
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15, check=False)
    else:
        descendants = _descendants(process.pid)
        # Every run_logged owner starts a new session. Nested owners may have
        # their own sessions, so signal the frozen descendant set as well.
        for pid in reversed(descendants):
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.kill(pid, signal.SIGTERM)
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(process.pid, signal.SIGKILL)
        for pid in reversed(descendants):
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.kill(pid, signal.SIGKILL)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def run_logged(argv: list[str], *, directory: Path, name: str,
               cwd: Path | None = None, env: dict[str, str] | None = None,
               timeout: float = 600) -> subprocess.CompletedProcess[str]:
    """Spool complete stdout/stderr to disk before interpreting a result.

    Exit 124 denotes timeout and 130 interruption; process evidence survives both.
    Environment variables are deliberately not copied to the receipt.
    """
    if timeout <= 0:
        raise ValueError('timeout must be positive')
    directory.mkdir(parents=True, exist_ok=True)
    out_path, err_path = directory / f'{name}.stdout.txt', directory / f'{name}.stderr.txt'
    result_path = directory / f'{name}.process.json'
    started = time.monotonic()
    record: dict[str, Any] = {'schema_version': 1, 'argv': list(argv),
                             'cwd': str(cwd) if cwd else None, 'state': 'starting',
                             'stdout': out_path.name, 'stderr': err_path.name}
    atomic_json(result_path, record)
    process = None
    code = 1
    with out_path.open('wb') as stdout, err_path.open('wb') as stderr:
        try:
            process = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                       stdout=stdout, stderr=stderr, start_new_session=os.name != 'nt')
            record.update(pid=process.pid, state='running')
            atomic_json(result_path, record)
            code = process.wait(timeout=timeout)
            record['state'] = 'completed'
        except subprocess.TimeoutExpired:
            stop_process_tree(process)
            code, record['state'] = 124, 'timed-out'
        except KeyboardInterrupt:
            if process is not None:
                stop_process_tree(process)
            code, record['state'] = 130, 'interrupted'
        except OSError as exc:
            record['state'], record['error'] = 'launch-failed', str(exc)
            stderr.write((str(exc) + '\n').encode('utf-8'))
        finally:
            record.update(returncode=code, elapsed_seconds=round(time.monotonic() - started, 6))
            atomic_json(result_path, record)
    return subprocess.CompletedProcess(argv, code, out_path.read_text(encoding='utf-8', errors='replace'),
                                       err_path.read_text(encoding='utf-8', errors='replace'))


@contextlib.contextmanager
def workspace_lock(root: Path) -> Iterator[None]:
    """OS-owned lock: no stale lockfile can permanently strand a recovered run."""
    root.mkdir(parents=True, exist_ok=True)
    path = root / '.northpoint.lock'
    stream = path.open('a+b')
    try:
        if os.name == 'nt':
            import msvcrt
            if path.stat().st_size == 0:
                stream.write(b'\0'); stream.flush()
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RuntimeError(f'workspace already active: {root}') from exc
        else:
            import fcntl
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError(f'workspace already active: {root}') from exc
        yield
    finally:
        # Closing releases the OS lock after success, exceptions, or termination.
        stream.close()


def new_run_id() -> str:
    return time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-' + uuid.uuid4().hex[:8]
