#!/usr/bin/env python3
"""Audit real mob texture PNGs for structural pixel-art/material hazards."""
from __future__ import annotations
import argparse, hashlib, json
from collections import Counter
from pathlib import Path
from typing import Any
from PIL import Image


def as_list(v:Any): return v if isinstance(v,list) else []

def inspect_png(path:Path)->dict[str,Any]:
    im=Image.open(path).convert('RGBA'); w,h=im.size; px=list(im.get_flattened_data() if hasattr(im, 'get_flattened_data') else im.getdata()); opaque=[p for p in px if p[3]>0]; partial=sum(1 for p in px if 0<p[3]<255); unique=Counter(opaque); singleton_colors={c for c,n in unique.items() if n==1}
    singleton_pixels=sum(1 for p in opaque if p in singleton_colors)
    # Local-isolation metric: opaque pixel whose 4-neighbors have different RGB/alpha.
    isolated=0; data=im.load()
    for y in range(h):
        for x in range(w):
            p=data[x,y]
            if p[3]==0: continue
            neigh=[]
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                xx,yy=x+dx,y+dy
                if 0<=xx<w and 0<=yy<h: neigh.append(data[xx,yy])
            if neigh and all(q!=p for q in neigh): isolated+=1
    return {'width':w,'height':h,'opaque':len(opaque),'coverage':len(opaque)/(w*h) if w*h else 0,'unique_rgba':len(unique),'partial_alpha':partial,'partial_alpha_ratio':partial/(w*h) if w*h else 0,'singleton_color_pixels':singleton_pixels,'isolated_pixels':isolated,'isolated_ratio':isolated/max(1,len(opaque)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('manifest',type=Path); ap.add_argument('--root',type=Path,required=True); ap.add_argument('--markdown',type=Path); ap.add_argument('--json',dest='json_out',type=Path); a=ap.parse_args()
    d=json.loads(a.manifest.read_text(encoding='utf-8')); findings=[]; rows=[]; hashes={}
    for ent in as_list(d.get('entities')):
        if not isinstance(ent,dict): continue
        eid=str(ent.get('id')); expected=None
        if ent.get('creature_spec'):
            sp=a.root/str(ent['creature_spec'])
            if sp.is_file():
                try:
                    spec=json.loads(sp.read_text()); tex=spec.get('texture',{}); expected=(int(tex['width']),int(tex['height']))
                except Exception: pass
        texfiles=as_list(ent.get('texture_files'))
        if not texfiles:
            findings.append({'level':'warning','entity':eid,'code':'texture.none','message':'no texture_files declared; texture artistry cannot be audited'})
        for ref in texfiles:
            p=Path(str(ref)); p=p if p.is_absolute() else a.root/p
            if not p.is_file(): findings.append({'level':'error','entity':eid,'code':'texture.missing','message':str(ref)}); continue
            try: r=inspect_png(p)
            except Exception as exc: findings.append({'level':'error','entity':eid,'code':'texture.read','message':f'{ref}: {exc}'}); continue
            r.update({'entity':eid,'file':str(ref)}); rows.append(r)
            if expected and (r['width'],r['height'])!=expected: findings.append({'level':'error','entity':eid,'code':'texture.dimensions','message':f"{ref} is {r['width']}x{r['height']}, spec expects {expected[0]}x{expected[1]}"})
            if r['coverage']<=0: findings.append({'level':'error','entity':eid,'code':'texture.empty','message':f'{ref} has no visible pixels'})
            if r['partial_alpha_ratio']>0.05: findings.append({'level':'warning','entity':eid,'code':'texture.partial_alpha','message':f"{ref} has {r['partial_alpha_ratio']:.1%} partial-alpha pixels; verify intentional pixel-art transparency"})
            if r['isolated_ratio']>0.20 and r['opaque']>=32: findings.append({'level':'warning','entity':eid,'code':'texture.pixel_noise','message':f"{ref} has {r['isolated_ratio']:.1%} locally isolated opaque pixels; inspect cluster discipline"})
            if r['unique_rgba']>max(48,int(r['opaque']*.45)): findings.append({'level':'warning','entity':eid,'code':'texture.palette_sprawl','message':f"{ref} uses {r['unique_rgba']} unique RGBA colors across {r['opaque']} opaque pixels; inspect uncontrolled ramps/noise"})
            if r['sha256'] in hashes: findings.append({'level':'warning','entity':eid,'code':'texture.duplicate','message':f"{ref} is byte-identical to {hashes[r['sha256']]}"})
            else: hashes[r['sha256']]=ref
        em=ent.get('emissive_file')
        if em:
            p=Path(str(em)); p=p if p.is_absolute() else a.root/p
            if not p.is_file(): findings.append({'level':'error','entity':eid,'code':'emissive.missing','message':str(em)})
            else:
                try:
                    rr=inspect_png(p); coverage=rr['coverage']
                    if expected and (rr['width'],rr['height'])!=expected: findings.append({'level':'error','entity':eid,'code':'emissive.dimensions','message':f'{em} does not match spec dimensions'})
                    if coverage>0.35: findings.append({'level':'warning','entity':eid,'code':'emissive.coverage','message':f'{em} emissive coverage {coverage:.1%} is very broad; verify focal hierarchy'})
                except Exception as exc: findings.append({'level':'error','entity':eid,'code':'emissive.read','message':str(exc)})
    errors=[x for x in findings if x['level']=='error']; warnings=[x for x in findings if x['level']=='warning']
    lines=['# Creature Texture Audit','',f"- Result: **{'PASS' if not errors else 'FAIL'}**",f'- Textures inspected: {len(rows)}',f'- Errors: {len(errors)}',f'- Warnings: {len(warnings)}','','## Findings','']
    lines += ['- None.'] if not findings else [f"- **{x['level'].upper()}** `{x['code']}` [{x['entity']}]: {x['message']}" for x in findings]
    lines += ['','These metrics catch structural/noise hazards only. Material artistry, focal hierarchy, hue/value ramps and native-lighting quality still require visual inspection.','']
    report='\n'.join(lines)
    if a.markdown: a.markdown.parent.mkdir(parents=True,exist_ok=True); a.markdown.write_text(report,encoding='utf-8')
    else: print(report,end='')
    if a.json_out: a.json_out.parent.mkdir(parents=True,exist_ok=True); a.json_out.write_text(json.dumps({'result':'pass' if not errors else 'fail','rows':rows,'findings':findings},indent=2)+'\n',encoding='utf-8')
    return 0 if not errors else 2
if __name__=='__main__': raise SystemExit(main())
