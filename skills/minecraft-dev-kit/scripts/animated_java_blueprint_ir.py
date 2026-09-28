#!/usr/bin/env python3
"""Normalize an Animated Java Plugin Blueprint export into conversion IR."""
from __future__ import annotations
import argparse, json
from collections import Counter
from pathlib import Path

NODE_TYPES={'bone','item_display','block_display','text_display','structure','camera','locator'}

def compact_transform(v):
    if not isinstance(v,dict): return {}
    return {k:v.get(k) for k in ('matrix','decomposed','position','rotation','head_rotation','scale') if k in v}

def interpolation_summary(kf):
    i=(kf or {}).get('interpolation') or {}
    if not isinstance(i,dict): return {'type':None}
    return {k:i.get(k) for k in ('type','easing','easing_arguments','left_handle_time','left_handle_value','right_handle_time','right_handle_value') if k in i}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('input',type=Path)
    ap.add_argument('--json-out',type=Path)
    ap.add_argument('--md-out',type=Path)
    args=ap.parse_args()
    d=json.loads(args.input.read_text(encoding='utf-8'))
    settings=d.get('settings') or {}
    textures=[]
    for key,t in (d.get('textures') or {}).items():
        if not isinstance(t,dict): continue
        rec={'key':key,'type':t.get('type')}
        if t.get('type')=='reference': rec['resource_location']=t.get('resource_location')
        elif t.get('type')=='custom':
            rec['mime_type']=t.get('mime_type','image/png')
            rec['embedded_bytes_estimate']=round(len(t.get('base64_string',''))*0.75)
            if 'animation' in t: rec['animation']=t.get('animation')
        rec['unknown_keys']=sorted(set(t)-{'type','resource_location','mime_type','base64_string','animation'})
        textures.append(rec)
    palettes=[]
    for key,p in (d.get('texture_palettes') or {}).items():
        if isinstance(p,dict): palettes.append({'key':key,'active_state':p.get('active_state'),'states':p.get('states') or {}})
    nodes=[]; node_types=Counter(); element_count=0; unknown_node_types=[]
    for key,n in (d.get('nodes') or {}).items():
        if not isinstance(n,dict): continue
        typ=n.get('type'); node_types[typ or '<missing>']+=1
        if typ not in NODE_TYPES: unknown_node_types.append({'key':key,'type':typ})
        rec={'key':key,'type':typ,'default_transformation':compact_transform(n.get('default_transformation')),'display_properties':n.get('display_properties') or {}}
        if typ=='bone':
            elems=[]
            for e in n.get('elements') or []:
                if not isinstance(e,dict): continue
                faces={}
                for fk,f in (e.get('faces') or {}).items():
                    if isinstance(f,dict): faces[fk]={k:f.get(k) for k in ('uv','rotation','tintindex','texture_provider') if k in f}
                elems.append({k:e.get(k) for k in ('from','to','rotation','shade','light_emission','display_rotation') if k in e} | {'faces':faces})
            rec['elements']=elems; element_count+=len(elems)
        rec['unknown_keys']=sorted(set(n)-{'type','default_transformation','display_properties','elements'})
        nodes.append(rec)
    animations=[]; interp=Counter(); channel_counts=Counter(); event_count=texture_key_count=0
    for key,a in (d.get('animations') or {}).items():
        if not isinstance(a,dict): continue
        g=a.get('global_keyframes') or {}; texk=g.get('texture') or {}; evk=g.get('event') or {}
        event_count += sum(len((v or {}).get('events') or []) for v in evk.values() if isinstance(v,dict)); texture_key_count += len(texk)
        node_tracks=[]; keyframes=0
        for node_id,tracks in (a.get('node_keyframes') or {}).items():
            if not isinstance(tracks,dict): continue
            ch={}
            for channel in ('position','rotation','scale'):
                kfs=[]
                for tm,kf in sorted((tracks.get(channel) or {}).items(), key=lambda kv: float(kv[0])):
                    if not isinstance(kf,dict): continue
                    isumm=interpolation_summary(kf); interp[isumm.get('type') or '<missing>']+=1; channel_counts[channel]+=1; keyframes+=1
                    kfs.append({'time':tm,'value':kf.get('value'),'post':kf.get('post'),'interpolation':isumm,'unknown_keys':sorted(set(kf)-{'value','post','interpolation'})})
                if kfs: ch[channel]=kfs
            if ch: node_tracks.append({'node':node_id,'channels':ch})
        loop=a.get('loop_mode') or {}
        animations.append({'key':key,'length':a.get('length'),'loop_mode':loop,'blend_weight':a.get('blend_weight','1'),'start_delay':a.get('start_delay','0'),'global_texture_keyframes':texk,'global_event_keyframes':evk,'node_tracks':node_tracks,'keyframe_count':keyframes,'unknown_keys':sorted(set(a)-{'loop_mode','length','blend_weight','start_delay','global_keyframes','node_keyframes'})})
    known_top={'format_version','settings','textures','texture_palettes','nodes','animations'}
    report={
        'source':str(args.input),'format':'Animated Java Plugin Blueprint','format_version':d.get('format_version'),'blueprint_id':settings.get('id'),
        'counts':{'textures':len(textures),'texture_palettes':len(palettes),'nodes':len(nodes),'bone_elements':element_count,'animations':len(animations),'event_emissions':event_count,'texture_state_keyframes':texture_key_count,'transformation_keyframes':sum(a['keyframe_count'] for a in animations)},
        'node_types':dict(node_types),'interpolation_types':dict(interp),'channel_keyframes':dict(channel_counts),'textures':textures,'texture_palettes':palettes,'nodes':nodes,'animations':animations,
        'unknown_node_types':unknown_node_types,'unknown_top_keys':sorted(set(d)-known_top),
        'conversion_notes':['This parses Animated Java Plugin Blueprint exports, not raw .ajmodel authoring projects. Preserve the .ajmodel too when available.','Preserve Molang expressions, event keyframes, texture-palette state changes, locator/camera/display nodes, loop delay/start delay/blend weight, and interpolation type/easing before mapping to a mod runtime.','Do not collapse item/block/text display nodes into ordinary bones without an explicit parity decision.']
    }
    text=json.dumps(report,indent=2)
    if args.json_out: args.json_out.parent.mkdir(parents=True,exist_ok=True); args.json_out.write_text(text+'\n',encoding='utf-8')
    if args.md_out:
        lines=['# Animated Java Plugin Blueprint IR','',f"- Blueprint: `{report['blueprint_id']}`",f"- Format version: `{report['format_version']}`",f"- Nodes: **{len(nodes)}** ({', '.join(f'{k}={v}' for k,v in node_types.items())})",f"- Animations: **{len(animations)}**",f"- Transform keyframes: **{report['counts']['transformation_keyframes']}**",f"- Event emissions: **{event_count}**",f"- Texture-state keyframes: **{texture_key_count}**",'', '## Conversion warnings']+[f'- {x}' for x in report['conversion_notes']]
        if unknown_node_types: lines += ['', '## Unknown node types']+[f"- `{x['key']}`: `{x['type']}`" for x in unknown_node_types]
        args.md_out.parent.mkdir(parents=True,exist_ok=True);args.md_out.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(text)
if __name__=='__main__': main()
