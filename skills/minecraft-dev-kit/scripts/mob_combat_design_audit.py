#!/usr/bin/env python3
"""Audit premium attack rosters for gameplay-purpose and contextual selection depth."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any

PURPOSES={'fast_check','heavy','gap_closer','disengage','anti_flank','ranged_pressure','area_denial','interrupt_punish','summon_control','defensive_counter','phase_signature','support','mobility','projectile','grab','terrain_control'}
def as_list(v:Any):return v if isinstance(v,list) else []
def num(v):
    try:return float(v)
    except:return None

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('manifest',type=Path);ap.add_argument('--root',type=Path,required=True);ap.add_argument('--markdown',type=Path);ap.add_argument('--json',dest='json_out',type=Path);a=ap.parse_args();d=json.loads(a.manifest.read_text(encoding='utf-8'));findings=[];rows=[]
    for ent in as_list(d.get('entities')):
        if not isinstance(ent,dict):continue
        eid=str(ent.get('id'));kind=str(ent.get('kind','mob')).lower();atts=[x for x in as_list(ent.get('attacks')) if isinstance(x,dict)];purposes=set();covered_phases=set();ranges=[];signatures={}
        for atk in atts:
            aid=str(atk.get('id'));purpose=str(atk.get('purpose',''))
            if purpose not in PURPOSES:findings.append({'level':'error','entity':eid,'code':'combat.purpose','message':f'{aid} missing/invalid purpose {purpose!r}'} )
            else:purposes.add(purpose)
            sel=atk.get('selection')
            if not isinstance(sel,dict):findings.append({'level':'error','entity':eid,'code':'combat.selection','message':f'{aid} needs contextual selection contract'});continue
            mn=num(sel.get('min_range'));mx=num(sel.get('max_range'));weight=num(sel.get('weight'))
            if mn is None or mx is None or mn<0 or mx<=mn:findings.append({'level':'error','entity':eid,'code':'combat.range','message':f'{aid} invalid min/max range'})
            else:ranges.append((mn,mx))
            if weight is None or weight<=0:findings.append({'level':'error','entity':eid,'code':'combat.weight','message':f'{aid} selection weight must be >0'})
            phases={int(x) for x in as_list(sel.get('phases')) if isinstance(x,int) and x>0};covered_phases|=phases
            if kind=='boss' and not phases:findings.append({'level':'error','entity':eid,'code':'combat.phase_eligibility','message':f'{aid} needs explicit eligible phases'})
            if not isinstance(sel.get('max_repeat'),int) or sel['max_repeat']<1:findings.append({'level':'error','entity':eid,'code':'combat.repeat','message':f'{aid} needs max_repeat >=1'})
            sig=(purpose,mn,mx,str(atk.get('hitbox')),round(float(atk.get('windup',0)),3),round(float(atk.get('recovery',0)),3))
            if sig in signatures:findings.append({'level':'warning','entity':eid,'code':'combat.duplicate_shape','message':f"{aid} is nearly design-identical to {signatures[sig]}"})
            else:signatures[sig]=aid
        need=5 if kind=='boss' else 3 if kind in {'elite','miniboss','mob'} and len(atts)>=3 else 0
        if len(purposes)<need:findings.append({'level':'error','entity':eid,'code':'combat.purpose_diversity','message':f'{len(purposes)} distinct attack purposes; expected at least {need}'})
        phases=int(ent.get('phases',1) or 1)
        if kind=='boss' and phases>1 and not set(range(1,phases+1)).issubset(covered_phases):findings.append({'level':'error','entity':eid,'code':'combat.phase_coverage','message':f'attacks do not cover all phases 1..{phases}'})
        if kind=='boss' and ranges:
            mins=min(x[0] for x in ranges);maxs=max(x[1] for x in ranges)
            if mins>2.0:findings.append({'level':'warning','entity':eid,'code':'combat.close_gap','message':'no attack is eligible at close range <=2 blocks'})
            if maxs<6.0 and not {'ranged_pressure','projectile','gap_closer'}&purposes:findings.append({'level':'warning','entity':eid,'code':'combat.range_pressure','message':'boss lacks long-range pressure or a gap closer'})
        rows.append({'entity':eid,'attacks':len(atts),'purposes':sorted(purposes),'phase_coverage':sorted(covered_phases)})
    errors=[x for x in findings if x['level']=='error'];warnings=[x for x in findings if x['level']=='warning']
    lines=['# Mob Combat Design Audit','',f"- Result: **{'PASS' if not errors else 'FAIL'}**",f'- Entities: {len(rows)}',f'- Errors: {len(errors)}',f'- Warnings: {len(warnings)}','','## Findings','']
    lines += ['- None.'] if not findings else [f"- **{x['level'].upper()}** `{x['code']}` [{x['entity']}]: {x['message']}" for x in findings]
    lines += ['','This checks authored decision diversity and selection contracts, not balance/fun. Native combat testing still decides fairness, pacing and player readability.','']
    report='\n'.join(lines)
    if a.markdown:a.markdown.parent.mkdir(parents=True,exist_ok=True);a.markdown.write_text(report,encoding='utf-8')
    else:print(report,end='')
    if a.json_out:a.json_out.parent.mkdir(parents=True,exist_ok=True);a.json_out.write_text(json.dumps({'result':'pass' if not errors else 'fail','rows':rows,'findings':findings},indent=2)+'\n',encoding='utf-8')
    return 0 if not errors else 2
if __name__=='__main__':raise SystemExit(main())
