#!/usr/bin/env python3
"""Cross-check premium attack gameplay/VFX/SFX markers against creature-spec animation markers."""
from __future__ import annotations
import argparse, json, math
from pathlib import Path
from typing import Any


def as_list(v: Any) -> list[Any]:
    return v if isinstance(v, list) else []


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('manifest', type=Path)
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--markdown', type=Path)
    ap.add_argument('--json', dest='json_out', type=Path)
    a=ap.parse_args()
    data=json.loads(a.manifest.read_text(encoding='utf-8'))
    findings=[]; rows=[]
    marker_fields=(('impact_marker','damage'),('vfx_marker','vfx'),('sfx_marker','sfx'))
    for ent in as_list(data.get('entities')):
        if not isinstance(ent,dict): continue
        eid=str(ent.get('id','<entity>')); ref=ent.get('creature_spec')
        if not ref:
            rows.append({'entity':eid,'status':'skip','checked':0})
            continue
        p=Path(ref); p=p if p.is_absolute() else a.root/p
        if not p.is_file():
            findings.append({'level':'error','entity':eid,'code':'spec.missing','message':str(ref)}); continue
        try: spec=json.loads(p.read_text(encoding='utf-8'))
        except Exception as exc:
            findings.append({'level':'error','entity':eid,'code':'spec.parse','message':str(exc)}); continue
        markers: dict[str,dict[str,dict[str,Any]]]={}
        for anim in as_list(spec.get('animations')):
            if not isinstance(anim,dict): continue
            amap={}
            for m in as_list(anim.get('markers')):
                if isinstance(m,dict) and m.get('id'):
                    amap[str(m['id'])]=m
            markers[str(anim.get('name'))]=amap
        checked=0
        for atk in as_list(ent.get('attacks')):
            if not isinstance(atk,dict): continue
            checked+=1
            aid=str(atk.get('id','<attack>')); anim=str(atk.get('animation','')); amap=markers.get(anim,{})
            for field, expected_kind in marker_fields:
                marker=str(atk.get(field,'') or '')
                if not marker:
                    findings.append({'level':'error','entity':eid,'code':f'attack.{field}.missing','message':f'{aid} lacks {field}'}); continue
                if marker not in amap:
                    findings.append({'level':'error','entity':eid,'code':f'attack.{field}.not_found','message':f'{aid} expects {marker!r} in animation {anim!r}'}); continue
                kind=str(amap[marker].get('kind','custom'))
                if kind != expected_kind:
                    findings.append({'level':'error','entity':eid,'code':f'attack.{field}.kind','message':f'{aid} marker {marker!r} is {kind!r}, expected {expected_kind!r}'})
            impact=str(atk.get('impact_marker','') or '')
            if impact in amap:
                try: mt=float(amap[impact].get('time')); windup=float(atk.get('windup'))
                except Exception: mt=windup=math.nan
                if math.isfinite(mt) and math.isfinite(windup):
                    tolerance=max(0.08, abs(windup)*0.15)
                    if abs(mt-windup)>tolerance:
                        findings.append({'level':'error','entity':eid,'code':'attack.impact_timing','message':f'{aid} impact marker at {mt:.3f}s differs from windup end {windup:.3f}s by more than {tolerance:.3f}s'})
        rows.append({'entity':eid,'status':'pass','checked':checked})
    errors=[f for f in findings if f['level']=='error']
    lines=['# Mob Event Marker Audit','',f"- Result: **{'PASS' if not errors else 'FAIL'}**",f'- Entities: {len(rows)}',f'- Errors: {len(errors)}','', '## Findings','']
    lines += ['- None.'] if not findings else [f"- **{f['level'].upper()}** `{f['code']}` [{f['entity']}]: {f['message']}" for f in findings]
    lines += ['', 'Impact timing is compared to the manifest windup endpoint. VFX/SFX markers must exist in the same authored attack animation; native runtime still proves their actual playback/synchronization.', '']
    report='\n'.join(lines)
    if a.markdown: a.markdown.parent.mkdir(parents=True,exist_ok=True); a.markdown.write_text(report,encoding='utf-8')
    else: print(report,end='')
    if a.json_out: a.json_out.parent.mkdir(parents=True,exist_ok=True); a.json_out.write_text(json.dumps({'result':'pass' if not errors else 'fail','rows':rows,'findings':findings},indent=2)+'\n',encoding='utf-8')
    return 0 if not errors else 2

if __name__=='__main__': raise SystemExit(main())
