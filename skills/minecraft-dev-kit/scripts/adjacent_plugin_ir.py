#!/usr/bin/env python3
"""Extract broad conversion-significant semantics from recognized non-first-class server plugin configs.

This is deliberately conservative: it records structured key paths, typed semantic candidates and
resource/ID references while preserving the original config as source of truth. Recognition is not
claimed as exact plugin-specific semantic parity.
"""
from __future__ import annotations
import argparse,json,re,tomllib
from pathlib import Path
import yaml

REGISTRY=Path(__file__).resolve().parent.parent/'references'/'server-plugin-registry.json'
MAX_BYTES=8*1024*1024
MAX_FILES=5000
TEXT_EXTS={'.yml','.yaml','.json','.toml','.conf','.cfg','.properties','.txt','.dsc','.sk'}
SEMANTIC_GROUPS={
 'visual':['model','texture','resourcepack','resource_pack','font','glyph','sound','particle','effect','skin','material','custommodeldata','custom_model_data','item_model','display'],
 'animation':['animation','state','pose','emote','timeline','keyframe','lerp','interpolation','loop'],
 'entity':['mob','entity','npc','citizen','disguise','variant','equipment','spawn','ai','goal','target','trait'],
 'combat':['weapon','gun','ammo','projectile','damage','recoil','scope','reload','fire','hitbox','skill','spell','ability','cooldown'],
 'quest_story':['quest','objective','condition','event','action','reward','dialog','conversation','cinematic','camera','trigger'],
 'item_content':['item','block','furniture','recipe','loot','drop','crate','shop','trade','component','attribute','enchant'],
 'mount_vehicle_pet':['seat','mount','vehicle','pet','passenger','leash'],
 'ui':['hud','hologram','menu','gui','scoreboard','nametag','bossbar','actionbar','chatbubble'],
 'world':['world','biome','structure','dungeon','region','claim','generator'],
 'integration':['placeholder','command','permission','depend','hook','integration','provider'],
}
REF_RE=re.compile(r'(?<![A-Za-z0-9_.-])([a-z0-9_.-]+:[a-z0-9_./-]+)',re.I)
CMD_RE=re.compile(r'(?i)(?:^|\s)/(?:[a-z][a-z0-9:_-]*)(?:\s+[^\n\r]{0,180})?')

def norm(s):return re.sub(r'[^a-z0-9]+','',str(s).lower())
def load_registry():return json.loads(REGISTRY.read_text(encoding='utf-8'))
def reg_index(reg):
    idx={}
    for e in reg.get('entries',[]):
        for k in [e.get('name',''),*(e.get('aliases') or []),*(e.get('markers') or [])]:
            n=norm(k)
            if n:idx.setdefault(n,e)
    return idx

def match_plugin(path:Path,root:Path,idx):
    rel=path.relative_to(root).as_posix();parts=Path(rel).parts
    candidates=[]
    # Prefer the most specific plugin/extension container segment. This matters for paths like
    # plugins/Geyser-Spigot/extensions/GeyserModelEngine/config.yml.
    for i,part in enumerate(parts[:-1]):
        if part.lower() in {'plugins','extensions'} and i+1<len(parts):
            candidates.insert(0,parts[i+1])
    candidates += [path.stem,*reversed(parts[:-1]),parts[0] if parts else '']
    for c in candidates:
        n=norm(c)
        if n in idx:return idx[n]
    # Marker fallback chooses the longest matching identity, preventing a broad parent name
    # (e.g. Geyser) from stealing GeyserModelEngine.
    low=norm(rel);matches=[]
    for k,e in idx.items():
        if len(k)>=5 and k in low:matches.append((len(k),k,e))
    if matches:
        matches.sort(key=lambda x:(-x[0],x[1],x[2]['name']))
        return matches[0][2]
    return None

def parse_file(p:Path):
    if p.stat().st_size>MAX_BYTES:return None,'too-large'
    text=p.read_text(encoding='utf-8',errors='replace');s=p.suffix.lower()
    try:
        if s in {'.yml','.yaml'}:return yaml.safe_load(text),None
        if s=='.json':return json.loads(text),None
        if s=='.toml':return tomllib.loads(text),None
        if s in {'.properties','.cfg','.conf'}:
            d={}
            for line in text.splitlines():
                line=line.strip()
                if not line or line.startswith(('#',';')):continue
                m=re.match(r'^([^:=]+?)\s*[:=]\s*(.*)$',line)
                if m:d[m.group(1).strip()]=m.group(2).strip()
            return d,None
        return {'__text__':text},None
    except Exception as exc:return {'__text__':text},str(exc)

