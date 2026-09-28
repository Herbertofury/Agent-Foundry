#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, pathlib, re
from typing import Any

IGNORE_DIRS = {'.git', '.gradle', '.idea', '.vscode', 'build', 'target', 'out', 'run', 'runs', 'logs', '.northpoint'}
CONFIG_NAME = 'northpoint.project.json'


def read_text(path: pathlib.Path, limit: int = 2_000_000) -> str:
    try:
        data = path.read_bytes()[:limit]
        return data.decode('utf-8', 'replace')
    except Exception:
        return ''


def read_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(read_text(path))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def parse_properties(path: pathlib.Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in read_text(path).splitlines():
        line = raw.strip()
        if not line or line.startswith(('#', '!')):
            continue
        sep = '=' if '=' in line else ':' if ':' in line else None
        if not sep:
            continue
        key, value = line.split(sep, 1)
        out[key.strip()] = value.strip()
    return out


def first_existing(root: pathlib.Path, rels: list[str]) -> pathlib.Path | None:
    for rel in rels:
        p = root / rel
        if p.is_file():
            return p
    return None


def find_files(root: pathlib.Path, names: set[str], max_depth: int = 7) -> list[pathlib.Path]:
    found: list[pathlib.Path] = []
    rr = root.resolve()
    for base, dirs, files in os.walk(rr):
        base_path = pathlib.Path(base)
        try:
            depth = len(base_path.relative_to(rr).parts)
        except Exception:
            continue
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith('.northpoint')]
        if depth > max_depth:
            dirs[:] = []
            continue
        for name in files:
            if name in names:
                found.append(base_path / name)
    return sorted(found)


def parse_toml_mod_id(text: str) -> str | None:
    matches = re.findall(r'(?m)^\s*modId\s*=\s*["\']([^"\']+)["\']', text)
    return matches[0].strip() if matches else None


def is_template_placeholder(value: str | None) -> bool:
    raw = str(value or '').strip()
    if not raw:
        return False
    return bool(
        re.fullmatch(r'\$\{[^{}]+\}', raw)
        or re.fullmatch(r'@[A-Za-z0-9_.-]+@', raw)
        or re.fullmatch(r'\{\{[^{}]+\}\}', raw)
    )


def property_mod_id(root: pathlib.Path) -> str | None:
    props: dict[str, str] = {}
    for rel in ('gradle.properties', 'project.properties'):
        p = root / rel
        if p.is_file():
            props.update(parse_properties(p))
    for key in ('mod_id', 'modId', 'modid'):
        value = str(props.get(key) or '').strip()
        if re.fullmatch(r'[a-z][a-z0-9_]{1,63}', value):
            return value
    return None


def parse_java_hint(text: str) -> int | None:
    pats = [
        r'JavaVersion\.VERSION_(\d+)',
        r'options\.release\s*=\s*(\d+)',
        r'options\.release\.set\(\s*(\d+)\s*\)',
        r'JavaLanguageVersion\.of\(\s*(\d+)\s*\)',
        r'<maven\.compiler\.release>\s*(\d+)\s*</maven\.compiler\.release>',
        r'<maven\.compiler\.source>\s*(\d+)\s*</maven\.compiler\.source>',
        r'<release>\s*(\d+)\s*</release>',
    ]
    for pat in pats:
        m = re.search(pat, text, re.I)
        if m:
            return int(m.group(1))
    return None


