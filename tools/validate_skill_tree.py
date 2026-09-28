#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from pathlib import Path

NAME_RE=re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
FORBIDDEN_PARTS={'__pycache__','.pytest_cache','.mypy_cache','.ruff_cache'}
FORBIDDEN_SUFFIXES={'.pyc','.pyo'}
MAX_BYTES=25*1024*1024

def parse_frontmatter(text:str):
    if not text.startswith('---\n'):
        raise ValueError('SKILL.md must start with YAML frontmatter')
    end=text.find('\n---\n',4)
    if end<0:
        raise ValueError('SKILL.md frontmatter closing --- missing')
    block=text[4:end]; data={}
    for raw in block.splitlines():
        if not raw.strip() or raw.lstrip().startswith('#'): continue
        if ':' not in raw: raise ValueError(f'unsupported frontmatter line: {raw!r}')
        k,v=raw.split(':',1); data[k.strip()]=v.strip().strip('"\'')
    return data

def validate(path:Path):
    errors=[]; warnings=[]
    if not path.is_dir(): return [f'{path}: not a directory'],warnings
    md=path/'SKILL.md'
    if not md.is_file(): return [f'{path}: SKILL.md missing'],warnings
    try: props=parse_frontmatter(md.read_text(encoding='utf-8'))
    except Exception as e: return [f'{path}: {e}'],warnings
    name=props.get('name',''); desc=props.get('description','')
    if not NAME_RE.fullmatch(name): errors.append('frontmatter name must be lowercase kebab-case')
    if name and path.name!=name: errors.append(f'directory name {path.name!r} must match frontmatter name {name!r}')
    if not desc: errors.append('frontmatter description is required')
    extra=set(props)-{'name','description'}
    if extra: warnings.append(f'non-portable frontmatter fields: {sorted(extra)}')
    total=0
    for f in path.rglob('*'):
        if not f.is_file(): continue
        rel=f.relative_to(path); total+=f.stat().st_size
        if any(p in FORBIDDEN_PARTS for p in rel.parts): errors.append(f'generated cache path forbidden: {rel}')
        if f.suffix in FORBIDDEN_SUFFIXES: errors.append(f'compiled cache forbidden: {rel}')
        if rel.parts and rel.parts[0]=='evidence': warnings.append(f'generated evidence bundled in source package: {rel}')
    if total>MAX_BYTES: errors.append(f'skill source exceeds 25 MiB: {total}')
    return errors,warnings

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('root',type=Path); ap.add_argument('--json',action='store_true')
    ns=ap.parse_args(); roots=[ns.root] if (ns.root/'SKILL.md').is_file() else sorted(p for p in ns.root.iterdir() if p.is_dir() and (p/'SKILL.md').is_file())
    result=[]; failed=False
    for p in roots:
        errors,warnings=validate(p); failed|=bool(errors); result.append({'skill':p.name,'errors':errors,'warnings':warnings})
    if ns.json: print(json.dumps(result,indent=2))
    else:
        for r in result:
            print(('PASS' if not r['errors'] else 'FAIL'),r['skill'])
            for x in r['errors']: print('  ERROR:',x)
            for x in r['warnings']: print('  WARN :',x)
    return 1 if failed else 0
if __name__=='__main__': raise SystemExit(main())
