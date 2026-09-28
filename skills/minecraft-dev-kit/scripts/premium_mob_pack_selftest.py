#!/usr/bin/env python3
"""Self-test the premium mob-pack production toolchain with positive and adversarial fixtures."""
from __future__ import annotations
import argparse, json, math, shutil, struct, subprocess, sys, tempfile, wave
from pathlib import Path
from PIL import Image, ImageDraw


def run(cmd:list[str], timeout:int=90)->subprocess.CompletedProcess[str]:
    return subprocess.run(cmd,text=True,capture_output=True,timeout=timeout)


def make_fixture(root:Path)->Path:
    (root/'models').mkdir(parents=True); (root/'specs').mkdir(); (root/'encounters').mkdir(); (root/'textures').mkdir(); (root/'sounds').mkdir()
    vfx_defs={}; sfx_defs={}
    roles=['assassin','tank','ranged-pressure','caster','support-healer','summoner-controller']
    entities=[]
    for i in range(6):
        eid=f'boss_{i+1:02d}'; anim_names=['idle','walk','hurt','death','phase_transition']+[f'attack_{n:02d}' for n in range(1,11)]+['dodge_left','dodge_right','spawn']
        attacks=[]
        for n in range(1,11):
            aid=f'attack_{n:02d}'; windup=[0.2,0.3,0.4][(n+i)%3]
            purpose=['fast_check','heavy','gap_closer','anti_flank','ranged_pressure','area_denial','interrupt_punish','summon_control','defensive_counter','phase_signature'][n-1]
            mx=[2.5,3.5,8.0,3.0,12.0,6.0,5.0,10.0,3.0,8.0][n-1]
            attacks.append({'id':aid,'animation':aid,'windup':windup,'active':0.1,'recovery':0.35+(n%2)*0.15,'hitbox':{'shape':'arc' if (n+i)%2 else 'line','range':3+(n%3)},'cooldown':1.5+n*0.1,'vfx':f'{eid}_vfx_{n:02d}','sfx':f'{eid}_sfx_{((n-1)%8)+1:02d}','telegraph':'pose+sound+effect','interrupt_policy':'phase-aware','impact_marker':f'impact_{n:02d}','vfx_marker':f'vfx_{n:02d}','sfx_marker':f'sfx_{n:02d}','purpose':purpose,'selection':{'min_range':0.0 if n in {1,2,4,9} else 1.5,'max_range':mx,'weight':1.0+(n%3)*0.25,'phases':[1,2] if n not in {10} else [2],'max_repeat':1}})
        ent={'id':eid,'name':f'Original Test Boss {i+1}','kind':'boss','role':roles[i],'archetype':f'archetype_{i+1}','variants':['base', {'id':'elite','changes':['silhouette','materials']}],'model_file':f'models/{eid}.bbmodel','creature_spec':f'specs/{eid}.creature.json','encounter_file':f'encounters/{eid}.encounter.json','texture_files':[f'textures/{eid}.png'],'emissive_file':f'textures/{eid}_emissive.png','animations':anim_names,'phases':2,'attacks':attacks,'vfx':[f'{eid}_vfx_{n:02d}' for n in range(1,11)],'sfx':[f'{eid}_sfx_{n:02d}' for n in range(1,9)],'ai_features':['distance-aware-selection','directional-reposition','target-hysteresis','anti-stuck','phase-cleanup','multiplayer-target-distribution',f'role-{roles[i]}'],'performance':{'bone_budget':16,'cube_budget':48,'max_vfx_concurrency':12,'max_sfx_concurrency':12},'runtime':{'dimensions':[1.4,2.6],'tracking_range':12,'update_interval':3,'attributes':{'max_health':260+i*25,'movement_speed':0.27,'attack_damage':10+i,'armor':8+i},'spawn':{'mode':'encounter-only'},'persistence':'boss','synced_fields':['combat_state','phase','stagger'],'boss_bar':{'enabled':True,'style':'progress'},'scaling':{'enabled':True,'health_per_extra_player':0.35,'stagger_per_extra_player':0.20}}}
        entities.append(ent)
        # Deterministic pixel-art fixture texture: test data only, not a quality claim.
        base=(42+i*8, 48+i*5, 54+i*4, 255); hi=(90+i*6, 98+i*4, 106+i*3, 255); accent=(80+i*12, 150-i*7, 120+i*5, 255)
        tex=Image.new('RGBA',(64,64),(0,0,0,0)); dr=ImageDraw.Draw(tex); dr.rectangle((0,0,63,31),fill=base); dr.rectangle((0,32,63,63),fill=hi)
        for q in range(0,64,8): dr.rectangle((q,8+(q//8)%3*4,min(63,q+3),11+(q//8)%3*4),fill=accent)
        tex.save(root/ent['texture_files'][0])
        em=Image.new('RGBA',(64,64),(0,0,0,0)); de=ImageDraw.Draw(em); de.rectangle((24,20,31,27),fill=accent); em.save(root/ent['emissive_file'])
        # Tiny deterministic WAV prototypes for file/variation contract testing.
        boss_sound_dir=root/'sounds'/eid; boss_sound_dir.mkdir(parents=True,exist_ok=True)
        wavs=[]
        for vi,freq in enumerate((95+i*7, 118+i*5),1):
            wp=boss_sound_dir/f'impact_{vi}.wav'; sr=22050; dur=.22
            with wave.open(str(wp),'wb') as wf:
                wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
                frames=[]
                for si in range(int(sr*dur)):
                    t=si/sr; env=max(0,1-t/dur); val=math.sin(2*math.pi*freq*t)*env*.55
                    frames.append(struct.pack('<h',int(val*32767)))
                wf.writeframes(b''.join(frames))
            wavs.append(str(wp.relative_to(root)))
        for si in range(1,9):
            sid=f'{eid}_sfx_{si:02d}'; sfx_defs[sid]={'role':'impact','files':wavs,'spatialized':True,'volume':1.0,'pitch_range':[0.96,1.04],'max_concurrency':6,'cooldown':0.05,'variation_group':f'{eid}_impact'}
        for atk in attacks:
            hr=float(atk['hitbox']['range']); vfx_defs[atk['vfx']]={'family':'selftest-role','coverage':'hitbox-aligned','anticipation':'charge-ring','action':'arc-trail','impact':'burst','aftermath':'embers','impact_radius':hr,'telegraph_radius':hr,'max_concurrency':6,'locator':'vfx_origin','motif':'role accent geometric burst'}
        # Minimal bbmodel-like asset for model/animation closure and complexity checks.
        bb={'meta':{'format_version':'4.10'},'elements':[{'uuid':f'{eid}-cube-{c}','name':f'cube_{c}','from':[0,0,0],'to':[1,1,1]} for c in range(20)],'groups':[{'uuid':f'{eid}-bone-{b}','name':f'bone_{b}','origin':[0,0,0],'children':[]} for b in range(8)],'animations':[{'name':n,'length':1.0,'animators':{}} for n in anim_names]}
        (root/ent['model_file']).write_text(json.dumps(bb,indent=2)+'\n')
        bones=[{'id':'root','pivot':[0,0,0]},{'id':'pelvis','parent':'root','pivot':[0,9,0]},{'id':'torso','parent':'pelvis','pivot':[0,14,0],'locators':{'vfx_origin':[0,4,-3]}},{'id':'head','parent':'torso','pivot':[0,20,0]},{'id':'arm_l','parent':'torso','pivot':[5,18,0]},{'id':'arm_r','parent':'torso','pivot':[-5,18,0],'locators':{'weapon':[-1,-5,0]}},{'id':'leg_l','parent':'pelvis','pivot':[2,9,0]},{'id':'leg_r','parent':'pelvis','pivot':[-2,9,0]}]
        cubes=[{'id':'pelvis_cube','bone':'pelvis','origin':[-3,7,-2],'size':[6,4,4],'uv':[0,0]},{'id':'torso_cube','bone':'torso','origin':[-4,10,-3],'size':[8,9,6],'uv':[0,8]},{'id':'head_cube','bone':'head','origin':[-3,18,-3],'size':[6,6,6],'uv':[28,0]},{'id':'arm_l_cube','bone':'arm_l','origin':[4,10,-2],'size':[3,8,4],'uv':[0,28]},{'id':'arm_r_cube','bone':'arm_r','origin':[-7,10,-2],'size':[3,8,4],'uv':[14,28]},{'id':'leg_l_cube','bone':'leg_l','origin':[1,0,-2],'size':[3,9,4],'uv':[28,28]},{'id':'leg_r_cube','bone':'leg_r','origin':[-4,0,-2],'size':[3,9,4],'uv':[42,28]}]
        cubes.append({'id':f'role_attachment_{i+1}','bone':'torso','origin':[4+i*0.5,15+i*0.25,-2],'size':[1.5+i*0.35,2.0+(i%3),1.5+(i%2)*0.4],'uv':[48,48]})
        attack_by={a['animation']:a for a in attacks}; anims=[]
        for idx,name in enumerate(anim_names):
            loop=name in {'idle','walk'}; length=2.0 if name=='idle' else 1.0 if name=='walk' else 1.2 if name=='phase_transition' else 0.9; markers=[]
            atk=attack_by.get(name)
            if atk:
                w=atk['windup']; markers=[{'id':atk['vfx_marker'],'time':max(0,w-0.04),'kind':'vfx'},{'id':atk['sfx_marker'],'time':max(0,w-0.02),'kind':'sfx'},{'id':atk['impact_marker'],'time':w,'kind':'damage'}]
            amp=4+idx%6; times=[0.0,length/2,length]
            def keys(vals): return [{'time':t,'value':v,**({'lerp':'catmullrom'} if k==1 else {})} for k,(t,v) in enumerate(zip(times,vals))]
            if loop:
                vals=[[[0,0,0],[amp,0,0],[0,0,0]],[[0,0,0],[-amp/2,amp/3,0],[0,0,0]],[[0,0,0],[amp*2,0,0],[0,0,0]],[[0,0,0],[-amp*2,0,0],[0,0,0]]]
            else:
                vals=[[[0,0,0],[-amp*2,amp,0],[amp/2,0,0]],[[0,0,0],[amp,0,0],[0,0,0]],[[0,0,0],[-amp*3,0,amp],[amp,0,0]],[[0,0,0],[amp*3,0,-amp],[-amp,0,0]]]
            tracks={bn:{'rotation':keys(v)} for bn,v in zip(['torso','head','arm_l','arm_r'],vals)}
            if name=='walk': tracks.update({'leg_l':{'rotation':keys([[25,0,0],[-25,0,0],[25,0,0]])},'leg_r':{'rotation':keys([[-25,0,0],[25,0,0],[-25,0,0]])}})
            anims.append({'name':name,'length':length,'loop':loop,'markers':markers,'bones':tracks})
        spec={'schema_version':1,'id':eid,'texture':{'width':64,'height':64},'visible_bounds':{'width':3.0,'height':3.2,'offset':[0,1.2,0]},'bones':bones,'cubes':cubes,'animations':anims}
        (root/ent['creature_spec']).write_text(json.dumps(spec,indent=2)+'\n')
        ids=[a['id'] for a in attacks]
        graph={'schema_version':1,'entity':eid,'entry':'prebattle','states':[{'id':'prebattle','kind':'setup','transitions':[{'to':'phase_1','when':'prebattle_complete'}]},{'id':'phase_1','kind':'combat','attacks':ids[:7],'transitions':[{'to':'phase_transition','when':'health_ratio<=0.5'},{'to':'death','when':'health<=0'}]},{'id':'phase_transition','kind':'phase_transition','transitions':[{'to':'phase_2','when':'transition_animation_complete'}]},{'id':'phase_2','kind':'combat','attacks':ids[3:],'transitions':[{'to':'death','when':'health<=0'}]},{'id':'death','kind':'death','transitions':[]}]}
        (root/ent['encounter_file']).write_text(json.dumps(graph,indent=2)+'\n')
    manifest={'schema_version':1,'pack':{'id':'premium_selftest','name':'Premium Selftest','profile':'boss-mega-2026','minecraft':'1.20.1','loader':'Forge','version':'test'},'art_direction':{'fantasy':'Original selftest faction','silhouette_language':'strong class-role silhouettes','palette_rules':'shared dark neutral base plus unique role accent','material_language':'metal cloth bone crystal by role','texture_density':'32x hero density','scale_ladder':'humanoid elites through oversized boss forms','variant_rule':'variants change silhouette and material treatment'},'entities':entities,'vfx_definitions':vfx_defs,'sfx_definitions':sfx_defs,'sidecars':{'equipment':['a','b'],'drops':['c','d'],'props':['e','f'],'items':[]},'controls':{'tuning':['health','damage','cooldowns','stagger','spawn'],'documentation':['install','configuration','developer notes']},'qa':{'native_client':True,'dedicated_server':True,'stress':{'simultaneous_entities':24},'visual_showcase':True}}
    mp=root/'premium-mob-pack.json'; mp.write_text(json.dumps(manifest,indent=2)+'\n'); return mp


def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--keep',type=Path); a=ap.parse_args(); base=Path(tempfile.mkdtemp(prefix='premium-mob-selftest-'))
    try:
        manifest=make_fixture(base); out=base/'out'; script=Path(__file__).resolve().parent/'premium_mob_pack_pipeline.py'; p=run([sys.executable,str(script),str(manifest),'--root',str(base),'--out',str(out),'--strict'])
        if p.returncode!=0: print('POSITIVE FIXTURE FAILED\n'+p.stdout+p.stderr); return 2
        # Adversarial impact-timing test must fail.
        bad=json.loads(manifest.read_text()); bad['entities'][0]['attacks'][0]['windup']=0.8; badp=base/'bad.json'; badp.write_text(json.dumps(bad,indent=2)+'\n')
        marker=run([sys.executable,str(Path(__file__).resolve().parent/'mob_event_marker_audit.py'),str(badp),'--root',str(base)])
        if marker.returncode==0: print('NEGATIVE MARKER FIXTURE FALSE-PASSED'); return 2
        tools=Path(__file__).resolve().parent; author=base/'authoring'; author.mkdir()
        block=run([sys.executable,str(tools/'creature_blockout_generator.py'),'--id','selftest-author','--archetype','humanoid','--out',str(author/'base.json'),'--height','26','--width','9','--depth','7'])
        motion=run([sys.executable,str(tools/'creature_animation_blockout.py'),str(author/'base.json'),'--output',str(author/'animated.json')]) if block.returncode==0 else block
        comp=run([sys.executable,str(tools/'creature_spec_compiler.py'),str(author/'animated.json'),'--validate-only']) if motion.returncode==0 else motion
        block2=run([sys.executable,str(tools/'creature_blockout_generator.py'),'--id','selftest-author-heavy','--archetype','humanoid','--out',str(author/'heavy.json'),'--height','30','--width','12','--depth','8','--mass','top_heavy'])
        retarget=run([sys.executable,str(tools/'creature_animation_retarget.py'),str(author/'animated.json'),str(author/'heavy.json'),'--output',str(author/'retarget.json'),'--position-scale','1.15']) if comp.returncode==0 and block2.returncode==0 else block2
        recomp=run([sys.executable,str(tools/'creature_spec_compiler.py'),str(author/'retarget.json'),'--validate-only']) if retarget.returncode==0 else retarget
        recipe=author/'materials.json'; recipe.write_text(json.dumps({'default_material':'hide','materials':{'hide':{'ramp':['#20282a','#3b474a','#647477','#93a2a4'],'pattern':'organic'},'magic':{'ramp':['#12352e','#1f725e','#39c49d','#9bffdc'],'emissive':True}},'assign':{'head':'magic'}},indent=2)+'\n')
        tex=run([sys.executable,str(tools/'creature_texture_blockout.py'),str(author/'base.json'),str(recipe),'--output',str(author/'blockout.png'),'--emissive',str(author/'blockout_emissive.png')]) if block.returncode==0 else block
        sfx=run([sys.executable,str(tools/'procedural_sfx_blockout.py'),'--kind','impact','--duration','0.2','--seed','7','--output',str(author/'impact.wav')])
        authoring={'blockout':block.returncode,'motion_seed':motion.returncode,'compile':comp.returncode,'retarget':retarget.returncode,'retarget_compile':recomp.returncode,'texture_blockout':tex.returncode,'sfx_blockout':sfx.returncode}
        if any(v!=0 for v in authoring.values()): print('AUTHORING SELFTEST FAILED\n'+json.dumps(authoring,indent=2)); return 2
        receipt=json.loads((out/'PIPELINE-RECEIPT.json').read_text())
        print(json.dumps({'result':'pass','pipeline':receipt['result'],'jobs':[(j['name'],j['returncode']) for j in receipt['jobs']],'authoring':authoring,'negative_marker_rc':marker.returncode},indent=2))
        if a.keep:
            if a.keep.exists(): shutil.rmtree(a.keep)
            shutil.copytree(base,a.keep)
        return 0
    finally:
        shutil.rmtree(base,ignore_errors=True)

if __name__=='__main__': raise SystemExit(main())
