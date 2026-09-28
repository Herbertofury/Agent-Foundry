#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, pathlib, shutil


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()



CONFIG_NAME = 'northpoint.project.json'
BASE_PROJECT_MARKERS = (
    'build.gradle', 'build.gradle.kts', 'pom.xml', 'gradlew', 'gradlew.bat', 'mvnw', 'mvnw.cmd',
)
BASE_EXCLUDED_PARTS = {
    '.git', '.gradle', '.idea', '.vscode', 'build', 'target', 'out', 'run', 'runs',
    'logs', 'crash-reports', '.northpoint', 'overlays',
}


def is_conventional_project(project: pathlib.Path) -> bool:
    return (project / 'src' / 'main').exists() or any((project / name).exists() for name in BASE_PROJECT_MARKERS)


def base_project_files(project: pathlib.Path):
    if not is_conventional_project(project):
        return
    for src in sorted(p for p in project.rglob('*') if p.is_file()):
        rel = src.relative_to(project)
        if any(part in BASE_EXCLUDED_PARTS for part in rel.parts):
            continue
        # Northpoint layer sources are inputs to composition, never copied as
        # nested source trees into the target workspace.
        if len(rel.parts) >= 2 and rel.parts[0] == 'src' and rel.parts[1] in {'common', 'loader', 'version', 'cell'}:
            continue
        yield src, rel.as_posix()

def overlay_roots(project: pathlib.Path, cell: dict) -> list[tuple[str, pathlib.Path]]:
    mc = str(cell['minecraft'])
    loader = str(cell['loader'])
    cid = str(cell['id'])
    # Legacy src/* roots stay supported for the lightweight compiler fixtures.
    # overlays/* is the production layout: files map directly into a normal
    # Gradle/Maven project root, so build.gradle/settings.gradle/src/main/...
    # can all vary by common -> loader -> version -> exact-cell precedence.
    return [
        ('common', project / 'src' / 'common'),
        ('overlay:common', project / 'overlays' / 'common'),
        (f'loader:{loader}', project / 'src' / 'loader' / loader),
        (f'overlay:loader:{loader}', project / 'overlays' / 'loader' / loader),
        (f'version:{mc}', project / 'src' / 'version' / mc),
        (f'overlay:version:{mc}', project / 'overlays' / 'version' / mc),
        (f'cell:{cid}', project / 'src' / 'cell' / cid),
        (f'overlay:cell:{cid}', project / 'overlays' / 'cell' / cid),
    ]


def inventory(project: pathlib.Path, cell: dict) -> dict:
    files: dict[str, dict] = {}
    # Northpoint config is control-plane input, not ordinary project source.
    # Preserve it even for overlay-only Stonecutter projects that have no
    # conventional Gradle/Maven/src/main root. Later overlays may replace it
    # using the same relative path and normal precedence.
    root_config = project / CONFIG_NAME
    if root_config.is_file():
        files[CONFIG_NAME] = {
            'relative_path': CONFIG_NAME,
            'origin': 'config:root',
            'source': str(root_config.resolve()),
            'sha256': sha256_file(root_config),
            'size': root_config.stat().st_size,
        }
    for src, rel in base_project_files(project) or ():
        files[rel] = {
            'relative_path': rel,
            'origin': 'base',
            'source': str(src.resolve()),
            'sha256': sha256_file(src),
            'size': src.stat().st_size,
        }
    for label, root in overlay_roots(project, cell):
        if not root.exists():
            continue
        for src in sorted(p for p in root.rglob('*') if p.is_file()):
            rel = src.relative_to(root).as_posix()
            files[rel] = {
                'relative_path': rel,
                'origin': label,
                'source': str(src.resolve()),
                'sha256': sha256_file(src),
                'size': src.stat().st_size,
            }
    digest = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return {'schema_version': 1, 'cell_id': cell['id'], 'files': files, 'sha256': digest}


def compose(project: pathlib.Path, cell: dict, output: pathlib.Path, clean: bool = True) -> dict:
    project = project.resolve()
    if clean and output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    inv = inventory(project, cell)
    for rel, meta in inv['files'].items():
        src = pathlib.Path(meta['source'])
        dst = output / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    (output / '.northpoint-compose.json').write_text(json.dumps(inv, indent=2) + '\n', encoding='utf-8')
    return inv


def main() -> int:
    p = argparse.ArgumentParser(description='Compose a Northpoint Stonecutter-style target workspace.')
    p.add_argument('--project', type=pathlib.Path, required=True)
    p.add_argument('--cell-json', type=pathlib.Path, required=True)
    p.add_argument('--output', type=pathlib.Path, required=True)
    args = p.parse_args()
    cell = json.loads(args.cell_json.read_text(encoding='utf-8'))
    print(json.dumps(compose(args.project, cell, args.output), indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())