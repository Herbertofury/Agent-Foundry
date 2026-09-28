#!/usr/bin/env python3
"""Audit whether mob-pack variants represent meaningful premium content rather than recolor padding."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any

VALID={'silhouette','attachments','palette','materials','animation_personality','combat','audio','vfx','environmental_role'}
def as_list(v:Any): return v if isinstance(v,list) else []

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('manifest',type=Path); ap.add_argument('--root',type=Path,required=True); ap.add_argument('--markdown',type=Path); ap.add_argument('--json',dest='json_out',type=Path); a=ap.parse_args(); d=json.loads(a.manifest.read_text(encoding='utf-8')); findings=[]; rows=[]; meaningful=0
    for ent in as_list(d.get('entities')):
        if not isinstance(ent,dict): continue
        eid=str(ent.get('id')); seen=set(); variants=as_list(ent.get('variants'))
        for i,v in enumerate(variants):
            if isinstance(v,str):
                vid=v
                if vid!='base': findings.append({'level':'warning','entity':eid,'code':'variant.legacy_string','message':f'{vid} has no declared change dimensions and does not count as a meaningful premium variant'})
                rows.append({'entity':eid,'variant':vid,'meaningful':False,'changes':[]}); continue
            if not isinstance(v,dict): findings.append({'level':'error','entity':eid,'code':'variant.invalid','message':f'variant index {i} must be string/object'}); continue
            vid=str(v.get('id',''))
            if not vid: findings.append({'level':'error','entity':eid,'code':'variant.id','message':f'variant index {i} lacks id'}); continue
            if vid in seen: findings.append({'level':'error','entity':eid,'code':'variant.duplicate','message':f'duplicate variant {vid}'}); seen.add(vid)
            changes={str(x) for x in as_list(v.get('changes'))}; bad=changes-VALID
            if bad: findings.append({'level':'error','entity':eid,'code':'variant.change','message':f'{vid} has invalid change dimensions {sorted(bad)}'})
            is_meaningful=len(changes & VALID)>=2
            if vid!='base' and not is_meaningful: findings.append({'level':'error','entity':eid,'code':'variant.padding','message':f'{vid} changes fewer than 2 meaningful dimensions'})
            if vid!='base' and changes<= {'palette','materials'}: findings.append({'level':'error','entity':eid,'code':'variant.recolor_only','message':f'{vid} is material/palette-only and cannot count as premium content'})
            for field in ('model_file','texture_file'):
                ref=v.get(field)
                if ref:
                    p=Path(str(ref)); p=p if p.is_absolute() else a.root/p
                    if not p.is_file(): findings.append({'level':'error','entity':eid,'code':'variant.asset','message':f'{vid} {field} not found: {ref}'})
            if vid!='base' and is_meaningful and not changes<= {'palette','materials'}: meaningful+=1
            rows.append({'entity':eid,'variant':vid,'meaningful':vid!='base' and is_meaningful and not changes<= {'palette','materials'},'changes':sorted(changes)})
    errors=[x for x in findings if x['level']=='error']; warnings=[x for x in findings if x['level']=='warning']
    lines=['# Mob Variant Quality Audit','',f"- Result: **{'PASS' if not errors else 'FAIL'}**",f'- Meaningful alternate variants: {meaningful}',f'- Errors: {len(errors)}',f'- Warnings: {len(warnings)}','','## Findings','']
    lines += ['- None.'] if not findings else [f"- **{x['level'].upper()}** `{x['code']}` [{x['entity']}]: {x['message']}" for x in findings]
    lines += ['','Only variants changing at least two meaningful dimensions count toward premium pack breadth; recolor-only skins remain valid bonus cosmetics, not content-count padding.','']
    report='\n'.join(lines)
    if a.markdown: a.markdown.parent.mkdir(parents=True,exist_ok=True); a.markdown.write_text(report,encoding='utf-8')
    else: print(report,end='')
    if a.json_out: a.json_out.parent.mkdir(parents=True,exist_ok=True); a.json_out.write_text(json.dumps({'result':'pass' if not errors else 'fail','meaningful_variants':meaningful,'rows':rows,'findings':findings},indent=2)+'\n',encoding='utf-8')
    return 0 if not errors else 2
if __name__=='__main__': raise SystemExit(main())
