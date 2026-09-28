#!/usr/bin/env python3
"""Inventory plugin JAR metadata and plugin config folders from an authorized staged server bundle.

This is intentionally metadata-only: it reads plugin descriptors and hashes JARs, but does not
execute or decompile plugin bytecode.
"""
from __future__ import annotations
import argparse, hashlib, json, re, zipfile
from pathlib import Path

CHUNK=1024*1024
MAX_DESCRIPTOR=1024*1024
MAX_JARS=4096
IGNORE_CONFIG_FOLDERS={'.paper-remapped','update','bstats','pluginmetrics','cache','logs','libraries'}
DESCRIPTORS=('paper-plugin.yml','plugin.yml','bungee.yml','extension.yml','velocity-plugin.json')


def sha256_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        while True:
            b=f.read(CHUNK)
            if not b: break
            h.update(b)
    return h.hexdigest()


def scalar(v:str):
    v=v.strip()
    if not v:return ''
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    return v


def inline_list(v:str):
    v=v.strip()
    if not (v.startswith('[') and v.endswith(']')): return None
    body=v[1:-1].strip()
    if not body:return []
    return [scalar(x) for x in body.split(',') if scalar(x)]


def parse_plugin_yaml(text:str)->dict:
    """Parse only stable top-level plugin descriptor fields without requiring PyYAML."""
    wanted={'name','version','main','api-version','website','description','prefix','loader'}
    list_fields={'depend','softdepend','loadbefore','authors','contributors'}
    out={}; current_list=None
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith('#'):continue
        indent=len(raw)-len(raw.lstrip(' ')); line=raw.strip()
        if indent==0:
            current_list=None
            m=re.match(r'^([A-Za-z0-9_.-]+)\s*:\s*(.*)$',line)
            if not m:continue
            k=m.group(1); v=m.group(2)
            if k in wanted:
                out[k]=scalar(v)
            elif k in list_fields:
                il=inline_list(v)
                if il is not None: out[k]=il
                elif v: out[k]=[scalar(v)]
                else: out[k]=[]; current_list=k
        elif current_list and line.startswith('- '):
            out[current_list].append(scalar(line[2:]))
    return out


def read_descriptor(z:zipfile.ZipFile):
    names={n.lower():n for n in z.namelist()}
    for candidate in DESCRIPTORS:
        actual=names.get(candidate)
        if actual:
            info=z.getinfo(actual)
            if info.file_size>MAX_DESCRIPTOR:
                return candidate,{},f'descriptor too large: {info.file_size}'
            try:
                text=z.read(actual).decode('utf-8',errors='replace')
                if candidate=='velocity-plugin.json':
                    raw=json.loads(text)
                    deps=[]; optional=[]
                    for dep in raw.get('dependencies') or []:
                        if isinstance(dep,str): deps.append(dep)
                        elif isinstance(dep,dict) and dep.get('id'):
                            (optional if dep.get('optional') else deps).append(str(dep['id']))
                    meta={
                        'name':raw.get('name') or raw.get('id') or '',
                        'id':raw.get('id') or '',
                        'version':raw.get('version') or '',
                        'main':raw.get('main') or '',
                        'description':raw.get('description') or '',
                        'authors':raw.get('authors') or [],
                        'depend':deps,'softdepend':optional,
                    }
                    return candidate,meta,None
                meta=parse_plugin_yaml(text)
                # Paper's modern descriptor nests plugin dependencies. Parse conservatively
                # with PyYAML when available, while keeping the top-level fallback above.
                if candidate=='paper-plugin.yml':
                    try:
                        import yaml
                        raw=yaml.safe_load(text) or {}
                        server=((raw.get('dependencies') or {}).get('server') or {}) if isinstance(raw,dict) else {}
                        required=[];optional=[]
                        if isinstance(server,dict):
                            for name,spec in server.items():
                                if isinstance(spec,dict) and spec.get('required') is False: optional.append(str(name))
                                else: required.append(str(name))
                        if required: meta['depend']=sorted(set((meta.get('depend') or [])+required))
                        if optional: meta['softdepend']=sorted(set((meta.get('softdepend') or [])+optional))
                    except Exception:
                        pass
                return candidate,meta,None
            except Exception as exc:
                return candidate,{},str(exc)
    return None,{},None


def plugin_containers(root:Path):
    """Find actual plugin/extension containers without treating server library JARs as plugins."""
    out=[];seen=set()
    direct=[root/'plugins',root/'extensions']
    # Multi-server/proxy captures may contain several server roots.
    direct += [p for p in root.rglob('*') if p.is_dir() and p.name.lower() in {'plugins','extensions'}]
    for p in direct:
        try:key=p.resolve()
        except Exception:continue
        if not p.is_dir() or key in seen:continue
        seen.add(key);out.append(p)
    return sorted(out,key=lambda x:x.as_posix().lower())

