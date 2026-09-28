#!/usr/bin/env python3
"""Detect exact geometry clones across a premium roster and report shape signatures."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from typing import Any

def as_list(v:Any):return v if isinstance(v,list) else []
def canon(spec:dict[str,Any]):
    bones=[]
    for b in as_list(spec.get('bones')):
        if not isinstance(b,dict):continue
        bones.append({'id':b.get('id'),'parent':b.get('parent'),'pivot':b.get('pivot'),'rotation':b.get('rotation'),'locators':b.get('locators')})
    cubes=[]
    xs=[];ys=[];zs=[]
    for c in as_list(spec.get('cubes')):
        if not isinstance(c,dict):continue
        o=c.get('origin') if isinstance(c.get('origin'),list) else [0,0,0]; sz=c.get('size') if isinstance(c.get('size'),list) else [0,0,0]
        cubes.append({'bone':c.get('bone'),'origin':o,'size':sz,'rotation':c.get('rotation'),'pivot':c.get('pivot')})
        if len(o)==3 and len(sz)==3:
            xs += [float(o[0]),float(o[0])+float(sz[0])];ys += [float(o[1]),float(o[1])+float(sz[1])];zs += [float(o[2]),float(o[2])+float(sz[2])]
    payload={'bones':bones,'cubes':cubes}; h=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest(); ext=[round(max(a)-min(a),3) if a else 0 for a in (xs,ys,zs)]; return h,ext,len(bones),len(cubes)

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('manifest',type=Path);ap.add_argument('--root',type=Path,required=True);ap.add_argument('--markdown',type=Path);ap.add_argument('--json',dest='json_out',type=Path);a=ap.parse_args();d=json.loads(a.manifest.read_text(encoding='utf-8'));findings=[];rows=[];byhash={}
    for e in as_list(d.get('entities')):
        if not isinstance(e,dict) or not e.get('creature_spec'):continue
        eid=str(e.get('id'));p=Path(str(e['creature_spec']));p=p if p.is_absolute() else a.root/p
        if not p.is_file():continue
        try:s=json.loads(p.read_text())
        except:continue
        h,ext,bones,cubes=canon(s);row={'entity':eid,'hash':h,'extents':ext,'bones':bones,'cubes':cubes};rows.append(row)
        if h in byhash:
            other=byhash[h]
            if not (e.get('shared_geometry_ok') and e.get('shared_geometry_reason')):
                findings.append({'level':'error','entity':eid,'code':'silhouette.exact_clone','message':f'geometry is identical to {other}; premium roster members need distinct geometry or explicit shared-base justification'})
        else:byhash[h]=eid
    errors=[x for x in findings if x['level']=='error']
    lines=['# Mob Silhouette / Geometry Diversity Audit','',f"- Result: **{'PASS' if not errors else 'FAIL'}**",f'- Creature specs: {len(rows)}',f'- Exact clone failures: {len(errors)}','','## Signatures','']
    for r in rows:lines.append(f"- `{r['entity']}`: extents {r['extents']}, bones {r['bones']}, cubes {r['cubes']}, geometry `{r['hash'][:12]}`")
    lines += ['','## Findings',''] + (['- None.'] if not findings else [f"- **ERROR** `{x['code']}` [{x['entity']}]: {x['message']}" for x in findings])
    lines += ['','This detects exact structural clones only. Near-duplicate silhouettes, role readability and artistic family cohesion still require lineup visual QA.','']
    report='\n'.join(lines)
    if a.markdown:a.markdown.parent.mkdir(parents=True,exist_ok=True);a.markdown.write_text(report,encoding='utf-8')
    else:print(report,end='')
    if a.json_out:a.json_out.parent.mkdir(parents=True,exist_ok=True);a.json_out.write_text(json.dumps({'result':'pass' if not errors else 'fail','rows':rows,'findings':findings},indent=2)+'\n',encoding='utf-8')
    return 0 if not errors else 2
if __name__=='__main__':raise SystemExit(main())
