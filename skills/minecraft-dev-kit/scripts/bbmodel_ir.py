#!/usr/bin/env python3
"""Normalize Blockbench-derived .bbmodel or FreeMinecraftModels .fmmodel JSON into conversion IR."""
from __future__ import annotations
import argparse,json,re
from collections import Counter
from pathlib import Path

def compact_face(face):
    if not isinstance(face,dict): return {}
    return {k:face.get(k) for k in ('uv','texture','rotation','tintindex','cullface','enabled') if k in face}

def major_version(d):
    raw=(d.get('meta') or {}).get('format_version') or d.get('format_version') or '4'
    try:return int(str(raw).split('.')[0])
    except Exception:return 4

def merge_groups_and_outliner(d):
    """Blockbench v5 may split full group data into `groups` while `outliner` keeps hierarchy refs."""
    out=d.get('outliner') or []
    if major_version(d)<5 or not isinstance(d.get('groups'),list):return out
    gm={g.get('uuid'):g for g in d.get('groups') or [] if isinstance(g,dict) and g.get('uuid')}
    def rec(items):
        result=[]
        for item in items or []:
            if isinstance(item,str):result.append(item);continue
            if not isinstance(item,dict):continue
            uid=item.get('uuid');merged=dict(gm.get(uid) or {})
            merged.update(item)
            if 'children' in item:merged['children']=rec(item.get('children') or [])
            result.append(merged)
        return result
    return rec(out)

def special_role(name):
    n=(name or '').lower()
    roles=[]
    if n=='hitbox' or n.startswith('hitbox_'):roles.append('hitbox')
    if n=='tag_name' or 'nameplate' in n:roles.append('nameplate')
    if n.startswith('mount_') or n.startswith('seat_'):roles.append('mount-seat')
    if n.startswith('h_') or n in {'head','head_rotation'}:roles.append('head-anchor')
    if 'leash' in n:roles.append('leash-anchor')
    if 'locator' in n or n.startswith('loc_'):roles.append('locator-convention')
    return roles

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('input',type=Path);ap.add_argument('--json-out',type=Path);args=ap.parse_args()
    d=json.loads(args.input.read_text(encoding='utf-8'));fmt='fmmodel' if args.input.suffix.lower()=='.fmmodel' else 'bbmodel'
    outliner=merge_groups_and_outliner(d)
    elements_by_id={e.get('uuid'):e for e in (d.get('elements') or []) if isinstance(e,dict) and e.get('uuid')}
    groups=[];nodes=[];element_refs=set();special=[]
    def walk(items,parent=None):
        for item in items or []:
            if isinstance(item,str):
                element_refs.add(item);nodes.append({'kind':'element_ref','uuid':item,'parent':parent});continue
            if not isinstance(item,dict):continue
            kind=item.get('type') or ('group' if 'children' in item else 'node')
            rec={k:item.get(k) for k in ('uuid','name','type','origin','rotation','visibility','export','locked','shade','mirror_uv') if k in item}
            rec.update({'kind':kind,'parent':parent});nodes.append(rec)
            roles=special_role(item.get('name'))
            if roles:special.append({'uuid':item.get('uuid'),'name':item.get('name'),'roles':roles,'parent':parent})
            if 'children' in item:
                groups.append(rec);walk(item.get('children'),item.get('uuid') or item.get('name') or parent)
    walk(outliner)
    elements=[]
    for e in d.get('elements') or []:
        if not isinstance(e,dict):continue
        typ=e.get('type','cube');roles=special_role(e.get('name'))
        rec={'uuid':e.get('uuid'),'name':e.get('name'),'type':typ,'from':e.get('from'),'to':e.get('to'),'origin':e.get('origin'),'rotation':e.get('rotation'),'inflate':e.get('inflate'),'mirror_uv':e.get('mirror_uv'),'visibility':e.get('visibility'),'faces':{k:compact_face(v) for k,v in (e.get('faces') or {}).items()}}
        # Preserve locator/null-object fields and other non-rendering anchors rather than dropping them.
        for k in ('position','scale','locked','export','ik_target','ik_source','name','color'):
            if k in e and k not in rec:rec[k]=e.get(k)
        elements.append(rec)
        if roles:special.append({'uuid':e.get('uuid'),'name':e.get('name'),'roles':roles,'element_type':typ})
    textures=[]
    for t in d.get('textures') or []:
        if isinstance(t,dict):textures.append({k:t.get(k) for k in ('uuid','id','name','path','folder','namespace','source','mode','frame_time','frame_interpolate','width','height','uv_width','uv_height') if k in t})
    animations=[]
    for a in d.get('animations') or []:
        if not isinstance(a,dict):continue
        anim={'uuid':a.get('uuid'),'name':a.get('name'),'loop':a.get('loop'),'length':a.get('length'),'snapping':a.get('snapping'),'override':a.get('override'),'blend_weight':a.get('blend_weight'),'start_delay':a.get('start_delay'),'loop_delay':a.get('loop_delay'),'animators':[]}
        for bone_uuid,track in (a.get('animators') or {}).items():
            if not isinstance(track,dict):continue
            keys=[]
            for kf in track.get('keyframes') or []:
                if not isinstance(kf,dict):continue
                keys.append({k:kf.get(k) for k in ('uuid','channel','time','interpolation','bezier_linked','bezier_left_time','bezier_right_time','bezier_left_value','bezier_right_value','data_points','uniform') if k in kf})
            anim['animators'].append({'bone_uuid':bone_uuid,'name':track.get('name'),'type':track.get('type'),'keyframes':keys})
        animations.append(anim)
    types=Counter(str(e.get('type') or 'cube') for e in elements)
    ir={'source':str(args.input),'input_format':fmt,'blockbench_major_version':major_version(d),'meta':d.get('meta') or {},'model_identifier':d.get('model_identifier'),'resolution':d.get('resolution'),'counts':{'elements':len(elements),'element_types':dict(types),'groups':len(groups),'nodes':len(nodes),'textures':len(textures),'animations':len(animations),'keyframes':sum(len(t['keyframes']) for a in animations for t in a['animators']),'special_role_nodes':len(special)},'nodes':nodes,'elements':elements,'textures':textures,'animations':animations,'special_role_nodes':special,'orphaned_elements':sorted(set(elements_by_id)-element_refs),'conversion_notes':['Preserve UUID-to-bone binding until target hierarchy is proven.','Blockbench v5 group data is merged with the outliner hierarchy before analysis.','Keep locators/nulls/special bones even when they do not render; server runtimes may attach seats, hitboxes, items, sounds, particles, or skill origins to them.','Do not flatten animation curves before preserving interpolation/timing semantics.']}
    if fmt=='fmmodel':ir['conversion_notes'].append('FreeMinecraftModels .fmmodel is runtime-oriented/possibly stripped authoring JSON; treat present geometry/rig/animation as source evidence but do not claim omitted Blockbench authoring metadata can be recovered.')
    text=json.dumps(ir,indent=2)
    if args.json_out:args.json_out.parent.mkdir(parents=True,exist_ok=True);args.json_out.write_text(text+'\n',encoding='utf-8')
    print(text)
if __name__=='__main__':main()
