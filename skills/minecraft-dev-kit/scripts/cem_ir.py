#!/usr/bin/env python3
"""Normalize authorized OptiFine/EMF CEM .jem/.jpm packs into conversion IR."""
from __future__ import annotations
import argparse, json, posixpath, zipfile
from collections import Counter
from pathlib import Path, PurePosixPath

class Bundle:
    def __init__(self,p:Path):
        self.p=p; self.z=zipfile.ZipFile(p) if p.is_file() and zipfile.is_zipfile(p) else None
        if not self.z and not p.is_dir(): raise SystemExit('pack must be a directory or ZIP')
        self.names=set(n for n in self.z.namelist() if not n.endswith('/')) if self.z else {x.relative_to(p).as_posix() for x in p.rglob('*') if x.is_file()}
    def read_json(self,n):
        try:
            raw=self.z.read(n) if self.z else (self.p/PurePosixPath(n)).read_bytes()
            return json.loads(raw.decode('utf-8'))
        except Exception:return None
    def close(self):
        if self.z:self.z.close()

def resolve_jpm(jem_path,ref):
    if not isinstance(ref,str): return None
    r=ref if ref.endswith('.jpm') else ref+'.jpm'
    if r.startswith('~/'): return 'assets/minecraft/optifine/'+r[2:]
    if r.startswith('./'): return posixpath.normpath(posixpath.join(posixpath.dirname(jem_path),r[2:]))
    if ':' in r:
        ns,path=r.split(':',1); return f'assets/{ns}/{path.lstrip("/")}'
    if r.startswith('assets/'): return r
    # OptiFine CEM model references are commonly relative to the JEM folder.
    return posixpath.normpath(posixpath.join(posixpath.dirname(jem_path),r))

def part_ir(obj,source,depth=0):
    if not isinstance(obj,dict): return {'source':source,'invalid':True}
    boxes=[]
    for b in obj.get('boxes') or []:
        if not isinstance(b,dict): continue
        faces={k:v for k,v in b.items() if k.startswith('uv')}
        boxes.append({'coordinates':b.get('coordinates'),'textureOffset':b.get('textureOffset'),'face_uv':faces,'sizeAdd':b.get('sizeAdd'),'sizesAdd':b.get('sizesAdd')})
    sprites=[]
    for sp in obj.get('sprites') or []:
        if isinstance(sp,dict): sprites.append({k:sp.get(k) for k in ('coordinates','textureOffset','sizeAdd') if k in sp})
    children=[]
    if isinstance(obj.get('submodel'),dict): children.append(part_ir(obj['submodel'],source,depth+1))
    for c in obj.get('submodels') or []:
        if isinstance(c,dict): children.append(part_ir(c,source,depth+1))
    anim=[]
    for block in obj.get('animations') or []:
        if isinstance(block,dict):
            for dest,expr in block.items(): anim.append({'target':dest,'expression':expr})
    known={'texture','textureSize','invertAxis','translate','rotate','mirrorTexture','attachments','boxes','sprites','submodel','submodels','animations','id'}
    return {'source':source,'id':obj.get('id'),'texture':obj.get('texture'),'textureSize':obj.get('textureSize'),'invertAxis':obj.get('invertAxis'),'translate':obj.get('translate'),'rotate':obj.get('rotate'),'mirrorTexture':obj.get('mirrorTexture'),'attachments':obj.get('attachments') or {},'boxes':boxes,'sprites':sprites,'animations':anim,'children':children,'unknown_keys':sorted(set(obj)-known)}

def flatten_parts(p):
    yield p
    for c in p.get('children') or []: yield from flatten_parts(c)

