#!/usr/bin/env python3
"""Deterministically shelf-pack Bedrock/Gecko box-UV islands for a creature spec."""
from __future__ import annotations
import argparse, json, math
from pathlib import Path
from typing import Any


def footprint(size:list[float])->tuple[int,int]:
    x,y,z=(abs(float(v)) for v in size)
    return max(1, math.ceil(2*(x+z))), max(1, math.ceil(y+z))


def next_pow2(n:int)->int:
    p=1
    while p<n: p*=2
    return p


def pack(cubes:list[dict[str,Any]], width:int, height:int, padding:int, repack:bool=False)->tuple[bool,list[dict[str,Any]],int,int]:
    # Largest islands first makes the simple shelf pack much less wasteful.
    todo=[]
    for idx,c in enumerate(cubes):
        if not repack and isinstance(c.get('uv'),list) and len(c['uv'])==2:
            continue
        w,h=footprint(c.get('size',[1,1,1])); todo.append((-(w*h),-h,-w,idx,w,h))
    todo.sort()
    occupied=[]
    # Preserve existing UV islands as obstacles.
    for idx,c in enumerate(cubes):
        if isinstance(c.get('uv'),list) and len(c['uv'])==2 and (not repack or idx not in [t[3] for t in todo]):
            w,h=footprint(c.get('size',[1,1,1])); x,y=(int(c['uv'][0]),int(c['uv'][1])); occupied.append((x,y,x+w,y+h))
    x=y=row_h=0
    for _,_,_,idx,w,h in todo:
        placed=False
        # deterministic shelf scan; if collision with preserved islands, advance x.
        while y+h<=height:
            if x+w>width:
                x=0; y+=row_h+padding; row_h=0; continue
            rect=(x,y,x+w,y+h)
            collision=next((r for r in occupied if not (rect[2]+padding<=r[0] or rect[0]>=r[2]+padding or rect[3]+padding<=r[1] or rect[1]>=r[3]+padding)),None)
            if collision:
                x=collision[2]+padding; continue
            cubes[idx]['uv']=[x,y]; occupied.append(rect); x+=w+padding; row_h=max(row_h,h); placed=True; break
        if not placed: return False,cubes,width,height
    return True,cubes,width,height


def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('spec',type=Path); ap.add_argument('--output',type=Path); ap.add_argument('--padding',type=int,default=1); ap.add_argument('--repack',action='store_true'); ap.add_argument('--grow',action='store_true'); ap.add_argument('--max-size',type=int,default=512); a=ap.parse_args()
    data=json.loads(a.spec.read_text(encoding='utf-8'))
    tex=data.setdefault('texture',{}); w=int(tex.get('width',64)); h=int(tex.get('height',64)); cubes=data.get('cubes') if isinstance(data.get('cubes'),list) else []
    if a.padding<0: raise SystemExit('padding must be >= 0')
    while True:
        attempt=json.loads(json.dumps(cubes))
        ok,packed,_,_=pack(attempt,w,h,a.padding,a.repack)
        if ok: break
        if not a.grow: print(f'UV pack does not fit {w}x{h}; rerun with --grow or larger texture'); return 2
        if w>=a.max_size and h>=a.max_size: print(f'UV pack exceeds max size {a.max_size}'); return 2
        if w<=h: w=next_pow2(w+1)
        else: h=next_pow2(h+1)
    data['cubes']=packed; tex['width']=w; tex['height']=h
    out=a.output or a.spec.with_name(a.spec.stem+'.uvpacked.json'); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    used=0
    for c in packed:
        fw,fh=footprint(c.get('size',[1,1,1])); used += fw*fh
    print(json.dumps({'result':'pass','output':str(out),'texture':[w,h],'island_area':used,'atlas_area':w*h,'fill_ratio':round(used/(w*h),4) if w*h else 0},indent=2))
    return 0
if __name__=='__main__': raise SystemExit(main())
