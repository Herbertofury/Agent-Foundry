#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, zipfile
from datetime import datetime, timezone
from pathlib import Path

FIXED_DT=(2026,1,1,0,0,0)

GENERATED_JUNK_PARTS={"__pycache__"}
GENERATED_JUNK_SUFFIXES={".pyc",".pyo"}

def include_source_file(skill:Path,path:Path):
    rel=path.relative_to(skill)
    if any(part in GENERATED_JUNK_PARTS for part in rel.parts): return False
    if path.suffix.lower() in GENERATED_JUNK_SUFFIXES: return False
    return path.is_file()

def file_sha(path:Path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def source_digest(skill:Path):
    h=hashlib.sha256()
    for f in sorted(p for p in skill.rglob('*') if include_source_file(skill,p)):
        rel=f.relative_to(skill).as_posix(); b=f.read_bytes()
        h.update(rel.encode()+b'\0'+hashlib.sha256(b).hexdigest().encode()+b'\n')
    return h.hexdigest()

def package(skill:Path,out_root:Path,source_url:str,revision:str,built_at:str):
    out=out_root/skill.name; out.mkdir(parents=True,exist_ok=True); zpath=out/'skill.zip'
    if zpath.exists(): zpath.unlink()
    with zipfile.ZipFile(zpath,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for f in sorted(p for p in skill.rglob('*') if include_source_file(skill,p)):
            rel=Path(skill.name)/f.relative_to(skill)
            info=zipfile.ZipInfo(rel.as_posix(),FIXED_DT); info.compress_type=zipfile.ZIP_DEFLATED; info.external_attr=(f.stat().st_mode & 0xFFFF)<<16
            z.writestr(info,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    receipt={
      'schemaVersion':1,'artifact':f'{skill.name}/skill.zip','version':None,'source':source_url,'sourceRevision':revision,
      'sourceTreeDigest':source_digest(skill),'sha256':file_sha(zpath),'sizeBytes':zpath.stat().st_size,'builtAt':built_at,
      'workflow':os.getenv('GITHUB_WORKFLOW_REF'),'attestation':None,'sbom':None,'agBOM':None,
      'validation':['Foundry source validation passed before packaging'],'supersedes':None
    }
    (out/'release-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return receipt

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--skills-root',type=Path,default=Path('skills')); ap.add_argument('--out',type=Path,default=Path('dist'))
    ap.add_argument('--source-url',default=os.getenv('GITHUB_SERVER_URL','https://github.com')+'/'+os.getenv('GITHUB_REPOSITORY','local/agent-foundry'))
    ap.add_argument('--revision',default=os.getenv('GITHUB_SHA','local')); ap.add_argument('--built-at',default=os.getenv('SOURCE_DATE_EPOCH'))
    ns=ap.parse_args(); ns.out.mkdir(parents=True,exist_ok=True)
    built_at=datetime.fromtimestamp(int(ns.built_at),tz=timezone.utc).isoformat().replace('+00:00','Z') if ns.built_at else '2026-09-27T00:00:00Z'
    receipts=[package(skill,ns.out,ns.source_url,ns.revision,built_at) for skill in sorted(p for p in ns.skills_root.iterdir() if p.is_dir() and (p/'SKILL.md').is_file())]
    (ns.out/'release-index.json').write_text(json.dumps({'schemaVersion':1,'artifacts':receipts},indent=2)+'\n',encoding='utf-8')
    print(json.dumps([{'artifact':r['artifact'],'sha256':r['sha256'],'sizeBytes':r['sizeBytes']} for r in receipts],indent=2))
if __name__=='__main__': main()
