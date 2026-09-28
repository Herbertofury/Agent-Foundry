#!/usr/bin/env python3
"""Create and maintain compaction-resistant ACTIVE-TASK state."""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = 1

def now(): return datetime.now(timezone.utc).isoformat()
def load(path): return json.loads(path.read_text(encoding='utf-8'))
def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    data['updated_at_utc']=now()
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--path',type=Path,default=Path('.agents/ACTIVE-TASK.json'))
    sub=p.add_subparsers(dest='cmd',required=True)
    i=sub.add_parser('init'); i.add_argument('--request',required=True); i.add_argument('--target',required=True); i.add_argument('--artifact',default=''); i.add_argument('--project-id',default=''); i.add_argument('--handoff',default='')
    a=sub.add_parser('add-requirement'); a.add_argument('--id',required=True); a.add_argument('--text',required=True); a.add_argument('--proof',required=True)
    e=sub.add_parser('evidence'); e.add_argument('--id',required=True); e.add_argument('--implementation',action='append',default=[]); e.add_argument('--verification',required=True); e.add_argument('--observed',required=True); e.add_argument('--status',choices=['pending','verified','blocked'],default='verified')
    n=sub.add_parser('note'); n.add_argument('--kind',choices=['decision','research','failure','blocker','remaining','completed'],required=True); n.add_argument('--text',required=True)
    sub.add_parser('validate')
    args=p.parse_args(); path=args.path
    if args.cmd=='init':
        data={'schema_version':SCHEMA,'created_at_utc':now(),'updated_at_utc':now(),'request':args.request,'canonical_target':args.target,'requested_artifact':args.artifact,'project_id':args.project_id,'project_handoff':args.handoff,'active_instruction_hashes':{},'requirements':[],'decisions':[],'failures':[],'blockers':[],'remaining':[],'completed':[]}
        save(path,data); print(path); return 0
    if not path.is_file(): print(f'missing task state: {path}',file=sys.stderr); return 2
    data=load(path)
    if args.cmd=='add-requirement':
        if any(r.get('id')==args.id for r in data['requirements']): print('duplicate requirement id',file=sys.stderr); return 1
        data['requirements'].append({'id':args.id,'text':args.text,'required_proof':args.proof,'status':'pending','implementation':[],'verification':'','observed_result':''})
    elif args.cmd=='evidence':
        r=next((r for r in data['requirements'] if r.get('id')==args.id),None)
        if not r: print('unknown requirement id',file=sys.stderr); return 2
        r.update({'status':args.status,'implementation':args.implementation,'verification':args.verification,'observed_result':args.observed})
    elif args.cmd=='note': data[args.kind+'s' if not args.kind.endswith('s') else args.kind].append({'at_utc':now(),'text':args.text})
    elif args.cmd=='validate':
        errors=[]
        for key in ('request','canonical_target','requirements'):
            if not data.get(key): errors.append(f'missing {key}')
        ids=set()
        for r in data.get('requirements',[]):
            if r.get('id') in ids: errors.append(f'duplicate requirement {r.get("id")}')
            ids.add(r.get('id'))
            if r.get('status')=='verified' and (not r.get('verification') or not r.get('observed_result')): errors.append(f'{r.get("id")}: verified without evidence')
        if errors:
            for x in errors: print(f'ERROR: {x}',file=sys.stderr)
            return 1
        print(f'ACTIVE-TASK valid: {len(data["requirements"])} requirements')
        return 0
    save(path,data); print(path); return 0
if __name__=='__main__': raise SystemExit(main())
