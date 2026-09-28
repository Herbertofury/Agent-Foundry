#!/usr/bin/env python3
"""Audit creature-spec rig/geometry structure for premium mob production hazards."""
from __future__ import annotations
import argparse,json,math,statistics
from pathlib import Path
from typing import Any

def as_list(v:Any): return v if isinstance(v,list) else []
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('manifest',type=Path); ap.add_argument('--root',type=Path,required=True); ap.add_argument('--markdown',type=Path); ap.add_argument('--json',dest='json_out',type=Path); a=ap.parse_args()
    data=json.loads(a.manifest.read_text(encoding='utf-8')); findings=[]; rows=[]
    for ent in as_list(data.get('entities')):
        if not isinstance(ent,dict) or not ent.get('creature_spec'): continue
        eid=str(ent.get('id')); kind=str(ent.get('kind','mob')).lower(); p=a.root/str(ent['creature_spec'])
        if not p.is_file(): continue
        try: spec=json.loads(p.read_text(encoding='utf-8'))
        except Exception: continue
        bones={str(b.get('id')):b for b in as_list(spec.get('bones')) if isinstance(b,dict) and b.get('id')}; children={k:[] for k in bones}
        for bid,b in bones.items():
            par=b.get('parent')
            if par in children: children[par].append(bid)
        cubes=as_list(spec.get('cubes')); cubes_by={k:[] for k in bones}; sigs=set(); volumes=[]; locators=0
        for c in cubes:
            if not isinstance(c,dict): continue
            bid=str(c.get('bone')); cubes_by.setdefault(bid,[]).append(c)
            origin=tuple(c.get('origin',[])); size=tuple(c.get('size',[])); rot=tuple(c.get('rotation',[0,0,0])); sig=(bid,origin,size,rot)
            if sig in sigs: findings.append({'level':'error','entity':eid,'code':'geometry.duplicate_cube','message':f"duplicate/coplanar cube signature on bone {bid}: {c.get('id')}"})
            sigs.add(sig)
            if len(size)==3 and all(isinstance(x,(int,float)) for x in size):
                vol=float(size[0])*float(size[1])*float(size[2]); volumes.append(vol)
                if min(float(x) for x in size)<0.125: findings.append({'level':'warning','entity':eid,'code':'geometry.micro_cube','message':f"cube {c.get('id')} has a sub-0.125 dimension; verify it earns its render/UV cost"})
        animated=set()
        for anim in as_list(spec.get('animations')):
            if isinstance(anim,dict) and isinstance(anim.get('bones'),dict): animated.update(anim['bones'])
        for bid,b in bones.items():
            ls=b.get('locators') if isinstance(b.get('locators'),dict) else {}; locators += len(ls)
            if bid!='root' and not cubes_by.get(bid) and not children.get(bid) and not ls and bid not in animated:
                findings.append({'level':'error','entity':eid,'code':'rig.dead_bone','message':f'bone {bid} has no geometry, children, locators, or animation use'})
        # hierarchy depth
        maxdepth=0
        for bid in bones:
            cur=bid; seen=set(); depth=0
            while cur in bones and bones[cur].get('parent') in bones and cur not in seen:
                seen.add(cur); cur=str(bones[cur]['parent']); depth+=1
            maxdepth=max(maxdepth,depth)
        if maxdepth>12: findings.append({'level':'warning','entity':eid,'code':'rig.deep_hierarchy','message':f'hierarchy depth {maxdepth}; verify complexity is necessary'})
        if ent.get('vfx') and locators==0:
            findings.append({'level':'error' if kind=='boss' else 'warning','entity':eid,'code':'rig.vfx_locator','message':'combat VFX declared but creature spec has no explicit locator'})
        if volumes and len(volumes)>=4:
            med=statistics.median(volumes)
            if med>0 and max(volumes)>med*40: findings.append({'level':'warning','entity':eid,'code':'geometry.volume_outlier','message':'one cube is >40x median cube volume; verify silhouette blockout is deliberate'})
        rows.append({'entity':eid,'bones':len(bones),'cubes':len(cubes),'locators':locators,'max_depth':maxdepth})
    errors=[f for f in findings if f['level']=='error']; warnings=[f for f in findings if f['level']=='warning']
    lines=['# Mob Geometry / Rig Quality Audit','',f"- Result: **{'PASS' if not errors else 'FAIL'}**",f'- Entities: {len(rows)}',f'- Errors: {len(errors)}',f'- Warnings: {len(warnings)}','','## Findings','']
    lines += ['- None.'] if not findings else [f"- **{f['level'].upper()}** `{f['code']}` [{f['entity']}]: {f['message']}" for f in findings]
    lines += ['', 'This catches structural waste and rig hazards only. Silhouette appeal, proportions, material breakup and texture craft require real multi-angle visual QA.', '']
    report='\n'.join(lines)
    if a.markdown: a.markdown.parent.mkdir(parents=True,exist_ok=True); a.markdown.write_text(report,encoding='utf-8')
    else: print(report,end='')
    if a.json_out: a.json_out.parent.mkdir(parents=True,exist_ok=True); a.json_out.write_text(json.dumps({'result':'pass' if not errors else 'fail','rows':rows,'findings':findings},indent=2)+'\n',encoding='utf-8')
    return 0 if not errors else 2
if __name__=='__main__': raise SystemExit(main())
