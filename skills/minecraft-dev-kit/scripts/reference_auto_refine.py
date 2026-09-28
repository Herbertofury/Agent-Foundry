#!/usr/bin/env python3
"""Automatically refine a cuboid creature/reference scaffold against calibrated views.

The refiner performs conservative coordinate descent: optional camera fit, then one cube
at a time, fitting only world axes whose unit vectors visibly move in at least one supplied
camera. This avoids random drift along single-view depth. It accepts only objective
improvements and preserves a full iteration ledger.
"""
from __future__ import annotations
import argparse,copy,json,math
from pathlib import Path
from typing import Any
import numpy as np
from reference_cuboid_fit import fit, project


def volume(c:dict)->float:
    try:return float(np.prod(np.abs(np.asarray(c.get('size',[0,0,0]),float))))
    except:return 0.0

def observable_axes(refs:list[dict])->list[int]:
    obs=[]
    for axis in range(3):
        visible=False
        for r in refs:
            cam=r.get('camera',{}); p=np.zeros((2,3),float);p[1,axis]=1.0
            q=project(p,cam,256,256); disp=float(np.linalg.norm(q[1]-q[0]))
            if disp>.25: visible=True;break
        if visible:obs.append(axis)
    return obs

def eval_cfg(spec,cfg,root):
    ss,rep,_=fit(spec,{**cfg,'parameters':[]},root,1,3,1337)
    return float(rep['optimizer']['cost']),rep

def camera_params(refs,yaw_span,pitch_span,scale_factor,offset_span):
    params=[];seen=set()
    for r in refs:
        cam=r.get('camera',{});cid=str(cam.get('id','view'))
        if cid in seen:continue
        seen.add(cid)
        y=float(cam.get('yaw',0));p=float(cam.get('pitch',0));sc=float(cam.get('ortho_scale',32));ox=float(cam.get('offset_x',0));oy=float(cam.get('offset_y',0))
        params += [
          {'target':f'camera/{cid}/yaw','min':y-yaw_span,'max':y+yaw_span},
          {'target':f'camera/{cid}/pitch','min':p-pitch_span,'max':p+pitch_span},
          {'target':f'camera/{cid}/ortho_scale','min':max(.1,sc/scale_factor),'max':sc*scale_factor},
          {'target':f'camera/{cid}/offset_x','min':ox-offset_span,'max':ox+offset_span},
          {'target':f'camera/{cid}/offset_y','min':oy-offset_span,'max':oy+offset_span},
        ]
    return params

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('spec',type=Path);ap.add_argument('references',type=Path,help='JSON with references[] compatible with reference_cuboid_fit');ap.add_argument('--output',type=Path,required=True);ap.add_argument('--report',type=Path,required=True);ap.add_argument('--passes',type=int,default=2);ap.add_argument('--maxiter',type=int,default=14);ap.add_argument('--popsize',type=int,default=6);ap.add_argument('--size-factor',type=float,default=1.65);ap.add_argument('--origin-fraction',type=float,default=.55);ap.add_argument('--auto-camera',action='store_true');ap.add_argument('--yaw-span',type=float,default=8);ap.add_argument('--pitch-span',type=float,default=8);ap.add_argument('--camera-scale-factor',type=float,default=1.22);ap.add_argument('--offset-span',type=float,default=10);ap.add_argument('--include',nargs='*');ap.add_argument('--min-iou',type=float,default=.90);ap.add_argument('--seed',type=int,default=1701);a=ap.parse_args()
    spec=json.loads(a.spec.read_text(encoding='utf-8'));rcfg=json.loads(a.references.read_text(encoding='utf-8'));refs=copy.deepcopy(rcfg.get('references',[]))
    if not isinstance(refs,list) or not refs:print('references[] required');return 2
    cfg={'references':refs};root=a.references.parent;axes=observable_axes(refs);ledger=[];current=copy.deepcopy(spec);cost,baseline=eval_cfg(current,cfg,root);start_cost=cost
    # Camera fit as one group. Persist fitted cameras back into each reference by id.
    if a.auto_camera:
        params=camera_params(refs,a.yaw_span,a.pitch_span,a.camera_scale_factor,a.offset_span)
        candidate,rep,_=fit(current,{**cfg,'parameters':params},root,a.maxiter,a.popsize,a.seed)
        nc=float(rep['optimizer']['cost']);accepted=nc+1e-8<cost;ledger.append({'stage':'camera','cost_before':cost,'cost_after':nc,'accepted':accepted,'parameters':rep.get('parameters',[])})
        if accepted:
            cost=nc; cams=rep.get('cameras',{}); 
            for r in refs:
                cid=str(r.get('camera',{}).get('id','view'))
                if cid in cams:r['camera']=cams[cid]
            cfg={'references':refs}
    include=set(a.include or [])
    cubes=[c for c in current.get('cubes',[]) if isinstance(c,dict) and c.get('id') and (not include or str(c['id']) in include)]
    cubes=sorted(cubes,key=lambda c:(-volume(c),str(c['id'])))
    for pass_i in range(max(1,a.passes)):
        improved=0
        for ci,cube in enumerate(cubes):
            cid=str(cube['id']); live=next((x for x in current.get('cubes',[]) if str(x.get('id'))==cid),None)
            if live is None:continue
            params=[]
            for axis in axes:
                size=float(live.get('size',[1,1,1])[axis]); origin=float(live.get('origin',[0,0,0])[axis]); span=max(.75,abs(size)*a.origin_fraction)
                params.append({'target':f'cube/{cid}/origin/{axis}','min':origin-span,'max':origin+span})
                params.append({'target':f'cube/{cid}/size/{axis}','min':max(.25,abs(size)/a.size_factor),'max':max(.5,abs(size)*a.size_factor)})
            if not params:continue
            candidate,rep,_=fit(current,{**cfg,'parameters':params},root,a.maxiter,a.popsize,a.seed+pass_i*1000+ci)
            nc=float(rep['optimizer']['cost']);accepted=nc+1e-7<cost
            ledger.append({'stage':f'pass{pass_i+1}:{cid}','cost_before':round(cost,8),'cost_after':round(nc,8),'accepted':accepted,'view_metrics':rep.get('views',[]),'parameters':rep.get('parameters',[])})
            if accepted:current=candidate;cost=nc;improved+=1
        if improved==0:break
    final_cost,final=eval_cfg(current,cfg,root);mean_iou=float(np.mean([v['iou'] for v in final.get('views',[])])) if final.get('views') else 0.0;passed=mean_iou>=a.min_iou
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(current,indent=2)+'\n',encoding='utf-8');report={'result':'pass' if passed else 'fail','observable_axes':axes,'start_cost':round(start_cost,8),'final_cost':round(final_cost,8),'mean_iou':round(mean_iou,6),'min_iou':a.min_iou,'passes_requested':a.passes,'cube_count':len(cubes),'ledger':ledger,'final_views':final.get('views',[]),'output':str(a.output),'note':'Only parameters observable in supplied projections are auto-fit. Hidden depth/concavities remain inferred; review semantics/pivots and native runtime.'};a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({'result':report['result'],'mean_iou':report['mean_iou'],'start_cost':report['start_cost'],'final_cost':report['final_cost'],'observable_axes':axes,'output':str(a.output)},indent=2));return 0 if passed else 2
if __name__=='__main__':raise SystemExit(main())
