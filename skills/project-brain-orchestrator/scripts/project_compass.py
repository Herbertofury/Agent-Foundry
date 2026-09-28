#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re, zipfile
from datetime import datetime, timezone
from pathlib import Path
KINDS=("northpoints","goals","feature_pillars","principles","wants","guardrails","acceptance_signals","publication_targets")
def now(): return datetime.now(timezone.utc).isoformat()
def load(p): return json.loads(p.read_text(encoding="utf-8"))
def write(p,d): p.parent.mkdir(parents=True,exist_ok=True); t=p.with_suffix(p.suffix+".tmp"); t.write_text(json.dumps(d,indent=2,ensure_ascii=False)+"\n",encoding="utf-8"); t.replace(p)
def append(p,d): p.parent.mkdir(parents=True,exist_ok=True); p.open("a",encoding="utf-8").write(json.dumps(d,ensure_ascii=False)+"\n")
def mem(root): return root.resolve()/".agents-memory"
def path(root): return mem(root)/"COMPASS.json"
def slug(s): return re.sub(r"[^a-z0-9]+","-",s.lower()).strip("-") or "item"
def render(root,d):
 out=["# Project Compass","",f"**Project:** `{d.get('project_id','unknown')}`  ",f"**Revision:** {d.get('revision',1)}  ",f"**Updated:** {d.get('updated_at_utc','')}",""]
 labels={k:k.replace('_',' ').title() for k in KINDS}
 for k in KINDS:
  out += [f"## {labels[k]}",""]
  for x in d.get(k,[]):
   title=x.get('title') or x.get('statement') or x.get('provider') or x.get('id')
   metadata=[x.get('status','active')]
   if x.get('priority'): metadata.append(f"priority: {x['priority']}")
   if x.get('source'): metadata.append(f"source: {x['source']}")
   out.append(f"- **{title}** (`{x.get('id','')}`) — {' · '.join(metadata)}")
   if x.get('statement') and x.get('title'): out.append(f"  {x['statement']}")
   for v in x.get('verification',[]): out.append(f"  - Proof: {v}")
  if not d.get(k): out.append("- None recorded.")
  out.append("")
 (mem(root)/"PROJECT-COMPASS.md").write_text("\n".join(out)+"\n",encoding="utf-8")
def validate(d):
 errs=[]
 if d.get('schema_version')!=1: errs.append('schema_version must be 1')
 global_ids={}
 for k in KINDS:
  if not isinstance(d.get(k),list): errs.append(f'{k} must be a list'); continue
  ids=[]
  for x in d[k]:
   if not isinstance(x,dict) or not x.get('id'): errs.append(f'{k} item missing id'); continue
   iid=x['id']; ids.append(iid)
   if iid in global_ids: errs.append(f'duplicate ID across {global_ids[iid]} and {k}: {iid}')
   else: global_ids[iid]=k
   if k not in ('publication_targets',) and not (x.get('statement') or x.get('title')): errs.append(f"{iid} missing statement/title")
   if x.get('priority')=='foundational':
    if not x.get('source'): errs.append(f'{iid} foundational item missing source')
    if not isinstance(x.get('verification'),list) or not x.get('verification'): errs.append(f'{iid} foundational item missing verification')
   if k=='publication_targets':
    if not x.get('provider'): errs.append(f'{iid} publication target missing provider')
    if not x.get('path'): errs.append(f'{iid} publication target missing path')
  if len(ids)!=len(set(ids)): errs.append(f'duplicate IDs in {k}')
 return errs
def init(args):
 p=path(args.root)
 if p.exists() and not args.force: raise SystemExit(f'already exists: {p}')
 d={"schema_version":1,"project_id":args.project_id,"revision":1,"updated_at_utc":now(),**{k:[] for k in KINDS}}
 write(p,d); append(mem(args.root)/"compass-events.jsonl",{"event":"initialized","at":now(),"project_id":args.project_id}); render(args.root,d); print(p)
