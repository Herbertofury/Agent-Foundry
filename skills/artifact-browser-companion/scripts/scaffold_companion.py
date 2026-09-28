#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent / 'assets' / 'electron-starter'


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r'[^a-z0-9]+', '-', value).strip('-')
    return value or 'artifact-companion'


def replace_tokens(path: Path, replacements: dict[str, str]) -> None:
    if path.suffix.lower() not in {'.js', '.json', '.html', '.css', '.md', '.txt'}:
        return
    text = path.read_text(encoding='utf-8')
    for key, value in replacements.items():
        text = text.replace(key, value)
    path.write_text(text, encoding='utf-8')


def main() -> int:
    parser = argparse.ArgumentParser(description='Scaffold a standalone artifact browser companion.')
    parser.add_argument('--name', required=True, help='Human-readable app name')
    parser.add_argument('--output', required=True, help='Destination project directory')
    parser.add_argument('--force', action='store_true', help='Replace an existing destination directory')
    args = parser.parse_args()

    output = Path(args.output).expanduser().resolve()
    if output.exists():
        if not args.force:
            raise SystemExit(f'Destination already exists: {output}. Use --force to replace it.')
        shutil.rmtree(output)

    shutil.copytree(TEMPLATE, output)
    replacements = {
        '__APP_NAME__': args.name.strip(),
        '__APP_SLUG__': slugify(args.name),
        '__GENERATED_AT__': dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    for path in output.rglob('*'):
        if path.is_file():
            replace_tokens(path, replacements)

    metadata = {
        'generator': 'artifact-browser-companion',
        'generatedAt': dt.datetime.now(dt.timezone.utc).isoformat(),
        'appName': args.name.strip(),
        'appSlug': slugify(args.name),
        'template': 'electron-starter',
    }
    (output / 'config' / 'scaffold-metadata.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    print(output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
