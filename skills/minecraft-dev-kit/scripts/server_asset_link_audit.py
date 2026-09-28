#!/usr/bin/env python3
"""Cross-link staged server model sources with parsed Mythic/content IR and report broken semantic references."""
from __future__ import annotations
import argparse,json,zipfile
from pathlib import Path,PurePosixPath

class Bundle:
    def __init__(self,p:Path):
        self.p=p;self.z=zipfile.ZipFile(p) if p.is_file() and zipfile.is_zipfile(p) else None
        if not self.z and not p.is_dir():raise SystemExit('assets must be directory or ZIP')
    def bbmodels(self):
        if self.z:
            for n in self.z.namelist():
                if n.lower().endswith('.bbmodel'):
                    try:yield n,json.loads(self.z.read(n).decode('utf-8'))
                    except Exception as e:yield n,{'__parse_error__':str(e)}
        else:
            for x in self.p.rglob('*.bbmodel'):
                try:yield x.relative_to(self.p).as_posix(),json.loads(x.read_text(encoding='utf-8'))
                except Exception as e:yield x.relative_to(self.p).as_posix(),{'__parse_error__':str(e)}
    def close(self):
        if self.z:self.z.close()

def load(p):return json.loads(p.read_text(encoding='utf-8')) if p else {}
def norm_id(x):return str(x).strip().lower().replace(' ','_') if x is not None else None

def model_id(path,d):
    for k in ('model_identifier','name','identifier'):
        if d.get(k):return norm_id(d[k])
    return norm_id(Path(path).stem)

def animation_aliases(name):
    n=norm_id(name);out={n}
    if not n:return set()
    parts=n.split('.')
    out.add(parts[-1])
    if len(parts)>=2:out.add('.'.join(parts[-2:]))
    # Common Blockbench naming: animation.<model>.<state>
    if parts and parts[0]=='animation' and len(parts)>=3:
        out.add('.'.join(parts[2:]));out.add(parts[-1])
    return {x for x in out if x}

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('assets',type=Path);ap.add_argument('--mythic-ir',type=Path);ap.add_argument('--content-ir',type=Path);ap.add_argument('--json-out',type=Path);ap.add_argument('--md-out',type=Path);args=ap.parse_args()
    b=Bundle(args.assets);models={};parse_errors=[]
    try:
        for path,d in b.bbmodels():
            if '__parse_error__' in d:parse_errors.append({'file':path,'error':d['__parse_error__']});continue
            mid=model_id(path,d);anims=[];aliases=set()
            for a in d.get('animations') or []:
                if not isinstance(a,dict):continue
                nm=a.get('name')
                if nm:anims.append(nm);aliases |= animation_aliases(nm)
            models.setdefault(mid,[]).append({'file':path,'animations':anims,'animation_aliases':sorted(aliases)})
    finally:b.close()
    mythic=load(args.mythic_ir);content=load(args.content_ir)
    state_refs=[];model_refs=[]
    for row in mythic.get('lines') or []:
        st=row.get('model_state') or {};mid=norm_id(st.get('modelid'));state=norm_id(st.get('state'))
        if mid or state:state_refs.append({'file':row.get('file'),'line':row.get('line'),'model_id':mid,'state':state,'operation':st.get('operation'),'raw':row.get('raw')})
        mech=row.get('mechanic') or {};argsm=mech.get('args') or {}
        if mech.get('name','').lower()=='model':
            low={str(k).lower():v for k,v in argsm.items()}
            for key in ('mid','modelid','model','m'):
                if key in low:model_refs.append({'file':row.get('file'),'line':row.get('line'),'model_id':norm_id(low[key]),'raw':row.get('raw')});break
    missing_models=[];missing_states=[];resolved_states=[]
    for ref in state_refs:
        mid=ref['model_id'];state=ref['state']
        if mid and mid not in models:
            missing_models.append({**ref,'reason':'model id not found in supplied .bbmodel sources'});continue
        candidates=models.get(mid,[]) if mid else [m for vv in models.values() for m in vv]
        if state:
            matched=[m['file'] for m in candidates if state in set(m['animation_aliases'])]
            if matched:resolved_states.append({**ref,'matched_models':matched})
            elif ref.get('operation')!='remove':missing_states.append({**ref,'available_animations':sorted({a for m in candidates for a in m['animations']})})
    for ref in model_refs:
        if ref['model_id'] and ref['model_id'] not in models:missing_models.append({**ref,'reason':'model application references missing .bbmodel source'})
    # Content pack refs are not automatically "missing" because they can resolve in generated Java RP; expose them as linkage inputs.
    content_refs=[]
    for e in content.get('entries') or []:
        for r in e.get('resource_references') or []:content_refs.append({'plugin':e.get('source_plugin'),'item_id':e.get('item_id'),'reference':r,'file':e.get('source_file')})
    report={'assets':str(args.assets),'models':models,'mythic_state_references':state_refs,'resolved_state_references':resolved_states,'missing_model_references':missing_models,'missing_state_animations':missing_states,'content_resource_references':content_refs,'bbmodel_parse_errors':parse_errors,'pass':not (missing_models or missing_states or parse_errors),'release_blockers':[]}
    if missing_models:report['release_blockers'].append(f'{len(missing_models)} missing model reference(s)')
    if missing_states:report['release_blockers'].append(f'{len(missing_states)} state/animation reference(s) have no matching supplied clip')
    if parse_errors:report['release_blockers'].append(f'{len(parse_errors)} bbmodel parse error(s)')
    text=json.dumps(report,indent=2)
    if args.json_out:args.json_out.parent.mkdir(parents=True,exist_ok=True);args.json_out.write_text(text+'\n',encoding='utf-8')
    if args.md_out:
        lines=['# Server Asset Link Audit','',f"- Result: **{'PASS' if report['pass'] else 'FAIL'}**",f"- Models: **{len(models)}**",f"- State refs: **{len(state_refs)}**",f"- Missing models: **{len(missing_models)}**",f"- Missing state clips: **{len(missing_states)}**",'', '## Release blockers']
        lines += [f'- {x}' for x in report['release_blockers']] or ['- None']
        if missing_states:
            lines += ['','## Missing states']+[f"- `{x['model_id']}:{x['state']}` from `{x['file']}:{x['line']}`" for x in missing_states]
        args.md_out.parent.mkdir(parents=True,exist_ok=True);args.md_out.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(text)
    raise SystemExit(0 if report['pass'] else 2)
if __name__=='__main__':main()
