#!/usr/bin/env python3
"""Seed semantic first-pass creature animations from a creature spec rig.

Generated motion is deliberately conservative blockout. Final premium animation requires hand/refined arcs, timing, acting and native visual QA.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
from typing import Any

def k(t,v,lerp=None):
    d={'time':round(float(t),4),'value':[round(float(x),3) for x in v]}
    if lerp:d['lerp']=lerp
    return d

def track(vals,length,loop=True):
    if len(vals)==3:return [k(0,vals[0]),k(length/2,vals[1],'catmullrom'),k(length,vals[2])]
    return [k(i*length/(len(vals)-1),v,'catmullrom' if 0<i<len(vals)-1 else None) for i,v in enumerate(vals)]

def boneset(spec):return {str(b.get('id')) for b in spec.get('bones',[]) if isinstance(b,dict) and b.get('id')}
def add_anim(spec,name,length,loop,tracks,replace):
    arr=spec.setdefault('animations',[]); idx=next((i for i,a in enumerate(arr) if isinstance(a,dict) and a.get('name')==name),None); anim={'name':name,'length':length,'loop':loop,'bones':tracks}
    if idx is None:arr.append(anim)
    elif replace:arr[idx]=anim

def scaled_tracks(tracks, time_scale=1.0, value_scale=1.0):
    out=json.loads(json.dumps(tracks))
    for channels in out.values():
        if not isinstance(channels,dict): continue
        for keys in channels.values():
            if not isinstance(keys,list): continue
            for key in keys:
                if not isinstance(key,dict): continue
                if isinstance(key.get('time'),(int,float)): key['time']=round(float(key['time'])*time_scale,4)
                if isinstance(key.get('value'),list): key['value']=[round(float(v)*value_scale,3) for v in key['value']]
    return out

def humanoid(spec,replace):
    b=boneset(spec); T={}
    if 'torso' in b:T['torso']={'rotation':track([[0,0,0],[2,0,0],[0,0,0]],2)}
    if 'head' in b:T['head']={'rotation':track([[0,-3,0],[-2,3,0],[0,-3,0]],2)}
    for arm,sgn in [('arm_l',1),('arm_r',-1)]:
        if arm in b:T[arm]={'rotation':track([[sgn*2,0,0],[-sgn*2,0,0],[sgn*2,0,0]],2)}
    add_anim(spec,'idle',2,True,T,replace)
    T={}
    for leg,sgn in [('leg_l',1),('leg_r',-1)]:
        if leg in b:T[leg]={'rotation':track([[sgn*28,0,0],[-sgn*28,0,0],[sgn*28,0,0]],1)}
    for arm,sgn in [('arm_l',-1),('arm_r',1)]:
        if arm in b:T[arm]={'rotation':track([[sgn*20,0,0],[-sgn*20,0,0],[sgn*20,0,0]],1)}
    if 'torso' in b:T['torso']={'rotation':track([[0,0,0],[2,0,0],[0,0,0]],1)}
    add_anim(spec,'walk',1,True,T,replace)
    add_anim(spec,'run',.7,True,scaled_tracks(T,.7,1.35),replace)
    add_anim(spec,'hurt',.45,False,{'torso':{'rotation':track([[0,0,0],[12,0,7],[0,0,0]],.45)}} if 'torso' in b else {},replace)
    add_anim(spec,'death',1.1,False,{'root':{'rotation':track([[0,0,0],[0,0,35],[0,0,82]],1.1)}} if 'root' in b else {},replace)

def quadruped(spec,replace):
    b=boneset(spec); T={}
    if 'body' in b:T['body']={'rotation':track([[0,0,0],[2,0,0],[0,0,0]],2)}
    if 'head' in b:T['head']={'rotation':track([[0,-4,0],[-3,4,0],[0,-4,0]],2)}
    tails=sorted(x for x in b if x.startswith('tail'))
    for i,t in enumerate(tails):T[t]={'rotation':track([[0,-6*(i+1),0],[0,6*(i+1),0],[0,-6*(i+1),0]],2)}
    add_anim(spec,'idle',2,True,T,replace)
    T={}
    phase={'leg_fl':1,'leg_br':1,'leg_fr':-1,'leg_bl':-1}
    for leg,sgn in phase.items():
        if leg in b:T[leg]={'rotation':track([[sgn*24,0,0],[-sgn*24,0,0],[sgn*24,0,0]],.9)}
    if 'body' in b:T['body']={'rotation':track([[1,0,0],[-2,0,0],[1,0,0]],.9)}
    add_anim(spec,'walk',.9,True,T,replace)
    add_anim(spec,'run',.62,True,scaled_tracks(T,.62/.9,1.45),replace)
    add_anim(spec,'hurt',.5,False,{'body':{'rotation':track([[0,0,0],[-10,0,8],[0,0,0]],.5)}} if 'body' in b else {},replace)
    add_anim(spec,'death',1.2,False,{'root':{'rotation':track([[0,0,0],[0,0,22],[0,0,76]],1.2)}} if 'root' in b else {},replace)

def avian(spec,replace):
    b=boneset(spec); add_anim(spec,'idle',2,True,{'body':{'position':track([[0,0,0],[0,.35,0],[0,0,0]],2)}} if 'body' in b else {},replace)
    T={}
    for wing,sgn in [('wing_l',1),('wing_r',-1)]:
        if wing in b:T[wing]={'rotation':track([[0,0,sgn*18],[0,0,-sgn*58],[0,0,sgn*18]],.72)}
    if 'body' in b:T['body']={'position':track([[0,0,0],[0,.7,0],[0,0,0]],.72)}
    add_anim(spec,'fly',.72,True,T,replace); add_anim(spec,'hurt',.4,False,{'body':{'rotation':track([[0,0,0],[10,0,14],[0,0,0]],.4)}} if 'body' in b else {},replace); add_anim(spec,'death',1.1,False,{'root':{'rotation':track([[0,0,0],[20,0,25],[50,0,75]],1.1)}} if 'root' in b else {},replace)

def serpentine(spec,replace):
    b=boneset(spec); segs=sorted(x for x in b if x.startswith('body_'));T={}
    for i,s in enumerate(segs):T[s]={'rotation':track([[0,-6*math.sin(i),0],[0,9*math.sin(i+1),0],[0,-6*math.sin(i),0]],1.1)}
    add_anim(spec,'slither',1.1,True,T,replace); add_anim(spec,'idle',2.2,True,{s:{'rotation':track([[0,-2*(i+1),0],[0,2*(i+1),0],[0,-2*(i+1),0]],2.2)} for i,s in enumerate(segs)},replace); add_anim(spec,'hurt',.45,False,{'body_01':{'rotation':track([[0,0,0],[0,18,8],[0,0,0]],.45)}} if 'body_01' in b else {},replace); add_anim(spec,'death',1.4,False,{'root':{'rotation':track([[0,0,0],[0,25,20],[0,60,65]],1.4)}} if 'root' in b else {},replace)

def arthropod(spec,replace):
    b=boneset(spec);T={}
    legs=sorted(x for x in b if x.startswith('leg_'))
    for i,l in enumerate(legs):sgn=1 if i%2==0 else -1;T[l]={'rotation':track([[sgn*18,0,sgn*6],[-sgn*18,0,-sgn*6],[sgn*18,0,sgn*6]],.75)}
    add_anim(spec,'walk',.75,True,T,replace);add_anim(spec,'run',.5,True,scaled_tracks(T,.5/.75,1.35),replace);add_anim(spec,'idle',2,True,{'body':{'position':track([[0,0,0],[0,.2,0],[0,0,0]],2)}} if 'body' in b else {},replace);add_anim(spec,'hurt',.35,False,{'body':{'rotation':track([[0,0,0],[9,0,9],[0,0,0]],.35)}} if 'body' in b else {},replace);add_anim(spec,'death',1,False,{'root':{'rotation':track([[0,0,0],[0,0,35],[0,0,90]],1)}} if 'root' in b else {},replace)

def floating(spec,replace):
    b=boneset(spec);T={}
    if 'body'in b:T['body']={'position':track([[0,0,0],[0,.6,0],[0,0,0]],2),'rotation':track([[0,-3,0],[0,3,0],[0,-3,0]],2)}
    for ring,sgn in [('ring_01',1),('ring_02',-1)]:
        if ring in b:T[ring]={'rotation':track([[0,sgn*8,0],[0,-sgn*8,0],[0,sgn*8,0]],2)}
    add_anim(spec,'idle',2,True,T,replace);add_anim(spec,'hover',1.2,True,scaled_tracks(T,.6,1.0),replace);add_anim(spec,'hurt',.4,False,{'body':{'position':track([[0,0,0],[0,-.8,.5],[0,0,0]],.4)}} if 'body'in b else {},replace);add_anim(spec,'death',1.3,False,{'root':{'position':track([[0,0,0],[0,-3,0],[0,-8,0]],1.3),'rotation':track([[0,0,0],[15,35,0],[35,90,0]],1.3)}} if 'root'in b else {},replace)

def dragon(spec,replace):
    quadruped(spec,replace);b=boneset(spec);T={}
    for wing,sgn in [('wing_l',1),('wing_r',-1)]:
        if wing in b:T[wing]={'rotation':track([[0,0,sgn*15],[0,0,-sgn*55],[0,0,sgn*15]],.9)}
    if 'body' in b:T['body']={'position':track([[0,0,0],[0,.8,0],[0,0,0]],.9)}
    add_anim(spec,'fly',.9,True,T,replace)

GEN={'humanoid':humanoid,'quadruped':quadruped,'avian':avian,'serpentine':serpentine,'arthropod':arthropod,'floating':floating,'dragon_or_multi_limb':dragon}
def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('spec',type=Path);ap.add_argument('--output',type=Path);ap.add_argument('--archetype',choices=GEN);ap.add_argument('--replace',action='store_true');a=ap.parse_args();s=json.loads(a.spec.read_text(encoding='utf-8'));arch=a.archetype or s.get('archetype')
    if arch not in GEN:print(f'Unsupported/missing archetype {arch!r}');return 2
    GEN[arch](s,a.replace);out=a.output or a.spec.with_name(a.spec.stem+'.animated.json');out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(s,indent=2)+'\n',encoding='utf-8');print(json.dumps({'result':'pass','archetype':arch,'output':str(out),'animations':[x.get('name') for x in s.get('animations',[]) if isinstance(x,dict)]},indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
