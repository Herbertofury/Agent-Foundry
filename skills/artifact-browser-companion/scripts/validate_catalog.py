#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

ALLOWED_PROTOCOLS = {'http', 'https'}


def is_http_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        return parsed.scheme in ALLOWED_PROTOCOLS and bool(parsed.netloc)
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description='Validate normalized Artifact Browser Companion catalog JSON.')
    parser.add_argument('catalog', help='Path to catalog.json')
    args = parser.parse_args()

    path = Path(args.catalog)
    data = json.loads(path.read_text(encoding='utf-8'))
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(data, dict):
        errors.append('Top-level value must be an object.')
        items = []
    else:
        items = data.get('items', [])
        if not isinstance(items, list):
            errors.append('items must be an array.')
            items = []

    ids: set[str] = set()
    names: dict[str, list[str]] = {}
    source_count = 0
    gallery_count = 0

    for index, item in enumerate(items, start=1):
        label = f'items[{index - 1}]'
        if not isinstance(item, dict):
            errors.append(f'{label} must be an object.')
            continue
        item_id = str(item.get('id', '')).strip()
        name = str(item.get('name', '')).strip()
        if not item_id:
            errors.append(f'{label} missing id.')
        elif item_id in ids:
            errors.append(f'Duplicate id: {item_id}')
        else:
            ids.add(item_id)
        if not name:
            errors.append(f'{label} missing name.')
        else:
            names.setdefault(name.casefold(), []).append(item_id or label)

        for source in item.get('sources', []) or []:
            source_count += 1
            if not isinstance(source, dict):
                errors.append(f'{label} source must be an object.')
                continue
            url = str(source.get('url', '')).strip()
            if not is_http_url(url):
                errors.append(f'{label} invalid source URL: {url!r}')
            if not str(source.get('provider', '')).strip():
                warnings.append(f'{label} source missing provider label: {url}')

        for author in item.get('authors', []) or []:
            if not isinstance(author, dict):
                errors.append(f'{label} author must be an object.')
                continue
            url = str(author.get('url', '')).strip()
            if url and not is_http_url(url):
                errors.append(f'{label} invalid author URL: {url!r}')

        for media in item.get('gallery', []) or []:
            gallery_count += 1
            if not isinstance(media, dict):
                errors.append(f'{label} gallery entry must be an object.')
                continue
            src = str(media.get('src', '')).strip()
            if not src:
                errors.append(f'{label} gallery entry missing src.')
            source_url = str(media.get('sourceUrl', '')).strip()
            if source_url and not is_http_url(source_url):
                errors.append(f'{label} invalid gallery sourceUrl: {source_url!r}')
            if not str(media.get('alt', '')).strip():
                warnings.append(f'{label} gallery entry missing alt text: {src}')

    duplicate_names = {name: refs for name, refs in names.items() if len(refs) > 1}
    if duplicate_names:
        warnings.append(f'{len(duplicate_names)} duplicate display-name group(s); confirm these are intentional distinct records.')

    report = {
        'catalog': str(path),
        'items': len(items),
        'uniqueIds': len(ids),
        'sources': source_count,
        'galleryEntries': gallery_count,
        'warnings': len(warnings),
        'errors': len(errors),
    }
    print(json.dumps(report, indent=2))
    for warning in warnings:
        print(f'WARNING: {warning}', file=sys.stderr)
    for error in errors:
        print(f'ERROR: {error}', file=sys.stderr)
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
