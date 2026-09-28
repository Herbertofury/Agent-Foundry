#!/usr/bin/env python3
"""Audit premium mob VFX recipes against attack/hitbox/performance contracts."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any

def as_list(v:Any): return v if isinstance(v,list) else []
def num(v):
    try:return float(v)
    except:return None

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('manifest',type=Path); ap.add_argument('--root',type=Path,required=True); ap.add_argument('--markdown',type=Path); ap.add_argument('--json',dest='json_out',type=Path); a=ap.parse_args()
    d=json.loads(a.manifest.read_text(encoding='utf-8')); defs=d.get('vfx_definitions',{}); findings=[]; rows=[]
    if not isinstance(defs,dict): defs={}; findings.append({'level':'error','entity':'pack','code':'vfx.definitions','message':'vfx_definitions must be an object'})
    for ent in as_list(d.get('entities')):
        if not isinstance(ent,dict): continue
        eid=str(ent.get('id')); maxc=int((ent.get('performance') or {}).get('max_vfx_concurrency',0) or 0); spec_locs=set()
        if ent.get('creature_spec'):
            p=a.root/str(ent['creature_spec'])
            if p.is_file():
                try:
                    s=json.loads(p.read_text());
                    for b in as_list(s.get('bones')):
                        if isinstance(b,dict) and isinstance(b.get('locators'),dict): spec_locs.update(str(k) for k in b['locators'])
                except Exception: pass
        for atk in as_list(ent.get('attacks')):
            if not isinstance(atk,dict): continue
            aid=str(atk.get('id')); vid=str(atk.get('vfx','')); v=defs.get(vid)
            if not isinstance(v,dict): findings.append({'level':'error','entity':eid,'code':'vfx.missing_definition','message':f'{aid} references {vid!r} without a definition'}); continue
            for stage in ('anticipation','action','impact'):
                if not v.get(stage): findings.append({'level':'error','entity':eid,'code':'vfx.stage','message':f'{vid} missing {stage} stage'})
            coverage=str(v.get('coverage',''))
            if coverage not in {'hitbox-aligned','weapon-trail','projectile','target-local','aura'}: findings.append({'level':'error','entity':eid,'code':'vfx.coverage','message':f'{vid} has invalid coverage mode {coverage!r}'})
            conc=int(v.get('max_concurrency',0) or 0)
            if conc<=0: findings.append({'level':'error','entity':eid,'code':'vfx.concurrency','message':f'{vid} max_concurrency must be >0'})
            elif maxc and conc>maxc: findings.append({'level':'error','entity':eid,'code':'vfx.concurrency_budget','message':f'{vid} max_concurrency {conc} exceeds entity budget {maxc}'})
            locator=str(v.get('locator','') or '')
            if coverage in {'weapon-trail','projectile','aura'} and not locator: findings.append({'level':'error','entity':eid,'code':'vfx.locator','message':f'{vid} coverage {coverage} requires a locator'})
            elif locator and spec_locs and locator not in spec_locs: findings.append({'level':'error','entity':eid,'code':'vfx.locator_ref','message':f'{vid} locator {locator!r} not found in creature spec'})
            if coverage=='hitbox-aligned' and isinstance(atk.get('hitbox'),dict):
                hr=num(atk['hitbox'].get('range')); vr=num(v.get('impact_radius')); tr=num(v.get('telegraph_radius'))
                if hr and vr:
                    ratio=vr/hr
                    if ratio<0.70 or ratio>1.40: findings.append({'level':'error','entity':eid,'code':'vfx.hitbox_radius','message':f'{vid} impact radius {vr:g} materially disagrees with hitbox range {hr:g}'})
                if hr and tr and tr<hr*0.80: findings.append({'level':'error','entity':eid,'code':'vfx.telegraph_radius','message':f'{vid} telegraph radius {tr:g} undersells hitbox range {hr:g}'})
            rows.append({'entity':eid,'attack':aid,'vfx':vid,'coverage':coverage})
    errors=[x for x in findings if x['level']=='error']; warnings=[x for x in findings if x['level']=='warning']
    lines=['# Mob VFX Contract Audit','',f"- Result: **{'PASS' if not errors else 'FAIL'}**",f'- Attack VFX checked: {len(rows)}',f'- Errors: {len(errors)}',f'- Warnings: {len(warnings)}','','## Findings','']
    lines += ['- None.'] if not findings else [f"- **{x['level'].upper()}** `{x['code']}` [{x['entity']}]: {x['message']}" for x in findings]
    lines += ['','This verifies semantic/readability contracts, not visual beauty. Native stress QA still proves particle cost, opacity/readability, cancellation cleanup and actual synchronization.','']
    report='\n'.join(lines)
    if a.markdown: a.markdown.parent.mkdir(parents=True,exist_ok=True); a.markdown.write_text(report,encoding='utf-8')
    else: print(report,end='')
    if a.json_out: a.json_out.parent.mkdir(parents=True,exist_ok=True); a.json_out.write_text(json.dumps({'result':'pass' if not errors else 'fail','rows':rows,'findings':findings},indent=2)+'\n',encoding='utf-8')
    return 0 if not errors else 2
if __name__=='__main__': raise SystemExit(main())
