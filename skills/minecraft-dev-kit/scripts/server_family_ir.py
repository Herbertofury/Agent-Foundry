#!/usr/bin/env python3
"""Build category-aware semantic IR for recognized server-plugin config families.

This sits between broad discovery and dedicated vendor adapters. It normalizes common semantic
surfaces while preserving all unmatched key paths so a family parser can never silently erase
vendor-specific behavior.
"""
from __future__ import annotations
import argparse,json,re
from pathlib import Path
import adjacent_plugin_ir as base

REGISTRY=base.REGISTRY
SUPPORTED={
 'weapons':'weapons','npc':'npc-story','quests-story':'npc-story','dungeons':'npc-story','scripting':'npc-story',
 'hud-ui':'presentation','holograms':'presentation','menus-ui':'presentation','scoreboard-nametag':'presentation','chat':'presentation','entity-presentation':'presentation',
 'rpg-progression':'rpg','enchantments':'rpg','magic':'magic','mobs-skills':'mobs','pets-mounts':'pet-vehicle','vehicles':'pet-vehicle',
 'economy-shop':'economy-loot','crates-loot':'economy-loot','fishing':'economy-loot','crafting':'economy-loot','food-drink':'economy-loot',
 'worldgen':'world','structures':'world','survival-overhaul':'world','world-management':'world','world-tools':'world','protection':'world','teleport':'world',
 'furniture':'custom-content','events':'custom-content','minigame':'custom-content','resource-pack':'resource-pack','bedrock-bridge':'resource-pack','custom-content':'custom-content','cosmetics':'presentation',
 'models-animation':'models-animation','effects-vfx':'presentation','skins':'presentation','presentation':'presentation','server-list':'presentation',
 'scripting':'scripting',
}
FIELDS={
 'models-animation':{
  'source_geometry':['bbmodel','fmmodel','model','geometry','cube','mesh','element','outliner'],
  'hierarchy_pivots':['group','bone','parent','child','pivot','origin','rotation','scale'],
  'uv_textures':['uv','texture','material','atlas','emissive','transparent','palette'],
  'animation':['animation','keyframe','timeline','interpolation','bezier','catmull','loop','length'],
  'runtime_nodes':['locator','hitbox','mount','seat','nameplate','leash','display','billboard'],
  'states_controllers':['state','controller','molang','condition','transition','priority'],
 },
 'scripting':{
  'triggers':['trigger','event','on ','when ','listener','command'],
  'conditions':['condition','if ','else','requirement','permission','chance'],
  'actions':['action','do ','execute','run','command','task','wait','delay'],
  'variables':['variable','flag','metadata','storage','score','placeholder'],
  'entity_item':['entity','npc','mob','player','item','block','inventory','equipment'],
  'world':['world','location','region','biome','teleport','spawn'],
  'visual_audio':['model','texture','animation','particle','effect','sound','hologram','hud'],
  'integration':['mythic','citizens','vault','placeholder','protocol','worldguard','api','hook'],
 },
 'weapons':{
  'identity':['weapon','gun','id','name','material','item_model','custom_model_data','model'],
  'damage':['damage','headshot','critical','armor','penetration','knockback'],
  'projectile':['projectile','bullet','hitscan','velocity','gravity','range','spread'],
  'fire_control':['trigger','fire_mode','burst','automatic','semi','rate','fire_rate','shoot'],
  'ammo_reload':['ammo','magazine','clip','reload','capacity','durability'],
  'recoil_accuracy':['recoil','spread','accuracy','bloom','shake'],
  'scope':['scope','zoom','ads','sights'],
  'effects':['sound','particle','muzzle','trail','explosion','effect'],
  'actions':['command','mechanic','ability','condition','permission','cooldown'],
 },
 'npc-story':{
  'identity':['npc','citizen','entity','type','name','uuid','skin','texture','profile'],
  'appearance':['equipment','pose','variant','model','disguise','hologram','nameplate'],
  'location_navigation':['location','world','position','path','navigate','destination','waypoint','teleport'],
  'dialogue':['dialog','conversation','speaker','message','text','choice','option'],
  'flow':['quest','stage','objective','condition','event','action','trigger','branch','next','entry'],
  'cinematic':['camera','cinematic','cutscene','timeline','animation'],
  'rewards':['reward','item','money','experience','xp','command','permission'],
  'combat_ai':['ai','goal','target','damage','skill','spell','trait','sentinel'],
 },
 'presentation':{
  'layout':['layout','position','offset','anchor','align','width','height','scale','layer','priority'],
  'visual':['image','texture','font','glyph','icon','model','material','color','gradient','animation','frame'],
  'content':['text','line','title','description','motd','favicon','lore','head','item','block','hologram','scoreboard','nametag'],
  'visibility':['condition','permission','world','range','viewer','placeholder','update'],
  'interaction':['click','action','command','menu','slot','button','event'],
  'resource_pack':['resourcepack','resource_pack','pack','namespace','shader'],
 },
 'rpg':{
  'skills':['skill','class','profession','tree','level','xp','experience','source'],
  'stats':['stat','attribute','modifier','health','mana','stamina','strength','defense'],
  'abilities':['ability','power','trigger','effect','condition','cooldown','cost'],
  'progression':['reward','requirement','unlock','permission','prestige','rank'],
  'items':['item','equipment','weapon','armor','material','model','recipe','loot'],
  'economy':['money','currency','price','cost','vault','points'],
 },
 'magic':{
  'spell_identity':['spell','wand','path','class','school','icon','material','model'],
  'casting':['cast','trigger','target','range','cooldown','cost','mana','duration'],
  'effects':['effect','particle','sound','projectile','damage','potion','entity','block'],
  'logic':['condition','requirement','action','command','permission','world'],
 },
 'mobs':{
  'identity':['mob','entity','type','name','level','variant','model','disguise'],
  'spawning':['spawn','biome','world','region','chance','weight','limit','despawn'],
  'ai':['ai','goal','target','faction','threat','follow','patrol'],
  'combat':['damage','health','armor','skill','ability','attack','projectile','cooldown'],
  'loot':['drop','loot','item','experience','xp','money','reward'],
  'presentation':['bossbar','hologram','nameplate','particle','sound','animation'],
 },
 'pet-vehicle':{
  'identity':['pet','vehicle','mount','model','skin','variant','type','name'],
  'ownership':['owner','permission','summon','dismiss','tame','follow','stay'],
  'attachment':['seat','passenger','driver','locator','offset','hitbox'],
  'movement':['speed','acceleration','turn','steer','jump','fly','hover','physics'],
  'resources':['fuel','health','durability','inventory','storage','upgrade'],
  'effects':['sound','particle','animation','state','emote'],
 },
 'economy-loot':{
  'identity':['item','fish','crate','shop','recipe','drink','loot','reward','id','name'],
  'item_data':['material','model','custom_model_data','component','lore','enchant','nbt'],
  'economy':['price','cost','sell','buy','money','currency','points','vault'],
  'logic':['chance','weight','rarity','condition','requirement','permission','cooldown'],
  'rewards':['reward','drop','loot','command','experience','xp'],
  'crafting':['recipe','ingredient','result','station','smelt','brew'],
 },
 'world':{
  'world_identity':['world','dimension','generator','preset','seed','environment'],
  'biomes':['biome','climate','temperature','precipitation'],
  'terrain':['terrain','noise','height','cave','ore','feature'],
  'structures':['structure','schematic','loot','spawn','dungeon','room'],
  'regions':['region','claim','plot','boundary','flag'],
  'resource':['block','item','material','entity','mob'],
 },
 'resource-pack':{
  'delivery':['url','hash','sha1','pack','resourcepack','resource_pack','host','priority','required','prompt'],
  'merge':['merge','cluster','path','zip','conflict','namespace','priority'],
  'bedrock':['bedrock','geyser','floodgate','mapping','attachable','geometry'],
  'assets':['model','texture','font','sound','shader','item_model','custom_model_data'],
 },
 'custom-content':{
  'identity':['item','block','furniture','entity','id','name','namespace','material'],
  'visual':['model','texture','item_model','custom_model_data','font','sound','particle'],
  'behavior':['behavior','behaviour','mechanic','event','trigger','condition','action','ability'],
  'physical':['hitbox','collision','seat','storage','light','hardness','tool'],
  'crafting_loot':['recipe','ingredient','drop','loot','reward'],
 },
}

