#!/usr/bin/env python3
"""Audit native runtime data needed to implement premium mobs as real mod entities."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any

def as_list(v:Any):return v if isinstance(v,list) else []
def posnum(v):return isinstance(v,(int,float)) and v>0

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('manifest',type=Path);ap.add_argument('--root',type=Path,required=True);ap.add_argument('--markdown',type=Path);ap.add_argument('--json',dest='json_out',type=Path);a=ap.parse_args();d=json.loads(a.manifest.read_text(encoding='utf-8'));findings=[];rows=[]
    for ent in as_list(d.get('entities')):
        if not isinstance(ent,dict):continue
        eid=str(ent.get('id'));kind=str(ent.get('kind','mob')).lower();r=ent.get('runtime')
        if not isinstance(r,dict):findings.append({'level':'error','entity':eid,'code':'runtime.missing','message':'runtime contract missing'});continue
        dims=r.get('dimensions')
        if not (isinstance(dims,list) and len(dims)==2 and all(posnum(x) for x in dims)):findings.append({'level':'error','entity':eid,'code':'runtime.dimensions','message':'dimensions must be [width,height] > 0'})
        for key in ('tracking_range','update_interval'):
            if not isinstance(r.get(key),int) or r[key]<=0:findings.append({'level':'error','entity':eid,'code':f'runtime.{key}','message':f'{key} must be positive integer'})
        attrs=r.get('attributes')
        if not isinstance(attrs,dict):findings.append({'level':'error','entity':eid,'code':'runtime.attributes','message':'attributes object missing'})
        else:
            for key in ('max_health','movement_speed'):
                if not posnum(attrs.get(key)):findings.append({'level':'error','entity':eid,'code':'runtime.attribute','message':f'{key} must be >0'})
        spawn=r.get('spawn')
        if not isinstance(spawn,dict) or spawn.get('mode') not in {'natural','encounter-only','structure','command-only'}:findings.append({'level':'error','entity':eid,'code':'runtime.spawn','message':'spawn.mode must be natural/encounter-only/structure/command-only'})
        elif spawn.get('mode')=='natural':
            if not as_list(spawn.get('biomes')) and not as_list(spawn.get('biome_tags')):findings.append({'level':'error','entity':eid,'code':'runtime.spawn_biome','message':'natural spawn requires biomes or biome_tags'})
            if not isinstance(spawn.get('weight'),int) or spawn['weight']<=0:findings.append({'level':'error','entity':eid,'code':'runtime.spawn_weight','message':'natural spawn weight must be positive'})
        if r.get('persistence') not in {'normal','persistent','boss','encounter'}:findings.append({'level':'error','entity':eid,'code':'runtime.persistence','message':'persistence policy missing/invalid'})
        sync={str(x) for x in as_list(r.get('synced_fields'))}
        required={'combat_state'}
        if kind=='boss':required|={'phase'}
        missing=required-sync
        if missing:findings.append({'level':'error','entity':eid,'code':'runtime.sync','message':f'missing synced fields {sorted(missing)}'})
        if kind=='boss' and not isinstance(r.get('boss_bar'),dict):findings.append({'level':'error','entity':eid,'code':'runtime.boss_bar','message':'boss needs boss_bar contract'})
        scale=r.get('scaling')
        if kind in {'boss','miniboss'} and not isinstance(scale,dict):findings.append({'level':'error','entity':eid,'code':'runtime.scaling','message':'boss/miniboss needs explicit difficulty/player scaling policy (can be disabled)'})
        rows.append({'entity':eid,'kind':kind,'spawn_mode':spawn.get('mode') if isinstance(spawn,dict) else None,'synced_fields':sorted(sync)})
    errors=[x for x in findings if x['level']=='error'];warnings=[x for x in findings if x['level']=='warning']
    lines=['# Native Mob Runtime Contract Audit','',f"- Result: **{'PASS' if not errors else 'FAIL'}**",f'- Entities: {len(rows)}',f'- Errors: {len(errors)}',f'- Warnings: {len(warnings)}','','## Findings','']
    lines += ['- None.'] if not findings else [f"- **{x['level'].upper()}** `{x['code']}` [{x['entity']}]: {x['message']}" for x in findings]
    lines += ['','This proves implementation inputs are present; it does not replace compiling/running the actual target mod.','']
    report='\n'.join(lines)
    if a.markdown:a.markdown.parent.mkdir(parents=True,exist_ok=True);a.markdown.write_text(report,encoding='utf-8')
    else:print(report,end='')
    if a.json_out:a.json_out.parent.mkdir(parents=True,exist_ok=True);a.json_out.write_text(json.dumps({'result':'pass' if not errors else 'fail','rows':rows,'findings':findings},indent=2)+'\n',encoding='utf-8')
    return 0 if not errors else 2
if __name__=='__main__':raise SystemExit(main())