def walk(obj,path='',depth=0,out=None,strings=None,limit=12000):
    if out is None:out=[]
    if strings is None:strings=[]
    if len(out)>=limit or depth>20:return out,strings
    if isinstance(obj,dict):
        for k,v in obj.items():
            kp=f'{path}.{k}' if path else str(k);out.append(kp)
            if isinstance(v,(str,int,float,bool)):strings.append((kp,str(v)))
            walk(v,kp,depth+1,out,strings,limit)
    elif isinstance(obj,list):
        for i,v in enumerate(obj[:1000]):
            kp=f'{path}[{i}]';
            if isinstance(v,(str,int,float,bool)):strings.append((kp,str(v)))
            walk(v,kp,depth+1,out,strings,limit)
    elif isinstance(obj,(str,int,float,bool)):strings.append((path,str(obj)))
    return out,strings

def semantic_hits(paths,strings):
    hits={k:[] for k in SEMANTIC_GROUPS};refs=set();commands=set()
    for kp in paths:
        low=kp.lower()
        words=' '.join(re.findall(r'[a-z0-9]+', low))
        for g,terms in SEMANTIC_GROUPS.items():
            matched=False
            for t in terms:
                needle=' '.join(re.findall(r'[a-z0-9]+', t.lower()))
                if not needle:
                    continue
                if re.search(r'(?<![a-z0-9])'+re.escape(needle)+r'(?![a-z0-9])', words):
                    matched=True;break
            if matched and len(hits[g])<100:hits[g].append(kp)
    for kp,val in strings:
        for x in REF_RE.findall(val):refs.add(x)
        for x in CMD_RE.findall(val):commands.add(x.strip())
    return {k:v for k,v in hits.items() if v},sorted(refs),sorted(commands)[:200]

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('root',type=Path);ap.add_argument('--json-out',type=Path);ap.add_argument('--md-out',type=Path);args=ap.parse_args();root=args.root.resolve()
    reg=load_registry();idx=reg_index(reg);files=[];plugins={};errors=[]
    candidates=[p for p in root.rglob('*') if p.is_file() and (p.suffix.lower() in TEXT_EXTS or p.name.lower().endswith(('.geo.json','.png.mcmeta')))][:MAX_FILES]
    for p in candidates:
        ent=match_plugin(p,root,idx)
        if not ent or ent.get('adapter')=='context-only':continue
        data,err=parse_file(p)
        if data is None:continue
        paths,strings=walk(data);hits,refs,commands=semantic_hits(paths,strings)
        rec={'source_file':p.relative_to(root).as_posix(),'plugin':ent['name'],'category':ent['category'],'impact':ent['impact'],'coverage':ent['adapter'],'parse_error':err,'semantic_groups':hits,'resource_or_namespaced_refs':refs,'command_candidates':commands,'key_path_count':len(paths),'sample_key_paths':paths[:120]}
        files.append(rec); plugins.setdefault(ent['name'],{'files':0,'semantic_groups':set(),'refs':set(),'commands':set(),'coverage':ent['adapter'],'impact':ent['impact'],'category':ent['category']})
        a=plugins[ent['name']];a['files']+=1;a['semantic_groups'].update(hits);a['refs'].update(refs);a['commands'].update(commands)
        if err:errors.append({'file':rec['source_file'],'error':err})
    psummary={}
    for k,v in plugins.items():psummary[k]={'files':v['files'],'semantic_groups':sorted(v['semantic_groups']),'resource_or_namespaced_refs':sorted(v['refs'])[:500],'command_candidates':sorted(v['commands'])[:200],'coverage':v['coverage'],'impact':v['impact'],'category':v['category']}
    report={'root':str(root),'registry_snapshot':reg.get('snapshot_date'),'files_scanned':len(files),'plugins':psummary,'files':files,'parse_errors':errors,'warnings':['This broad IR is a discovery/normalization layer, not proof of exact plugin-specific semantics.','For every conversion-impact plugin present, preserve the original config and implement/review every behavior that affects visible or gameplay parity.']}
    text=json.dumps(report,indent=2)
    if args.json_out:args.json_out.parent.mkdir(parents=True,exist_ok=True);args.json_out.write_text(text+'\n',encoding='utf-8')
    if args.md_out:
        lines=['# Adjacent Server Plugin Semantic IR','',f'- Registry snapshot: **{reg.get("snapshot_date")}**',f'- Recognized plugin families with parsed configs: **{len(psummary)}**',f'- Config files normalized: **{len(files)}**','', '## Plugin summaries']
        for n,v in sorted(psummary.items()):lines.append(f"- **{n}** — {v['coverage']} / {v['impact']}; files={v['files']}; groups={', '.join(v['semantic_groups']) or 'none'}; refs={len(v['resource_or_namespaced_refs'])}; commands={len(v['command_candidates'])}")
        lines += ['', '## Interpretation','- `first-class`/`generic` coverage can feed stronger adapters elsewhere in the pipeline.','- `detect-only` coverage means the semantic groups are mapped for review, not silently discarded. Extend a dedicated adapter when exact parity depends on vendor-specific behavior.']
        args.md_out.parent.mkdir(parents=True,exist_ok=True);args.md_out.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(text)
if __name__=='__main__':main()
