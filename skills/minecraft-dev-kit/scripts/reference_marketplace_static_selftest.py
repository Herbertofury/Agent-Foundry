#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,shutil,subprocess,sys,tempfile
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from reference_attachment_fit import collect_points,transform_point
from reference_cuboid_fit import project
TOOLS=Path(__file__).resolve().parent
CLASSES=['sword','dagger','greatsword','axe','mace','hammer','spear','polearm','scythe','shield','crossbow','staff','bow','armor','head_cosmetic','furniture','decor']
def run(c,t=45):
    try:return subprocess.run(c,text=True,capture_output=True,timeout=t)
    except subprocess.TimeoutExpired as e:return subprocess.CompletedProcess(c,124,e.stdout or '',(e.stderr or '')+'\nTIMEOUT')
def must(cp,label):
    if cp.returncode:raise RuntimeError(f'{label} rc={cp.returncode}\n{cp.stdout}\n{cp.stderr}')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--keep',type=Path);a=ap.parse_args();r=Path(tempfile.mkdtemp(prefix='market-static-'));out={}
    try:
        for k in CLASSES:
            sp=r/f'{k}.json';must(run([sys.executable,str(TOOLS/'reference_asset_scaffold.py'),'--id',k,'--class',k,'--out',str(sp)]),f'scaffold {k}');must(run([sys.executable,str(TOOLS/'creature_spec_compiler.py'),str(sp),'--validate-only','--report',str(r/f'{k}.md')]),f'compile {k}')
        out['scaffold_classes']=len(CLASSES)
        sword=json.load(open(r/'sword.json'));pts=collect_points(sword);anchor=pts['grip'];aw=np.array([-5.,10.,0.]);scale=1.28;rot=np.array([12.,-28.,-37.]);off=np.array([1.6,2.2,-1.1]);cam={'projection':'perspective','yaw':24,'pitch':-8,'distance':72,'fov':31,'target':[0,16,0]};rows=[]
        for name in ['grip','tip','bone:guard','cube:blade:top','cube:pommel:center']:
            wp=transform_point(pts[name],anchor,aw,scale,rot,off);px=project(wp.reshape(1,3),cam,320,320)[0];rows.append({'point':name,'target_px':px.tolist()})
        tip=transform_point(pts['tip'],anchor,aw,scale,rot,off);m={'anchor':{'asset_point':'grip','player':{'profile':'default','point':'hand_r'}},'camera':cam,'image_width':320,'image_height':320,'screen_constraints':rows,'world_constraints':[{'point':'tip','target_world':tip.tolist(),'weight':.35}],'initial':{'scale':1,'rotation':[0,0,0],'offset':[0,0,0]},'bounds':{'scale':[.6,1.8],'rotation_span':[90,90,90],'offset_span':[6,6,6]},'regularization':{'scale':.001,'rotation':.0001,'offset':.001}};(r/'held.json').write_text(json.dumps(m,indent=2)+'\n');must(run([sys.executable,str(TOOLS/'reference_attachment_fit.py'),str(r/'sword.json'),str(r/'held.json'),'--output',str(r/'held-runtime.json'),'--report',str(r/'held-report.json'),'--min-screen-rmse','.15','--min-world-rmse','.05']),'held fit');hr=json.load(open(r/'held-report.json'));out['held_screen_rmse_px']=hr['screen_rmse_px'];out['held_world_rmse']=hr['world_rmse']
        furn=json.load(open(r/'furniture.json'));fp=collect_points(furn);fa=fp['placement_origin'];wc=[]
        for name in ['seat','interaction']:
            target=transform_point(fp[name],fa,np.zeros(3),1.18,np.array([0.,31.,0.]),np.array([2.,.5,-1.5]));wc.append({'point':name,'target_world':target.tolist()})
        fm={'anchor':{'asset_point':'placement_origin','world':[0,0,0]},'world_constraints':wc,'initial':{'scale':1,'rotation':[0,0,0],'offset':[0,0,0]},'bounds':{'scale':[.7,1.5],'rotation_span':[20,80,20],'offset_span':[5,5,5]},'regularization':{'scale':.0001,'rotation':.0001,'offset':.0001}};(r/'furniture-fit.json').write_text(json.dumps(fm,indent=2)+'\n');must(run([sys.executable,str(TOOLS/'reference_attachment_fit.py'),str(r/'furniture.json'),str(r/'furniture-fit.json'),'--output',str(r/'furniture-runtime.json'),'--report',str(r/'furniture-report.json'),'--min-world-rmse','.02']),'furniture fit');out['furniture_world_rmse']=json.load(open(r/'furniture-report.json'))['world_rmse']
        sheet=Image.new('RGBA',(96,64),(0,0,0,0));d=ImageDraw.Draw(sheet);cols=[(220,70,60,255),(65,190,95,255),(70,110,220,255),(210,165,55,255),(145,75,190,255),(70,185,190,255)]
        for i,col in enumerate(cols):rr=i//3;cc=i%3;x=cc*32;y=rr*32;d.rectangle((x+6,y+6,x+25,y+25),fill=col);d.rectangle((x+12,y+2,x+19,y+29),fill=tuple(max(0,c-25) for c in col[:3])+(255,))
        sheet.save(r/'icons.png');must(run([sys.executable,str(TOOLS/'reference_sprite_extract.py'),str(r/'icons.png'),'--out',str(r/'icons'),'--mode','grid','--rows','2','--cols','3','--target-size','32']),'icons');out['sprite_count']=json.load(open(r/'icons'/'SPRITES.json'))['sprite_count']
        for idx,name in enumerate(['sword','axe','crossbow']):
            im=Image.new('RGBA',(64,64),(60,50,42,255));dd=ImageDraw.Draw(im);dd.rectangle((0,12+idx,63,19+idx),fill=(128,100,65,255));dd.rectangle((0,36-idx,63,43-idx),fill=(188,156,92,255));dd.rectangle((8+idx*9,4,13+idx*9,59),fill=(86+idx*3,70+idx*2,52,255));im.save(r/f'{name}.png')
        good={'style_contract':{'texture_unit':16,'density_ratio_warn':5.0,'clone_shape_distance':.02,'shared_palette_delta_e_warn':50},'assets':[{'id':n,'family':'weapons','palette_family':'metal','spec':f'{n}.json','texture':f'{n}.png','must_be_distinct':True} for n in ['sword','axe','crossbow']]};(r/'good.json').write_text(json.dumps(good,indent=2)+'\n');must(run([sys.executable,str(TOOLS/'reference_pack_consistency_audit.py'),str(r/'good.json'),'--output',str(r/'good-report.json')]),'pack good');shutil.copy2(r/'sword.json',r/'clone.json');shutil.copy2(r/'sword.png',r/'clone.png');bad={'assets':[{'id':'a','family':'set','spec':'sword.json','texture':'sword.png','must_be_distinct':True},{'id':'b','family':'set','spec':'clone.json','texture':'clone.png','must_be_distinct':True}]};(r/'bad.json').write_text(json.dumps(bad)+'\n');bp=run([sys.executable,str(TOOLS/'reference_pack_consistency_audit.py'),str(r/'bad.json'),'--output',str(r/'bad-report.json')]);assert bp.returncode==2;out['pack_clone_negative_rc']=2
        print(json.dumps({'result':'pass',**out},indent=2));
        if a.keep:
            if a.keep.exists():shutil.rmtree(a.keep)
            shutil.copytree(r,a.keep)
        return 0
    except Exception as e:
        print(f'MARKET STATIC SELFTEST FAILED: {e}',file=sys.stderr)
        if a.keep:
            if a.keep.exists():shutil.rmtree(a.keep)
            shutil.copytree(r,a.keep)
        return 2
    finally:shutil.rmtree(r,ignore_errors=True)
if __name__=='__main__':raise SystemExit(main())