def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('pack',type=Path); ap.add_argument('--jem',action='append',default=[]); ap.add_argument('--json-out',type=Path); ap.add_argument('--md-out',type=Path); args=ap.parse_args()
    b=Bundle(args.pack)
    try:
        jems=args.jem or sorted(n for n in b.names if n.lower().endswith('.jem'))
        entities=[]; unresolved=[]; parse_errors=[]; animation_targets=Counter(); part_count=box_count=sprite_count=attachment_count=0
        for jp in jems:
            d=b.read_json(jp)
            if d is None: parse_errors.append(jp); continue
            id_defs={m.get('id'):m for m in d.get('models') or [] if isinstance(m,dict) and m.get('id')}
            models=[]
            for idx,m0 in enumerate(d.get('models') or []):
                if not isinstance(m0,dict): continue
                merged={}
                base=m0.get('baseId')
                if base and base in id_defs: merged.update(id_defs[base])
                merged.update(m0)
                ext=resolve_jpm(jp,merged.get('model')) if merged.get('model') else None
                source=jp; body=dict(merged)
                if ext:
                    pd=b.read_json(ext)
                    if pd is None: unresolved.append({'jem':jp,'model_index':idx,'jpm':ext})
                    else:
                        tmp=dict(pd); tmp.update({k:v for k,v in merged.items() if k not in {'model'}}); body=tmp; source=ext
                pir=part_ir(body,source)
                allparts=list(flatten_parts(pir)); part_count+=len(allparts); box_count+=sum(len(x.get('boxes') or []) for x in allparts); sprite_count+=sum(len(x.get('sprites') or []) for x in allparts); attachment_count+=sum(len(x.get('attachments') or {}) for x in allparts)
                for part in allparts:
                    for a in part.get('animations') or []:
                        dest=str(a.get('target')); var=dest.rsplit('.',1)[-1] if '.' in dest else dest; animation_targets[var]+=1
                models.append({'id':merged.get('id'),'baseId':base,'part':merged.get('part'),'attach':merged.get('attach',False),'scale':merged.get('scale',1.0),'external_model':ext,'part_model':pir})
            entities.append({'jem':jp,'entity_name':Path(jp).stem.rstrip('0123456789') or Path(jp).stem,'texture':d.get('texture'),'textureSize':d.get('textureSize'),'shadowSize':d.get('shadowSize'),'models':models,'unknown_keys':sorted(set(d)-{'texture','textureSize','shadowSize','models'})})
        report={'source':str(args.pack),'format':'OptiFine/EMF Custom Entity Models (CEM)','entities':entities,'counts':{'jem':len(entities),'parts':part_count,'boxes':box_count,'sprites':sprite_count,'attachments':attachment_count,'animation_assignments':sum(animation_targets.values())},'animation_target_variables':dict(animation_targets),'unresolved_jpm':unresolved,'parse_errors':parse_errors,'conversion_notes':['Preserve CEM expression-driven animation as expressions/state logic; it is evaluated during rendering and is not equivalent to a finite keyframe clip.','Preserve attach-vs-replace semantics, baseId inheritance, axis inversion, mirrorTexture, nested submodels, sizeAdd/sizesAdd, attachments, and per-face UVs.','Use EMF/OptiFine rendering as an oracle for CEM-origin assets before declaring native conversion parity.']}
        text=json.dumps(report,indent=2)
        if args.json_out:args.json_out.parent.mkdir(parents=True,exist_ok=True);args.json_out.write_text(text+'\n',encoding='utf-8')
        if args.md_out:
            lines=['# CEM Conversion IR','',f"- JEM models: **{len(entities)}**",f"- Parts: **{part_count}**",f"- Boxes: **{box_count}**",f"- Sprites: **{sprite_count}**",f"- Attachments: **{attachment_count}**",f"- Animation assignments: **{sum(animation_targets.values())}**",f"- Unresolved JPM: **{len(unresolved)}**",'', '## Conversion notes']+[f'- {x}' for x in report['conversion_notes']]
            args.md_out.parent.mkdir(parents=True,exist_ok=True);args.md_out.write_text('\n'.join(lines)+'\n',encoding='utf-8')
        print(text)
        raise SystemExit(1 if unresolved or parse_errors else 0)
    finally:b.close()
if __name__=='__main__':main()
