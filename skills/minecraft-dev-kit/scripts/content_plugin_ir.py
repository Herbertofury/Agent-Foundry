#!/usr/bin/env python3
"""Normalize authorized ItemsAdder/Oraxen/Nexo-style YAML content configs into mod-conversion IR."""
from __future__ import annotations
import argparse, json, re, zipfile
from pathlib import Path, PurePosixPath
import yaml

YAML_EXTS=(".yml",".yaml")
MAX_BYTES=8*1024*1024

class Bundle:
    def __init__(self,p:Path):
        self.p=p;self.z=zipfile.ZipFile(p) if p.is_file() and zipfile.is_zipfile(p) else None
        if not self.z and not p.is_dir() and not p.is_file():raise SystemExit('input must be YAML file, directory, or ZIP')
    def items(self):
        if self.z:
            for n in self.z.namelist():
                if not n.endswith('/') and n.lower().endswith(YAML_EXTS):
                    with self.z.open(n) as f:yield n,f.read(MAX_BYTES).decode('utf-8',errors='ignore')
        elif self.p.is_dir():
            for x in sorted(self.p.rglob('*')):
                if x.is_file() and x.name.lower().endswith(YAML_EXTS):yield x.relative_to(self.p).as_posix(),x.read_text(encoding='utf-8',errors='ignore')
        elif self.p.name.lower().endswith(YAML_EXTS):yield self.p.name,self.p.read_text(encoding='utf-8',errors='ignore')
    def close(self):
        if self.z:self.z.close()

def lower_map(d):return {str(k).lower():k for k in d} if isinstance(d,dict) else {}
def get_ci(d,*names):
    if not isinstance(d,dict):return None
    lm=lower_map(d)
    for n in names:
        if n.lower() in lm:return d[lm[n.lower()]]
    return None

def detect_plugin(path,data):
    low=path.lower();scores={'ItemsAdder':0,'Oraxen':0,'Nexo':0,'CraftEngine':0,'ExecutableItems':0,'ExecutableBlocks':0,'MMOItems':0,'EcoItems':0,'HMCCosmetics':0}
    if 'itemsadder' in low or '/contents/' in '/'+low:scores['ItemsAdder']+=3
    if 'oraxen' in low:scores['Oraxen']+=3
    if 'nexo' in low:scores['Nexo']+=3
    if 'craftengine' in low or 'craft-engine' in low or 'craft_engine' in low:scores['CraftEngine']+=4
    if 'executableitems' in low:scores['ExecutableItems']+=4
    if 'executableblocks' in low:scores['ExecutableBlocks']+=4
    if 'mmoitems' in low:scores['MMOItems']+=4
    if 'ecoitems' in low:scores['EcoItems']+=4
    if 'hmccosmetics' in low:scores['HMCCosmetics']+=4
    if isinstance(data,dict):
        if isinstance(data.get('info'),dict) and 'namespace' in data.get('info',{}) and isinstance(data.get('items'),dict):scores['ItemsAdder']+=4
        text=' '.join(str(k) for k in data.keys()).lower()
        # Nexo convention prominently uses Components/ItemModel/itemname.
        if any(isinstance(v,dict) and any(str(k).lower() in {'components','itemmodel','itemname'} for k in v) for v in data.values()):scores['Nexo']+=2
        # Oraxen frequently uses displayname and Mechanics with furniture/noteblock/stringblock/clickActions.
        if any(isinstance(v,dict) and any(str(k).lower()=='displayname' for k in v) for v in data.values()):scores['Oraxen']+=1
        # These second-wave ecosystems vary more by version; path identity is primary and schema hints only boost confidence.
        if any(str(k).lower() in {'behaviors','behaviours','block','item','furniture','recipes'} for k in data):scores['CraftEngine']+=1
        if any('activator' in str(k).lower() for k in data):scores['ExecutableItems']+=1;scores['ExecutableBlocks']+=1
        if any(str(k).lower() in {'base','material','name','lore','stats','abilities'} for k in data):scores['MMOItems']+=1
        if any(str(k).lower() in {'effects','conditions','triggers'} for k in data):scores['EcoItems']+=1
        if any('cosmetic' in str(k).lower() or 'slot' in str(k).lower() for k in data):scores['HMCCosmetics']+=1
    winner=max(scores,key=scores.get)
    return winner if scores[winner]>=2 else 'Unknown',scores

