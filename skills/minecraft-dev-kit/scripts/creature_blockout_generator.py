#!/usr/bin/env python3
"""Generate a deterministic semantic cuboid blockout for supported creature archetypes.

This is a starting volume/rig, never a premium final model. Ratios should come from the
pack bible or measured reference silhouette, then be artistically refined.
"""
from __future__ import annotations
import argparse,json,math,sys
from pathlib import Path
from creature_uv_packer import pack


def cube(cid,bone,origin,size): return {'id':cid,'bone':bone,'origin':[round(x,3) for x in origin],'size':[round(x,3) for x in size]}
def bone(bid,pivot,parent=None,locators=None):
    d={'id':bid,'pivot':[round(x,3) for x in pivot]}
    if parent: d['parent']=parent
    if locators: d['locators']=locators
    return d

def humanoid(h,w,d,mass,head_scale):
    leg_h=h*0.42; torso_h=h*0.34; head_h=h*0.20*head_scale; pelvis_y=leg_h
    shoulder=w*(1.15 if mass=='top_heavy' else .9 if mass=='lanky' else 1.0); limb=w*(.22 if mass=='lanky' else .28)
    bones=[bone('root',[0,0,0]),bone('pelvis',[0,pelvis_y,0],'root'),bone('torso',[0,pelvis_y+torso_h*.55,0],'pelvis',{'vfx_origin':[0,torso_h*.25,-d*.6]}),bone('head',[0,pelvis_y+torso_h,0],'torso',{'look':[0,head_h*.5,-d*.6]}),bone('arm_l',[shoulder*.55,pelvis_y+torso_h*.82,0],'torso'),bone('arm_r',[-shoulder*.55,pelvis_y+torso_h*.82,0],'torso',{'weapon':[-limb*.5,-leg_h*.38,0]}),bone('leg_l',[w*.2,pelvis_y,0],'pelvis'),bone('leg_r',[-w*.2,pelvis_y,0],'pelvis')]
    cubes=[cube('pelvis','pelvis',[-w*.35,pelvis_y-torso_h*.12,-d*.45],[w*.7,torso_h*.24,d*.9]),cube('torso','torso',[-shoulder*.5,pelvis_y,-d*.5],[shoulder,torso_h,d]),cube('head','head',[-w*.34,pelvis_y+torso_h,-d*.46],[w*.68,head_h,d*.92]),cube('arm_l','arm_l',[shoulder*.5,pelvis_y+torso_h*.2,-limb*.5],[limb,leg_h*.72,limb]),cube('arm_r','arm_r',[-shoulder*.5-limb,pelvis_y+torso_h*.2,-limb*.5],[limb,leg_h*.72,limb]),cube('leg_l','leg_l',[w*.08,0,-limb*.55],[limb,leg_h,limb*1.1]),cube('leg_r','leg_r',[-w*.08-limb,0,-limb*.55],[limb,leg_h,limb*1.1])]
    return bones,cubes

def quadruped(h,w,d,mass,head_scale):
    body_y=h*.58; length=w*1.8; body_w=w; body_h=h*.36; leg=h*.55; thick=w*.22; head=w*.58*head_scale
    bones=[bone('root',[0,0,0]),bone('body',[0,body_y,0],'root',{'vfx_origin':[0,body_h*.35,-length*.25]}),bone('head',[0,body_y+body_h*.2,-length*.55],'body',{'look':[0,head*.2,-head*.5]}),bone('leg_fl',[w*.34,body_y,-length*.32],'body'),bone('leg_fr',[-w*.34,body_y,-length*.32],'body'),bone('leg_bl',[w*.34,body_y,length*.32],'body'),bone('leg_br',[-w*.34,body_y,length*.32],'body'),bone('tail_01',[0,body_y+body_h*.1,length*.5],'body')]
    cubes=[cube('body','body',[-body_w*.5,body_y-body_h*.35,-length*.5],[body_w,body_h,length]),cube('head','head',[-head*.5,body_y,-length*.5-head],[head,head*.75,head]),cube('tail','tail_01',[-thick*.35,body_y,length*.5],[thick*.7,thick*.7,length*.55])]
    for tag,x,z in [('fl',w*.22,-length*.34),('fr',-w*.22-thick,-length*.34),('bl',w*.22,length*.2),('br',-w*.22-thick,length*.2)]: cubes.append(cube('leg_'+tag,'leg_'+tag,[x,0,z],[thick,leg,thick]))
    return bones,cubes

def avian(h,w,d,mass,head_scale):
    body_y=h*.48; bh=h*.35; wing=w*1.15; head=w*.42*head_scale
    bones=[bone('root',[0,0,0]),bone('body',[0,body_y,0],'root',{'vfx_origin':[0,bh*.2,-d*.4]}),bone('head',[0,body_y+bh*.35,-d*.7],'body'),bone('wing_l',[w*.45,body_y+bh*.2,0],'body'),bone('wing_r',[-w*.45,body_y+bh*.2,0],'body'),bone('tail',[0,body_y,d*.55],'body'),bone('leg_l',[w*.16,body_y-bh*.2,0],'body'),bone('leg_r',[-w*.16,body_y-bh*.2,0],'body')]
    cubes=[cube('body','body',[-w*.45,body_y-bh*.4,-d*.5],[w*.9,bh,d]),cube('head','head',[-head*.5,body_y+bh*.15,-d*.5-head],[head,head,head]),cube('wing_l','wing_l',[w*.35,body_y,-d*.22],[wing,bh*.12,d*.55]),cube('wing_r','wing_r',[-w*.35-wing,body_y,-d*.22],[wing,bh*.12,d*.55]),cube('tail','tail',[-w*.25,body_y,d*.4],[w*.5,bh*.12,d*.8])]
    return bones,cubes

