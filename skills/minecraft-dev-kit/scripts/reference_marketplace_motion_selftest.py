#!/usr/bin/env python3
from __future__ import annotations
import argparse,copy,json,shutil,subprocess,sys,tempfile
from pathlib import Path
import cv2,numpy as np
from PIL import Image
from reference_cuboid_fit import render_mask,render_wireframe
TOOLS=Path(__file__).resolve().parent
def run(c,t=60):
    try:return subprocess.run(c,text=True,capture_output=True,timeout=t)
    except subprocess.TimeoutExpired as e:return subprocess.CompletedProcess(c,124,e.stdout or '',(e.stderr or '')+'\nTIMEOUT')
def must(cp,label):
    if cp.returncode:raise RuntimeError(f'{label} rc={cp.returncode}\n{cp.stdout}\n{cp.stderr}')
def ingest(p,o):must(run([sys.executable,str(TOOLS/'reference_media_ingest.py'),str(p),'--out',str(o)]),'ingest');return next(o.glob('*/manifest.json'))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--keep',type=Path);a=ap.parse_args();r=Path(tempfile.mkdtemp(prefix='market-motion-'));out={}
    try:
        truth={'schema_version':1,'id':'p','texture':{'width':64,'height':64},'bones':[{'id':'root','pivot':[0,0,0]}],'cubes':[{'id':'body','bone':'root','origin':[-4,0,-3],'size':[8,10,6],'uv':[0,0]},{'id':'head','bone':'root','origin':[-3,10,-4],'size':[6,5,7],'uv':[30,0]},{'id':'horn','bone':'root','origin':[1,15,-2],'size':[2,4,2],'uv':[0,20]}],'animations':[]};fs=[]
        for yaw in range(0,360,45):c={'projection':'perspective','yaw':yaw,'pitch':0,'distance':72,'fov':30,'target':[0,9.5,0]};m=render_mask(truth,c,(144,144));x=np.zeros((144,144,4),np.uint8);x[:,:,:3]=[110,85,155];x[:,:,3]=m;fs.append(Image.fromarray(x,'RGBA'))
        g=r/'turn.gif';fs[0].save(g,save_all=True,append_images=fs[1:],duration=70,loop=0,disposal=2);mm=ingest(g,r/'ti');cal=r/'cal.json';must(run([sys.executable,str(TOOLS/'reference_turntable_calibrate.py'),str(mm),'--output',str(cal),'--bounds-min','-6','-1','-6','--bounds-max','6','20','6','--subject-height','19','--count','8','--projection','perspective','--fov','30','--target','0','9.5','0']),'calibrate');cd=json.load(open(cal));hm={'id':'h','bounds':cd['bounds'],'voxel':1.0,'references':[{'id':x['id'],'mask':x['mask'],'camera':x['camera']} for x in cd['references']]};(r/'hm.json').write_text(json.dumps(hm,indent=2)+'\n');must(run([sys.executable,str(TOOLS/'reference_visual_hull.py'),str(r/'hm.json'),'--output',str(r/'hull.json'),'--report',str(r/'hr.json'),'--min-iou','.88']),'hull');out['perspective_turntable_hull_iou']=json.load(open(r/'hr.json'))['mean_iou']
        spec={'schema_version':1,'id':'m','texture':{'width':64,'height':64},'bones':[{'id':'root','pivot':[0,0,0]},{'id':'plate','parent':'root','pivot':[0,9,3.1],'_fit_translation':[0,0,0]}],'cubes':[{'id':'body','bone':'root','origin':[-7,0,-3],'size':[14,18,6],'uv':[0,0]},{'id':'plate','bone':'plate','origin':[-1.5,7,3.05],'size':[3,4,.5],'uv':[40,0]}],'animations':[]};(r/'spec.json').write_text(json.dumps(spec,indent=2)+'\n');cam={'projection':'orthographic','yaw':0,'pitch':0,'ortho_scale':26,'target':[0,9,0]};ff=[]
        for pos in [-3,0,2.5,0,-3]:ss=copy.deepcopy(spec);ss['bones'][1]['_fit_translation']=[pos,0,0];m=render_mask(ss,cam,(112,112));e=render_wireframe(ss,cam,(112,112));x=np.zeros((112,112,4),np.uint8);x[:,:,:3]=[70,90,120];x[:,:,3]=m;x[e>0,:3]=[235,220,150];ff.append(Image.fromarray(x,'RGBA'))
        mg=r/'motion.gif';ff[0].save(mg,save_all=True,append_images=ff[1:],duration=70,loop=0,disposal=2);mi=ingest(mg,r/'mi');cfg={'camera':cam,'animation_name':'slide','selected_frames':list(range(5)),'parameters':[{'target':'bone/plate/position/0','min':-4,'max':4}],'edge_weight':2,'edge_tolerance':2,'min_edge_f1':.94,'min_frame_iou':.99};(r/'cfg.json').write_text(json.dumps(cfg,indent=2)+'\n');must(run([sys.executable,str(TOOLS/'reference_pose_sequence_fit.py'),str(r/'spec.json'),str(mi),str(r/'cfg.json'),'--output',str(r/'anim.json'),'--report',str(r/'mr.json'),'--maxiter','35','--popsize','6']),'internal motion');mr=json.load(open(r/'mr.json'));out['internal_motion_iou']=mr['mean_iou'];out['internal_motion_edge_f1']=mr['mean_geometry_edge_f1']
        print(json.dumps({'result':'pass',**out},indent=2));
        if a.keep:
            if a.keep.exists():shutil.rmtree(a.keep)
            shutil.copytree(r,a.keep)
        return 0
    except Exception as e:
        print(f'MARKET MOTION SELFTEST FAILED: {e}',file=sys.stderr)
        if a.keep:
            if a.keep.exists():shutil.rmtree(a.keep)
            shutil.copytree(r,a.keep)
        return 2
    finally:shutil.rmtree(r,ignore_errors=True)
if __name__=='__main__':raise SystemExit(main())
