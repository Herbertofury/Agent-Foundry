#!/usr/bin/env python3
"""Create and validate machine-readable closeout receipts with runnable-build proof."""
from __future__ import annotations
import argparse,json,sys
from datetime import datetime,timezone
from pathlib import Path

def now(): return datetime.now(timezone.utc).isoformat()
def save(p,d): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def load(p): return json.loads(p.read_text(encoding='utf-8'))

def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--path',type=Path,default=Path('.agents/CLOSEOUT-RECEIPT.json'))
    s=ap.add_subparsers(dest='cmd',required=True)
    i=s.add_parser('init'); i.add_argument('--target',required=True); i.add_argument('--build-id',required=True)
    b=s.add_parser('build'); b.add_argument('--artifact',action='append',required=True); b.add_argument('--verification-command',required=True); b.add_argument('--exit-code',type=int,required=True); b.add_argument('--observation',required=True); b.add_argument('--status',choices=['verified','failed','blocked'],required=True); b.add_argument('--fresh-copy',action='store_true')
    a=s.add_parser('add'); a.add_argument('--id',required=True); a.add_argument('--implementation',action='append',required=True); a.add_argument('--verification-command',required=True); a.add_argument('--exit-code',type=int,required=True); a.add_argument('--observation',required=True); a.add_argument('--artifact',action='append',default=[]); a.add_argument('--status',choices=['verified','failed','blocked'],required=True)
    s.add_parser('validate')
    args=ap.parse_args(); p=args.path
    if args.cmd=='init': save(p,{'schema_version':2,'created_at_utc':now(),'target':args.target,'build_id':args.build_id,'runnable_build':None,'requirements':[],'remaining_failures':[]}); print(p); return 0
    if not p.is_file(): print(f'missing receipt: {p}',file=sys.stderr); return 2
    d=load(p)
    if args.cmd=='build':
        d['runnable_build']={'artifacts':args.artifact,'verification_command':args.verification_command,'exit_code':args.exit_code,'runtime_observation':args.observation,'status':args.status,'fresh_copy_or_install':bool(args.fresh_copy),'recorded_at_utc':now()}
        if args.status!='verified' or args.exit_code!=0: d['remaining_failures'].append('runnable-build')
        else: d['remaining_failures']=[x for x in d.get('remaining_failures',[]) if x!='runnable-build']
        save(p,d); print(p); return 0
    if args.cmd=='add':
        d['requirements']=[r for r in d['requirements'] if r.get('id')!=args.id]
        d['requirements'].append({'id':args.id,'implementation':args.implementation,'verification_command':args.verification_command,'exit_code':args.exit_code,'runtime_observation':args.observation,'artifacts':args.artifact,'status':args.status,'recorded_at_utc':now()})
        d['remaining_failures']=[x for x in d.get('remaining_failures',[]) if x!=args.id]
        if args.status!='verified' or args.exit_code!=0: d['remaining_failures'].append(args.id)
        save(p,d); print(p); return 0
    errors=[]
    if not d.get('target') or not d.get('build_id'): errors.append('missing target/build_id')
    if int(d.get('schema_version',1)) >= 2:
        build=d.get('runnable_build')
        if not isinstance(build,dict): errors.append('missing runnable_build proof')
        else:
            if build.get('status')!='verified': errors.append(f'runnable_build: status={build.get("status")}')
            if build.get('exit_code')!=0: errors.append(f'runnable_build: exit_code={build.get("exit_code")}')
            if not build.get('artifacts'): errors.append('runnable_build: no artifact recorded')
            if not build.get('runtime_observation'): errors.append('runnable_build: missing runtime observation')
            if not build.get('fresh_copy_or_install'): errors.append('runnable_build: fresh-copy/install verification not recorded')
    if not d.get('requirements'): errors.append('no requirement receipts')
    for r in d.get('requirements',[]):
        if r.get('status')!='verified': errors.append(f'{r.get("id")}: status={r.get("status")}')
        if r.get('exit_code')!=0: errors.append(f'{r.get("id")}: exit_code={r.get("exit_code")}')
        if not r.get('runtime_observation'): errors.append(f'{r.get("id")}: missing runtime observation')
    if d.get('remaining_failures'): errors.append('remaining_failures is not empty')
    if errors:
        for x in errors: print(f'ERROR: {x}',file=sys.stderr)
        return 1
    print(f'Closeout receipt valid: runnable build + {len(d["requirements"])} verified requirements')
    return 0
if __name__=='__main__': raise SystemExit(main())
