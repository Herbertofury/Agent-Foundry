#!/usr/bin/env python3
"""Advanced regression for premium image/GIF inverse-reconstruction additions."""
from __future__ import annotations
import argparse,copy,json,shutil,subprocess,sys,tempfile
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
from reference_cuboid_fit import render_mask,render_wireframe

TOOLS=Path(__file__).resolve().parent

def run(args:list[str],timeout:int=240)->subprocess.CompletedProcess[str]:
    try:return subprocess.run(args,text=True,capture_output=True,timeout=timeout)
    except subprocess.TimeoutExpired as e:return subprocess.CompletedProcess(args,124,e.stdout or '',(e.stderr or '')+'\nTIMEOUT')
def must(cp,label):
    if cp.returncode!=0:raise RuntimeError(f'{label} rc={cp.returncode}\n{cp.stdout}\n{cp.stderr}')
def stage_gif(gif:Path,out:Path)->Path:
    must(run([sys.executable,str(TOOLS/'reference_media_ingest.py'),str(gif),'--out',str(out)]),'media ingest');return next(out.glob('*/manifest.json'))

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--keep',type=Path);a=ap.parse_args();root=Path(tempfile.mkdtemp(prefix='reference-advanced-selftest-'));results={}
    try:
        # 1 semantic non-creature scaffolds must compile structurally.
        matrix={}
        for k in ['sword','staff','bow','armor','head_cosmetic','furniture','decor']:
            sp=root/f'{k}.json';must(run([sys.executable,str(TOOLS/'reference_asset_scaffold.py'),'--id',f'test_{k}','--class',k,'--out',str(sp)]),f'scaffold {k}')
            rp=root/f'{k}.report.md';must(run([sys.executable,str(TOOLS/'creature_spec_compiler.py'),str(sp),'--validate-only','--report',str(rp)]),f'compile {k}');matrix[k]='pass'
        results['scaffolds']=matrix

        # 2 constant-camera turntable -> calibrated visual hull.
        truth={'schema_version':1,'id':'turntruth','texture':{'width':64,'height':64},'bones':[{'id':'root','pivot':[0,0,0]}],'cubes':[{'id':'body','bone':'root','origin':[-4,0,-3],'size':[8,10,6],'uv':[0,0]},{'id':'head','bone':'root','origin':[-3,10,-4],'size':[6,5,7],'uv':[30,0]},{'id':'horn','bone':'root','origin':[1,15,-2],'size':[2,4,2],'uv':[0,20]}],'animations':[]}
        turn=[]
        for yaw in range(0,360,45):
            cam={'id':f'y{yaw}','projection':'orthographic','yaw':yaw,'pitch':0,'ortho_scale':28,'target':[0,9.5,0]};m=render_mask(truth,cam,(160,160));rgba=np.zeros((160,160,4),np.uint8);rgba[:,:,:3]=[80,130,180];rgba[:,:,3]=m;turn.append(Image.fromarray(rgba,'RGBA'))
        gif=root/'turn.gif';turn[0].save(gif,save_all=True,append_images=turn[1:],duration=70,loop=0,disposal=2);manifest=stage_gif(gif,root/'turn-ingest');cal=root/'turntable.json'
        must(run([sys.executable,str(TOOLS/'reference_turntable_calibrate.py'),str(manifest),'--output',str(cal),'--bounds-min','-6','-1','-6','--bounds-max','6','20','6','--subject-height','19','--count','8','--target','0','9.5','0']),'turntable calibrate')
        cd=json.loads(cal.read_text());hm=root/'hull-manifest.json';hm.write_text(json.dumps({'id':'turn-hull','bounds':cd['bounds'],'voxel':1.0,'references':[{'id':x['id'],'mask':x['mask'],'camera':x['camera']} for x in cd['references']]},indent=2)+'\n');hr=root/'hull-report.json'
        must(run([sys.executable,str(TOOLS/'reference_visual_hull.py'),str(hm),'--output',str(root/'hull.json'),'--report',str(hr),'--min-iou','.93']),'turntable hull');hrep=json.loads(hr.read_text());assert hrep['mean_iou']>=.93;results['turntable_hull_iou']=hrep['mean_iou']

        # 3 internal geometry edges constrain a detail fully inside the silhouette.
        detail={'schema_version':1,'id':'detail','texture':{'width':64,'height':64},'bones':[{'id':'root','pivot':[0,0,0]}],'cubes':[{'id':'body','bone':'root','origin':[-5,0,-3],'size':[10,14,6],'uv':[0,0]},{'id':'plate','bone':'root','origin':[1,5,3.05],'size':[3,4,.5],'uv':[40,0]}],'animations':[]};cam={'id':'front','projection':'orthographic','yaw':0,'pitch':0,'ortho_scale':24,'target':[0,7,0]};cv2.imwrite(str(root/'detail-mask.png'),render_mask(detail,cam,(160,160)));cv2.imwrite(str(root/'detail-edges.png'),render_wireframe(detail,cam,(160,160)));start=copy.deepcopy(detail);start['cubes'][1]['origin'][:2]=[-3,2];(root/'detail-start.json').write_text(json.dumps(start,indent=2)+'\n');(root/'detail-fit.json').write_text(json.dumps({'references':[{'id':'front','mask':'detail-mask.png','edges':'detail-edges.png','edge_weight':1.0,'camera':cam}],'parameters':[{'target':'cube/plate/origin/0','min':-4,'max':3},{'target':'cube/plate/origin/1','min':1,'max':9}]},indent=2)+'\n');dr=root/'detail-report.json'
        must(run([sys.executable,str(TOOLS/'reference_cuboid_fit.py'),str(root/'detail-start.json'),str(root/'detail-fit.json'),'--out-spec',str(root/'detail-fitted.json'),'--report',str(dr),'--maxiter','35','--popsize','6','--min-iou','.99']),'detail fit');drep=json.loads(dr.read_text());assert drep['views'][0]['geometry_edge_f1']>.98;results['internal_geometry_edge_f1']=drep['views'][0]['geometry_edge_f1']

        # 4 translation animation fit.
        ps={'schema_version':1,'id':'move','texture':{'width':32,'height':32},'bones':[{'id':'root','pivot':[0,0,0]}],'cubes':[{'id':'body','bone':'root','origin':[-3,0,-2],'size':[6,10,4],'uv':[0,0]}],'animations':[]};(root/'move-spec.json').write_text(json.dumps(ps,indent=2)+'\n');pcam={'id':'ref','projection':'orthographic','yaw':0,'pitch':0,'ortho_scale':24,'target':[0,5,0]};fs=[]
        for x in [-3,0,4,0,-3]:
            ss=copy.deepcopy(ps);ss['bones'][0]['_fit_translation']=[x,0,0];m=render_mask(ss,pcam,(112,112));rgba=np.zeros((112,112,4),np.uint8);rgba[:,:,:3]=[110,170,90];rgba[:,:,3]=m;fs.append(Image.fromarray(rgba,'RGBA'))
        mg=root/'move.gif';fs[0].save(mg,save_all=True,append_images=fs[1:],duration=70,loop=0,disposal=2);mm=stage_gif(mg,root/'move-ingest');mc={'camera':pcam,'animation_name':'move','selected_frames':list(range(5)),'parameters':[{'target':'bone/root/position/0','min':-5,'max':5}],'min_frame_iou':.97,'loop':True};(root/'move-config.json').write_text(json.dumps(mc,indent=2)+'\n');mr=root/'move-report.json';must(run([sys.executable,str(TOOLS/'reference_pose_sequence_fit.py'),str(root/'move-spec.json'),str(mm),str(root/'move-config.json'),'--output',str(root/'move-anim.json'),'--report',str(mr),'--maxiter','35','--popsize','6']),'position fit');mrep=json.loads(mr.read_text());assert mrep['mean_iou']>.98;results['position_fit_iou']=mrep['mean_iou']

        # 5 flow partition should find a fast independently moving region.
        parts=[]
        for x in [0,5,10,5,0]:
            im=Image.new('RGBA',(112,112),(255,255,255,0));d=ImageDraw.Draw(im);d.rectangle((36,30,72,90),fill=(90,120,160,255));d.rectangle((68+x,40,88+x,53),fill=(190,80,70,255));parts.append(im)
        pg=root/'parts.gif';parts[0].save(pg,save_all=True,append_images=parts[1:],duration=70,loop=0,disposal=2);pm=stage_gif(pg,root/'parts-ingest');pr=root/'partition.json';must(run([sys.executable,str(TOOLS/'reference_motion_partition.py'),str(pm),'--output',str(pr),'--labels',str(root/'partition.png'),'--clusters','3','--min-motion','.2']),'motion partition');prep=json.loads(pr.read_text());fast=max(x['mean_speed'] for x in prep['clusters']);assert fast>3;results['fast_motion_cluster_speed']=fast

        # 6 de-light draft reduces smooth illumination variation.
        h=w=48;base=np.zeros((h,w,3),np.float32);base[:,:24]=[120,70,45];base[:,24:]=[45,95,145];y,x=np.indices((h,w));shade=.62+.72*x/(w-1)+.1*np.sin(y/8);img=np.clip(base*shade[:,:,None],0,255).astype(np.uint8);Image.fromarray(np.dstack([img,np.full((h,w),255,np.uint8)]),'RGBA').save(root/'lit.png');Image.fromarray(np.full((h,w),255,np.uint8),'L').save(root/'cov.png');tr=root/'delight.json';must(run([sys.executable,str(TOOLS/'reference_texture_delight.py'),str(root/'lit.png'),'--coverage',str(root/'cov.png'),'--output',str(root/'albedo.png'),'--report',str(tr),'--palette','8','--sigma','6']),'delight');trep=json.loads(tr.read_text());assert trep['draft_luma_std']<trep['input_luma_std'];results['delight_luma_std']=[trep['input_luma_std'],trep['draft_luma_std']]

        # 7 automatic single-view sword refinement should not drift hidden depth.
        sword=root/'sword.json';must(run([sys.executable,str(TOOLS/'reference_asset_scaffold.py'),'--id','sword','--class','sword','--out',str(sword)]),'sword scaffold');truth_s=json.loads(sword.read_text())
        for q in truth_s['cubes']:
            if q['id']=='blade':q['size'][0]=4.4;q['size'][1]=22;q['origin'][0]=-2.2
            if q['id']=='guard':q['size'][0]=14;q['origin'][0]=-7
        scam={'id':'front','projection':'orthographic','yaw':0,'pitch':0,'ortho_scale':38,'target':[0,13,0]};cv2.imwrite(str(root/'sword-mask.png'),render_mask(truth_s,scam,(192,192)));cv2.imwrite(str(root/'sword-edges.png'),render_wireframe(truth_s,scam,(192,192)));refs={'references':[{'id':'front','mask':'sword-mask.png','edges':'sword-edges.png','edge_weight':.7,'camera':scam}]};(root/'sword-refs.json').write_text(json.dumps(refs,indent=2)+'\n');ar=root/'auto-report.json';must(run([sys.executable,str(TOOLS/'reference_auto_refine.py'),str(sword),str(root/'sword-refs.json'),'--output',str(root/'sword-fitted.json'),'--report',str(ar),'--passes','2','--maxiter','10','--popsize','5','--include','blade','guard','--min-iou','.96']),'auto refine');arep=json.loads(ar.read_text());assert arep['mean_iou']>.98 and arep['observable_axes']==[0,1];results['auto_refine_iou']=arep['mean_iou'];results['auto_refine_axes']=arep['observable_axes']

        print(json.dumps({'result':'pass',**results},indent=2))
        if a.keep:
            if a.keep.exists():shutil.rmtree(a.keep)
            shutil.copytree(root,a.keep)
        return 0
    except Exception as e:
        print(f'ADVANCED RECONSTRUCTION SELFTEST FAILED: {e}',file=sys.stderr)
        if a.keep:
            if a.keep.exists():shutil.rmtree(a.keep)
            shutil.copytree(root,a.keep)
        return 2
    finally:shutil.rmtree(root,ignore_errors=True)
if __name__=='__main__':raise SystemExit(main())