def refs(obj,out=None):
    if out is None:out=set()
    if isinstance(obj,str):
        for x in re.findall(r'(?<![A-Za-z0-9_.-])([a-z0-9_.-]+:[a-z0-9_./-]+)',obj,re.I):out.add(x)
    elif isinstance(obj,dict):
        for v in obj.values():refs(v,out)
    elif isinstance(obj,list):
        for v in obj:refs(v,out)
    return out

def normalize_furniture(mech):
    if not isinstance(mech,dict):return None
    furn=get_ci(mech,'furniture')
    if not isinstance(furn,dict):return None
    hitbox=get_ci(furn,'hitbox') or {}
    return {
        'seats':get_ci(furn,'seats','seat'),
        'hitbox':hitbox,
        'storage':get_ci(furn,'storage'),
        'drop':get_ci(furn,'drop','drops'),
        'block_sounds':get_ci(furn,'block_sounds','sounds'),
        'connectable':get_ci(furn,'connectable'),
        'click_actions':get_ci(furn,'clickactions','click_actions'),
        'waterloggable':get_ci(furn,'waterloggable'),
        'protection':get_ci(furn,'blocklocker','protection'),
        'properties':get_ci(furn,'properties','display_entity_properties'),
    }

def normalize_entry(plugin,namespace,item_id,d,path):
    if not isinstance(d,dict):return None
    pack=get_ci(d,'pack') or {}
    resource=get_ci(d,'resource') or {}
    components=get_ci(d,'components') or {}
    mechanics=get_ci(d,'mechanics') or {}
    behaviours=get_ci(d,'behaviours','behaviors') or {}
    events=get_ci(d,'events') or {}
    known={'itemname','displayname','display_name','name','material','permission','lore','pack','resource','components','mechanics','behaviours','behaviors','events','events_settings','attribute_modifiers','attributes','enchantments','unbreakable','template','templates','mmoitem','activators','conditions','triggers','effects','commands','cooldown','cooldowns','abilities','stats','slot','slots','model','model_data','custom_model_data','item_model','parent_model','equip','equipment','recipes','recipe'}
    unclassified=[str(k) for k in d if str(k).lower() not in known]
    return {
        'source_plugin':plugin,'source_file':path,'namespace':namespace,'item_id':str(item_id),
        'display_name':get_ci(d,'itemname','displayname','display_name','name'),
        'material':get_ci(d,'material'),'permission':get_ci(d,'permission'),'lore':get_ci(d,'lore'),
        'pack':pack,'resource':resource,'components':components,'mechanics':mechanics,'behaviours':behaviours,'events':events,
        'event_settings':get_ci(d,'events_settings'),'attributes':get_ci(d,'attribute_modifiers','attributes'),'enchantments':get_ci(d,'enchantments'),
        'template_refs':get_ci(d,'templates','template'),'external_item_base':get_ci(d,'mmoitem'),
        'furniture':normalize_furniture(mechanics) or normalize_furniture(behaviours),
        'runtime_semantic_candidates':{k:get_ci(d,k) for k in ('activators','conditions','triggers','effects','commands','cooldown','cooldowns','abilities','stats','slot','slots','model','model_data','custom_model_data','item_model','parent_model','equip','equipment','recipes','recipe') if get_ci(d,k) is not None},
        'resource_references':sorted(refs({'pack':pack,'resource':resource,'components':components,'mechanics':mechanics,'behaviours':behaviours,'events':events,'runtime':d})),
        'unclassified_keys':unclassified,
    }

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('input',type=Path);ap.add_argument('--json-out',type=Path);ap.add_argument('--md-out',type=Path);args=ap.parse_args()
    b=Bundle(args.input);entries=[];files=[];errors=[]
    try:
        for path,text in b.items():
            try:data=yaml.safe_load(text)
            except Exception as exc:errors.append({'file':path,'error':str(exc)});continue
            if not isinstance(data,dict):continue
            plugin,scores=detect_plugin(path,data);namespace=None;item_map=None
            if plugin=='ItemsAdder' and isinstance(data.get('items'),dict):
                namespace=(data.get('info') or {}).get('namespace');item_map=data['items']
            else:
                # Oraxen/Nexo item config files are commonly top-level item-id maps. Skip known core/meta configs.
                core_names={'settings','mechanics','config','sound','sounds','glyphs','recipes','font_images','categories','info','language','messages','general'}
                candidate={k:v for k,v in data.items() if str(k).lower() not in core_names and isinstance(v,dict)}
                if candidate:item_map=candidate
            files.append({'file':path,'detected_plugin':plugin,'scores':scores,'namespace':namespace,'candidate_entries':len(item_map or {})})
            for item_id,d in (item_map or {}).items():
                x=normalize_entry(plugin,namespace,item_id,d,path)
                if x:entries.append(x)
    finally:b.close()
    semantic_counts={
        'entries':len(entries),'with_pack_or_resource':sum(bool(x['pack'] or x['resource']) for x in entries),'with_components':sum(bool(x['components']) for x in entries),
        'with_mechanics_or_behaviours':sum(bool(x['mechanics'] or x['behaviours']) for x in entries),'with_events':sum(bool(x['events']) for x in entries),'with_furniture':sum(bool(x['furniture']) for x in entries),
        'with_unclassified_keys':sum(bool(x['unclassified_keys']) for x in entries)
    }
    actions=[]
    if semantic_counts['with_components']:actions.append('Translate item/DataComponent semantics against the exact target Minecraft version.')
    if semantic_counts['with_furniture']:actions.append('Translate furniture seats/hitboxes/storage/drops/sounds/connectivity/interactions into native persistent block/entity behavior.')
    if semantic_counts['with_events']:actions.append('Translate source event/condition/action graphs into typed native event handlers and predicates.')
    if semantic_counts['with_unclassified_keys']:actions.append('Review unclassified source keys before claiming full conversion; extend the adapter instead of dropping them.')
    report={'input':str(args.input),'files':files,'semantic_counts':semantic_counts,'entries':entries,'parse_errors':errors,'migration_actions':actions,'warnings':['Generic normalization recognizes multiple plugin ecosystems but does not claim every plugin-specific mechanic is understood; path/schema recognition is not semantic parity.','Keep original YAML as provenance and extend semantic handlers for every unclassified behavior that affects runtime.']}
    text=json.dumps(report,indent=2,default=str)
    if args.json_out:args.json_out.parent.mkdir(parents=True,exist_ok=True);args.json_out.write_text(text+'\n',encoding='utf-8')
    if args.md_out:
        lines=['# Custom Content Plugin IR','',f"- Entries: **{len(entries)}**",f"- Files parsed: **{len(files)}**",f"- Parse errors: **{len(errors)}**",'', '## Counts']+[f'- {k}: {v}' for k,v in semantic_counts.items()]+['','## Entries']
        for x in entries:lines.append(f"- `{x['source_plugin']}` `{x['namespace']+':' if x['namespace'] else ''}{x['item_id']}` material=`{x['material']}` furniture={'yes' if x['furniture'] else 'no'} unknown={len(x['unclassified_keys'])}")
        lines += ['','## Migration actions']+[f'- {x}' for x in actions]
        args.md_out.parent.mkdir(parents=True,exist_ok=True);args.md_out.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(text)
if __name__=='__main__':main()
