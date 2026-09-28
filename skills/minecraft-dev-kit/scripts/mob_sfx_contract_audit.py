#!/usr/bin/env python3
"""Audit premium mob sound contracts and attack SFX references."""
from __future__ import annotations
import argparse,json,wave
from pathlib import Path
from typing import Any

def as_list(v:Any): return v if isinstance(v,list) else []
def duration(path:Path):
    if path.suffix.lower()=='.wav':
        try:
            with wave.open(str(path),'rb') as w:return w.getnframes()/max(1,w.getframerate())
        except:return None
    return None

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('manifest',type=Path); ap.add_argument('--root',type=Path,required=True); ap.add_argument('--markdown',type=Path); ap.add_argument('--json',dest='json_out',type=Path); a=ap.parse_args(); d=json.loads(a.manifest.read_text(encoding='utf-8')); defs=d.get('sfx_definitions',{}); findings=[]; rows=[]
    if not isinstance(defs,dict): defs={}; findings.append({'level':'error','entity':'pack','code':'sfx.definitions','message':'sfx_definitions must be an object'})
    used=set()
    for ent in as_list(d.get('entities')):
        if not isinstance(ent,dict):continue
        eid=str(ent.get('id')); perf=ent.get('performance') if isinstance(ent.get('performance'),dict) else {}; maxc=int(perf.get('max_sfx_concurrency',16) or 16)
        for atk in as_list(ent.get('attacks')):
            if not isinstance(atk,dict):continue
            sid=str(atk.get('sfx','')); used.add(sid); sd=defs.get(sid)
            if not isinstance(sd,dict): findings.append({'level':'error','entity':eid,'code':'sfx.missing_definition','message':f"{atk.get('id')} references {sid!r} without a definition"}); continue
            role=str(sd.get('role',''))
            if role not in {'telegraph','action','impact','vocal','foley','phase','ambient'}: findings.append({'level':'error','entity':eid,'code':'sfx.role','message':f'{sid} has invalid role {role!r}'})
            files=as_list(sd.get('files'))
            if not files: findings.append({'level':'error','entity':eid,'code':'sfx.files','message':f'{sid} has no source files'})
            durations=[]
            for ref in files:
                p=Path(str(ref)); p=p if p.is_absolute() else a.root/p
                if not p.is_file(): findings.append({'level':'error','entity':eid,'code':'sfx.file_missing','message':f'{sid}: {ref}'})
                else:
                    du=duration(p)
                    if du is not None:durations.append(round(du,3))
            conc=int(sd.get('max_concurrency',0) or 0)
            if conc<=0: findings.append({'level':'error','entity':eid,'code':'sfx.concurrency','message':f'{sid} max_concurrency must be >0'})
            elif conc>maxc: findings.append({'level':'error','entity':eid,'code':'sfx.concurrency_budget','message':f'{sid} concurrency {conc} exceeds entity budget {maxc}'})
            if sd.get('spatialized') is not True and role in {'impact','action','vocal','foley'}: findings.append({'level':'warning','entity':eid,'code':'sfx.spatial','message':f'{sid} is a world {role} sound but is not spatialized'})
            pr=sd.get('pitch_range')
            if not (isinstance(pr,list) and len(pr)==2 and all(isinstance(x,(int,float)) for x in pr) and 0.25<=float(pr[0])<=float(pr[1])<=4): findings.append({'level':'error','entity':eid,'code':'sfx.pitch','message':f'{sid} needs valid pitch_range [min,max]'})
            if role in {'impact','foley','vocal'} and len(files)<2 and not sd.get('single_signature_ok'): findings.append({'level':'warning','entity':eid,'code':'sfx.variation','message':f'{sid} frequent role has only one variation'})
            rows.append({'entity':eid,'sfx':sid,'role':role,'files':len(files),'durations':durations})
    errors=[x for x in findings if x['level']=='error']; warnings=[x for x in findings if x['level']=='warning']
    lines=['# Mob SFX Contract Audit','',f"- Result: **{'PASS' if not errors else 'FAIL'}**",f'- Attack SFX definitions checked: {len(rows)}',f'- Errors: {len(errors)}',f'- Warnings: {len(warnings)}','','## Findings','']
    lines += ['- None.'] if not findings else [f"- **{x['level'].upper()}** `{x['code']}` [{x['entity']}]: {x['message']}" for x in findings]
    lines += ['','This verifies file/semantic/mix contracts, not final sound artistry. Native testing still proves mix balance, attenuation, duplicate playback and event synchronization.','']
    report='\n'.join(lines)
    if a.markdown:a.markdown.parent.mkdir(parents=True,exist_ok=True);a.markdown.write_text(report,encoding='utf-8')
    else:print(report,end='')
    if a.json_out:a.json_out.parent.mkdir(parents=True,exist_ok=True);a.json_out.write_text(json.dumps({'result':'pass' if not errors else 'fail','rows':rows,'findings':findings},indent=2)+'\n',encoding='utf-8')
    return 0 if not errors else 2
if __name__=='__main__':raise SystemExit(main())
