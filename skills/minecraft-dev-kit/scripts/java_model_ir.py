#!/usr/bin/env python3
"""Normalize one Java resource-pack model and its in-pack parent chain into conversion IR."""
from __future__ import annotations
import argparse, json, zipfile
from pathlib import Path, PurePosixPath

class Bundle:
    def __init__(self,p):
        self.p=p; self.z=zipfile.ZipFile(p) if p.is_file() and zipfile.is_zipfile(p) else None
        if not self.z and not p.is_dir(): raise SystemExit('pack must be directory or ZIP')
        self.names=set(n for n in self.z.namelist() if not n.endswith('/')) if self.z else {x.relative_to(p).as_posix() for x in p.rglob('*') if x.is_file()}
    def json(self,n):
        try:
            raw=self.z.read(n) if self.z else (self.p/PurePosixPath(n)).read_bytes()
            return json.loads(raw.decode('utf-8'))
        except Exception:return None
    def close(self):
        if self.z:self.z.close()

def normalize_model(arg,default_ns='minecraft'):
    if arg.startswith('assets/') and arg.endswith('.json'): return arg
    if ':' in arg:ns,path=arg.split(':',1)
    else:ns,path=default_ns,arg
    if path.startswith('models/'): path=path[7:]
    if path.endswith('.json'): path=path[:-5]
    return f'assets/{ns}/models/{path}.json'

def parent_file(parent,default_ns):
    if not isinstance(parent,str) or parent.startswith('builtin/'):return None
    return normalize_model(parent,default_ns)

def resolve_texture(value,textures,default_ns):
    seen=set()
    while isinstance(value,str) and value.startswith('#'):
        key=value[1:]
        if key in seen:return {'raw':value,'cycle':True}
        seen.add(key); value=textures.get(key)
    if not isinstance(value,str):return {'raw':value,'resolved':None}
    if ':' in value:ns,path=value.split(':',1)
    else:ns,path=default_ns,value
    return {'raw':value,'resolved':f'assets/{ns}/textures/{path}.png'}

def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('pack',type=Path); ap.add_argument('model'); ap.add_argument('--json-out',type=Path); args=ap.parse_args()
    b=Bundle(args.pack)
    try:
        start=normalize_model(args.model)
        chain=[]; current=start; visited=set(); missing_parent=None
        while current and current not in visited:
            visited.add(current); d=b.json(current)
            if d is None:
                missing_parent=current; break
            chain.append((current,d))
            ns=current.split('/')[1]
            pf=parent_file(d.get('parent'),ns)
            if pf and pf not in b.names:
                missing_parent=pf; break
            current=pf
        if current in visited and current != start: cycle=current
        else: cycle=None
        # Apply parent -> child texture overrides. Elements/display come from nearest child that defines them.
        textures={}
        for _,d in reversed(chain): textures.update(d.get('textures') or {})
        elements=None; elements_source=None; display={}; gui_light=None; ambientocclusion=None
        for n,d in reversed(chain):
            if 'display' in d: display.update(d.get('display') or {})
            if gui_light is None and 'gui_light' in d: gui_light=d.get('gui_light')
            if ambientocclusion is None and 'ambientocclusion' in d: ambientocclusion=d.get('ambientocclusion')
        for n,d in chain:
            if 'elements' in d:
                elements=d.get('elements') or []; elements_source=n; break
        elem_ir=[]
        for i,e in enumerate(elements or []):
            faces={}
            for face,f in (e.get('faces') or {}).items():
                tex=resolve_texture(f.get('texture'),textures,(elements_source or start).split('/')[1])
                faces[face]={'uv':f.get('uv'),'texture':tex,'rotation':f.get('rotation'),'cullface':f.get('cullface'),'tintindex':f.get('tintindex')}
            elem_ir.append({'index':i,'from':e.get('from'),'to':e.get('to'),'rotation':e.get('rotation'),'shade':e.get('shade'),'light_emission':e.get('light_emission'),'faces':faces})
        resolved_textures={k:resolve_texture(v,textures,start.split('/')[1]) for k,v in textures.items()}
        missing_textures=sorted({r['resolved'] for r in resolved_textures.values() if r.get('resolved') and r['resolved'] not in b.names})
        # Also check final element faces after indirection.
        for e in elem_ir:
            for f in e['faces'].values():
                r=f['texture'].get('resolved')
                if r and r not in b.names and r not in missing_textures:missing_textures.append(r)
        report={'pack':str(args.pack),'model':args.model,'resolved_start':start,'parent_chain':[n for n,_ in chain],'missing_or_external_parent':missing_parent,'parent_cycle':cycle,'textures':resolved_textures,'elements_source':elements_source,'elements':elem_ir,'display':display,'gui_light':gui_light,'ambientocclusion':ambientocclusion,'missing_or_external_textures':sorted(missing_textures),'conversion_notes':['Generated Java models can preserve geometry/UV evidence but usually do not preserve original Blockbench bone hierarchy, pivots, animation tracks, or server gameplay semantics.','Prefer the original .bbmodel when available; use this IR as inverse-assembly evidence when only the generated pack exists.']}
        text=json.dumps(report,indent=2)
        if args.json_out:args.json_out.parent.mkdir(parents=True,exist_ok=True);args.json_out.write_text(text+'\n',encoding='utf-8')
        print(text)
    finally:b.close()
if __name__=='__main__':main()