def serpentine(h,w,d,mass,head_scale):
    seg=max(w*.7,2); n=6; base_y=h*.35; bones=[bone('root',[0,0,0])]; cubes=[]; parent='root'
    for i in range(n):
        bid=f'body_{i+1:02d}'; z=i*seg; bones.append(bone(bid,[0,base_y,z],parent,{'vfx_origin':[0,w*.2,-seg*.3]} if i==0 else None)); cubes.append(cube(bid,bid,[-w*.5,base_y-w*.35,z-seg*.15],[w,w*.7,seg])); parent=bid
    bones.append(bone('head',[0,base_y,-seg*.55],'body_01',{'look':[0,w*.2,-w*.5]})); cubes.append(cube('head','head',[-w*.55,base_y-w*.25,-seg*.9],[w*1.1,w*.8,seg*.75])); return bones,cubes

def arthropod(h,w,d,mass,head_scale):
    body_y=h*.45; length=d*1.6; bones=[bone('root',[0,0,0]),bone('body',[0,body_y,0],'root',{'vfx_origin':[0,h*.2,-length*.3]}),bone('head',[0,body_y,-length*.55],'body')]; cubes=[cube('body','body',[-w*.5,body_y-h*.18,-length*.45],[w,h*.36,length*.9]),cube('head','head',[-w*.38,body_y-h*.12,-length*.75],[w*.76,h*.28,length*.35])]
    for i,z in enumerate([-length*.28,0,length*.28],1):
        for side,sgn in [('l',1),('r',-1)]:
            bid=f'leg_{i}_{side}'; bones.append(bone(bid,[sgn*w*.45,body_y,z],'body')); x=w*.45 if sgn>0 else -w*.45-w*.75; cubes.append(cube(bid,bid,[x,body_y-h*.1,z-h*.06],[w*.75,h*.12,h*.12]))
    return bones,cubes

def floating(h,w,d,mass,head_scale):
    y=h*.55; bones=[bone('root',[0,0,0]),bone('body',[0,y,0],'root',{'vfx_origin':[0,0,-d*.6]}),bone('core',[0,y,0],'body'),bone('ring_01',[0,y,0],'body'),bone('ring_02',[0,y,0],'body')]; cubes=[cube('core','core',[-w*.35,y-h*.18,-d*.35],[w*.7,h*.36,d*.7]),cube('ring_l','ring_01',[w*.42,y-h*.06,-d*.18],[w*.42,h*.12,d*.36]),cube('ring_r','ring_01',[-w*.84,y-h*.06,-d*.18],[w*.42,h*.12,d*.36]),cube('crown','ring_02',[-w*.18,y+h*.28,-d*.18],[w*.36,h*.18,d*.36])]; return bones,cubes

def dragon(h,w,d,mass,head_scale):
    bones,cubes=quadruped(h,w,d,mass,head_scale); body_y=h*.58; length=w*1.8
    bones += [bone('wing_l',[w*.42,body_y+h*.15,0],'body'),bone('wing_r',[-w*.42,body_y+h*.15,0],'body')]
    cubes += [cube('wing_l','wing_l',[w*.35,body_y,-d*.2],[w*1.6,h*.10,d*.55]),cube('wing_r','wing_r',[-w*.35-w*1.6,body_y,-d*.2],[w*1.6,h*.10,d*.55])]
    # mouth locator on head
    for b in bones:
        if b['id']=='head': b['locators']={'vfx_mouth':[0,0,-w*.55],'look':[0,w*.2,-w*.4]}
    return bones,cubes

FUNCS={'humanoid':humanoid,'quadruped':quadruped,'avian':avian,'serpentine':serpentine,'arthropod':arthropod,'floating':floating,'dragon_or_multi_limb':dragon}

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--id',required=True); ap.add_argument('--archetype',choices=FUNCS,required=True); ap.add_argument('--out',type=Path,required=True); ap.add_argument('--height',type=float,default=24); ap.add_argument('--width',type=float,default=8); ap.add_argument('--depth',type=float,default=6); ap.add_argument('--mass',choices=['balanced','top_heavy','lanky','compact'],default='balanced'); ap.add_argument('--head-scale',type=float,default=1.0); ap.add_argument('--texture',type=int,default=64); ap.add_argument('--uv-padding',type=int,default=1); a=ap.parse_args()
    if not all(math.isfinite(v) and v>0 for v in (a.height,a.width,a.depth,a.head_scale)): raise SystemExit('dimensions/head-scale must be finite and >0')
    bones,cubes=FUNCS[a.archetype](a.height,a.width,a.depth,a.mass,a.head_scale)
    ok,packed,w,h=pack(cubes,a.texture,a.texture,a.uv_padding,True)
    while not ok and max(w,h)<512:
        w*=2; h*=2; ok,packed,w,h=pack(cubes,w,h,a.uv_padding,True)
    if not ok: print('Could not fit box UVs <=512x512'); return 2
    spec={'schema_version':1,'id':a.id,'archetype':a.archetype,'blockout_parameters':{'height':a.height,'width':a.width,'depth':a.depth,'mass':a.mass,'head_scale':a.head_scale},'texture':{'width':w,'height':h},'visible_bounds':{'width':round(max(a.width,a.depth)/16*2.2,3),'height':round(a.height/16*1.35,3),'offset':[0,round(a.height/32,3),0]},'bones':bones,'cubes':packed,'animations':[]}
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(spec,indent=2)+'\n',encoding='utf-8'); print(a.out); return 0
if __name__=='__main__': raise SystemExit(main())
