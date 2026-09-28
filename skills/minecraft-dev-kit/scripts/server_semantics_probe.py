#!/usr/bin/env python3
"""Extract conversion-relevant server gameplay/model semantics from authorized configs and bbmodels."""
from __future__ import annotations
import argparse, json, re, zipfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

TEXT_EXTS={'.yml','.yaml','.txt','.json','.cfg','.conf','.toml','.properties','.bbmodel','.ajmodel'}
MAX=2*1024*1024

class Bundle:
    def __init__(self,p:Path):
        self.p=p; self.z=zipfile.ZipFile(p) if p.is_file() and zipfile.is_zipfile(p) else None
        if not self.z and not p.is_dir(): raise SystemExit('input must be directory or ZIP')
        self.names=[n for n in self.z.namelist() if not n.endswith('/')] if self.z else [x.relative_to(p).as_posix() for x in p.rglob('*') if x.is_file()]
    def read(self,n):
        if self.z:
            with self.z.open(n) as f:return f.read(MAX)
        with (self.p/PurePosixPath(n)).open('rb') as f:return f.read(MAX)
    def close(self):
        if self.z:self.z.close()

def walk_outliner(items,out):
    for x in items or []:
        if isinstance(x,dict):
            name=x.get('name') or ''
            typ=x.get('type') or ('group' if 'children' in x else 'node')
            if name: out.append({'name':name,'uuid':x.get('uuid'),'type':typ,'origin':x.get('origin')})
            walk_outliner(x.get('children'),out)

def classify_bone(name):
    n=name.lower()
    tags=[]
    tests={
        'seat/mount':('mount','seat','driver','passenger'),
        'hitbox':('hitbox','collision'),
        'held-item':('item','hand','weapon','held'),
        'leash':('leash',),
        'nameplate/tag':('tag_name','nameplate','nametag'),
        'locator/effect-origin':('locator','particle','effect','fx','muzzle','socket')
    }
    for tag,words in tests.items():
        if any(n==w or n.startswith(w+'_') or n.endswith('_'+w) for w in words): tags.append(tag)
    return tags

def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('input',type=Path); ap.add_argument('--json-out',type=Path); ap.add_argument('--md-out',type=Path); args=ap.parse_args()
    b=Bundle(args.input)
    mechanics=Counter(); triggers=Counter(); targeters=Counter(); model_ids=Counter(); states=Counter(); configs=defaultdict(dict)
    special_bones=[]; animations=[]; parse_errors=[]
    try:
        for n in sorted(b.names):
            low=n.lower(); ext=Path(low).suffix
            if ext not in TEXT_EXTS: continue
            raw=b.read(n); text=raw.decode('utf-8',errors='ignore')
            if low.endswith('.bbmodel'):
                try:
                    d=json.loads(text); bones=[]; walk_outliner(d.get('outliner') or [],bones)
                    for bone in bones:
                        tags=classify_bone(bone['name'])
                        if tags: special_bones.append({'file':n,**bone,'semantic_tags':tags})
                    for a in d.get('animations') or []:
                        if isinstance(a,dict): animations.append({'file':n,'name':a.get('name'),'loop':a.get('loop'),'length':a.get('length')})
                except Exception as exc: parse_errors.append({'file':n,'error':str(exc)})
            if low.endswith(('.yml','.yaml','.txt','.cfg','.conf','.toml','.properties')):
                ms=re.findall(r'(?mi)^\s*-\s*([A-Za-z][A-Za-z0-9_:-]*)\s*(?=\{|\s|$)',text)
                ts=re.findall(r'~([A-Za-z][A-Za-z0-9_]*)',text)
                tg=re.findall(r'@([A-Za-z][A-Za-z0-9_]*)',text)
                mids=re.findall(r'(?i)(?:\bmid\b|\bmodel\b)\s*=\s*([A-Za-z0-9_.:-]+)',text)
                sts=re.findall(r'(?i)(?:\bs\b|\bstate\b)\s*=\s*([A-Za-z0-9_.:-]+)',text)
                for x in ms: mechanics[x.lower()]+=1
                for x in ts: triggers[x]+=1
                for x in tg: targeters[x]+=1
                for x in mids: model_ids[x]+=1
                for x in sts: states[x]+=1
                if ms or ts or tg or mids or sts:
                    configs[n]={'mechanics':sorted(set(x.lower() for x in ms)),'triggers':sorted(set(ts)),'targeters':sorted(set(tg)),'model_ids':sorted(set(mids)),'states':sorted(set(sts))}
        required=[]
        if mechanics: required.append('Translate server mechanics/skill graph into native mod server logic; do not keep YAML as inert documentation.')
        if triggers: required.append('Map source triggers to authoritative mod events/state transitions with matching cooldown/order semantics.')
        if targeters: required.append('Map targeters/conditions to explicit entity/location selection predicates.')
        if states or animations: required.append('Preserve model state and animation names/timing so gameplay events drive the intended clips.')
        if special_bones: required.append('Preserve special/non-render bones until seats, hitboxes, item attachments, leashes, tags, and effect origins are mapped.')
        report={'input':str(args.input),'mechanics':dict(mechanics.most_common()),'triggers':dict(triggers.most_common()),'targeters':dict(targeters.most_common()),'model_ids':dict(model_ids.most_common()),'model_states':dict(states.most_common()),'special_bones':special_bones,'animations':animations,'config_semantics':dict(configs),'parse_errors':parse_errors,'required_translation_actions':required}
        text=json.dumps(report,indent=2)
        if args.json_out: args.json_out.parent.mkdir(parents=True,exist_ok=True); args.json_out.write_text(text+'\n',encoding='utf-8')
        if args.md_out:
            lines=['# Server Semantics Probe','',f"- Mechanics: **{sum(mechanics.values())}** ({', '.join(mechanics) or 'none'})",f"- Triggers: **{sum(triggers.values())}** ({', '.join(triggers) or 'none'})",f"- Targeters: **{sum(targeters.values())}** ({', '.join(targeters) or 'none'})",f"- Model states: **{sum(states.values())}** ({', '.join(states) or 'none'})",f"- Special bones: **{len(special_bones)}**",f"- Animations: **{len(animations)}**",'', '## Required translation actions']+[f'- {x}' for x in required]
            args.md_out.parent.mkdir(parents=True,exist_ok=True); args.md_out.write_text('\n'.join(lines)+'\n',encoding='utf-8')
        print(text)
    finally:b.close()
if __name__=='__main__':main()
