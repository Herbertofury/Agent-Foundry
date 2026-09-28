#!/usr/bin/env python3
"""Generate semantic zero-start creature-spec scaffolds for reference reconstruction.

These are deliberately simple rigs/anchors, not final art. Image/GIF inverse fitting,
visual-hull replacement, UV/texture recovery, and native target-runtime mapping refine them.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
from creature_uv_packer import pack,next_pow2


def b(id,pivot,parent=None,locators=None,rotation=None):
    x={'id':id,'pivot':[float(v) for v in pivot]}
    if parent: x['parent']=parent
    if locators: x['locators']=locators
    if rotation: x['rotation']=rotation
    return x

def c(id,bone,origin,size,rotation=None,pivot=None,inflate=None):
    x={'id':id,'bone':bone,'origin':[float(v) for v in origin],'size':[float(v) for v in size]}
    if rotation: x['rotation']=[float(v) for v in rotation]
    if pivot: x['pivot']=[float(v) for v in pivot]
    if inflate is not None: x['inflate']=float(inflate)
    return x

def sword():
    bones=[b('root',[0,0,0],locators={'grip':[0,4,0],'tip':[0,27,0]}),b('grip',[0,7,0],'root'),b('guard',[0,8,0],'grip'),b('blade',[0,9,0],'guard'),b('pommel',[0,0,0],'grip'),b('ornament',[0,10,0],'guard')]
    cubes=[c('grip','grip',[-1,1,-1],[2,7,2]),c('guard','guard',[-5,8,-1],[10,2,2]),c('blade','blade',[-1.5,10,-.75],[3,17,1.5]),c('pommel','pommel',[-2,-2,-2],[4,3,4]),c('ornament','ornament',[-2.5,10,-1],[5,3,2])]
    return bones,cubes,{'primary_axis':'y','anchors':['grip','tip'],'target':'held weapon/item transform'}
def dagger():
    bones=[b('root',[0,0,0],locators={'grip':[0,4,0],'tip':[0,18,0]}),b('grip',[0,6,0],'root'),b('guard',[0,7,0],'grip'),b('blade',[0,8,0],'guard'),b('pommel',[0,1,0],'grip')]
    cubes=[c('grip','grip',[-.8,1,-.8],[1.6,6,1.6]),c('guard','guard',[-3.2,7,-.8],[6.4,1.5,1.6]),c('blade','blade',[-1.1,8,-.55],[2.2,10,1.1]),c('pommel','pommel',[-1.4,-.8,-1.4],[2.8,2.2,2.8])]
    return bones,cubes,{'primary_axis':'y','anchors':['grip','tip'],'target':'dagger/short-blade held transform'}

def greatsword():
    bones=[b('root',[0,0,0],locators={'grip':[0,6,0],'tip':[0,40,0]}),b('grip',[0,10,0],'root'),b('guard',[0,12,0],'grip'),b('blade',[0,13,0],'guard'),b('pommel',[0,1,0],'grip'),b('ornament',[0,16,0],'guard')]
    cubes=[c('grip','grip',[-1.2,1,-1.2],[2.4,11,2.4]),c('guard','guard',[-8,11,-1.25],[16,2.5,2.5]),c('blade','blade',[-2.6,13,-1],[5.2,27,2]),c('pommel','pommel',[-2.2,-2,-2.2],[4.4,4,4.4]),c('ornament','ornament',[-3.4,14,-1.3],[6.8,5,2.6])]
    return bones,cubes,{'primary_axis':'y','anchors':['grip','tip'],'target':'greatsword/two-handed weapon transform'}

def axe():
    bones=[b('root',[0,0,0],locators={'grip':[0,6,0],'strike_origin':[0,25,0]}),b('haft',[0,0,0],'root'),b('head',[0,23,0],'haft'),b('blade',[0,24,0],'head'),b('poll',[0,24,0],'head')]
    cubes=[c('haft','haft',[-1,0,-1],[2,25,2]),c('head','head',[-3,22,-1.6],[6,4,3.2]),c('blade','blade',[-9,21,-1.1],[7,7,2.2]),c('poll','poll',[3,22,-1],[4,4,2])]
    return bones,cubes,{'primary_axis':'y','anchors':['grip','strike_origin'],'target':'axe held transform'}

def mace():
    bones=[b('root',[0,0,0],locators={'grip':[0,6,0],'strike_origin':[0,26,0]}),b('shaft',[0,0,0],'root'),b('head',[0,24,0],'shaft'),b('flange_x',[0,26,0],'head'),b('flange_z',[0,26,0],'head')]
    cubes=[c('shaft','shaft',[-1,0,-1],[2,23,2]),c('head','head',[-3,23,-3],[6,6,6]),c('flange_x','flange_x',[-5,24,-1.2],[10,4,2.4]),c('flange_z','flange_z',[-1.2,24,-5],[2.4,4,10])]
    return bones,cubes,{'primary_axis':'y','anchors':['grip','strike_origin'],'target':'mace held transform'}

def hammer():
    bones=[b('root',[0,0,0],locators={'grip':[0,6,0],'strike_origin':[0,27,0]}),b('shaft',[0,0,0],'root'),b('head',[0,25,0],'shaft'),b('face_l',[-5,27,0],'head'),b('face_r',[5,27,0],'head')]
    cubes=[c('shaft','shaft',[-1.2,0,-1.2],[2.4,25,2.4]),c('head','head',[-8,24,-3],[16,6,6]),c('face_l','face_l',[-10,25,-3.5],[3,5,7]),c('face_r','face_r',[7,25,-3.5],[3,5,7])]
    return bones,cubes,{'primary_axis':'y','anchors':['grip','strike_origin'],'target':'hammer held transform'}

def spear():
    bones=[b('root',[0,0,0],locators={'grip':[0,10,0],'tip':[0,42,0],'projectile_origin':[0,42,0]}),b('shaft',[0,0,0],'root'),b('head',[0,36,0],'shaft'),b('blade',[0,38,0],'head')]
    cubes=[c('shaft','shaft',[-.75,0,-.75],[1.5,37,1.5]),c('socket','head',[-1.5,35,-1.5],[3,4,3]),c('blade','blade',[-2.2,38,-.8],[4.4,7,1.6])]
    return bones,cubes,{'primary_axis':'y','anchors':['grip','tip','projectile_origin'],'target':'spear/pole weapon transform'}

def polearm():
    bones,cubes,contract=spear()
    bones.append(b('side_blade',[0,37,0],'head'))
    cubes.append(c('side_blade','side_blade',[-7,35,-.9],[6,7,1.8],rotation=[0,0,-18],pivot=[-1,36,0]))
    contract={**contract,'target':'glaive/polearm transform'}
    return bones,cubes,contract

def scythe():
    bones=[b('root',[0,0,0],locators={'grip':[0,10,0],'tip':[-14,40,0],'strike_origin':[-8,38,0]}),b('shaft',[0,0,0],'root'),b('neck',[0,35,0],'shaft'),b('blade',[-1,38,0],'neck'),b('tip',[-13,40,0],'blade')]
    cubes=[c('shaft','shaft',[-.9,0,-.9],[1.8,37,1.8]),c('neck','neck',[-2,35,-1.2],[4,5,2.4]),c('blade','blade',[-13,37,-.75],[13,3,1.5],rotation=[0,0,10],pivot=[-1,38,0]),c('tip','tip',[-15,39,-.65],[4,2,1.3],rotation=[0,0,28],pivot=[-12,40,0])]
    return bones,cubes,{'primary_axis':'y','anchors':['grip','tip','strike_origin'],'target':'scythe held transform'}

def shield():
    bones=[b('root',[0,10,0],locators={'grip':[0,10,1.5],'block_face':[0,10,-2]}),b('body',[0,10,0],'root'),b('boss',[0,10,-2],'body'),b('rim',[0,10,0],'body')]
    cubes=[c('body','body',[-7,2,-1.5],[14,16,3]),c('boss','boss',[-3,7,-3.5],[6,6,2.5]),c('rim_top','rim',[-7,17,-2],[14,2,4]),c('rim_bottom','rim',[-7,1,-2],[14,2,4]),c('rim_l','rim',[-8,3,-2],[2,14,4]),c('rim_r','rim',[6,3,-2],[2,14,4])]
    return bones,cubes,{'primary_axis':'y','anchors':['grip','block_face'],'target':'shield offhand/block transform'}

def crossbow():
    bones=[b('root',[0,9,0],locators={'grip':[0,7,2],'projectile_origin':[0,12,-12]}),b('stock',[0,9,0],'root'),b('body',[0,12,0],'stock'),b('limb_l',[-1,12,-5],'body'),b('limb_r',[1,12,-5],'body'),b('rail',[0,12,-5],'body')]
    cubes=[c('stock','stock',[-1.5,2,0],[3,13,5],rotation=[25,0,0],pivot=[0,9,1]),c('body','body',[-3,10,-6],[6,5,8]),c('limb_l','limb_l',[-13,11,-7],[12,2.5,2],rotation=[0,-8,-5],pivot=[-1,12,-6]),c('limb_r','limb_r',[1,11,-7],[12,2.5,2],rotation=[0,8,5],pivot=[1,12,-6]),c('rail','rail',[-.7,11,-14],[1.4,2,13])]
    return bones,cubes,{'primary_axis':'z','anchors':['grip','projectile_origin'],'target':'crossbow ranged/display transform'}

def staff():
    bones=[b('root',[0,0,0],locators={'grip':[0,7,0],'cast_origin':[0,30,0]}),b('shaft',[0,0,0],'root'),b('head',[0,25,0],'shaft'),b('core',[0,29,0],'head')]
    cubes=[c('shaft','shaft',[-1,0,-1],[2,26,2]),c('head_cross','head',[-5,25,-1],[10,3,2]),c('head_spine','head',[-1.5,25,-1.5],[3,8,3]),c('core','core',[-2,28,-2],[4,4,4])]
    return bones,cubes,{'primary_axis':'y','anchors':['grip','cast_origin'],'target':'staff/weapon'}
def bow():
    bones=[b('root',[0,12,0],locators={'grip':[0,12,0],'projectile_origin':[0,12,-1]}),b('grip',[0,12,0],'root'),b('upper',[0,13,0],'grip'),b('lower',[0,11,0],'grip')]
    cubes=[c('grip','grip',[-1,9,-1],[2,6,2]),c('upper','upper',[-1,14,-1],[2,12,2],rotation=[0,0,-18],pivot=[0,14,0]),c('lower','lower',[-1,-2,-1],[2,12,2],rotation=[0,0,18],pivot=[0,10,0])]
    return bones,cubes,{'primary_axis':'y','anchors':['grip','projectile_origin'],'target':'bow/ranged item'}
def armor():
    bones=[b('root',[0,0,0]),b('body',[0,18,0],'root'),b('head',[0,28,0],'body'),b('arm_r',[-5,22,0],'body'),b('arm_l',[5,22,0],'body'),b('leg_r',[-2,12,0],'root'),b('leg_l',[2,12,0],'root')]
    cubes=[c('helmet','head',[-4,24,-4],[8,8,8],inflate=.65),c('chest','body',[-4,12,-2],[8,12,4],inflate=.55),c('arm_r_shell','arm_r',[-8,12,-2],[4,12,4],inflate=.5),c('arm_l_shell','arm_l',[4,12,-2],[4,12,4],inflate=.5),c('leg_r_shell','leg_r',[-4,0,-2],[4,12,4],inflate=.45),c('leg_l_shell','leg_l',[0,0,-2],[4,12,4],inflate=.45)]
    return bones,cubes,{'player_oracle':'8x12x4 body, 8x8x8 head, 4x12x4 limbs','target':'wearable armor; map scaffold bones to actual player/Gecko armor rig and test slim/default arms'}
def head_cosmetic():
    bones=[b('root',[0,28,0],locators={'head_origin':[0,28,0]}),b('head',[0,28,0],'root'),b('brim',[0,25,0],'head'),b('crown',[0,28,0],'head'),b('ornament',[0,32,0],'crown')]
    cubes=[c('brim','brim',[-6,24.5,-6],[12,1,12]),c('crown','crown',[-4,25,-4],[8,8,8],inflate=.35),c('ornament','ornament',[-1,33,-1],[2,5,2])]
    return bones,cubes,{'player_oracle':'head centered around y=28','target':'hat/head cosmetic'}
def furniture():
    bones=[b('root',[0,0,0],locators={'placement_origin':[0,0,0],'seat':[0,9,0],'interaction':[0,7,4]}),b('base',[0,0,0],'root'),b('body',[0,4,0],'base'),b('top',[0,12,0],'body'),b('detail',[0,10,0],'body')]
    cubes=[c('base','base',[-6,0,-6],[12,3,12]),c('body','body',[-5,3,-5],[10,9,10]),c('top','top',[-6,12,-6],[12,3,12]),c('detail','detail',[-2,8,-6],[4,4,2])]
    return bones,cubes,{'anchors':['placement_origin','seat','interaction'],'target':'furniture/decor; collision/seat/interact volumes must be authored separately'}
def decor():
    bones=[b('root',[0,0,0],locators={'placement_origin':[0,0,0]}),b('core',[0,6,0],'root'),b('upper',[0,12,0],'core'),b('accent',[4,8,0],'core')]
    cubes=[c('base','root',[-5,0,-5],[10,3,10]),c('core','core',[-4,3,-4],[8,10,8]),c('upper','upper',[-3,13,-3],[6,6,6]),c('accent','accent',[4,7,-2],[4,4,4])]
    return bones,cubes,{'anchors':['placement_origin'],'target':'static/animated decor prop'}

FUNCS={'sword':sword,'dagger':dagger,'greatsword':greatsword,'axe':axe,'mace':mace,'hammer':hammer,'spear':spear,'polearm':polearm,'scythe':scythe,'shield':shield,'crossbow':crossbow,'staff':staff,'bow':bow,'armor':armor,'head_cosmetic':head_cosmetic,'furniture':furniture,'decor':decor}

def pack_uv(cubes,texture,padding,max_size=512):
    w=h=next_pow2(max(16,texture))
    while True:
        attempt=json.loads(json.dumps(cubes)); ok,packed,_,_=pack(attempt,w,h,padding,True)
        if ok: return packed,w,h
        if w>=max_size and h>=max_size: raise ValueError('UV pack exceeded max size')
        if w<=h:w=next_pow2(w+1)
        else:h=next_pow2(h+1)

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--id',required=True);ap.add_argument('--class',dest='klass',choices=sorted(FUNCS),required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--texture',type=int,default=64);ap.add_argument('--uv-padding',type=int,default=1);ap.add_argument('--scale',type=float,default=1.0);a=ap.parse_args()
    bones,cubes,contract=FUNCS[a.klass](); scale=float(a.scale)
    if scale<=0: print('scale must be >0'); return 2
    if abs(scale-1)>1e-9:
        for bone in bones:
            bone['pivot']=[v*scale for v in bone['pivot']]
            if isinstance(bone.get('locators'),dict): bone['locators']={k:[x*scale for x in v] for k,v in bone['locators'].items()}
        for cube in cubes:
            cube['origin']=[v*scale for v in cube['origin']]; cube['size']=[v*scale for v in cube['size']]
            if 'pivot' in cube:cube['pivot']=[v*scale for v in cube['pivot']]
            if 'inflate' in cube:cube['inflate']*=scale
    cubes,w,h=pack_uv(cubes,a.texture,a.uv_padding)
    spec={'schema_version':1,'id':a.id,'archetype':f'reference_{a.klass}','asset_class':a.klass,'texture':{'width':w,'height':h},'bones':bones,'cubes':cubes,'animations':[],'reconstruction_scaffold':{'purpose':'semantic zero-start only; fit/replace geometry from authorized references','runtime_contract':contract}}
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(spec,indent=2)+'\n',encoding='utf-8');print(json.dumps({'result':'pass','class':a.klass,'bones':len(bones),'cubes':len(cubes),'texture':[w,h],'output':str(a.out)},indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
