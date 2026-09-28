#!/usr/bin/env python3
"""Validate boss/miniboss encounter state graphs referenced by a premium pack manifest."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any

def as_list(v:Any): return v if isinstance(v,list) else []
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('manifest',type=Path); ap.add_argument('--root',type=Path,required=True); ap.add_argument('--markdown',type=Path); ap.add_argument('--json',dest='json_out',type=Path); a=ap.parse_args()
    data=json.loads(a.manifest.read_text(encoding='utf-8')); findings=[]; rows=[]
    for ent in as_list(data.get('entities')):
        if not isinstance(ent,dict) or str(ent.get('kind','')).lower() not in {'boss','miniboss'}: continue
        eid=str(ent.get('id')); ref=ent.get('encounter_file'); attacks={str(x.get('id')) for x in as_list(ent.get('attacks')) if isinstance(x,dict) and x.get('id')}
        if not ref: findings.append({'level':'error','entity':eid,'code':'encounter.missing','message':'encounter_file missing'}); continue
        p=Path(str(ref)); p=p if p.is_absolute() else a.root/p
        if not p.is_file(): findings.append({'level':'error','entity':eid,'code':'encounter.not_found','message':str(ref)}); continue
        try: g=json.loads(p.read_text(encoding='utf-8'))
        except Exception as exc: findings.append({'level':'error','entity':eid,'code':'encounter.parse','message':str(exc)}); continue
        states=as_list(g.get('states')); ids=[]
        for st in states:
            if isinstance(st,dict) and st.get('id'): ids.append(str(st['id']))
        idset=set(ids)
        if len(ids)!=len(idset): findings.append({'level':'error','entity':eid,'code':'encounter.duplicate_state','message':'duplicate state ids'})
        entry=str(g.get('entry',''))
        if entry not in idset: findings.append({'level':'error','entity':eid,'code':'encounter.entry','message':f'entry state {entry!r} missing'})
        edges={sid:[] for sid in idset}; terminal=set(); phase_states=set()
        for st in states:
            if not isinstance(st,dict) or str(st.get('id','')) not in idset: continue
            sid=str(st['id']); kind=str(st.get('kind','')).lower()
            if kind in {'death','terminal','cleanup'}: terminal.add(sid)
            if kind in {'phase','phase_transition','enrage'} or 'phase' in sid.lower(): phase_states.add(sid)
            for aid in as_list(st.get('attacks')):
                if str(aid) not in attacks: findings.append({'level':'error','entity':eid,'code':'encounter.attack_ref','message':f'state {sid} references missing attack {aid}'})
            trans=as_list(st.get('transitions'))
            for tr in trans:
                if not isinstance(tr,dict): continue
                to=str(tr.get('to','')); cond=tr.get('when')
                if to not in idset: findings.append({'level':'error','entity':eid,'code':'encounter.transition_target','message':f'{sid} -> {to!r} missing'})
                else: edges[sid].append(to)
                if not isinstance(cond,str) or not cond.strip(): findings.append({'level':'error','entity':eid,'code':'encounter.transition_guard','message':f'{sid} -> {to!r} lacks explicit guard'})
        reachable=set(); stack=[entry] if entry in idset else []
        while stack:
            cur=stack.pop()
            if cur in reachable: continue
            reachable.add(cur); stack.extend(edges.get(cur,[]))
        for sid in sorted(idset-reachable): findings.append({'level':'error','entity':eid,'code':'encounter.unreachable','message':f'unreachable state {sid}'})
        if not terminal: findings.append({'level':'error','entity':eid,'code':'encounter.terminal','message':'no death/terminal/cleanup state'})
        if str(ent.get('kind','')).lower()=='boss' and int(ent.get('phases',1) or 1)>=2 and not phase_states: findings.append({'level':'error','entity':eid,'code':'encounter.phase','message':'multi-phase boss has no explicit phase state'})
        rows.append({'entity':eid,'states':len(idset),'reachable':len(reachable),'phase_states':len(phase_states),'terminal_states':len(terminal)})
    errors=[f for f in findings if f['level']=='error']
    lines=['# Mob Encounter Graph Audit','',f"- Result: **{'PASS' if not errors else 'FAIL'}**",f'- Encounter graphs: {len(rows)}',f'- Errors: {len(errors)}','','## Findings','']
    lines += ['- None.'] if not findings else [f"- **{f['level'].upper()}** `{f['code']}` [{f['entity']}]: {f['message']}" for f in findings]
    lines += ['', 'Graph validity does not prove good AI. Native tests still verify targeting stability, navigation, multiplayer pressure, phase cleanup, stagger/parry windows, anti-cheese behavior, and real attack selection.', '']
    report='\n'.join(lines)
    if a.markdown: a.markdown.parent.mkdir(parents=True,exist_ok=True); a.markdown.write_text(report,encoding='utf-8')
    else: print(report,end='')
    if a.json_out: a.json_out.parent.mkdir(parents=True,exist_ok=True); a.json_out.write_text(json.dumps({'result':'pass' if not errors else 'fail','rows':rows,'findings':findings},indent=2)+'\n',encoding='utf-8')
    return 0 if not errors else 2
if __name__=='__main__': raise SystemExit(main())
