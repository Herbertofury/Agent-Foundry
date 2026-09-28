#!/usr/bin/env python3
"""Expand premium mob manifest/runtime contracts into a concrete native mod implementation plan."""
from __future__ import annotations
import argparse,json,re
from pathlib import Path
from typing import Any

def as_list(v:Any):return v if isinstance(v,list) else []
def pascal(s:str)->str:return ''.join(x[:1].upper()+x[1:] for x in re.split(r'[^A-Za-z0-9]+',s) if x) or 'Mob'

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('manifest',type=Path);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--json',dest='json_out',type=Path);a=ap.parse_args();d=json.loads(a.manifest.read_text(encoding='utf-8'));pack=d.get('pack',{});loader=str(pack.get('loader',''));mc=str(pack.get('minecraft',''));rows=[]
    lines=[f"# Native Premium Mob Runtime Plan - {pack.get('name','Unnamed Pack')}",'',f'- Target: **Minecraft {mc} / {loader}**','', '## Shared runtime modules','', '- entity type registry + attribute registration;', '- sound and particle registries;', '- server-authoritative attack scheduler built from authored timing/marker contracts;', '- Gecko animation controller/event bridge for presentation;', '- synchronized combat/phase state data;', '- data/config loader for tuning without hard-coded balance constants;', '- debug spawn/state/attack/stress commands;', '- deterministic QA world/encounter harness;', '- loot/spawn/data integration;', '- dedicated-server and native client/integrated-server regression gates.','']
    for e in as_list(d.get('entities')):
        if not isinstance(e,dict):continue
        eid=str(e.get('id')); cls=pascal(eid);r=e.get('runtime') if isinstance(e.get('runtime'),dict) else {}; attacks=as_list(e.get('attacks')); lines += [f'## {e.get("name",eid)} (`{eid}`)','',f'- Entity class: `{cls}Entity` (normal Minecraft mob subtype + Gecko `GeoEntity` where target route uses GeckoLib).',f'- Model: `{cls}Model` -> `{e.get("model_file")}`.',f'- Renderer: `{cls}Renderer` + client renderer registration.',f'- Runtime dimensions: `{r.get("dimensions")}`; tracking `{r.get("tracking_range")}`; update interval `{r.get("update_interval")}`.',f'- Synced state: `{", ".join(str(x) for x in as_list(r.get("synced_fields")))}`.',f'- Spawn mode: `{(r.get("spawn") or {}).get("mode") if isinstance(r.get("spawn"),dict) else None}`.',f'- Encounter graph: `{e.get("encounter_file","n/a")}`.','', '### Attack implementation ledger','']
        for atk in attacks:
            if not isinstance(atk,dict):continue
            lines.append(f"- `{atk.get('id')}` -> animation `{atk.get('animation')}`; start/impact/recovery `{atk.get('windup')}` / `{atk.get('active')}` / `{atk.get('recovery')}` s; server hitbox `{atk.get('hitbox')}`; purpose `{atk.get('purpose')}`; selection `{atk.get('selection')}`; client markers `{atk.get('vfx_marker')}`, `{atk.get('sfx_marker')}`; authoritative marker `{atk.get('impact_marker')}`.")
        lines += ['', '### Native acceptance','', '- spawn and renderer registration;','- attribute + persistence/restart proof;','- target/navigation behavior;','- every attack server-authoritative hitbox/damage timing;','- animation/VFX/SFX alignment at impact;','- cancel/stagger/phase cleanup;','- multiplayer target behavior;','- configured simultaneous-entity stress test;','- no task-related fresh log/model/atlas warnings;','']
        rows.append({'entity':eid,'class':cls,'attacks':len(attacks),'runtime':r})
    lines += ['## Authority invariant','', 'Do **not** apply authoritative damage from a client animation keyframe callback. Use the same authored marker time in the server attack scheduler; Gecko custom instruction/sound/particle handlers are presentation/synchronization hooks.','']
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text('\n'.join(lines),encoding='utf-8')
    if a.json_out:a.json_out.parent.mkdir(parents=True,exist_ok=True);a.json_out.write_text(json.dumps({'target':{'minecraft':mc,'loader':loader},'entities':rows},indent=2)+'\n',encoding='utf-8')
    print(a.output);return 0
if __name__=='__main__':raise SystemExit(main())