def normalize_mc(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.strip().strip('"\'')
    exact = re.search(r'(?<!\d)(\d+(?:\.\d+){1,2})(?!\d)', raw)
    return exact.group(1) if exact else None


def detect_build(root: pathlib.Path) -> tuple[str, dict[str, Any]]:
    if (root / 'gradlew').is_file() or (root / 'gradlew.bat').is_file() or (root / 'build.gradle').is_file() or (root / 'build.gradle.kts').is_file():
        return 'gradle', {'wrapper': 'gradlew' if (root / 'gradlew').exists() or (root / 'gradlew.bat').exists() else None}
    if (root / 'mvnw').is_file() or (root / 'mvnw.cmd').is_file() or (root / 'pom.xml').is_file():
        return 'maven', {'wrapper': 'mvnw' if (root / 'mvnw').exists() or (root / 'mvnw.cmd').exists() else None}
    if (root / 'src' / 'main' / 'java').is_dir():
        return 'javac', {'wrapper': None}
    return 'unknown', {'wrapper': None}


def metadata_candidates(root: pathlib.Path) -> list[pathlib.Path]:
    return find_files(root, {'fabric.mod.json', 'quilt.mod.json', 'mods.toml', 'neoforge.mods.toml'}, max_depth=8)


def normalize_runtime_scope(value: Any) -> str:
    raw = str(value or '').strip().lower()
    aliases = {
        '*': 'both',
        'both': 'both',
        'common': 'both',
        'client+server': 'both',
        'client': 'client',
        'server': 'server',
        'dedicated_server': 'server',
    }
    return aliases.get(raw, 'unknown')


def detect_runtime_scope(root: pathlib.Path, loader: str | None) -> str:
    if loader == 'fabric':
        for p in metadata_candidates(root):
            if p.name != 'fabric.mod.json':
                continue
            return normalize_runtime_scope(read_json(p).get('environment') or '*')
    return 'unknown'


def configured_runtime_scope(cfg: dict[str, Any] | None) -> str:
    if not isinstance(cfg, dict):
        return 'unknown'
    runtime = cfg.get('runtime')
    if not isinstance(runtime, dict):
        return 'unknown'
    return normalize_runtime_scope(runtime.get('scope'))


def detect_loader_and_mod_id(root: pathlib.Path) -> tuple[str | None, str | None, list[dict[str, str]], list[str]]:
    rows: list[dict[str, str]] = []
    warnings: list[str] = []
    loaders: list[str] = []
    mod_ids: list[str] = []
    for p in metadata_candidates(root):
        name = p.name
        loader = None
        mod_id = None
        if name == 'fabric.mod.json':
            loader = 'fabric'; mod_id = str(read_json(p).get('id') or '').strip() or None
        elif name == 'quilt.mod.json':
            loader = 'quilt'
            q = read_json(p)
            mod_id = str(((q.get('quilt_loader') or {}) if isinstance(q.get('quilt_loader'), dict) else {}).get('id') or q.get('id') or '').strip() or None
        elif name == 'neoforge.mods.toml':
            loader = 'neoforge'; mod_id = parse_toml_mod_id(read_text(p))
        elif name == 'mods.toml':
            loader = 'forge'; mod_id = parse_toml_mod_id(read_text(p))
        if loader:
            loaders.append(loader)
        row_mod_id = mod_id or ''
        if mod_id and is_template_placeholder(mod_id):
            warnings.append(f'metadata template placeholder detected at {p.relative_to(root)}: {mod_id}')
            mod_id = None
        if mod_id:
            mod_ids.append(mod_id)
        rows.append({'path': str(p.relative_to(root)), 'loader': loader or 'unknown', 'mod_id': row_mod_id})
    loader_set = sorted(set(loaders))
    mod_set = sorted(set(mod_ids))
    if len(loader_set) > 1:
        warnings.append('multiple loader metadata families detected: ' + ', '.join(loader_set))
    if len(mod_set) > 1:
        warnings.append('multiple mod ids detected: ' + ', '.join(mod_set))
    resolved_mod_id = mod_set[0] if len(mod_set) == 1 else None
    if resolved_mod_id is None and len(loader_set) == 1:
        resolved_mod_id = property_mod_id(root)
        if resolved_mod_id:
            warnings.append('resolved mod id from project properties because packaged metadata is templated or absent')
    return (loader_set[0] if len(loader_set) == 1 else None, resolved_mod_id, rows, warnings)


def detect_source_version_and_java(root: pathlib.Path) -> tuple[str | None, int | None, dict[str, str]]:
    props: dict[str, str] = {}
    for rel in ('gradle.properties', 'project.properties'):
        p = root / rel
        if p.is_file():
            props.update(parse_properties(p))
    version_keys = [
        'minecraft_version', 'minecraftVersion', 'mc_version', 'minecraft.version',
        'minecraft_version_range', 'minecraftVersionRange',
    ]
    mc = None
    for key in version_keys:
        if key in props:
            mc = normalize_mc(props[key])
            if mc:
                break
    build_text = '\n'.join(read_text(root / rel) for rel in ('build.gradle', 'build.gradle.kts', 'pom.xml') if (root / rel).is_file())
    if not mc:
        for pat in [
            r'com\.mojang:minecraft:([^"\'\s)]+)',
            r'minecraft\s*[=:]\s*["\']([^"\']+)',
            r'<minecraft\.version>\s*([^<]+)</minecraft\.version>',
        ]:
            m = re.search(pat, build_text, re.I)
            if m:
                mc = normalize_mc(m.group(1))
                if mc:
                    break
    java = None
    for key in ('java_version', 'javaVersion', 'java_version_major', 'java.version'):
        if key in props and str(props[key]).strip().isdigit():
            java = int(str(props[key]).strip()); break
    if java is None:
        java = parse_java_hint(build_text)
    return mc, java, props


def count_sources(root: pathlib.Path) -> dict[str, int]:
    counts = {'java': 0, 'kotlin': 0, 'resources': 0, 'mixins': 0}
    src = root / 'src'
    if src.exists():
        for p in src.rglob('*'):
            if not p.is_file() or any(part in IGNORE_DIRS for part in p.parts):
                continue
            if p.suffix == '.java': counts['java'] += 1
            elif p.suffix in {'.kt', '.kts'}: counts['kotlin'] += 1
            else: counts['resources'] += 1
            if 'mixin' in p.name.lower() or 'mixin' in str(p).lower(): counts['mixins'] += 1
    return counts


def source_digest(root: pathlib.Path) -> str:
    h = hashlib.sha256()
    rr = root.resolve()
    for base, dirs, files in os.walk(rr):
        bp = pathlib.Path(base)
        dirs[:] = sorted(d for d in dirs if d not in IGNORE_DIRS and not d.startswith('.northpoint'))
        for name in sorted(files):
            p = bp / name
            rel = p.relative_to(rr).as_posix()
            if rel == CONFIG_NAME:
                pass
            try:
                stat = p.stat()
            except OSError:
                continue
            if stat.st_size > 20 * 1024 * 1024:
                continue
            h.update(rel.encode()); h.update(b'\0')
            try:
                with p.open('rb') as f:
                    for chunk in iter(lambda: f.read(1024 * 1024), b''):
                        h.update(chunk)
            except OSError:
                continue
            h.update(b'\0')
    return h.hexdigest()


def infer_config(project: pathlib.Path, cell: dict[str, Any] | None = None) -> dict[str, Any]:
    root = project.resolve()
    mode, _ = detect_build(root)
    loader, mod_id, _, _ = detect_loader_and_mod_id(root)
    mc, java, _ = detect_source_version_and_java(root)
    scope = detect_runtime_scope(root, loader)
    cfg: dict[str, Any] = {
        'schema_version': 1,
        '_inferred': True,
        'build': {'mode': mode if mode != 'unknown' else 'auto'},
        'parity': {'source_authority': '.'},
        'runtime': {'required': True, 'scope': scope},
    }
    if mod_id: cfg['mod_id'] = mod_id
    if mode == 'javac':
        cfg['build']['source_roots'] = ['src/main/java']
        cfg['build']['resource_roots'] = ['src/main/resources']
        if java: cfg['build']['java'] = java
    cfg['source'] = {'minecraft': mc, 'loader': loader, 'java': java}
    return cfg


def inspect_project(project: pathlib.Path) -> dict[str, Any]:
    root = project.resolve()
    if not root.is_dir():
        raise RuntimeError(f'project is not a directory: {root}')
    mode, build = detect_build(root)
    loader, mod_id, metadata, warnings = detect_loader_and_mod_id(root)
    mc, java, props = detect_source_version_and_java(root)
    existing_cfg = read_json(root / CONFIG_NAME) if (root / CONFIG_NAME).is_file() else None
    runtime_scope = configured_runtime_scope(existing_cfg)
    if runtime_scope == 'unknown':
        runtime_scope = detect_runtime_scope(root, loader)
    if mode == 'unknown': warnings.append('no Gradle, Maven, or src/main/java build layout was detected')
    if not loader: warnings.append('loader could not be determined uniquely from mod metadata')
    if not mc: warnings.append('source Minecraft version could not be determined exactly')
    return {
        'schema_version': 1,
        'project_root': str(root),
        'source_sha256': source_digest(root),
        'build': {'mode': mode, **build},
        'loader': loader,
        'mod_id': mod_id,
        'minecraft': mc,
        'java': java,
        'runtime_scope': runtime_scope,
        'metadata': metadata,
        'source_counts': count_sources(root),
        'properties': {k: props[k] for k in sorted(props) if any(x in k.lower() for x in ('minecraft', 'loader', 'forge', 'neo', 'fabric', 'quilt', 'java'))},
        'existing_config': existing_cfg,
        'proposed_config': existing_cfg or infer_config(root),
        'warnings': warnings,
    }


def main() -> int:
    p = argparse.ArgumentParser(description='Inspect a Minecraft mod source tree without mutating it.')
    p.add_argument('--project', type=pathlib.Path, required=True)
    p.add_argument('--json-out', type=pathlib.Path)
    args = p.parse_args()
    result = inspect_project(args.project)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text + '\n', encoding='utf-8')
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({'schema_version': 1, 'error': str(exc)}))
        raise SystemExit(2)