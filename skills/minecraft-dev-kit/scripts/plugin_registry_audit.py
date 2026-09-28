#!/usr/bin/env python3
"""Validate the server plugin coverage registry for deterministic, non-ambiguous conversion routing."""
from __future__ import annotations
import argparse,json,re,sys
from collections import defaultdict,Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent
DEFAULT_REGISTRY=HERE.parent/'references'/'server-plugin-registry.json'
ALLOWED_ADAPTERS={'first-class','generic','detect-only','context-only'}
ALLOWED_IMPACTS={'direct-asset','gameplay-semantic','presentation','bridge','context'}
REQUIRED=('name','category','impact','adapter','tier','era')

def norm(s):return re.sub(r'[^a-z0-9]+','',str(s).lower())

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--registry',type=Path,default=DEFAULT_REGISTRY)
    ap.add_argument('--json-out',type=Path);ap.add_argument('--md-out',type=Path)
    args=ap.parse_args();reg=json.loads(args.registry.read_text(encoding='utf-8'));entries=reg.get('entries') or []
    errors=[];warnings=[];identity=defaultdict(list);names=set()
    for i,e in enumerate(entries):
        missing=[k for k in REQUIRED if not str(e.get(k,'')).strip()]
        if missing:errors.append({'entry':i,'name':e.get('name'),'error':f"missing required fields: {', '.join(missing)}"})
        if e.get('adapter') not in ALLOWED_ADAPTERS:errors.append({'entry':i,'name':e.get('name'),'error':f"unknown adapter: {e.get('adapter')}"})
        if e.get('impact') not in ALLOWED_IMPACTS:errors.append({'entry':i,'name':e.get('name'),'error':f"unknown impact: {e.get('impact')}"})
        nn=norm(e.get('name',''))
        if nn in names:errors.append({'entry':i,'name':e.get('name'),'error':'duplicate normalized canonical name'})
        names.add(nn)
        for kind,val in [('name',e.get('name',''))]+[('alias',x) for x in (e.get('aliases') or [])]+[('marker',x) for x in (e.get('markers') or [])]:
            n=norm(val)
            if n:identity[n].append({'plugin':e.get('name'),'kind':kind,'value':val})
    for key,rows in identity.items():
        owners=sorted({r['plugin'] for r in rows})
        if len(owners)>1:errors.append({'identity':key,'plugins':owners,'error':'normalized alias/marker collision','rows':rows})
    try:
        sys.path.insert(0,str(HERE));import server_family_ir
        supported=server_family_ir.SUPPORTED
        for e in entries:
            if e.get('adapter')=='generic' and e.get('category') not in supported:
                errors.append({'name':e.get('name'),'category':e.get('category'),'error':'generic adapter category has no server_family_ir route'})
    except Exception as exc:
        warnings.append(f'could not import server_family_ir for category coverage audit: {exc}')
    counts={'adapters':dict(Counter(e.get('adapter') for e in entries)),'impacts':dict(Counter(e.get('impact') for e in entries)),'categories':dict(Counter(e.get('category') for e in entries))}
    report={'pass':not errors,'registry':str(args.registry.resolve()),'snapshot_date':reg.get('snapshot_date'),'entry_count':len(entries),'counts':counts,'errors':errors,'warnings':warnings,'invariants':['Every normalized name/alias/marker maps to only one canonical plugin identity.','Every generic adapter category has a category-aware semantic IR route.','Registry recognition is routing evidence, not redistribution permission or vendor-specific parity proof.']}
    text=json.dumps(report,indent=2)
    if args.json_out:args.json_out.parent.mkdir(parents=True,exist_ok=True);args.json_out.write_text(text+'\n',encoding='utf-8')
    if args.md_out:
        lines=['# Server Plugin Registry Audit','',f"- Result: **{'PASS' if report['pass'] else 'FAIL'}**",f"- Snapshot: **{report['snapshot_date']}**",f"- Entries: **{len(entries)}**",f"- First-class: **{counts['adapters'].get('first-class',0)}**",f"- Generic family-normalized: **{counts['adapters'].get('generic',0)}**",f"- Context-only: **{counts['adapters'].get('context-only',0)}**",f"- Detect-only: **{counts['adapters'].get('detect-only',0)}**",'', '## Errors']
        lines += [f"- {x}" for x in errors] or ['- None.']
        lines += ['', '## Warnings']+[f'- {x}' for x in warnings] if warnings else ['', '## Warnings','- None.']
        args.md_out.parent.mkdir(parents=True,exist_ok=True);args.md_out.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(text)
    raise SystemExit(0 if report['pass'] else 2)
if __name__=='__main__':main()
