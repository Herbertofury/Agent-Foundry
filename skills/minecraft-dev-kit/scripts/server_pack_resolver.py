#!/usr/bin/env python3
"""Resolve Java resource-pack model/texture dependency closure for server-to-mod conversion."""
from __future__ import annotations
import argparse, json, re, zipfile
from collections import defaultdict
from pathlib import Path, PurePosixPath

class Bundle:
    def __init__(self, root: Path):
        self.root=root; self.zf=zipfile.ZipFile(root) if root.is_file() and zipfile.is_zipfile(root) else None
        if self.zf is None and not root.is_dir(): raise SystemExit('input must be a directory or ZIP')
        self.names=set([n for n in self.zf.namelist() if not n.endswith('/')]) if self.zf else {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    def read_json(self,name):
        try:
            raw=self.zf.read(name) if self.zf else (self.root/PurePosixPath(name)).read_bytes()
            return json.loads(raw.decode('utf-8'))
        except Exception: return None
    def close(self):
        if self.zf: self.zf.close()

def rid(value, default_ns):
    if not isinstance(value,str) or value.startswith('#') or value.startswith('builtin/'): return None
    if ':' in value: ns,path=value.split(':',1)
    else: ns,path=default_ns,value
    return ns,path

def model_file(value, default_ns):
    r=rid(value,default_ns)
    return None if not r else f'assets/{r[0]}/models/{r[1]}.json'

def texture_file(value, default_ns):
    r=rid(value,default_ns)
    return None if not r else f'assets/{r[0]}/textures/{r[1]}.png'

def collect_model_refs(obj):
    refs=[]
    if isinstance(obj,dict):
        for k,v in obj.items():
            if k in {'model','item_model','fallback','base'} and isinstance(v,str): refs.append(v)
            refs += collect_model_refs(v)
    elif isinstance(obj,list):
        for v in obj: refs += collect_model_refs(v)
    return refs

def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('input',type=Path); ap.add_argument('--json-out',type=Path); ap.add_argument('--md-out',type=Path); args=ap.parse_args()
    b=Bundle(args.input)
    try:
        graph=defaultdict(set); kinds={}; parse_errors=[]; cmd_overrides=[]
        models=sorted(n for n in b.names if re.match(r'^assets/[^/]+/models/.+\.json$',n))
        blockstates=sorted(n for n in b.names if re.match(r'^assets/[^/]+/blockstates/.+\.json$',n))
        itemdefs=sorted(n for n in b.names if re.match(r'^assets/[^/]+/items/.+\.json$',n))
        for n in models:
            ns=n.split('/')[1]; d=b.read_json(n)
            if d is None: parse_errors.append(n); continue
            kinds[n]='model'
            p=d.get('parent'); mf=model_file(p,ns) if p else None
            if mf: graph[n].add(mf)
            for v in (d.get('textures') or {}).values():
                tf=texture_file(v,ns)
                if tf: graph[n].add(tf)
            for ov in d.get('overrides') or []:
                if isinstance(ov,dict):
                    mf=model_file(ov.get('model'),ns)
                    if mf: graph[n].add(mf)
                    pred=ov.get('predicate') or {}
                    if 'custom_model_data' in pred: cmd_overrides.append({'file':n,'custom_model_data':pred.get('custom_model_data'),'model':ov.get('model')})
        def walk_model_fields(n,d,kind):
            ns=n.split('/')[1]; kinds[n]=kind
            for r in collect_model_refs(d):
                mf=model_file(r,ns)
                if mf: graph[n].add(mf)
        for n in blockstates:
            d=b.read_json(n)
            if d is None: parse_errors.append(n); continue
            walk_model_fields(n,d,'blockstate')
        for n in itemdefs:
            d=b.read_json(n)
            if d is None: parse_errors.append(n); continue
            walk_model_fields(n,d,'item_definition')
        existing=b.names
        missing=sorted({dep for deps in graph.values() for dep in deps if dep not in existing and not dep.startswith('assets/minecraft/models/builtin/')})
        external_vanilla=sorted(dep for dep in missing if dep.startswith('assets/minecraft/'))
        unresolved=sorted(dep for dep in missing if not dep.startswith('assets/minecraft/'))
        referenced_textures=sorted({dep for deps in graph.values() for dep in deps if '/textures/' in dep})
        animated=[t+'.mcmeta' for t in referenced_textures if t+'.mcmeta' in existing]
        report={'input':str(args.input),'models':len(models),'blockstates':len(blockstates),'item_definitions_1_21_4_plus':len(itemdefs),'dependency_edges':sum(len(v) for v in graph.values()),'custom_model_data_overrides':cmd_overrides,'referenced_textures':referenced_textures,'animated_referenced_textures':animated,'external_vanilla_references':external_vanilla,'unresolved_references':unresolved,'parse_errors':parse_errors,'graph':{k:sorted(v) for k,v in sorted(graph.items())}}
        text=json.dumps(report,indent=2)
        if args.json_out: args.json_out.parent.mkdir(parents=True,exist_ok=True); args.json_out.write_text(text+'\n',encoding='utf-8')
        if args.md_out:
            lines=['# Resource-Pack Dependency Closure','',f"- Models: **{len(models)}**",f"- Blockstates: **{len(blockstates)}**",f"- 1.21.4+ item definitions: **{len(itemdefs)}**",f"- Dependency edges: **{report['dependency_edges']}**",f"- Legacy CMD overrides: **{len(cmd_overrides)}**",f"- Unresolved references: **{len(unresolved)}**",'', '## Unresolved']+[f'- `{x}`' for x in unresolved[:500]]
            args.md_out.parent.mkdir(parents=True,exist_ok=True); args.md_out.write_text('\n'.join(lines)+'\n',encoding='utf-8')
        print(text)
    finally: b.close()
if __name__=='__main__': main()