def words(s):return ' '.join(re.findall(r'[a-z0-9]+',str(s).lower()))
def hit(path,terms):
    w=words(path)
    for t in terms:
        n=words(t)
        if not n:continue
        # Config schemas commonly pluralize semantic nouns (`models`, `textures`, `skills`).
        # Accept a simple plural only for single alphabetic tokens; keep phrases exact.
        pat=re.escape(n)
        if ' ' not in n and n.isalpha():pat += 's?'
        if re.search(r'(?<![a-z0-9])'+pat+r'(?![a-z0-9])',w):return True
    return False

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('root',type=Path);ap.add_argument('--json-out',type=Path);ap.add_argument('--md-out',type=Path);args=ap.parse_args();root=args.root.resolve()
    reg=base.load_registry();idx=base.reg_index(reg);entries=[];plugins={};errors=[]
    candidates=[p for p in root.rglob('*') if p.is_file() and p.suffix.lower() in base.TEXT_EXTS][:base.MAX_FILES]
    for p in candidates:
        ent=base.match_plugin(p,root,idx)
        if not ent or ent.get('adapter')=='context-only':continue
        fam=SUPPORTED.get(ent.get('category'))
        if not fam or fam not in FIELDS:continue
        data,err=base.parse_file(p)
        if data is None:continue
        paths,strings=base.walk(data)
        field_paths={};matched=set()
        for field,terms in FIELDS[fam].items():
            vals=[]
            for kp,val in strings:
                # Config keys are useful, but script DSLs often encode the semantic verb only
                # in the scalar/text value. Match both without flattening the original source.
                units=[(kp,val)]
                if kp=='__text__' and '\n' in val:
                    units=[(f'{kp}:line{i}',line) for i,line in enumerate(val.splitlines(),1) if line.strip()]
                for up,uv in units:
                    if hit(kp,terms) or hit(uv,terms):
                        vals.append({'path':up,'value':uv[:500]});matched.add(kp)
                        if len(vals)>=80:break
                if len(vals)>=80:break
            # include non-scalar structured paths as evidence too
            path_only=[kp for kp in paths if hit(kp,terms)][:120]
            matched.update(path_only)
            if vals or path_only:field_paths[field]={'values':vals,'paths':path_only}
        unmatched=[kp for kp in paths if kp not in matched][:500]
        refs=sorted({x for _,v in strings for x in base.REF_RE.findall(v)})[:500]
        commands=sorted({x.strip() for _,v in strings for x in base.CMD_RE.findall(v)})[:200]
        rec={'source_file':p.relative_to(root).as_posix(),'plugin':ent['name'],'category':ent['category'],'family':fam,'registry_coverage':ent['adapter'],'fields':field_paths,'resource_or_namespaced_refs':refs,'command_candidates':commands,'unmatched_key_paths':unmatched,'parse_error':err}
        entries.append(rec)
        a=plugins.setdefault(ent['name'],{'family':fam,'category':ent['category'],'files':0,'canonical_fields':set(),'unmatched_key_paths':0,'refs':set(),'commands':set()})
        a['files']+=1;a['canonical_fields'].update(field_paths);a['unmatched_key_paths']+=len(unmatched);a['refs'].update(refs);a['commands'].update(commands)
        if err:errors.append({'file':rec['source_file'],'error':err})
    summary={}
    for n,v in plugins.items():summary[n]={'family':v['family'],'category':v['category'],'files':v['files'],'canonical_fields':sorted(v['canonical_fields']),'unmatched_key_paths':v['unmatched_key_paths'],'resource_or_namespaced_refs':sorted(v['refs'])[:500],'command_candidates':sorted(v['commands'])[:200]}
    report={'root':str(root),'registry_snapshot':reg.get('snapshot_date'),'supported_families':sorted(set(SUPPORTED.values())),'plugin_summaries':summary,'entries':entries,'parse_errors':errors,'invariant':'Unmatched key paths remain explicit; family IR is a migration schema, not proof that vendor-specific behavior is fully implemented.'}
    text=json.dumps(report,indent=2)
    if args.json_out:args.json_out.parent.mkdir(parents=True,exist_ok=True);args.json_out.write_text(text+'\n',encoding='utf-8')
    if args.md_out:
        lines=['# Server Plugin Family Semantic IR','',f'- Registry snapshot: **{reg.get("snapshot_date")}**',f'- Plugin families found: **{len(summary)}**',f'- Config records: **{len(entries)}**','', '## Summaries']
        for n,v in sorted(summary.items()):lines.append(f"- **{n}** ({v['family']}) — files={v['files']}; fields={', '.join(v['canonical_fields']) or 'none'}; unmatched-key-evidence={v['unmatched_key_paths']}; refs={len(v['resource_or_namespaced_refs'])}; commands={len(v['command_candidates'])}")
        lines += ['', '## Rule','- Canonical fields accelerate translation; unmatched key paths are mandatory review evidence. A family adapter never authorizes silently dropping vendor-specific behavior.']
        args.md_out.parent.mkdir(parents=True,exist_ok=True);args.md_out.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(text)
if __name__=='__main__':main()
