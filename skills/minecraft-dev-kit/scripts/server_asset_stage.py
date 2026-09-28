#!/usr/bin/env python3
"""Safely stage an authorized server asset directory/ZIP without mutating the source."""
from __future__ import annotations
import argparse, hashlib, json, shutil, stat, zipfile
from pathlib import Path, PurePosixPath

CHUNK=1024*1024

def sha256_file(p:Path):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while True:
            b=f.read(CHUNK)
            if not b:break
            h.update(b)
    return h.hexdigest()

def safe_rel(name:str):
    pp=PurePosixPath(name.replace('\\','/'))
    if pp.is_absolute() or '..' in pp.parts or not pp.parts:return None
    # Drop empty/dot components while preserving path identity.
    parts=[x for x in pp.parts if x not in ('','.')] 
    if not parts:return None
    return Path(*parts)

def classify(rel:Path):
    s=rel.as_posix().lower(); suf=rel.suffix.lower()
    if suf in {'.bbmodel','.ajmodel','.fmmodel','.blend','.gltf','.glb'}:return 'authoring-model'
    if s.endswith('.geo.json') or suf in {'.jem','.jpm'} or '/animations/' in '/'+s and suf=='.json':return 'animation-model-resource'
    if s.startswith('assets/') or s.startswith('data/') or rel.name.lower() in {'pack.mcmeta','pack.png'}:return 'resource-pack-or-datapack'
    if any(x in '/'+s for x in ('/plugins/','/mythicmobs/','/modelengine/','/itemsadder/','/oraxen/','/nexo/')) and suf in {'.yml','.yaml','.json','.toml','.conf','.cfg','.properties'}:return 'server-config'
    if suf in {'.png','.tga','.jpg','.jpeg','.webp','.ogg','.wav','.mcmeta'}:return 'asset'
    return 'other'

def copy_stream(src,dst):
    dst.parent.mkdir(parents=True,exist_ok=True)
    with src, dst.open('wb') as out:shutil.copyfileobj(src,out,CHUNK)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('input',type=Path);ap.add_argument('output',type=Path);ap.add_argument('--force',action='store_true');args=ap.parse_args()
    src=args.input.resolve(); out=args.output.resolve()
    if out.exists() and any(out.iterdir()) and not args.force:raise SystemExit(f'output is not empty: {out}; use --force only for a disposable staging dir')
    out.mkdir(parents=True,exist_ok=True); staged=out/'source';staged.mkdir(exist_ok=True)
    entries=[];rejected=[];kind='directory'
    if src.is_file() and zipfile.is_zipfile(src):
        kind='zip';source_identity={'path':str(src),'size':src.stat().st_size,'sha256':sha256_file(src)}
        with zipfile.ZipFile(src) as z:
            for info in z.infolist():
                if info.is_dir():continue
                rel=safe_rel(info.filename)
                # Refuse Unix symlink entries instead of materializing arbitrary link targets.
                mode=(info.external_attr>>16)&0xFFFF
                if rel is None or stat.S_ISLNK(mode):
                    rejected.append({'path':info.filename,'reason':'unsafe path or symlink'});continue
                dst=staged/rel
                with z.open(info) as inp:copy_stream(inp,dst)
                entries.append({'path':rel.as_posix(),'size':dst.stat().st_size,'sha256':sha256_file(dst),'role':classify(rel)})
    elif src.is_dir():
        tree_hash=hashlib.sha256();files=[]
        for p in sorted(src.rglob('*')):
            if p.is_symlink():
                rejected.append({'path':p.relative_to(src).as_posix(),'reason':'symlink skipped'});continue
            if not p.is_file():continue
            rel=p.relative_to(src);files.append((rel,p))
        for rel,p in files:
            h=sha256_file(p);tree_hash.update(rel.as_posix().encode()+b'\0'+h.encode()+b'\n')
            dst=staged/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst)
            entries.append({'path':rel.as_posix(),'size':p.stat().st_size,'sha256':h,'role':classify(rel)})
        source_identity={'path':str(src),'file_count':len(files),'tree_sha256':tree_hash.hexdigest()}
    else:raise SystemExit('input must be a directory or ZIP')
    role_counts={}
    for e in entries:role_counts[e['role']]=role_counts.get(e['role'],0)+1
    manifest={'input_kind':kind,'source_identity':source_identity,'staged_root':str(staged),'file_count':len(entries),'role_counts':role_counts,'files':entries,'rejected':rejected,'invariants':['Staged bytes are copied without source mutation.','Every staged regular file has SHA-256 provenance.','Unsafe traversal paths and symlink entries are rejected, not followed.','Staging does not bypass encryption, obfuscation, or access controls.']}
    (out/'STAGE-MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    with (out/'SHA256SUMS.txt').open('w',encoding='utf-8') as f:
        for e in entries:f.write(f"{e['sha256']}  source/{e['path']}\n")
    print(json.dumps({'output':str(out),'file_count':len(entries),'role_counts':role_counts,'rejected':rejected,'source_identity':source_identity},indent=2))
if __name__=='__main__':main()
