#!/usr/bin/env python3
"""Regression for premium marketplace image/GIF reconstruction breadth.

Protects the vendor-style frontier: weapon/armor/prop scaffolds, context transforms,
perspective turntables, internal-motion edges, icon sheets, and pack anti-clone/style QA.
"""
from __future__ import annotations

import argparse, copy, json, shutil, subprocess, sys, tempfile
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw

from reference_attachment_fit import collect_points, transform_point
from reference_cuboid_fit import project, render_mask, render_wireframe

TOOLS=Path(__file__).resolve().parent
CLASSES=['sword','dagger','greatsword','axe','mace','hammer','spear','polearm','scythe','shield','crossbow','staff','bow','armor','head_cosmetic','furniture','decor']

def run(cmd:list[str],timeout:int=180)->subprocess.CompletedProcess[str]:
    try:return subprocess.run(cmd,text=True,capture_output=True,timeout=timeout)
    except subprocess.TimeoutExpired as e:return subprocess.CompletedProcess(cmd,124,e.stdout or '',(e.stderr or '')+'\nTIMEOUT')
def must(cp,label):
    if cp.returncode!=0:raise RuntimeError(f'{label} rc={cp.returncode}\n{cp.stdout}\n{cp.stderr}')
def ingest(gif:Path,out:Path)->Path:
    must(run([sys.executable,str(TOOLS/'reference_media_ingest.py'),str(gif),'--out',str(out)]),'ingest');return next(out.glob('*/manifest.json'))

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--keep',type=Path);a=ap.parse_args();root=Path(tempfile.mkdtemp(prefix='reference-marketplace-selftest-'));result={}
    try:
        # Semantic breadth.
        for klass in CLASSES:
            sp=root/f'{klass}.json';must(run([sys.executable,str(TOOLS/'reference_asset_scaffold.py'),'--id',klass,'--class',klass,'--out',str(sp)]),f'scaffold {klass}')
            must(run([sys.executable,str(TOOLS/'creature_spec_compiler.py'),str(sp),'--validate-only','--report',str(root/f'{klass}.md')]),f'compile {klass}')
        result['scaffold_classes']=len(CLASSES)

        # Held-item context inverse transform from player hand + preview landmarks.
        sword=json.load(open(root/'sword.json'));pts=collect_points(sword);anchor=pts['grip'];anchor_world=np.array([-5.,10.,0.]);scale=1.28;rot=np.array([12.,-28.,-37.]);off=np.array([1.6,2.2,-1.1]);cam={'id':'preview','projection':'perspective','yaw':24,'pitch':-8,'distance':72,'fov':31,'target':[0,16,0]};rows=[]
        for name in ['grip','tip','bone:guard','cube:blade:top','cube:pommel:center']:
            wp=transform_point(pts[name],anchor,anchor_world,scale,rot,off);px=project(wp.reshape(1,3),cam,320,320)[0];rows.append({'id':name,'point':name,'target_px':px.tolist()})
        tipw=transform_point(pts['tip'],anchor,anchor_world,scale,rot,off);mf={'context':'third_person_mainhand','anchor':{'asset_point':'grip','player':{'profile':'default','point':'hand_r'}},'camera':cam,'image_width':320,'image_height':320,'screen_constraints':rows,'world_constraints':[{'point':'tip','target_world':tipw.tolist(),'weight':.35}],'initial':{'scale':1,'rotation':[0,0,0],'offset':[0,0,0]},'bounds':{'scale':[.6,1.8],'rotation_span':[90,90,90],'offset_span':[6,6,6]},'regularization':{'scale':.001,'rotation':.0001,'offset':.001}};(root/'held.json').write_text(json.dumps(mf,indent=2)+'\n');must(run([sys.executable,str(TOOLS/'reference_attachment_fit.py'),str(root/'sword.json'),str(root/'held.json'),'--output',str(root/'held-runtime.json'),'--report',str(root/'held-report.json'),'--min-screen-rmse','.15','--min-world-rmse','.05']),'held context');hr=json.load(open(root/'held-report.json'));result['held_screen_rmse_px']=hr['screen_rmse_px'];result['held_world_rmse']=hr['world_rmse']

        # Furniture 3D anchor context fit.
        furn=json.load(open(root/'furniture.json'));fp=collect_points(furn);fa=fp['placement_origin'];fscale=1.18;frot=np.array([0.,31.,0.]);foff=np.array([2.0,.5,-1.5]);wc=[]
        for name in ['seat','interaction']:
            target=transform_point(fp[name],fa,np.zeros(3),fscale,frot,foff);wc.append({'point':name,'target_world':target.tolist()})
        fm={'context':'furniture','anchor':{'asset_point':'placement_origin','world':[0,0,0]},'world_constraints':wc,'initial':{'scale':1,'rotation':[0,0,0],'offset':[0,0,0]},'bounds':{'scale':[.7,1.5],'rotation_span':[20,80,20],'offset_span':[5,5,5]},'regularization':{'scale':.0001,'rotation':.0001,'offset':.0001}};(root/'furniture-fit.json').write_text(json.dumps(fm,indent=2)+'\n');must(run([sys.executable,str(TOOLS/'reference_attachment_fit.py'),str(root/'furniture.json'),str(root/'furniture-fit.json'),'--output',str(root/'furniture-runtime.json'),'--report',str(root/'furniture-report.json'),'--min-world-rmse','.02']),'furniture context');fr=json.load(open(root/'furniture-report.json'));result['furniture_world_rmse']=fr['world_rmse']

        # Perspective turntable seed -> multiview visual hull.
        truth={'schema_version':1,'id':'persp','texture':{'width':64,'height':64},'bones':[{'id':'root','pivot':[0,0,0]}],'cubes':[{'id':'body','bone':'root','origin':[-4,0,-3],'size':[8,10,6],'uv':[0,0]},{'id':'head','bone':'root','origin':[-3,10,-4],'size':[6,5,7],'uv':[30,0]},{'id':'horn','bone':'root','origin':[1,15,-2],'size':[2,4,2],'uv':[0,20]}],'animations':[]};frames=[]
        for yaw in range(0,360,45):
            c={'projection':'perspective','yaw':yaw,'pitch':0,'distance':72,'fov':30,'target':[0,9.5,0]};m=render_mask(truth,c,(160,160));rgba=np.zeros((160,160,4),np.uint8);rgba[:,:,:3]=[110,85,155];rgba[:,:,3]=m;frames.append(Image.fromarray(rgba,'RGBA'))
        tg=root/'turn.gif';frames[0].save(tg,save_all=True,append_images=frames[1:],duration=70,loop=0,disposal=2);tm=ingest(tg,root/'turn-ingest');cal=root/'turntable.json';must(run([sys.executable,str(TOOLS/'reference_turntable_calibrate.py'),str(tm),'--output',str(cal),'--bounds-min','-6','-1','-6','--bounds-max','6','20','6','--subject-height','19','--count','8','--projection','perspective','--fov','30','--target','0','9.5','0']),'perspective turntable');cd=json.load(open(cal));hm={'id':'ph','bounds':cd['bounds'],'voxel':1.0,'references':[{'id':x['id'],'mask':x['mask'],'camera':x['camera']} for x in cd['references']]};(root/'hull-manifest.json').write_text(json.dumps(hm,indent=2)+'\n');must(run([sys.executable,str(TOOLS/'reference_visual_hull.py'),str(root/'hull-manifest.json'),'--output',str(root/'hull-spec.json'),'--report',str(root/'hull-report.json'),'--min-iou','.88']),'perspective hull');ph=json.load(open(root/'hull-report.json'));result['perspective_turntable_hull_iou']=ph['mean_iou']

        # Internal motion with unchanged silhouette must fit from edge evidence.
        ms={'schema_version':1,'id':'internal-motion','texture':{'width':64,'height':64},'bones':[{'id':'root','pivot':[0,0,0]},{'id':'plate','parent':'root','pivot':[0,9,3.1],'_fit_translation':[0,0,0]}],'cubes':[{'id':'body','bone':'root','origin':[-7,0,-3],'size':[14,18,6],'uv':[0,0]},{'id':'plate','bone':'plate','origin':[-1.5,7,3.05],'size':[3,4,.5],'uv':[40,0]}],'animations':[]};(root/'motion-spec.json').write_text(json.dumps(ms,indent=2)+'\n');mcam={'id':'ref','projection':'orthographic','yaw':0,'pitch':0,'ortho_scale':26,'target':[0,9,0]};mframes=[]
        for x in [-3,0,2.5,0,-3]:
            ss=copy.deepcopy(ms);ss['bones'][1]['_fit_translation']=[x,0,0];m=render_mask(ss,mcam,(128,128));e=render_wireframe(ss,mcam,(128,128));rgba=np.zeros((128,128,4),np.uint8);rgba[:,:,:3]=[70,90,120];rgba[:,:,3]=m;rgba[e>0,:3]=[235,220,150];mframes.append(Image.fromarray(rgba,'RGBA'))
        mg=root/'internal.gif';mframes[0].save(mg,save_all=True,append_images=mframes[1:],duration=70,loop=0,disposal=2);mm=ingest(mg,root/'motion-ingest');mc={'camera':mcam,'animation_name':'plate_slide','selected_frames':list(range(5)),'parameters':[{'target':'bone/plate/position/0','min':-4,'max':4}],'edge_weight':2.0,'edge_tolerance':2,'min_edge_f1':.94,'min_frame_iou':.99,'loop':True};(root/'motion-config.json').write_text(json.dumps(mc,indent=2)+'\n');must(run([sys.executable,str(TOOLS/'reference_pose_sequence_fit.py'),str(root/'motion-spec.json'),str(mm),str(root/'motion-config.json'),'--output',str(root/'motion-animation.json'),'--report',str(root/'motion-report.json'),'--maxiter','45','--popsize','7']),'internal motion');imr=json.load(open(root/'motion-report.json'));result['internal_motion_edge_f1']=imr['mean_geometry_edge_f1']

        # Grid sprite/icon extraction.
        sheet=Image.new('RGBA',(96,64),(0,0,0,0));d=ImageDraw.Draw(sheet);colors=[(220,70,60,255),(65,190,95,255),(70,110,220,255),(210,165,55,255),(145,75,190,255),(70,185,190,255)]
        for i,color in enumerate(colors):rr=i//3;cc=i%3;x=cc*32;y=rr*32;d.rectangle((x+6,y+6,x+25,y+25),fill=color);d.rectangle((x+12,y+2,x+19,y+29),fill=tuple(max(0,c-25) for c in color[:3])+(255,))
        sheet.save(root/'icons.png');must(run([sys.executable,str(TOOLS/'reference_sprite_extract.py'),str(root/'icons.png'),'--out',str(root/'icons'),'--mode','grid','--rows','2','--cols','3','--target-size','32','--prefix','skill']),'sprite extract');icons=json.load(open(root/'icons'/'SPRITES.json'));assert icons['sprite_count']==6;result['sprite_count']=6

        # Coherent pack passes; declared-distinct clone fails.
        for idx,name in enumerate(['sword','axe','crossbow']):
            im=Image.new('RGBA',(64,64),(60,50,42,255));dd=ImageDraw.Draw(im);dd.rectangle((0,12+idx,63,19+idx),fill=(128,100,65,255));dd.rectangle((0,36-idx,63,43-idx),fill=(188,156,92,255));dd.rectangle((8+idx*9,4,13+idx*9,59),fill=(86+idx*3,70+idx*2,52,255));im.save(root/f'{name}.png')
        good={'style_contract':{'texture_unit':16,'density_ratio_warn':5.0,'clone_shape_distance':.02,'shared_palette_delta_e_warn':50},'assets':[{'id':'sword','family':'weapons','palette_family':'metal','spec':'sword.json','texture':'sword.png','must_be_distinct':True},{'id':'axe','family':'weapons','palette_family':'metal','spec':'axe.json','texture':'axe.png','must_be_distinct':True},{'id':'crossbow','family':'weapons','palette_family':'metal','spec':'crossbow.json','texture':'crossbow.png','must_be_distinct':True}]};(root/'pack-good.json').write_text(json.dumps(good,indent=2)+'\n');must(run([sys.executable,str(TOOLS/'reference_pack_consistency_audit.py'),str(root/'pack-good.json'),'--output',str(root/'pack-good-report.json')]),'pack good')
        shutil.copy2(root/'sword.json',root/'sword-clone.json');shutil.copy2(root/'sword.png',root/'sword-clone.png');bad={'assets':[{'id':'a','family':'set','spec':'sword.json','texture':'sword.png','must_be_distinct':True},{'id':'b','family':'set','spec':'sword-clone.json','texture':'sword-clone.png','must_be_distinct':True}]};(root/'pack-bad.json').write_text(json.dumps(bad,indent=2)+'\n');bp=run([sys.executable,str(TOOLS/'reference_pack_consistency_audit.py'),str(root/'pack-bad.json'),'--output',str(root/'pack-bad-report.json')]);assert bp.returncode==2;result['pack_clone_negative_rc']=bp.returncode

        out={'result':'pass',**result};print(json.dumps(out,indent=2))
        if a.keep:
            if a.keep.exists():shutil.rmtree(a.keep)
            shutil.copytree(root,a.keep)
        return 0
    except Exception as exc:
        print(f'MARKETPLACE RECONSTRUCTION SELFTEST FAILED: {exc}',file=sys.stderr)
        if a.keep:
            if a.keep.exists():shutil.rmtree(a.keep)
            shutil.copytree(root,a.keep)
        return 2
    finally:shutil.rmtree(root,ignore_errors=True)
if __name__=='__main__':raise SystemExit(main())
