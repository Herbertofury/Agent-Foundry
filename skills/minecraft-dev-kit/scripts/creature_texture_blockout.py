#!/usr/bin/env python3
"""Generate a deterministic material-aware pixel texture blockout from creature-spec box UVs.

This accelerates first-pass materials only. It is not a substitute for final texture artistry.
"""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
from typing import Any
from PIL import Image


def rgb(h:str)->tuple[int,int,int,int]:
    h=h.strip().lstrip('#')
    if len(h)==6: return tuple(int(h[i:i+2],16) for i in (0,2,4))+(255,)
    if len(h)==8: return tuple(int(h[i:i+2],16) for i in (0,2,4,6))
    raise ValueError(f'bad color {h!r}')

def box_faces(uv:list[float], size:list[float])->dict[str,tuple[int,int,int,int]]:
    u,v=(int(round(x)) for x in uv); x,y,z=(max(1,int(round(abs(float(q))))) for q in size)
    return {
      'up':(u+z,v,x,z), 'down':(u+z+x,v,x,z),
      'left':(u,v+z,z,y), 'front':(u+z,v+z,x,y),
      'right':(u+z+x,v+z,z,y), 'back':(u+2*z+x,v+z,x,y)
    }

def choose(ramp:list[tuple[int,int,int,int]], face:str)->tuple[int,int,int,int]:
    if not ramp:return (127,127,127,255)
    idx={'down':0,'back':max(0,len(ramp)//3-1),'left':len(ramp)//3,'right':len(ramp)//2,'front':max(0,len(ramp)-2),'up':len(ramp)-1}.get(face,len(ramp)//2)
    return ramp[max(0,min(len(ramp)-1,idx))]

def paint_face(im:Image.Image, rect:tuple[int,int,int,int], ramp:list[tuple[int,int,int,int]], face:str, pattern:str, seed:int):
    x,y,w,h=rect; px=im.load(); base=choose(ramp,face); dark=ramp[max(0,min(len(ramp)-1, max(0,len(ramp)//3-1)))] if ramp else base; hi=ramp[-1] if ramp else base
    for yy in range(y,min(im.height,y+h)):
        for xx in range(x,min(im.width,x+w)): px[xx,yy]=base
    # Deliberate connected clusters, never random singleton confetti.
    if pattern in {'mottle','organic','stone','chitin','wood'} and w>=3 and h>=3:
        count=max(1,(w*h)//18)
        for n in range(count):
            hx=int(hashlib.sha256(f'{seed}:{face}:{n}'.encode()).hexdigest()[:8],16)
            cx=x+(hx % max(1,w-1)); cy=y+((hx>>8)%max(1,h-1)); col=dark if n%2==0 else hi
            for dx,dy in ((0,0),(1,0),(0,1)):
                if x<=cx+dx<x+w and y<=cy+dy<y+h and 0<=cx+dx<im.width and 0<=cy+dy<im.height: px[cx+dx,cy+dy]=col
    if pattern=='bands' and h>=3:
        for yy in range(y+1,min(y+h,im.height),3):
            for xx in range(x,min(x+w,im.width)): px[xx,yy]=dark
    if pattern=='edge' and w>=2 and h>=2:
        for xx in range(x,min(x+w,im.width)):
            if 0<=y<im.height: px[xx,y]=hi
        for yy in range(y,min(y+h,im.height)):
            if 0<=x<im.width: px[x,yy]=hi

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('spec',type=Path); ap.add_argument('recipe',type=Path); ap.add_argument('--output',type=Path,required=True); ap.add_argument('--emissive',type=Path); a=ap.parse_args()
    s=json.loads(a.spec.read_text(encoding='utf-8')); r=json.loads(a.recipe.read_text(encoding='utf-8')); tex=s.get('texture',{}); w,h=int(tex.get('width',64)),int(tex.get('height',64)); materials=r.get('materials',{}); assign=r.get('assign',{}); default=r.get('default_material')
    if not isinstance(materials,dict) or not materials: print('recipe.materials must be non-empty'); return 2
    if default not in materials: print('default_material missing from materials'); return 2
    im=Image.new('RGBA',(w,h),(0,0,0,0)); em=Image.new('RGBA',(w,h),(0,0,0,0))
    for c in s.get('cubes',[]):
        if not isinstance(c,dict) or not isinstance(c.get('uv'),list) or not isinstance(c.get('size'),list): continue
        mid=assign.get(c.get('id'), c.get('material',default)); mat=materials.get(mid,materials[default]); ramp=[rgb(x) for x in mat.get('ramp',[])]; pattern=str(mat.get('pattern','solid')); seed=int(hashlib.sha256(f"{s.get('id')}:{c.get('id')}:{mid}".encode()).hexdigest()[:8],16)
        for face,rect in box_faces(c['uv'],c['size']).items(): paint_face(im,rect,ramp,face,pattern,seed)
        if mat.get('emissive'):
            eramp=[rgb(x) for x in mat.get('emissive_ramp',mat.get('ramp',[]))]
            for face,rect in box_faces(c['uv'],c['size']).items(): paint_face(em,rect,eramp,face,'solid',seed)
    a.output.parent.mkdir(parents=True,exist_ok=True); im.save(a.output)
    if a.emissive:
        a.emissive.parent.mkdir(parents=True,exist_ok=True); em.save(a.emissive)
    print(json.dumps({'result':'pass','texture':str(a.output),'emissive':str(a.emissive) if a.emissive else None,'size':[w,h],'note':'material blockout only; final artistry requires refinement and visual QA'},indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
