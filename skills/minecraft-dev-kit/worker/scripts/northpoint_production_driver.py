#!/usr/bin/env python3
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import zipfile
from typing import Any

from northpoint_execution import run_logged

COMMAND_LOG_DIR: pathlib.Path | None = None
COMMAND_SEQUENCE = 0

from northpoint_compose import compose
from northpoint_source_intake import infer_config, inspect_project
from northpoint_target_26_3 import ConversionBlock, materialize_port

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
CONFIG_NAME = 'northpoint.project.json'
ARTIFACT_ENGINE_FILES = (
    'scripts/northpoint_compose.py',
    'scripts/northpoint_source_intake.py',
    'scripts/northpoint_target_26_3.py',
    'scripts/port_26_3_pipeline.py',
    'scripts/port_scaffold_26_3.py',
    'scripts/port_intake.py',
    'scripts/port_26_3_common.py',
    'scripts/port_semantic_planner.py',
    'scripts/mapping_lineage.py',
    'scripts/mixin_surface_audit.py',
    'scripts/content_identity_inventory.py',
    'scripts/content_parity_audit.py',
    'scripts/registration_identity_inventory.py',
    'scripts/registration_parity_audit.py',
    'scripts/classfile_symbol_index.py',
    'scripts/packaged_linkage_audit.py',
    'references/minecraft-26.3-port-rules.json',
    'references/minecraft-26.3-semantic-migrations.json',
    'references/minecraft-mapping-prewarm-profiles.json',
    'references/minecraft-mapping-sources.json',
)


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def run(cmd: list[str], *, cwd: pathlib.Path | None = None, timeout: int = 180, env: dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess:
    global COMMAND_SEQUENCE
    if COMMAND_LOG_DIR is not None:
        COMMAND_SEQUENCE += 1
        cp = run_logged(cmd, directory=COMMAND_LOG_DIR, name=f"command-{COMMAND_SEQUENCE:03d}",
                        cwd=cwd, env=env, timeout=timeout)
        if check and cp.returncode:
            raise RuntimeError(f"command exited {cp.returncode}; full logs: {COMMAND_LOG_DIR}\n" +
                               (cp.stderr or cp.stdout or f"command failed: {cmd}").strip()[-16000:])
        return cp
    cp = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    if check and cp.returncode:
        raise RuntimeError((cp.stderr or cp.stdout or f'command failed: {cmd}').strip()[-16000:])
    return cp


def cell_java_binary(cell: dict[str, Any]) -> str | None:
    pinned = str(cell.get('java_path') or '').strip()
    return pinned or shutil.which('java')


def cell_javac_binary(cell: dict[str, Any]) -> str | None:
    pinned = str(cell.get('java_path') or '').strip()
    if pinned:
        java_path = pathlib.Path(pinned)
        name = 'javac.exe' if java_path.name.lower().endswith('.exe') else 'javac'
        candidate = java_path.with_name(name)
        return str(candidate) if candidate.is_file() else None
    return shutil.which('javac')


def cell_java_env(cell: dict[str, Any]) -> dict[str, str]:
    env = dict(os.environ)
    pinned = str(cell.get('java_path') or '').strip()
    if not pinned:
        return env
    java_path = pathlib.Path(pinned).resolve()
    bin_dir = java_path.parent
    env['JAVA_HOME'] = str(bin_dir.parent)
    env['PATH'] = str(bin_dir) + os.pathsep + env.get('PATH', '')
    return env


def java_major(binary: str | None = None) -> int | None:
    java = binary or shutil.which('java')
    if not java:
        return None
    cp = run([java, '-version'], check=False, timeout=15)
    text = (cp.stdout + '\n' + cp.stderr)
    m = re.search(r'version\s+"?(\d+)', text) or re.search(r'openjdk\s+(\d+)', text, re.I)
    return int(m.group(1)) if m else None


def javac_major(binary: str | None = None) -> int | None:
    javac = binary or shutil.which('javac')
    if not javac:
        return None
    cp = run([javac, '-version'], check=False, timeout=15)
    m = re.search(r'javac\s+(\d+)', cp.stdout + cp.stderr)
    return int(m.group(1)) if m else None


def tool_version(exe: str, args: list[str]) -> str | None:
    path = shutil.which(exe)
    if not path:
        return None
    try:
        cp = run([path, *args], check=False, timeout=15)
    except Exception:
        return None
    text = (cp.stdout + '\n' + cp.stderr).strip()
    return text[:2000] if text else ''


def read_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise RuntimeError(f'{path.name} must contain a JSON object')
    return value


def stable_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def artifact_engine_fingerprint(cell: dict[str, Any]) -> str:
    if str(cell.get('minecraft') or '').strip() != '26.3':
        return ''
    h = hashlib.sha256()
    for rel in ARTIFACT_ENGINE_FILES:
        path = ROOT / rel
        if not path.is_file():
            h.update(f'missing:{rel}'.encode('utf-8')); h.update(b'\0')
            continue
        h.update(rel.encode('utf-8')); h.update(b'\0')
        h.update(sha256_file(path).encode('ascii')); h.update(b'\0')
    return h.hexdigest()


def load_config(project: pathlib.Path, cell: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    # The canonical config is composed too, so loader/version/cell overlays can
    # replace build/runtime rules without branching the entire project.
    base = project / CONFIG_NAME
    root_cfg = read_json(base) if base.exists() else infer_config(project, cell)
    per_cell = root_cfg.get('cells') or {}
    merged = dict(root_cfg)
    merged.pop('cells', None)
    for key in (str(cell.get('loader')), str(cell.get('minecraft')), str(cell.get('id'))):
        patch = per_cell.get(key)
        if isinstance(patch, dict):
            merged = deep_merge(merged, patch)
    return root_cfg, merged


def deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def materialize_legacy_target(project: pathlib.Path, cell: dict[str, Any], work: pathlib.Path) -> tuple[pathlib.Path, dict[str, Any] | None]:
    # Explicit Northpoint projects already own their target composition. Automatic
    # migration is only for an ordinary legacy source tree selected by the user.
    if (project / CONFIG_NAME).is_file():
        return project, None
    if str(cell.get('minecraft') or '').strip() != '26.3':
        return project, None

    source = inspect_project(project)
    source_mc = str(source.get('minecraft') or '').strip()
    source_loader = str(source.get('loader') or '').strip()
    target_loader = str(cell.get('loader') or '').strip()
    if not source_loader:
        raise ConversionBlock('source loader could not be determined uniquely; explicit Northpoint target configuration is required')
    if source_loader != target_loader:
        raise ConversionBlock(
            f'source loader {source_loader!r} does not match target loader {target_loader!r}; '
            'cross-loader conversion requires an explicit target adapter/overlay'
        )
    if not source_mc:
        raise ConversionBlock('source Minecraft version could not be determined exactly; refusing an unchanged 26.3 false pass')
    if source_mc == '26.3':
        return project, None

    target = work / 'materialized-target'
    manifest = materialize_port(project, target, target_loader)
    return target, manifest


def render_token(value: Any, context: dict[str, str]) -> str:
    text = str(value)
    for key, replacement in context.items():
        text = text.replace('{' + key + '}', replacement)
    return text


def render_argv(argv: Any, context: dict[str, str]) -> list[str]:
    if not isinstance(argv, list) or not argv:
        raise RuntimeError('build/runtime command must be a non-empty JSON array; shell strings are not accepted')
    return [render_token(v, context) for v in argv]


def safe_rel(root: pathlib.Path, value: str) -> pathlib.Path:
    candidate = (root / value).resolve()
    rr = root.resolve()
    if candidate != rr and rr not in candidate.parents:
        raise RuntimeError(f'path escapes composed workspace: {value}')
    return candidate


def build_probe(project: pathlib.Path, cell: dict[str, Any]) -> dict[str, Any]:
    _, cfg = load_config(project, cell)
    build = cfg.get('build') if isinstance(cfg.get('build'), dict) else {}
    mode = str(build.get('mode') or 'auto').lower()
    wrapper = None
    if (project / 'gradlew').exists(): wrapper = 'gradlew'
    elif (project / 'mvnw').exists(): wrapper = 'mvnw'
    return {
        'protocol': 2,
        'driver': 'northpoint-production',
        'driver_schema': 1,
        'java_major': java_major(cell_java_binary(cell)),
        'javac_major': javac_major(cell_javac_binary(cell)),
        'java_path': str(cell.get('java_path') or ''),
        'gradle': tool_version('gradle', ['--version']),
        'maven': tool_version('mvn', ['-version']),
        'wrapper': wrapper,
        'requested_java': int(cell.get('java') or 0),
        'build_mode': mode,
        'config_sha256': stable_hash(cfg),
        'artifact_fingerprint': artifact_engine_fingerprint(cell),
    }


def run_py(script: str, args: list[str], *, cwd: pathlib.Path, timeout: int = 180) -> subprocess.CompletedProcess:
    return run([sys.executable, str(SCRIPTS / script), *args], cwd=cwd, timeout=timeout, check=False)


def write_evidence(path: pathlib.Path, name: str, cp: subprocess.CompletedProcess) -> dict[str, Any]:
    path.mkdir(parents=True, exist_ok=True)
    out = path / f'{name}.stdout.txt'; err = path / f'{name}.stderr.txt'
    out.write_text(cp.stdout or '', encoding='utf-8')
    err.write_text(cp.stderr or '', encoding='utf-8')
    return {'gate': name, 'exit': cp.returncode, 'stdout': out.name, 'stderr': err.name}


def build_direct_javac(composed: pathlib.Path, work: pathlib.Path, cfg: dict[str, Any], cell: dict[str, Any], timeout: int) -> pathlib.Path:
    build = cfg.get('build') or {}
    roots = build.get('source_roots') or ['src/main/java']
    source_files: list[pathlib.Path] = []
    for rel in roots:
        root = safe_rel(composed, str(rel))
        if root.exists():
            source_files.extend(sorted(root.rglob('*.java')))
    if not source_files:
        raise RuntimeError('javac build has no Java sources')
    required = int(cell.get('java') or build.get('java') or 0)
    javac = cell_javac_binary(cell)
    have = javac_major(javac)
    if not javac or not have:
        raise ToolchainBlock('JDK compiler javac is unavailable')
    if required and required > have:
        raise ToolchainBlock(f'Java {required} required; runner has javac {have}')
    classes = work / 'classes'
    classes.mkdir(parents=True, exist_ok=True)
    cp_entries = []
    for rel in build.get('classpath') or []:
        p = safe_rel(composed, str(rel))
        cp_entries.append(str(p))
    compile_only_roots = build.get('compile_only_source_roots') or []
    if compile_only_roots:
        stubs = work / 'compile-only-classes'
        stub_sources: list[pathlib.Path] = []
        for rel in compile_only_roots:
            root = safe_rel(composed, str(rel))
            if root.exists():
                stub_sources.extend(sorted(root.rglob('*.java')))
        if not stub_sources:
            raise RuntimeError('compile_only_source_roots configured but no Java sources were found')
        stubs.mkdir(parents=True, exist_ok=True)
        stub_cmd = [javac]
        if required:
            stub_cmd += ['--release', str(required)]
        stub_cmd += ['-d', str(stubs), *map(str, stub_sources)]
        run(stub_cmd, cwd=composed, timeout=timeout, env=cell_java_env(cell))
        cp_entries.append(str(stubs))
    cmd = [javac]
    if required:
        cmd += ['--release', str(required)]
    if cp_entries:
        cmd += ['-cp', os.pathsep.join(cp_entries)]
    cmd += ['-d', str(classes), *map(str, source_files)]
    run(cmd, cwd=composed, timeout=timeout, env=cell_java_env(cell))
    for rel in build.get('resource_roots') or ['src/main/resources']:
        root = safe_rel(composed, str(rel))
        if not root.exists(): continue
        for src in sorted(p for p in root.rglob('*') if p.is_file()):
            dst = classes / src.relative_to(root)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    jar = work / 'built.jar'
    with zipfile.ZipFile(jar, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for src in sorted(p for p in classes.rglob('*') if p.is_file()):
            z.write(src, src.relative_to(classes).as_posix())
    return jar


class ToolchainBlock(RuntimeError):
    pass


def detect_build_mode(composed: pathlib.Path, cfg: dict[str, Any]) -> str:
    build = cfg.get('build') if isinstance(cfg.get('build'), dict) else {}
    mode = str(build.get('mode') or 'auto').lower()
    if mode != 'auto':
        return mode
    if (composed / 'gradlew').exists() or (composed / 'build.gradle').exists() or (composed / 'build.gradle.kts').exists():
        return 'gradle'
    if (composed / 'mvnw').exists() or (composed / 'pom.xml').exists():
        return 'maven'
    return 'javac'


def find_artifact(composed: pathlib.Path, cfg: dict[str, Any], mode: str) -> pathlib.Path:
    build = cfg.get('build') or {}
    patterns = build.get('artifact_globs')
    if not patterns:
        patterns = ['build/libs/*.jar'] if mode == 'gradle' else ['target/*.jar'] if mode == 'maven' else []
    candidates: list[pathlib.Path] = []
    for pattern in patterns:
        for raw in glob.glob(str(composed / str(pattern))):
            p = pathlib.Path(raw).resolve()
            if p.is_file() and not p.name.endswith(('-sources.jar', '-javadoc.jar')):
                candidates.append(p)
    if not candidates:
        raise RuntimeError(f'no built artifact matched: {patterns}')
    candidates.sort(key=lambda p: (p.stat().st_mtime_ns, p.stat().st_size), reverse=True)
    return candidates[0]


def build_project(composed: pathlib.Path, work: pathlib.Path, cfg: dict[str, Any], cell: dict[str, Any], timeout: int) -> pathlib.Path:
    mode = detect_build_mode(composed, cfg)
    required = int(cell.get('java') or 0)
    java_bin = cell_java_binary(cell)
    have = java_major(java_bin)
    if required and (not have or have < required):
        raise ToolchainBlock(f'Java {required} required; runner has Java {have or "unavailable"}')
    if str(cell.get('java_path') or '').strip() and not cell_javac_binary(cell):
        raise ToolchainBlock(f'JDK {required or have or "requested"} is required; pinned Java has no javac')
    build = cfg.get('build') if isinstance(cfg.get('build'), dict) else {}
    context = {
        'minecraft': str(cell.get('minecraft')),
        'loader': str(cell.get('loader')),
        'java': str(required),
        'composed': str(composed),
        'work': str(work),
        'compile_only': str((work / 'compile-only-classes').resolve()),
        'pathsep': os.pathsep,
    }
    if mode == 'javac':
        return build_direct_javac(composed, work, cfg, cell, timeout)
    if mode == 'gradle':
        if build.get('command'):
            cmd = render_argv(build['command'], context)
        elif (composed / 'gradlew').exists():
            cmd = [str(composed / 'gradlew'), '--no-daemon', 'clean', 'build']
        elif shutil.which('gradle'):
            cmd = [shutil.which('gradle') or 'gradle', '--no-daemon', 'clean', 'build']
        else:
            raise ToolchainBlock('Gradle project detected but neither gradlew nor gradle is available')
        run(cmd, cwd=composed, timeout=timeout, env=cell_java_env(cell))
        return find_artifact(composed, cfg, mode)
    if mode == 'maven':
        if build.get('command'):
            cmd = render_argv(build['command'], context)
        elif (composed / 'mvnw').exists():
            cmd = [str(composed / 'mvnw'), '-B', '-DskipTests=false', 'clean', 'package']
        elif shutil.which('mvn'):
            cmd = [shutil.which('mvn') or 'mvn', '-B', '-DskipTests=false', 'clean', 'package']
        else:
            raise ToolchainBlock('Maven project detected but neither mvnw nor mvn is available')
        run(cmd, cwd=composed, timeout=timeout, env=cell_java_env(cell))
        return find_artifact(composed, cfg, mode)
    if mode == 'command':
        cmd = render_argv(build.get('command'), context)
        run(cmd, cwd=composed, timeout=timeout, env=cell_java_env(cell))
        return find_artifact(composed, cfg, mode)
    raise RuntimeError(f'unsupported build mode: {mode}')


def inspect_metadata(jar: pathlib.Path, cfg: dict[str, Any], cell: dict[str, Any]) -> list[str]:
    expected = str(cfg.get('mod_id') or '').strip()
    evidence: list[str] = []
    with zipfile.ZipFile(jar) as z:
        names = set(z.namelist())
        loader = str(cell.get('loader'))
        if loader == 'fabric':
            if 'fabric.mod.json' not in names: raise RuntimeError('Fabric artifact is missing fabric.mod.json')
            value = json.loads(z.read('fabric.mod.json'))
            if expected and str(value.get('id')) != expected:
                raise RuntimeError(f'fabric.mod.json id mismatch: expected {expected}, got {value.get("id")}')
            evidence.append('metadata:fabric.mod.json')
        elif loader == 'neoforge':
            if 'META-INF/neoforge.mods.toml' not in names: raise RuntimeError('NeoForge artifact is missing META-INF/neoforge.mods.toml')
            text = z.read('META-INF/neoforge.mods.toml').decode('utf-8', 'replace')
            if expected and not re.search(rf'\bmodId\s*=\s*["\']{re.escape(expected)}["\']', text):
                raise RuntimeError(f'NeoForge modId {expected} not found in metadata')
            evidence.append('metadata:neoforge.mods.toml')
        elif loader == 'forge':
            if 'META-INF/mods.toml' not in names: raise RuntimeError('Forge artifact is missing META-INF/mods.toml')
            text = z.read('META-INF/mods.toml').decode('utf-8', 'replace')
            if expected and not re.search(rf'\bmodId\s*=\s*["\']{re.escape(expected)}["\']', text):
                raise RuntimeError(f'Forge modId {expected} not found in metadata')
            evidence.append('metadata:mods.toml')
        else:
            evidence.append(f'metadata:{loader}:unchecked')
    return evidence


def generic_static_gates(project: pathlib.Path, composed: pathlib.Path, jar: pathlib.Path, evidence_dir: pathlib.Path, cfg: dict[str, Any], cell: dict[str, Any], timeout: int) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    blockers: list[str] = []

    mixin_json = evidence_dir / 'mixin-surface.json'
    cp = run_py('mixin_surface_audit.py', [str(composed), '--target-minecraft', str(cell['minecraft']), '--loader', str(cell['loader']), '--json-out', str(mixin_json), '--fail-on-blocker'], cwd=ROOT, timeout=timeout)
    rows.append(write_evidence(evidence_dir, 'mixin-surface', cp))
    if cp.returncode != 0:
        blockers.append('mixin-surface-audit')

    parity = cfg.get('parity') if isinstance(cfg.get('parity'), dict) else {}
    if parity.get('source_authority'):
        source_authority = safe_rel(project, str(parity['source_authority']))
    else:
        source_authority = composed
    src_content = evidence_dir / 'source-content.json'
    cp = run_py('content_identity_inventory.py', [str(source_authority), '--json-out', str(src_content)], cwd=ROOT, timeout=timeout)
    rows.append(write_evidence(evidence_dir, 'source-content', cp))
    if cp.returncode != 0: blockers.append('source-content-inventory')

    content_parity = evidence_dir / 'content-parity.json'
    if src_content.exists():
        cp = run_py('content_parity_audit.py', [str(src_content), str(jar), '--json-out', str(content_parity), '--fail-on-missing'], cwd=ROOT, timeout=timeout)
        rows.append(write_evidence(evidence_dir, 'content-parity', cp))
        if cp.returncode != 0: blockers.append('content-parity')

    src_reg = evidence_dir / 'source-registration.json'
    cp = run_py('registration_identity_inventory.py', [str(source_authority), '--json-out', str(src_reg)], cwd=ROOT, timeout=timeout)
    rows.append(write_evidence(evidence_dir, 'source-registration', cp))
    if cp.returncode != 0: blockers.append('source-registration-inventory')

    reg_parity = evidence_dir / 'registration-parity.json'
    if src_reg.exists():
        cp = run_py('registration_parity_audit.py', [str(src_reg), str(composed), '--json-out', str(reg_parity), '--fail-on-missing'], cwd=ROOT, timeout=timeout)
        rows.append(write_evidence(evidence_dir, 'registration-parity', cp))
        if cp.returncode != 0: blockers.append('registration-parity')

    return rows, blockers


def linkage_gate(composed: pathlib.Path, work: pathlib.Path, jar: pathlib.Path, evidence_dir: pathlib.Path, cfg: dict[str, Any], cell: dict[str, Any], timeout: int) -> tuple[dict[str, Any] | None, str | None]:
    link = cfg.get('linkage') if isinstance(cfg.get('linkage'), dict) else {}
    target = link.get('target_index')
    target_path: pathlib.Path | None = safe_rel(composed, str(target)) if target else None
    if target_path is None and link.get('target_classes'):
        raw_classes = str(link['target_classes'])
        classes = (work / 'compile-only-classes').resolve() if raw_classes == '__compile_only__' else safe_rel(composed, raw_classes)
        target_path = evidence_dir / 'target-index.json'
        cp_index = run_py('classfile_symbol_index.py', ['index', str(classes), '--include-refs', '--runtime-java', str(cell.get('java') or 0), '--out', str(target_path)], cwd=ROOT, timeout=timeout)
        write_evidence(evidence_dir, 'target-index', cp_index)
        if cp_index.returncode != 0:
            return None, 'target-index'
    if target_path is None:
        return None, None
    out = evidence_dir / 'packaged-linkage.json'
    argv = [str(jar), '--target-index', str(target_path), '--runtime-java', str(cell.get('java') or 0), '--json-out', str(out), '--fail-on-blocker']
    for dep in link.get('dependency_indexes') or []:
        argv += ['--dependency-index', str(safe_rel(composed, str(dep)))]
    for prefix in link.get('prefixes') or ['net/minecraft/']:
        argv += ['--prefix', str(prefix)]
    cp = run_py('packaged_linkage_audit.py', argv, cwd=ROOT, timeout=timeout)
    row = write_evidence(evidence_dir, 'packaged-linkage', cp)
    return row, None if cp.returncode == 0 else 'packaged-linkage'


def runtime_gate(composed: pathlib.Path, jar: pathlib.Path, work: pathlib.Path, cfg: dict[str, Any], cell: dict[str, Any], timeout: int) -> tuple[str, list[str], str | None]:
    runtime = cfg.get('runtime') if isinstance(cfg.get('runtime'), dict) else {}
    required = bool(runtime.get('required', False))
    command = runtime.get('command')
    if not command:
        return ('runtime-unverified' if required else 'passed'), [], ('runtime command is not configured' if required else None)
    context = {
        'minecraft': str(cell.get('minecraft')),
        'loader': str(cell.get('loader')),
        'java': str(cell.get('java') or 0),
        'artifact': str(jar),
        'composed': str(composed),
        'work': str(work),
        'compile_only': str((work / 'compile-only-classes').resolve()),
        'pathsep': os.pathsep,
    }
    cmd = render_argv(command, context)
    cp = run(cmd, cwd=composed, timeout=int(runtime.get('timeout') or timeout), env=cell_java_env(cell), check=False)
    evidence = [f'runtime-exit:{cp.returncode}']
    expected = runtime.get('stdout_contains')
    if cp.returncode != 0:
        return 'failed', evidence, (cp.stderr or cp.stdout or 'runtime command failed').strip()[-12000:]
    if expected is not None and str(expected) not in cp.stdout:
        return 'failed', evidence, f'runtime stdout did not contain expected marker: {expected}'
    evidence.append('runtime-command')
    return 'passed', evidence, None


def main() -> int:
    global COMMAND_LOG_DIR
    p = argparse.ArgumentParser(description='Build and verify a real Northpoint composed mod target.')
    p.add_argument('--probe', action='store_true')
    p.add_argument('--cell-json', type=pathlib.Path, required=True)
    p.add_argument('--project', type=pathlib.Path, required=True)
    p.add_argument('--work', type=pathlib.Path)
    p.add_argument('--output', type=pathlib.Path)
    p.add_argument('--timeout', type=int, default=180)
    args = p.parse_args()
    cell = read_json(args.cell_json)
    project = args.project.resolve()
    if args.probe:
        print(json.dumps(build_probe(project, cell), sort_keys=True))
        return 0
    if not args.work or not args.output:
        raise RuntimeError('--work and --output are required outside --probe')
    work = args.work.resolve(); out = args.output.resolve(); out.mkdir(parents=True, exist_ok=True)
    COMMAND_LOG_DIR = work / 'evidence' / 'commands'
    try:
        conversion_root, conversion_manifest = materialize_legacy_target(project, cell, work)
    except ConversionBlock as exc:
        print(json.dumps({'state': 'blocked', 'reason': str(exc), 'evidence': ['conversion-block'], 'conversion': None}))
        return 0

    composed = work / 'composed'
    inv = compose(conversion_root, cell, composed, clean=True)
    _, cfg = load_config(composed, cell)
    if not cfg:
        # Support root config that intentionally lives outside overlays.
        _, cfg = load_config(project, cell)
    evidence_dir = work / 'evidence'; evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence: list[Any] = [f'compose:{inv["sha256"]}', f'project-config:{stable_hash(cfg)}']
    if conversion_manifest:
        source_meta = conversion_manifest.get('source') or {}
        target_meta = conversion_manifest.get('target') or {}
        evidence.insert(0, f"conversion:{source_meta.get('minecraft') or 'unknown'}->{target_meta.get('minecraft') or cell.get('minecraft')}")
        evidence.append(f"conversion-target:{conversion_manifest.get('target_sha256')}")
    try:
        jar = build_project(composed, work, cfg, cell, args.timeout)
    except ToolchainBlock as exc:
        print(json.dumps({'state': 'blocked', 'reason': str(exc), 'evidence': evidence + ['toolchain-block'], 'conversion': conversion_manifest}))
        return 0
    evidence.append(f'build-artifact:{sha256_file(jar)}')
    evidence += inspect_metadata(jar, cfg, cell)

    rows, blockers = generic_static_gates(project, composed, jar, evidence_dir, cfg, cell, args.timeout)
    evidence.extend(rows)
    link_row, link_blocker = linkage_gate(composed, work, jar, evidence_dir, cfg, cell, args.timeout)
    if link_row: evidence.append(link_row)
    if link_blocker: blockers.append(link_blocker)
    if blockers:
        print(json.dumps({'state': 'failed', 'reason': 'static release blockers: ' + ', '.join(sorted(set(blockers))), 'evidence': evidence, 'conversion': conversion_manifest}))
        return 0

    state, runtime_evidence, runtime_reason = runtime_gate(composed, jar, work, cfg, cell, args.timeout)
    evidence.extend(runtime_evidence)
    if state == 'runtime-unverified':
        final = out / jar.name
        shutil.copy2(jar, final)
        print(json.dumps({
            'state': state,
            'reason': runtime_reason,
            'artifact': final.name,
            'evidence': evidence + ['candidate-artifact-preserved'],
            'conversion': conversion_manifest,
        }))
        return 0
    if state != 'passed':
        print(json.dumps({'state': state, 'reason': runtime_reason, 'evidence': evidence, 'conversion': conversion_manifest}))
        return 0

    final = out / jar.name
    shutil.copy2(jar, final)
    print(json.dumps({'state': 'passed', 'artifact': final.name, 'evidence': evidence, 'conversion': conversion_manifest}))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({'state': 'failed', 'reason': str(exc), 'evidence': []}))
        raise SystemExit(0)