#!/usr/bin/env python3
"""Semantically triage unknown server plugins/config folders and emit safe registry-candidate scaffolds.

This never mutates the canonical registry and never executes/decompiles plugin bytecode. It is a
recovery path for obscure/legacy/future plugins encountered in an authorized server capture.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path
import adjacent_plugin_ir as base

MAX_FILES_PER_PLUGIN=250

FAMILY_RULES=[
    (('animation','visual'),'models-animation','direct-asset'),
    (('mount_vehicle_pet',),'pets-mounts','gameplay-semantic'),
    (('quest_story',),'quests-story','gameplay-semantic'),
    (('combat','entity'),'mobs-skills','gameplay-semantic'),
    (('item_content',),'custom-content','direct-asset'),
    (('ui',),'hud-ui','presentation'),
    (('world',),'worldgen','gameplay-semantic'),
    (('combat',),'weapons','gameplay-semantic'),
    (('visual',),'presentation','presentation'),
    (('entity',),'mobs-skills','gameplay-semantic'),
    (('integration',),'library-bridge','bridge'),
]

def safe_marker(name):
    s=re.sub(r'[^a-z0-9]+','-',str(name).lower()).strip('-')
    return s or 'unknown-plugin'

def infer(group_counts):
    present={k for k,v in group_counts.items() if v}
    for required,cat,impact in FAMILY_RULES:
        if set(required)<=present:
            strength=sum(group_counts.get(k,0) for k in required)
            confidence='high' if strength>=5 else 'medium' if strength>=2 else 'low'
            return cat,impact,confidence
    return 'unknown','unknown','low'

def scan_config_dir(root:Path, rel:str):
    p=(root/rel).resolve()
    try:p.relative_to(root.resolve())
    except Exception:return {'error':'config path escapes staged root'}
    if not p.is_dir():return {'error':'config folder missing'}
    counts=Counter();refs=set();commands=set();files=[];errors=[];sample_paths=[]
    candidates=[q for q in p.rglob('*') if q.is_file() and q.suffix.lower() in base.TEXT_EXTS][:MAX_FILES_PER_PLUGIN]
    for q in candidates:
        data,err=base.parse_file(q)
        if data is None:continue
        paths,strings=base.walk(data);hits,r,c=base.semantic_hits(paths,strings)
        for g,vals in hits.items():counts[g]+=len(vals)
        refs.update(r);commands.update(c)
        files.append(q.relative_to(root).as_posix());sample_paths.extend(paths[:30])
        if err:errors.append({'file':q.relative_to(root).as_posix(),'error':err})
    cat,impact,confidence=infer(counts)
    return {'files_scanned':len(files),'sample_files':files[:30],'semantic_group_hits':dict(counts),'resource_or_namespaced_refs':sorted(refs)[:500],'command_candidates':sorted(commands)[:200],'sample_key_paths':sample_paths[:300],'parse_errors':errors,'inferred_category':cat,'inferred_impact':impact,'confidence':confidence}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('root',type=Path);ap.add_argument('--inventory',type=Path,required=True);ap.add_argument('--coverage',type=Path,required=True)
    ap.add_argument('--json-out',type=Path);ap.add_argument('--md-out',type=Path);args=ap.parse_args()
    root=args.root.resolve();inv=json.loads(args.inventory.read_text());cov=json.loads(args.coverage.read_text())
    unknown=cov.get('unknown_conversion_risk') or []
    byname=defaultdict(lambda:{'sources':[],'details':[]})
    for row in unknown:
        n=row.get('observed_name') or 'UnknownPlugin';byname[n]['sources'].append(row.get('source'));byname[n]['details'].append(row.get('details') or {})
    records=[]
    for name,b in sorted(byname.items()):
        config_paths=[d.get('path') for src,d in zip(b['sources'],b['details']) if src=='config-folder' and d.get('path')]
        scans=[scan_config_dir(root,r) for r in config_paths]
        agg=Counter();refs=set();commands=set();file_count=0
        for s in scans:
            agg.update(s.get('semantic_group_hits') or {});refs.update(s.get('resource_or_namespaced_refs') or []);commands.update(s.get('command_candidates') or []);file_count+=s.get('files_scanned',0) or 0
        cat,impact,confidence=infer(agg)
        deps=[];versions=[]
        for d in b['details']:
            deps += list(d.get('depend') or [])+list(d.get('softdepend') or [])
            if d.get('version'):versions.append(str(d['version']))
        candidate={
            'name':name,'aliases':[],'category':cat,'impact':impact,'adapter':'detect-only','tier':'C','era':'unknown-observed',
            'source':'','notes':f'Auto-triage candidate from authorized capture; verify vendor/docs before promotion. Config files scanned: {file_count}.',
            'markers':[safe_marker(name)],
        }
        records.append({'observed_name':name,'sources':sorted(set(b['sources'])),'versions':sorted(set(versions)),'declared_dependencies':sorted(set(deps)),'config_scan':{'files_scanned':file_count,'semantic_group_hits':dict(agg),'resource_or_namespaced_refs':sorted(refs)[:500],'command_candidates':sorted(commands)[:200]},'inference':{'category':cat,'impact':impact,'confidence':confidence},'registry_candidate':candidate,'rule':'Candidate is evidence only. Verify identity/license/schema, then add deliberately; never auto-promote to generic/first-class.'})
    report={'root':str(root),'unknown_plugin_count':len(records),'records':records,'pass':not records,'invariants':['No unknown JAR bytecode is executed or decompiled.','The canonical registry is never mutated automatically.','Unknowns remain unresolved for full-server parity until their identity and conversion impact are verified.']}
    text=json.dumps(report,indent=2)
    if args.json_out:args.json_out.parent.mkdir(parents=True,exist_ok=True);args.json_out.write_text(text+'\n',encoding='utf-8')
    if args.md_out:
        lines=['# Unknown Server Plugin Semantic Triage','',f'- Unknown supplied plugin identities: **{len(records)}**','']
        if not records: lines += ['No unknown supplied plugin/config identities require triage.']
        for r in records:
            i=r['inference'];lines += [f"## {r['observed_name']}",f"- Sources: {', '.join(r['sources'])}",f"- Version(s): {', '.join(r['versions']) or 'unknown'}",f"- Inferred family: **{i['category']}** / **{i['impact']}** ({i['confidence']})",f"- Config files scanned: {r['config_scan']['files_scanned']}",f"- Semantic groups: {r['config_scan']['semantic_group_hits'] or '{}'}",f"- Declared dependencies: {', '.join(r['declared_dependencies']) or 'none observed'}",'- Registry candidate is emitted in JSON only; verify before adding.','']
        args.md_out.parent.mkdir(parents=True,exist_ok=True);args.md_out.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(text)
    raise SystemExit(0)
if __name__=='__main__':main()