def plugin_jar_paths(root:Path):
    found=[];seen=set()
    for container in plugin_containers(root):
        for p in sorted(container.glob('*.jar'),key=lambda x:x.name.lower()):
            try:key=p.resolve()
            except Exception:continue
            if key in seen:continue
            seen.add(key);found.append(p)
    return found

def plugin_config_folders(root:Path):
    found=[];seen=set()
    for container in plugin_containers(root):
        kind='extensions' if container.name.lower()=='extensions' else 'plugins'
        for p in sorted(container.iterdir(),key=lambda x:x.name.lower()):
            if not p.is_dir() or p.name.lower() in IGNORE_CONFIG_FOLDERS:continue
            try:key=p.resolve()
            except Exception:continue
            if key in seen:continue
            seen.add(key);files=[]
            for q in p.rglob('*'):
                rel_inside=q.relative_to(p).parts
                if 'extensions' in {x.lower() for x in rel_inside}:
                    continue
                if q.is_file() and q.suffix.lower() in {'.yml','.yaml','.json','.toml','.conf','.cfg','.properties','.txt','.dsc','.sk'}:
                    files.append(q.relative_to(root).as_posix())
                    if len(files)>=250:break
            # A config-only capture is meaningful only when it actually carries readable config.
            # JAR-only plugins are already represented by descriptor inventory.
            if not files:continue
            found.append({'folder':p.name,'path':p.relative_to(root).as_posix(),'container_type':kind,'config_file_count':len(files),'sample_config_files':files[:20]})
    return found


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('root',type=Path)
    ap.add_argument('--json-out',type=Path)
    ap.add_argument('--md-out',type=Path)
    args=ap.parse_args();root=args.root.resolve()
    if not root.is_dir():raise SystemExit(f'not a directory: {root}')
    all_plugin_jars=plugin_jar_paths(root)
    jar_paths=all_plugin_jars[:MAX_JARS]
    jars=[]
    for p in jar_paths:
        rec={'path':p.relative_to(root).as_posix(),'file_name':p.name,'size':p.stat().st_size,'sha256':sha256_file(p),'zip_valid':False}
        try:
            with zipfile.ZipFile(p) as z:
                rec['zip_valid']=True
                desc,meta,err=read_descriptor(z)
                rec['descriptor']=desc;rec['metadata']=meta
                if err:rec['descriptor_error']=err
                # Lightweight platform/shape hints only; do not enumerate or decompile classes.
                low_names=[n.lower() for n in z.namelist()[:20000]]
                rec['hints']={
                    'paper_plugin_descriptor':'paper-plugin.yml' in low_names,
                    'bukkit_plugin_descriptor':'plugin.yml' in low_names,
                    'velocity_plugin':'velocity-plugin.json' in low_names,
                    'waterfall_or_bungee_plugin':'bungee.yml' in low_names,
                    'geyser_extension':'extension.yml' in low_names,
                }
        except Exception as exc:
            rec['archive_error']=str(exc)
        jars.append(rec)
    folders=plugin_config_folders(root)
    report={
        'root':str(root),'jar_count':len(jars),'jar_scan_truncated':len(all_plugin_jars)>MAX_JARS,
        'plugin_container_count':len(plugin_containers(root)),
        'plugin_jars':jars,'plugin_config_folders':folders,
        'invariants':[
            'JARs are hashed and descriptor metadata is read without execution.',
            'No bytecode decompilation is performed by this inventory step.',
            'Only immediate JAR children of plugin/extension containers are treated as plugin artifacts; server libraries are excluded.',
            'Config folders are inventoried separately because servers often omit plugin JARs from asset captures.',
        ]
    }
    text=json.dumps(report,indent=2)
    if args.json_out:args.json_out.parent.mkdir(parents=True,exist_ok=True);args.json_out.write_text(text+'\n',encoding='utf-8')
    if args.md_out:
        lines=['# Server Plugin Inventory','',f'- Root: `{root}`',f'- Plugin JARs: **{len(jars)}**',f'- Plugin config folders: **{len(folders)}**','', '## Plugin JARs']
        if jars:
            for x in jars:
                m=x.get('metadata') or {}; label=m.get('name') or x['file_name']; vers=m.get('version') or 'unknown'
                deps=', '.join((m.get('depend') or [])+(m.get('softdepend') or [])) or 'none recorded'
                lines.append(f"- **{label}** `{vers}` — `{x['path']}`; descriptor={x.get('descriptor') or 'none'}; deps={deps}")
        else:lines.append('- None supplied.')
        lines += ['', '## Plugin config folders']
        if folders:
            for x in folders:lines.append(f"- **{x['folder']}** — {x['config_file_count']} config-like file(s); `{x['path']}`")
        else:lines.append('- None supplied.')
        args.md_out.parent.mkdir(parents=True,exist_ok=True);args.md_out.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(text)
if __name__=='__main__':main()
