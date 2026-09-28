#!/usr/bin/env python3
"""Validate and export a portable AGENTS bundle for Codex or other agents."""
from __future__ import annotations
import argparse, shutil, subprocess, sys, zipfile
from pathlib import Path

TOOLS = [
    'agents_doctor.py','compile_policy.py','task_state.py','closeout_receipt.py',
    'project_probe.py','ui_audit.py','project_memory.py','project_catalog.py','project_compass.py','research_memory.py','asset_intelligence.py','library_manager.py','install_agents_bundle.py'
]

def run(cmd):
    r=subprocess.run(cmd,text=True,capture_output=True,timeout=120)
    if r.returncode:
        raise RuntimeError((r.stderr or r.stdout).strip())

def add_tree(zf, source: Path, prefix: str):
    for p in sorted(source.rglob('*')):
        if p.is_file():
            info=zipfile.ZipInfo(f'{prefix}/{p.relative_to(source).as_posix()}')
            info.date_time=(2026,1,1,0,0,0); info.external_attr=0o644<<16
            zf.writestr(info,p.read_bytes())

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--skill-root',type=Path,default=Path(__file__).resolve().parents[1])
    ap.add_argument('--output-dir',type=Path,default=Path('/mnt/data'))
    ap.add_argument('--name',default='AGENTS-workflow-bundle.zip')
    args=ap.parse_args(); root=args.skill_root.resolve(); out=args.output_dir.resolve(); out.mkdir(parents=True,exist_ok=True)
    run([sys.executable,str(root/'scripts/compile_policy.py'),'--skill-root',str(root)])
    run([sys.executable,str(root/'scripts/manage_pitfalls.py'),'--skill-root',str(root),'validate'])
    run([sys.executable,str(root/'scripts/agents_doctor.py'),'--skill-root',str(root)])
    run([sys.executable,str(root/'scripts/asset_intelligence.py'),'validate'])
    bundle=root/'assets/agents-md-hybrid'
    zip_path=out/args.name
    with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        add_tree(zf,bundle,'agents-workflow')
        for rel in TOOLS:
            p=root/'scripts'/rel
            if p.is_file():
                info=zipfile.ZipInfo(f'agents-workflow/tools/{rel}'); info.date_time=(2026,1,1,0,0,0); info.external_attr=0o755<<16
                zf.writestr(info,p.read_bytes())
        for directory in ('codex','hooks','memory','library'):
            p=root/'assets'/directory
            if p.is_dir(): add_tree(zf,p,f'agents-workflow/{directory}')
        version=root/'VERSION'
        if version.is_file(): zf.writestr('agents-workflow/VERSION',version.read_bytes())
    standalone=out/'AGENTS-all-in-one.md'; shutil.copy2(bundle/'AGENTS.md',standalone)
    modular=out/'AGENTS-modular.md'; shutil.copy2(bundle/'AGENTS.modular.md',modular)
    print(zip_path); print(standalone); print(modular)
    return 0
if __name__=='__main__': raise SystemExit(main())
