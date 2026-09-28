#!/usr/bin/env python3
"""Audit creature-spec animation curves for common premium-quality structural failures."""
from __future__ import annotations
import argparse, json, math
from pathlib import Path
from typing import Any


def as_list(v: Any): return v if isinstance(v,list) else []
def vdist(a,b): return math.sqrt(sum((float(x)-float(y))**2 for x,y in zip(a,b)))

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('manifest',type=Path); ap.add_argument('--root',type=Path,required=True); ap.add_argument('--markdown',type=Path); ap.add_argument('--json',dest='json_out',type=Path); a=ap.parse_args()
    data=json.loads(a.manifest.read_text(encoding='utf-8')); findings=[]; rows=[]
    for ent in as_list(data.get('entities')):
        if not isinstance(ent,dict) or not ent.get('creature_spec'): continue
        eid=str(ent.get('id')); kind=str(ent.get('kind','mob')).lower(); p=a.root/str(ent['creature_spec'])
        if not p.is_file(): continue
        try: spec=json.loads(p.read_text(encoding='utf-8'))
        except Exception: continue
        attack_anims={str(x.get('animation')) for x in as_list(ent.get('attacks')) if isinstance(x,dict)}
        for anim in as_list(spec.get('animations')):
            if not isinstance(anim,dict): continue
            name=str(anim.get('name')); tracks=anim.get('bones') if isinstance(anim.get('bones'),dict) else {}; dyn_bones=0; key_total=0
            if not tracks:
                findings.append({'level':'error','entity':eid,'animation':name,'code':'curve.empty','message':'animation has no authored bone tracks'})
            for bid,channels in tracks.items():
                bone_dynamic=False
                if not isinstance(channels,dict): continue
                for channel,keys in channels.items():
                    if not isinstance(keys,list) or not keys: continue
                    key_total += len(keys)
                    vals=[k.get('value') for k in keys if isinstance(k,dict) and isinstance(k.get('value'),list) and len(k['value'])==3]
                    if len(vals)>=2 and any(vdist(vals[i-1],vals[i])>1e-5 for i in range(1,len(vals))): bone_dynamic=True
                    if channel=='rotation' and len(vals)>=2:
                        for i in range(1,len(vals)):
                            if max(abs(float(vals[i][j])-float(vals[i-1][j])) for j in range(3))>170:
                                findings.append({'level':'warning','entity':eid,'animation':name,'code':'curve.rotation_jump','message':f'{bid} has >170 degree adjacent-key rotation; verify intentional shortest-path/spin behavior'})
                    if anim.get('loop') is True and len(vals)>=2 and vdist(vals[0],vals[-1])>0.05:
                        findings.append({'level':'error','entity':eid,'animation':name,'code':'curve.loop_seam','message':f'{bid}/{channel} first and last keys do not close the loop'})
                if bone_dynamic: dyn_bones+=1
            need=3 if kind=='boss' and name in attack_anims else 2 if name in attack_anims else 2 if any(t in name.lower() for t in ('walk','run','fly','swim','phase','transform')) else 1
            if dyn_bones < need:
                findings.append({'level':'warning' if dyn_bones else 'error','entity':eid,'animation':name,'code':'curve.motion_breadth','message':f'{dyn_bones} dynamically animated bones; expected about {need}+ for this state'})
            if name in attack_anims and key_total < 6:
                findings.append({'level':'warning','entity':eid,'animation':name,'code':'curve.attack_sparse','message':f'only {key_total} total keyframes across attack tracks; verify anticipation/impact/recovery are actually authored'})
            rows.append({'entity':eid,'animation':name,'dynamic_bones':dyn_bones,'keyframes':key_total,'loop':anim.get('loop',False)})
    errors=[f for f in findings if f['level']=='error']; warnings=[f for f in findings if f['level']=='warning']
    lines=['# Mob Animation Curve Audit','',f"- Result: **{'PASS' if not errors else 'FAIL'}**",f'- Animations inspected: {len(rows)}',f'- Errors: {len(errors)}',f'- Warnings: {len(warnings)}','','## Findings','']
    lines += ['- None.'] if not findings else [f"- **{f['level'].upper()}** `{f['code']}` [{f['entity']} / {f['animation']}]: {f['message']}" for f in findings]
    lines += ['', 'This is a structural motion audit, not an aesthetic score. Human/native visual QA decides whether arcs, weight, overlap, appeal, and timing actually look premium.', '']
    report='\n'.join(lines)
    if a.markdown: a.markdown.parent.mkdir(parents=True,exist_ok=True); a.markdown.write_text(report,encoding='utf-8')
    else: print(report,end='')
    if a.json_out: a.json_out.parent.mkdir(parents=True,exist_ok=True); a.json_out.write_text(json.dumps({'result':'pass' if not errors else 'fail','rows':rows,'findings':findings},indent=2)+'\n',encoding='utf-8')
    return 0 if not errors else 2
if __name__=='__main__': raise SystemExit(main())
