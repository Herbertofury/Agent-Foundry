#!/usr/bin/env python3
"""Convert a staged turntable GIF into calibrated multiview silhouette references.

The user/contract supplies world bounds/height and the assumption that the GIF is a
turntable. Yaw is inferred from frame time around one 360-degree loop. Framing/ortho
scale/distance are estimated from staged silhouette bbox evidence. Orthographic and
perspective turntables are supported; camera fitting should refine the seed when the preview
uses nonuniform angular speed, camera orbit pitch, lens changes, or animation during spin.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np


def vec3(x,name):
    if not isinstance(x,list) or len(x)!=3 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in x): raise ValueError(f'{name} must be 3 finite numbers')
    return [float(v) for v in x]


def select_even(frames:list[dict],count:int)->list[int]:
    n=len(frames); count=max(2,min(count,n))
    return sorted(set(round(i*(n-1)/max(1,count-1)) for i in range(count)))


def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('media_manifest',type=Path); ap.add_argument('--output',type=Path,required=True); ap.add_argument('--bounds-min',nargs=3,type=float,required=True); ap.add_argument('--bounds-max',nargs=3,type=float,required=True); ap.add_argument('--count',type=int,default=8); ap.add_argument('--start-yaw',type=float,default=0.0); ap.add_argument('--direction',choices=['cw','ccw'],default='cw'); ap.add_argument('--pitch',type=float,default=0.0); ap.add_argument('--roll',type=float,default=0.0); ap.add_argument('--projection',choices=['orthographic','perspective'],default='orthographic'); ap.add_argument('--ortho-scale',type=float,default=0.0,help='orthographic: 0 infers scale from median bbox height and subject-height'); ap.add_argument('--fov',type=float,default=35.0,help='perspective vertical/horizontal approximation in the Dev Kit projector'); ap.add_argument('--distance',type=float,default=0.0,help='perspective camera distance; 0 infers from subject-height, FOV and bbox height'); ap.add_argument('--subject-height',type=float,default=0.0,help='world-space visible subject height; 0 uses bounds height'); ap.add_argument('--target',nargs=3,type=float); a=ap.parse_args()
    d=json.loads(a.media_manifest.read_text(encoding='utf-8')); frames=d.get('frames',[])
    if not isinstance(frames,list) or len(frames)<2: print('turntable calibration needs >=2 frames'); return 2
    bmin=np.asarray(a.bounds_min,dtype=float); bmax=np.asarray(a.bounds_max,dtype=float)
    if np.any(bmax<=bmin): print('invalid bounds'); return 2
    target=np.asarray(a.target if a.target else ((bmin+bmax)/2).tolist(),dtype=float); bounds_h=float(bmax[1]-bmin[1]); subject_h=float(a.subject_height) if a.subject_height>0 else bounds_h; width,height=map(int,d.get('size',[0,0]))
    if width<=0 or height<=0: print('media size missing'); return 2
    selected=select_even(frames,a.count); bbox_heights=[max(1,int(frames[i]['bbox'][3]-frames[i]['bbox'][1])) for i in selected if frames[i].get('bbox')]
    bbox_centers=[[(float(frames[i]['bbox'][0])+float(frames[i]['bbox'][2]))/2.0,(float(frames[i]['bbox'][1])+float(frames[i]['bbox'][3]))/2.0] for i in selected if frames[i].get('bbox')]
    if not bbox_heights: print('selected frames have no foreground bboxes'); return 2
    median_h=float(np.median(bbox_heights)); ortho=float(a.ortho_scale) if a.ortho_scale>0 else subject_h*width/max(1.0,median_h)
    fov=float(a.fov)
    if not (1.0 < fov < 170.0): print('fov must be between 1 and 170 degrees'); return 2
    focal=0.5*width/math.tan(math.radians(fov)/2.0)
    distance=float(a.distance) if a.distance>0 else subject_h*focal/max(1.0,median_h)
    # A true turntable keeps the camera framing fixed. Use one global frame offset
    # from the median silhouette-box center across the full rotation so asymmetric
    # shape mass at a particular yaw cannot masquerade as per-frame camera motion.
    global_center=np.median(np.asarray(bbox_centers,dtype=float),axis=0) if bbox_centers else np.asarray([width/2,height/2],dtype=float)
    global_offset=[float(global_center[0]-width/2),float(global_center[1]-height/2)]
    total=int(d.get('total_duration_ms_staged',0))
    if total<=0: total=max(1,len(frames))
    sign=1.0 if a.direction=='cw' else -1.0
    media_root=a.media_manifest.parent.parent; refs=[]
    for idx in selected:
        f=frames[idx]; frac=(float(f.get('time_ms',idx))/total) if int(d.get('total_duration_ms_staged',0))>0 else idx/len(frames)
        yaw=(a.start_yaw+sign*360.0*frac)%360.0; cent=f.get('centroid') or [width/2,height/2]; bbox=f.get('bbox')
        # Frame by silhouette-box center, not mass centroid: asymmetric shapes legitimately
        # have an off-center centroid even when the camera itself is perfectly centered.
        if bbox: box_center=[(float(bbox[0])+float(bbox[2]))/2.0,(float(bbox[1])+float(bbox[3]))/2.0]
        else: box_center=cent
        cam={'id':f'turn_{idx:04d}','projection':a.projection,'yaw':round(yaw,6),'pitch':float(a.pitch),'roll':float(a.roll),'target':[round(float(x),6) for x in target], 'offset_x':round(global_offset[0],4),'offset_y':round(global_offset[1],4)}
        if a.projection=='perspective': cam.update({'distance':round(distance,6),'fov':round(fov,6)})
        else: cam['ortho_scale']=round(ortho,6)
        refs.append({'id':cam['id'],'frame':idx,'time_ms':int(f.get('time_ms',0)),'mask':str((media_root/str(f['mask'])).resolve()),'edges':str((media_root/str(f['edges'])).resolve()),'camera':cam,'bbox':bbox,'centroid':cent,'bbox_center':box_center})
    out={'schema_version':1,'source':d.get('source'),'bounds':{'min':bmin.tolist(),'max':bmax.tolist()},'selected_frames':selected,'projection':a.projection,'inferred_ortho_scale':round(ortho,6) if a.projection=='orthographic' else None,'inferred_distance':round(distance,6) if a.projection=='perspective' else None,'fov':round(fov,6) if a.projection=='perspective' else None,'subject_height':round(subject_h,6),'global_offset_px':[round(global_offset[0],4),round(global_offset[1],4)],'yaw_rule':{'start_yaw':a.start_yaw,'direction':a.direction,'assumption':'one uniform 360-degree turn over staged GIF duration'},'references':refs,'warnings':['Turntable assumption must be true. Refine camera parameters if angular speed, orbit pitch, lens, target, or pose changes during the spin.']}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8'); print(json.dumps({'result':'pass','selected_frames':selected,'projection':a.projection,'ortho_scale':round(ortho,6) if a.projection=='orthographic' else None,'distance':round(distance,6) if a.projection=='perspective' else None,'fov':round(fov,6) if a.projection=='perspective' else None,'output':str(a.output)},indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
