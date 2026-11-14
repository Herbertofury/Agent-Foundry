#!/usr/bin/env python3
"""Install the AGENTS governance bundle into a repository without losing existing files."""
from __future__ import annotations
import argparse, shutil, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

TOOL_FILES=(
    'agents_doctor.py','task_state.py','closeout_receipt.py','project_probe.py','ui_audit.py','project_memory.py','project_catalog.py','project_compass.py','research_memory.py','asset_intelligence.py','library_manager.py'
)

def copy_path(source:Path,destination:Path):
    if source.is_dir(): shutil.copytree(source,destination,dirs_exist_ok=True)
    else: destination.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(source,destination)

def backup_existing(target:Path,paths:list[Path]):
    existing=[p for p in paths if (target/p).exists()]
    if not existing:return None
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'); backup=target/'.agents-backups'/stamp
    for rel in existing: copy_path(target/rel,backup/rel)
    return backup

def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('target',type=Path)
    ap.add_argument('--mode',choices=('repository','all-in-one','modular','hybrid'),default='repository')
    ap.add_argument('--dry-run',action='store_true',help='Read-only plan; never installs files.')
    ap.add_argument('--legacy-chat-contract',action='store_true',help='Explicitly opt into legacy chat-oriented contracts instead of thin repository governance.')
    ap.add_argument('--without-tools',action='store_true')
    ap.add_argument('--init-memory',action='store_true',help='Initialize project-owned second-brain state after installation.')
    ap.add_argument('--project-name',help='Project name required with --init-memory.')
    ap.add_argument('--project-purpose',default='')
    ap.add_argument('--memory-alias',action='append',default=[])
    ap.add_argument('--memory-vault',type=Path)
    ap.add_argument('--init-library',action='store_true',help='Initialize the organized artifact-library vault.')
    ap.add_argument('--library-vault',type=Path,help='Override AGENTS_LIBRARY_HOME for --init-library.')
    args=ap.parse_args(); target=args.target.expanduser().resolve()
    if not target.is_dir(): print(f'Target is not an existing directory: {target}',file=sys.stderr); return 2
    root=Path(__file__).resolve().parents[1]; bundle=root/'assets/agents-md-hybrid'
    if args.init_memory and not args.project_name:
        print('--project-name is required with --init-memory',file=sys.stderr); return 2
    if args.mode=='repository':
        if args.init_memory or args.init_library:
            print('Initialize chat memory/library separately; repository adoption does not activate chat workflows.',file=sys.stderr); return 2
        tool=root.parents[1]/'tools/repository_governance.py'
        if not tool.is_file():
            print('Thin repository adoption requires the canonical Agent-Foundry checkout; legacy export is not a substitute.',file=sys.stderr); return 2
        return subprocess.run([sys.executable,str(tool),'plan' if args.dry_run else 'apply','--target',str(target)],timeout=120).returncode
    if not args.legacy_chat_contract:
        print('Legacy modes require --legacy-chat-contract; prefer the default repository adapter.',file=sys.stderr); return 2
    planned=[Path('AGENTS.md'),Path('AGENTS-all-in-one.md'),Path('AGENTS.modular.md'),Path('AGENTS-README.md'),Path('.agents')]
    if any((target/p).exists() or (target/p).is_symlink() for p in planned):
        print('Refusing to replace existing project instructions/modules; use thin repository adoption and review local integration.',file=sys.stderr); return 2
    if args.dry_run:
        print(f'Would install explicitly selected legacy {args.mode} chat contract into {target}'); return 0
    backup=backup_existing(target,planned)
    if args.mode=='all-in-one':
        copy_path(bundle/'AGENTS.md',target/'AGENTS.md')
    elif args.mode=='modular':
        copy_path(bundle/'AGENTS.modular.md',target/'AGENTS.md'); copy_path(bundle/'.agents',target/'.agents')
    else:
        # Use the complete standalone contract as the automatically loaded root. Keep modular files available too.
        copy_path(bundle/'AGENTS.md',target/'AGENTS.md'); copy_path(bundle/'AGENTS.md',target/'AGENTS-all-in-one.md')
        copy_path(bundle/'AGENTS.modular.md',target/'AGENTS.modular.md'); copy_path(bundle/'.agents',target/'.agents')
        copy_path(bundle/'README.md',target/'AGENTS-README.md')
    if not args.without_tools:
        tools=target/'.agents/tools'; tools.mkdir(parents=True,exist_ok=True)
        for name in TOOL_FILES: copy_path(root/'scripts'/name,tools/name)
        copy_path(root/'assets/codex/compact-prompt.md',target/'.agents/compact-prompt.md')
        copy_path(root/'assets/codex/ACTIVE-TASK.template.json',target/'.agents/ACTIVE-TASK.template.json')
        copy_path(root/'assets/hooks/agent_hook.py',target/'.agents/tools/agent_hook.py')
        copy_path(root/'assets/hooks/README.md',target/'.agents/HOOKS-README.md')
        copy_path(root/'assets/memory/README.md',target/'.agents/MEMORY-README.md')
        copy_path(root/'assets/memory/USER-PROJECTS-DATABASE.seed.md',target/'.agents/memory/USER-PROJECTS-DATABASE.seed.md')
        copy_path(root/'assets/memory/PROJECT-CATALOG.template.json',target/'.agents/memory/PROJECT-CATALOG.template.json')
        copy_path(root/'assets/memory/PROJECT-COMPASS.template.json',target/'.agents/memory/PROJECT-COMPASS.template.json')
        copy_path(root/'assets/memory/FEATURE-FOUNDRY-COMPASS.seed.json',target/'.agents/memory/FEATURE-FOUNDRY-COMPASS.seed.json')
        copy_path(root/'assets/memory/FEATURE-FOUNDRY-SOURCE-HUBS.seed.json',target/'.agents/memory/FEATURE-FOUNDRY-SOURCE-HUBS.seed.json')
        copy_path(root/'assets/memory/FEATURE-FOUNDRY-OBJECT-INTELLIGENCE.seed.json',target/'.agents/memory/FEATURE-FOUNDRY-OBJECT-INTELLIGENCE.seed.json')
        copy_path(root/'assets/library/README.md',target/'.agents/library/README.md')
        copy_path(root/'assets/library/quota-profiles.json',target/'.agents/library/quota-profiles.json')
    if args.init_memory:
        if not args.project_name:
            print('--project-name is required with --init-memory',file=sys.stderr); return 2
        cmd=[sys.executable,str(root/'scripts/project_memory.py'),'init',str(target),'--name',args.project_name,'--purpose',args.project_purpose]
        for alias in args.memory_alias: cmd += ['--alias',alias]
        if args.memory_vault: cmd += ['--vault',str(args.memory_vault)]
        result=subprocess.run(cmd,text=True,timeout=120)
        if result.returncode:
            print('AGENTS files installed, but project memory initialization failed.',file=sys.stderr)
            return result.returncode
    if args.init_library:
        cmd=[sys.executable,str(root/'scripts/library_manager.py')]
        if args.library_vault: cmd += ['--vault',str(args.library_vault)]
        cmd += ['init']
        result=subprocess.run(cmd,text=True,timeout=120)
        if result.returncode:
            print('AGENTS files installed, but artifact library initialization failed.',file=sys.stderr)
            return result.returncode
    print(f'Installed {args.mode} AGENTS setup into {target}')
    print(f'Backup: {backup}' if backup else 'No existing AGENTS files required backup')
    return 0
if __name__=='__main__': raise SystemExit(main())