def add(args):
 d=load(path(args.root)); arr=d[args.kind]; iid=args.id or slug(args.title or args.statement)
 if any(x['id']==iid for x in arr): raise SystemExit(f'duplicate id: {iid}')
 item={"id":iid,"status":args.status,"source":args.source}
 if args.title: item['title']=args.title
 if args.statement: item['statement']=args.statement
 if args.priority: item['priority']=args.priority
 if args.verify: item['verification']=args.verify
 arr.append(item); d['revision']=d.get('revision',1)+1; d['updated_at_utc']=now(); write(path(args.root),d); append(mem(args.root)/"compass-events.jsonl",{"event":"added","at":now(),"kind":args.kind,"item":item}); render(args.root,d); print(iid)
def supersede(args):
 d=load(path(args.root)); found=None
 for x in d[args.kind]:
  if x['id']==args.id: found=x; break
 if not found: raise SystemExit('item not found')
 found['status']='superseded'; found['superseded_at_utc']=now(); found['superseded_by']=args.by; found['supersession_reason']=args.reason
 d['revision']+=1; d['updated_at_utc']=now(); write(path(args.root),d); append(mem(args.root)/"compass-events.jsonl",{"event":"superseded","at":now(),"kind":args.kind,"id":args.id,"by":args.by,"reason":args.reason}); render(args.root,d)
def check(args):
 d=load(path(args.root)); e=validate(d); render(args.root,d)
 if e:
  print('\n'.join(e)); return 1
 print('Project Compass valid'); return 0
def publish(args):
 if not re.fullmatch(r'[0-9a-fA-F]{64}',args.sha256): raise SystemExit('sha256 must be 64 hex characters')
 rec={"at":now(),"provider":args.provider,"remote_id":args.remote_id,"remote_url":args.remote_url,"name":args.name,"local_size":args.local_size,"remote_size":args.remote_size,"sha256":args.sha256.lower(),"verified":args.local_size==args.remote_size}
 if not rec['verified']: raise SystemExit('remote size does not match local size')
 append(mem(args.root)/"publications.jsonl",rec); print(json.dumps(rec))
def export(args):
 m=mem(args.root); files=[p for p in m.rglob('*') if p.is_file()]
 with zipfile.ZipFile(args.output,'w',zipfile.ZIP_DEFLATED) as z:
  for p in files: z.write(p,p.relative_to(args.root.resolve()))
 digest=hashlib.sha256(args.output.read_bytes()).hexdigest(); print(json.dumps({"path":str(args.output),"bytes":args.output.stat().st_size,"sha256":digest}))
def main():
 p=argparse.ArgumentParser(); s=p.add_subparsers(dest='cmd',required=True)
 a=s.add_parser('init'); a.add_argument('root',type=Path); a.add_argument('--project-id',required=True); a.add_argument('--force',action='store_true'); a.set_defaults(fn=init)
 a=s.add_parser('add'); a.add_argument('root',type=Path); a.add_argument('kind',choices=KINDS); a.add_argument('--id'); a.add_argument('--title'); a.add_argument('--statement'); a.add_argument('--status',default='active'); a.add_argument('--source',default='user'); a.add_argument('--priority'); a.add_argument('--verify',action='append',default=[]); a.set_defaults(fn=add)
 a=s.add_parser('supersede'); a.add_argument('root',type=Path); a.add_argument('kind',choices=KINDS); a.add_argument('id'); a.add_argument('--by',required=True); a.add_argument('--reason',required=True); a.set_defaults(fn=supersede)
 a=s.add_parser('validate'); a.add_argument('root',type=Path); a.set_defaults(fn=check)
 a=s.add_parser('publish-record'); a.add_argument('root',type=Path); a.add_argument('--provider',required=True); a.add_argument('--remote-id',required=True); a.add_argument('--remote-url',required=True); a.add_argument('--name',required=True); a.add_argument('--local-size',type=int,required=True); a.add_argument('--remote-size',type=int,required=True); a.add_argument('--sha256',required=True); a.set_defaults(fn=publish)
 a=s.add_parser('export'); a.add_argument('root',type=Path); a.add_argument('--output',type=Path,required=True); a.set_defaults(fn=export)
 args=p.parse_args(); return args.fn(args) or 0
if __name__=='__main__': raise SystemExit(main())
