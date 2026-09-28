#!/usr/bin/env python3
"""Static sanity checks for Blockbench-derived .bbmodel/.fmmodel files."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import bbmodel_ir as bir

def walk_outliner(nodes,groups,elements,parent=None):
    for n in nodes or []:
        if isinstance(n,str):elements.add(n)
        elif isinstance(n,dict):
            name=n.get('name') or n.get('uuid') or '<unnamed>'
            groups.append({'name':name,'uuid':n.get('uuid'),'parent':parent,'origin':n.get('origin'),'type':n.get('type')})
            walk_outliner(n.get('children',[]),groups,elements,name)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('input',type=Path);ap.add_argument('--json-out',type=Path);args=ap.parse_args()
    data=json.loads(args.input.read_text(encoding='utf-8'));outliner=bir.merge_groups_and_outliner(data);groups=[];referenced=set();walk_outliner(outliner,groups,referenced)
    elems=data.get('elements',[]) or [];elem_ids={e.get('uuid') for e in elems if isinstance(e,dict) and e.get('uuid')};textures=data.get('textures',[]) or [];animations=data.get('animations',[]) or []
    warnings=[];orphaned=sorted(elem_ids-referenced)
    if orphaned:warnings.append(f'{len(orphaned)} element(s) are not referenced by the merged outliner')
    unnamed=[g for g in groups if g['name']=='<unnamed>']
    if unnamed:warnings.append(f'{len(unnamed)} unnamed group(s)')
    if not textures:warnings.append('no textures embedded/referenced')
    dup=[];seen=set()
    for e in elems:
        if not isinstance(e,dict):continue
        u=e.get('uuid')
        if u in seen and u:dup.append(u)
        if u:seen.add(u)
    if dup:warnings.append(f'{len(set(dup))} duplicate element UUID(s)')
    root_groups=[g for g in groups if g['parent'] is None];animators=sum(len(a.get('animators',{}) or {}) for a in animations if isinstance(a,dict))
    report={'file':str(args.input),'input_format':'fmmodel' if args.input.suffix.lower()=='.fmmodel' else 'bbmodel','format_version':(data.get('meta') or {}).get('format_version') or data.get('format_version'),'blockbench_major_version':bir.major_version(data),'elements':len(elems),'element_types':{t:sum(1 for e in elems if isinstance(e,dict) and (e.get('type') or 'cube')==t) for t in sorted({(e.get('type') or 'cube') for e in elems if isinstance(e,dict)})},'groups':len(groups),'root_groups':[g['name'] for g in root_groups],'textures':len(textures),'animations':len(animations),'animation_animator_tracks':animators,'orphaned_element_uuids':orphaned,'duplicate_element_uuids':sorted(set(dup)),'warnings':warnings}
    text=json.dumps(report,indent=2)
    if args.json_out:args.json_out.parent.mkdir(parents=True,exist_ok=True);args.json_out.write_text(text+'\n',encoding='utf-8')
    print(text);raise SystemExit(1 if orphaned or dup else 0)
if __name__=='__main__':main()
