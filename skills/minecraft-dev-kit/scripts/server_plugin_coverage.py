#!/usr/bin/env python3
"""Classify inventoried server plugins against the Dev Kit conversion coverage registry."""
from __future__ import annotations
import argparse,json,re
from pathlib import Path

DEFAULT_REGISTRY=Path(__file__).resolve().parent.parent/'references'/'server-plugin-registry.json'


def norm(s:str)->str:return re.sub(r'[^a-z0-9]+','',str(s).lower())

def load(p:Path):return json.loads(p.read_text(encoding='utf-8'))

def registry_index(reg):
    idx={}
    for ent in reg.get('entries',[]):
        keys=[ent.get('name',''),*(ent.get('aliases') or []),*(ent.get('markers') or [])]
        for k in keys:
            n=norm(k)
            if n:idx.setdefault(n,ent)
    return idx

def match(name,idx):
    n=norm(name)
    if not n:return None
    if n in idx:return idx[n]
    # Controlled fuzzy: exact normalized alias substring only for long names.
    candidates=[]
    for k,e in idx.items():
        if len(k)>=6 and (k in n or n in k):candidates.append((abs(len(k)-len(n)), -len(k), e))
    if not candidates:return None
    candidates.sort(key=lambda x:(x[0],x[1],x[2]['name']))
    best=candidates[0]
    if best[0] <= max(2,len(n)//5):return best[2]
    return None

def high_impact(ent):return ent and ent.get('impact') in {'direct-asset','gameplay-semantic','presentation'} and ent.get('adapter') not in {'first-class','generic'}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--inventory',type=Path,required=True);ap.add_argument('--registry',type=Path,default=DEFAULT_REGISTRY)
    ap.add_argument('--json-out',type=Path);ap.add_argument('--md-out',type=Path);args=ap.parse_args()
    inv=load(args.inventory);reg=load(args.registry);idx=registry_index(reg)
    discovered=[];seen=set()
    def add(source,name,details):
        key=norm(name)
        if not key:return
        ent=match(name,idx);canon=ent.get('name') if ent else None
        identity=(source,key)
        if identity in seen:return
        seen.add(identity)
        discovered.append({'source':source,'observed_name':name,'registry_name':canon,'coverage':(ent.get('adapter') if ent else 'unknown'),'impact':(ent.get('impact') if ent else 'unknown'),'category':(ent.get('category') if ent else 'unknown'),'tier':(ent.get('tier') if ent else None),'era':(ent.get('era') if ent else None),'details':details})
    for x in inv.get('plugin_jars') or []:
        m=x.get('metadata') or {}; add('jar',m.get('name') or Path(x.get('file_name','')).stem,{'path':x.get('path'),'version':m.get('version'),'depend':m.get('depend') or [],'softdepend':m.get('softdepend') or []})
        # Dependencies can reveal omitted plugins whose configs/JARs were not captured.
        for dep in (m.get('depend') or [])+(m.get('softdepend') or []):add('declared-dependency',dep,{'declared_by':m.get('name') or x.get('file_name')})
    for x in inv.get('plugin_config_folders') or []:add('config-folder',x.get('folder',''),{'path':x.get('path'),'config_file_count':x.get('config_file_count',0)})
    counts={}
    for d in discovered:counts[d['coverage']]=counts.get(d['coverage'],0)+1
    unknown=[d for d in discovered if d['coverage']=='unknown']
    def uniq_family(rows):
        out=[];seen_family=set()
        for d in rows:
            k=d.get('registry_name') or d.get('observed_name')
            if k in seen_family:continue
            seen_family.add(k);out.append(d)
        return out
    review=uniq_family([d for d in discovered if d['coverage']=='detect-only' and d['impact'] in {'direct-asset','gameplay-semantic','presentation'}])
    first=uniq_family([d for d in discovered if d['coverage'] in {'first-class','generic'}])
    context=uniq_family([d for d in discovered if d['coverage']=='context-only'])
    # Unknown JARs/config folders are surfaced. They are not automatic release blockers because admin/utility plugins are common;
    # but unknowns with config folders are conversion-risk candidates until classified.
    risk_unknown=[d for d in unknown if d['source'] in {'jar','config-folder'}]
    risk_unknown_families=uniq_family(risk_unknown)
    report={'registry_snapshot':reg.get('snapshot_date'),'registry_entries':len(reg.get('entries') or []),'discovered':discovered,'counts':counts,'first_class_or_generic':first,'recognized_needing_semantic_review':review,'context_only':context,'unknown':unknown,'unknown_conversion_risk':risk_unknown,'unknown_conversion_risk_families':risk_unknown_families,'coverage_gate':{'pass':not risk_unknown,'reason':'PASS means every supplied plugin JAR/config folder is classified; detect-only entries can still require a dedicated semantic adapter before full parity.'}}
    text=json.dumps(report,indent=2)
    if args.json_out:args.json_out.parent.mkdir(parents=True,exist_ok=True);args.json_out.write_text(text+'\n',encoding='utf-8')
    if args.md_out:
        lines=['# Server Plugin Conversion Coverage','',f"- Registry snapshot: **{reg.get('snapshot_date')}**",f"- Registry entries: **{len(reg.get('entries') or [])}**",f"- Discovered plugin/dependency identities: **{len(discovered)}**",f"- Classification gate: **{'PASS' if not risk_unknown else 'REVIEW'}**",'', '## Discovered']
        for d in discovered:
            lines.append(f"- **{d['observed_name']}** -> {d['registry_name'] or 'UNKNOWN'} | `{d['coverage']}` | `{d['impact']}` | source={d['source']}")
        lines += ['', '## Unknown supplied plugins/config folders']
        lines += [f"- **{d['observed_name']}** — observed via one or more supplied JAR/config sources; classify before claiming full conversion parity." for d in risk_unknown_families] or ['- None.']
        lines += ['', '## Recognized conversion-impact plugins still requiring semantic review']
        lines += [f"- **{d['registry_name']}** — {d['category']} / {d['impact']}" for d in review] or ['- None.']
        args.md_out.parent.mkdir(parents=True,exist_ok=True);args.md_out.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(text)
    raise SystemExit(0)
if __name__=='__main__':main()
