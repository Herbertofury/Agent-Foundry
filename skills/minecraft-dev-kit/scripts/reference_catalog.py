#!/usr/bin/env python3
"""Inventory original reference media without editing them or guessing approval.

Explicit rules distinguish design targets, state references, inspiration and rejected
history. Hash-pinned selection prevents a newer filename or old contact sheet from
silently becoming the modeling authority. Never deletes duplicate originals.
"""
from __future__ import annotations
import argparse, hashlib, json
from collections import defaultdict
from pathlib import Path

EXTENSIONS={'.png','.jpg','.jpeg','.webp','.gif','.bmp','.tif','.tiff'}
ROLES={'primary','state','baseline','inspiration','rejected','superseded','duplicate','unclassified'}

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def decoded_pixel_digest(path):
    """Compare decoded images, including all animation frames/timing and color profiles."""
    from PIL import Image, ImageOps
    h=hashlib.sha256()
    with Image.open(path) as image:
        profile=image.info.get('icc_profile',b'')
        h.update(profile if isinstance(profile,bytes) else str(profile).encode())
        frames=getattr(image,'n_frames',1)
        h.update(str(frames).encode())
        for index in range(frames):
            image.seek(index)
            frame=ImageOps.exif_transpose(image.copy()).convert('RGBA')
            h.update(f'{frame.width}x{frame.height}:{image.info.get("duration",0) if frames>1 else 0}:'.encode())
            h.update(frame.tobytes())
    return h.hexdigest()

def safe_relative(root,name):
    path=Path(name)
    if path.is_absolute() or '..' in path.parts: raise ValueError(f'Unsafe reference path: {name}')
    resolved=(root/path).resolve()
    if not resolved.is_relative_to(root.resolve()):raise ValueError(f'Reference escapes root: {name}')
    return resolved

def build_catalog(root,policy):
    root=Path(root).resolve(); rules=policy.get('rules',[]); overrides=policy.get('overrides',{})
    for rule in rules:
        safe_relative(root,rule['prefix'])
        if rule['role'] not in ROLES:raise ValueError('Unknown reference role')
    for name,row in overrides.items():
        safe_relative(root,name)
        if row.get('role','unclassified') not in ROLES:raise ValueError('Unknown override role')
    rows=[]; hashes=defaultdict(list); pixels=defaultdict(list)
    for path in sorted(root.rglob('*')):
        if not path.is_file() or path.suffix.lower() not in EXTENSIONS:continue
        name=path.relative_to(root).as_posix();safe_relative(root,name)
        matches=[r for r in rules if name==r['prefix'].rstrip('/') or name.startswith(r['prefix'].rstrip('/')+'/')]
        rule=max(matches,key=lambda r:len(r['prefix'])) if matches else {}
        row={'path':name,'name':path.stem,'role':rule.get('role','unclassified'),
             'source_url':rule.get('source_url',policy.get('source_url')),
             'sha256':digest(path),'bytes':path.stat().st_size}
        override=overrides.get(name,{})
        expected=override.get('expected_sha256')
        if expected and row['sha256']!=expected:raise ValueError(f'Reference hash changed: {name}')
        row['decoded_pixel_sha256']=decoded_pixel_digest(path)
        for k in ('role','variant','state','source_url','decision_source','note'):
            if k in override:row[k]=override[k]
        row['target_pinned']=bool(expected and row['role'] in {'primary','state'})
        hashes[row['sha256']].append(name);pixels[row['decoded_pixel_sha256']].append(name);rows.append(row)
    missing=set(overrides)-{r['path'] for r in rows}
    if missing:raise ValueError(f'Missing reference overrides: {sorted(missing)}')
    return {'schema_version':1,'scope':'Original media inventory; neither design approval nor visual parity proof.',
            'assets':rows,'duplicate_groups':[{'sha256':h,'paths':ps} for h,ps in sorted(hashes.items()) if len(ps)>1],
            'pixel_duplicate_groups':[{'decoded_pixel_sha256':h,'paths':ps} for h,ps in sorted(pixels.items()) if len(ps)>1],
            'counts':{role:sum(r['role']==role for r in rows) for role in sorted(ROLES)}}

def select_target(catalog,variant,state='base'):
    matches=[r for r in catalog['assets'] if r.get('variant')==variant and r.get('state','base')==state
             and r['role'] in {'primary','state'} and r.get('target_pinned')]
    if len(matches)!=1:raise ValueError(f'Expected one hash-pinned target for {variant}/{state}; found {len(matches)}')
    return matches[0]

def verify_catalog(root,catalog):
    for row in catalog['assets']:
        p=safe_relative(Path(root),row['path'])
        if not p.is_file() or digest(p)!=row['sha256']:raise ValueError(f'Missing or changed reference: {row["path"]}')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('root',type=Path);ap.add_argument('--policy',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--variant');ap.add_argument('--state',default='base');args=ap.parse_args()
    cat=build_catalog(args.root,json.loads(args.policy.read_text()));verify_catalog(args.root,cat)
    if args.variant:cat['selected_target']=select_target(cat,args.variant,args.state)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(cat,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'images':len(cat['assets']),'duplicates':len(cat['duplicate_groups']),'counts':cat['counts']}))
if __name__=='__main__':main()
