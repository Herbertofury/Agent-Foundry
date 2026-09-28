#!/usr/bin/env python3
"""Portable hook adapter for agent runtimes that can invoke commands on lifecycle events.

Input: one JSON object on stdin with an `event` field. Output: JSON decision.
This adapter is runtime-neutral; wire event names to the installed agent's current hook API.
"""
from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path


def run(cmd, cwd):
    r=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True)
    return {'exit_code':r.returncode,'stdout':r.stdout[-4000:],'stderr':r.stderr[-4000:]}

def main():
    payload=json.load(sys.stdin); event=str(payload.get('event','')).lower(); repo=Path(payload.get('repository') or os.getcwd()).resolve()
    tools=repo/'.agents'/'tools'; result={'event':event,'allow':True,'messages':[]}
    if event in ('sessionstart','session_start'):
        doctor=tools/'agents_doctor.py'
        if doctor.is_file():
            x=run([sys.executable,str(doctor),'--repository',str(repo)],repo); result['doctor']=x; result['allow']=x['exit_code']==0
        memory=tools/'project_memory.py'
        marker=repo/'.agents-memory/PROJECT.json'
        if marker.is_file() and memory.is_file():
            try:
                registry_hint=json.loads(marker.read_text(encoding='utf-8')).get('registry_hint','')
            except Exception:
                registry_hint=''
            cmd=[sys.executable,str(memory),'doctor',str(repo)]
            if registry_hint: cmd += ['--vault',registry_hint]
            m=run(cmd,repo); result['project_memory']=m; result['allow']=result['allow'] and m['exit_code']==0
            result['messages'].append('Load .agents-memory/HANDOFF.md and verify project identity before mutation.')
        else:
            result['messages'].append('Before mutating a named or resumed project, run project_memory.py identify; initialize memory only after duplicate-project checks.')
        library=tools/'library_manager.py'
        if library.is_file():
            l=run([sys.executable,str(library),'doctor'],repo); result['artifact_library']=l; result['allow']=result['allow'] and l['exit_code']==0
            result['messages'].append('Load the library catalog before creating another export; record current Storage UI usage when quota state is unknown.')
    elif event in ('userpromptsubmit','user_prompt_submit','after_compaction'):
        state=repo/'.agents'/'ACTIVE-TASK.json'
        result['messages'].append('Refresh applicable AGENTS instructions, load the project handoff/research memory, and update ACTIVE-TASK.json before substantive work.')
        result['active_task_present']=state.is_file()
    elif event in ('pretooluse','pre_tool_use'):
        command=str(payload.get('command',''))
        destructive=('rm -rf','git reset --hard','git clean -fd','git push --force','format c:','remove-item -recurse -force')
        if any(x in command.lower() for x in destructive):
            result.update({'allow':False,'reason':'destructive command requires explicit user authorization and a recoverable checkpoint'})
    elif event in ('posttooluse','post_tool_use'):
        result['messages'].append('Record command outcome and observed evidence in ACTIVE-TASK.json or the closeout receipt; checkpoint durable project memory after meaningful progress.')
    elif event in ('stop','closeout'):
        receipt=repo/'.agents'/'CLOSEOUT-RECEIPT.json'
        validator=tools/'closeout_receipt.py'
        if not receipt.is_file(): result.update({'allow':False,'reason':'missing closeout receipt'})
        elif validator.is_file():
            x=run([sys.executable,str(validator),'--path',str(receipt),'validate'],repo); result['receipt']=x; result['allow']=x['exit_code']==0
        memory=tools/'project_memory.py'
        marker=repo/'.agents-memory/PROJECT.json'
        if result['allow'] and marker.is_file() and memory.is_file():
            try:
                registry_hint=json.loads(marker.read_text(encoding='utf-8')).get('registry_hint','')
            except Exception:
                registry_hint=''
            cmd=[sys.executable,str(memory),'doctor',str(repo)]
            if registry_hint: cmd += ['--vault',registry_hint]
            m=run(cmd,repo); result['project_memory']=m; result['allow']=m['exit_code']==0
            if not result['allow']: result['reason']='project memory is invalid or not safely checkpointed'
        library=tools/'library_manager.py'
        if result['allow'] and library.is_file():
            l=run([sys.executable,str(library),'doctor'],repo); result['artifact_library']=l; result['allow']=l['exit_code']==0
            if not result['allow']: result['reason']='artifact library catalog is invalid or cleanup state is unresolved'
    json.dump(result,sys.stdout,ensure_ascii=False); sys.stdout.write('\n'); return 0 if result['allow'] else 2
if __name__=='__main__': raise SystemExit(main())
