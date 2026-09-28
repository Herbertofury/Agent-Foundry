#!/usr/bin/env python3
"""Run the authorized server-asset conversion intake/IR/audit pipeline in one command."""
from __future__ import annotations
import argparse, json, shutil, subprocess, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent

def run(script,args,stdout_path,allow=(0,),timeout_seconds=900):
    cmd=[sys.executable,str(HERE/script),*map(str,args)]
    stdout_path.parent.mkdir(parents=True,exist_ok=True)
    try:
        cp=subprocess.run(cmd,text=True,capture_output=True,timeout=timeout_seconds)
        stdout_path.write_text(cp.stdout,encoding='utf-8')
        if cp.stderr: stdout_path.with_suffix(stdout_path.suffix+'.stderr').write_text(cp.stderr,encoding='utf-8')
        return {'script':script,'command':cmd,'returncode':cp.returncode,'ok':cp.returncode in allow,'stdout':str(stdout_path),'stderr':cp.stderr[-2000:] if cp.stderr else '','timeout_seconds':timeout_seconds}
    except subprocess.TimeoutExpired as exc:
        stdout=(exc.stdout or '') if isinstance(exc.stdout,str) else (exc.stdout or b'').decode('utf-8',errors='ignore')
        stderr=(exc.stderr or '') if isinstance(exc.stderr,str) else (exc.stderr or b'').decode('utf-8',errors='ignore')
        stdout_path.write_text(stdout,encoding='utf-8')
        if stderr: stdout_path.with_suffix(stdout_path.suffix+'.stderr').write_text(stderr,encoding='utf-8')
        return {'script':script,'command':cmd,'returncode':124,'ok':False,'stdout':str(stdout_path),'stderr':f'timed out after {timeout_seconds}s; '+stderr[-1800:],'timeout_seconds':timeout_seconds}

def read_json(p):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except Exception:return {}

def detect_aj_blueprints(root):
    found=[]
    for p in root.rglob('*.json'):
        try:d=json.loads(p.read_text(encoding='utf-8'))
        except Exception:continue
        if isinstance(d,dict) and 'format_version' in d and isinstance(d.get('settings'),dict) and d['settings'].get('id') and isinstance(d.get('nodes'),dict) and isinstance(d.get('animations'),dict):
            types={str(v.get('type')) for v in d['nodes'].values() if isinstance(v,dict) and v.get('type')}
            if types & {'bone','item_display','block_display','text_display','structure','camera','locator'}:found.append(p)
    return found

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('input',type=Path);ap.add_argument('output',type=Path);ap.add_argument('--minecraft',required=True);ap.add_argument('--loader',required=True);ap.add_argument('--force',action='store_true');args=ap.parse_args()
    out=args.output.resolve()
    if out.exists() and any(out.iterdir()):
        if not args.force:raise SystemExit(f'output is not empty: {out}; use --force only for a disposable analysis output')
        shutil.rmtree(out)
    out.mkdir(parents=True,exist_ok=True);steps=[]
    stage=out/'00-stage'; steps.append(run('server_asset_stage.py',[args.input,stage],out/'00-stage.stdout.json'))
    if not steps[-1]['ok']:
        (out/'PIPELINE-RECEIPT.json').write_text(json.dumps({'pass':False,'steps':steps},indent=2)+'\n');raise SystemExit(2)
    source=stage/'source'
    registry_audit=out/'00-plugin-registry-audit.json';steps.append(run('plugin_registry_audit.py',['--json-out',registry_audit,'--md-out',out/'00-plugin-registry-audit.md'],out/'00-plugin-registry-audit.stdout.json'))
    if not steps[-1]['ok']:
        (out/'PIPELINE-RECEIPT.json').write_text(json.dumps({'pass':False,'steps':steps,'release_blockers':['server plugin registry audit failed']},indent=2)+'\n');raise SystemExit(2)
    inventory=out/'00-plugin-inventory.json';steps.append(run('server_plugin_inventory.py',[source,'--json-out',inventory,'--md-out',out/'00-plugin-inventory.md'],out/'00-plugin-inventory.stdout.json'))
    coverage=out/'00-plugin-coverage.json';steps.append(run('server_plugin_coverage.py',['--inventory',inventory,'--json-out',coverage,'--md-out',out/'00-plugin-coverage.md'],out/'00-plugin-coverage.stdout.json'))
    unknown_triage=out/'00-plugin-unknown-triage.json';steps.append(run('unknown_plugin_triage.py',[source,'--inventory',inventory,'--coverage',coverage,'--json-out',unknown_triage,'--md-out',out/'00-plugin-unknown-triage.md'],out/'00-plugin-unknown-triage.stdout.json'))
    probe=out/'01-probe.json';steps.append(run('server_asset_probe.py',[source,'--json-out',probe,'--md-out',out/'01-probe.md'],out/'01-probe.stdout.json'))
    pdata=read_json(probe);ecos=pdata.get('detected_ecosystems') or {};ac=pdata.get('asset_counts') or {}
    covdata=read_json(coverage)
    for d in covdata.get('discovered') or []:
        name=d.get('registry_name')
        if name and name not in ecos:
            ecos[name]={'confidence':'inventory','evidence':[f"plugin registry: {d.get('coverage')} / {d.get('impact')}"]}
    semantics=out/'02-semantics.json';steps.append(run('server_semantics_probe.py',[source,'--json-out',semantics,'--md-out',out/'02-semantics.md'],out/'02-semantics.stdout.json'))
    mythic=None
    if 'MythicMobs' in ecos:
        mythic=out/'03-mythic-ir.json';steps.append(run('mythic_skill_ir.py',[source,'--json-out',mythic,'--md-out',out/'03-mythic-ir.md'],out/'03-mythic-ir.stdout.json'))
    content=None
    if set(ecos)&{'ItemsAdder','Oraxen','Nexo','CraftEngine','ExecutableItems','ExecutableBlocks','MMOItems','EcoItems','HMCCosmetics','HMCWraps'}:
        content=out/'04-content-ir.json';steps.append(run('content_plugin_ir.py',[source,'--json-out',content,'--md-out',out/'04-content-ir.md'],out/'04-content-ir.stdout.json'))
    adjacent=out/'04b-adjacent-plugin-ir.json';steps.append(run('adjacent_plugin_ir.py',[source,'--json-out',adjacent,'--md-out',out/'04b-adjacent-plugin-ir.md'],out/'04b-adjacent-plugin-ir.stdout.json'))
    family=out/'04c-plugin-family-ir.json';steps.append(run('server_family_ir.py',[source,'--json-out',family,'--md-out',out/'04c-plugin-family-ir.md'],out/'04c-plugin-family-ir.stdout.json'))
    closure=None
    if (source/'pack.mcmeta').exists() or ac.get('java_models') or ac.get('item_definitions_1_21_4_plus'):
        closure=out/'05-rp-closure.json';steps.append(run('server_pack_resolver.py',[source,'--json-out',closure,'--md-out',out/'05-rp-closure.md'],out/'05-rp-closure.stdout.json'))
    bbmodels=sorted([*source.rglob('*.bbmodel'),*source.rglob('*.fmmodel')]); bb_ir_dir=out/'06-bbmodel-ir';bb_ir_dir.mkdir(exist_ok=True)
    for i,p in enumerate(bbmodels):
        rel=p.relative_to(source).as_posix().replace('/','__')
        steps.append(run('bbmodel_ir.py',[p,'--json-out',bb_ir_dir/f'{i:03d}-{rel}.json'],bb_ir_dir/f'{i:03d}-{rel}.stdout.json'))
        steps.append(run('bbmodel_lint.py',[p,'--json-out',bb_ir_dir/f'{i:03d}-{rel}.lint.json'],bb_ir_dir/f'{i:03d}-{rel}.lint.stdout.json',allow=(0,1)))
    aj_irs=[];ajdir=out/'07-animated-java-ir';ajdir.mkdir(exist_ok=True)
    for i,p in enumerate(detect_aj_blueprints(source)):
        j=ajdir/f'{i:03d}-{p.name}.json';aj_irs.append(j);steps.append(run('animated_java_blueprint_ir.py',[p,'--json-out',j,'--md-out',ajdir/f'{i:03d}-{p.name}.md'],ajdir/f'{i:03d}-{p.name}.stdout.json'))
    cem=None
    if ac.get('cem_jem_jpm'):
        cem=out/'08-cem-ir.json';steps.append(run('cem_ir.py',[source,'--json-out',cem,'--md-out',out/'08-cem-ir.md'],out/'08-cem-ir.stdout.json'))
    link=None
    if bbmodels and mythic:
        link=out/'09-link-audit.json';la=[source,'--mythic-ir',mythic,'--json-out',link,'--md-out',out/'09-link-audit.md']
        if content:la[1:1]=['--content-ir',content]
        steps.append(run('server_asset_link_audit.py',la,out/'09-link-audit.stdout.json',allow=(0,2)))
    # Choose the richest detected source route for target selection.
    source_kind=('fmmodel' if bbmodels and all(p.suffix.lower()=='.fmmodel' for p in bbmodels) else 'bbmodel') if bbmodels else 'animated-java' if aj_irs or ac.get('ajmodel') else 'cem' if ac.get('cem_jem_jpm') else 'geckolib' if ac.get('geo_json') else 'static'
    features=set()
    if bbmodels or aj_irs or ac.get('cem_jem_jpm'):features.add('animation')
    if aj_irs:features|={'molang','locators','effects','text-displays'}
    sem=read_json(semantics)
    if sem.get('special_bones'):features|={'hitboxes','mounts','locators'}
    renderer=out/'10-renderer.json'; rr=run('renderer_target_selector.py',['--minecraft',args.minecraft,'--loader',args.loader,'--source',source_kind,'--features',','.join(sorted(features))],out/'10-renderer.stdout.json')
    steps.append(rr)
    if rr['ok']:
        try:renderer.write_text((out/'10-renderer.stdout.json').read_text(),encoding='utf-8')
        except Exception:pass
    manifest=out/'11-conversion-manifest.json';ma=['--probe',probe,'--target-version',args.minecraft,'--loader',args.loader,'--json-out',manifest,'--md-out',out/'11-conversion-manifest.md']
    for flag,val in [('--plugin-inventory',inventory),('--plugin-coverage',coverage),('--unknown-triage',unknown_triage),('--adjacent-ir',adjacent),('--family-ir',family),('--closure',closure),('--semantics',semantics),('--mythic-ir',mythic),('--content-ir',content),('--cem-ir',cem),('--link-audit',link),('--renderer',renderer)]:
        if val and Path(val).exists():ma += [flag,val]
    for j in aj_irs:ma += ['--aj-ir',j]
    steps.append(run('server_conversion_manifest.py',ma,out/'11-conversion-manifest.stdout.json'))
    hard_fail=[x for x in steps if not x['ok']]
    linkdata=read_json(link) if link else {}; closuredata=read_json(closure) if closure else {}
    blockers=[];warnings=[]
    risk_unknown=covdata.get('unknown_conversion_risk_families') or covdata.get('unknown_conversion_risk') or []
    if risk_unknown:warnings.append(f"{len(risk_unknown)} supplied plugin JAR/config identity(ies) are unclassified; full-server parity requires manual classification.")
    if linkdata and not linkdata.get('pass',False):blockers += linkdata.get('release_blockers') or ['cross-file link audit failed']
    if closuredata.get('unresolved_references'):blockers.append(f"{len(closuredata['unresolved_references'])} unresolved non-vanilla resource-pack references")
    receipt={'pass':not hard_fail and not blockers,'input':str(args.input),'staged_source':str(source),'target':{'minecraft':args.minecraft,'loader':args.loader},'detected_ecosystems':sorted(ecos),'source_kind':source_kind,'features':sorted(features),'steps':steps,'release_blockers':blockers,'warnings':warnings,'plugin_coverage':{'registry_entries':covdata.get('registry_entries'),'counts':covdata.get('counts') or {},'unknown_conversion_risk':len(risk_unknown)},'manifest':str(manifest)}
    (out/'PIPELINE-RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'pass':receipt['pass'],'output':str(out),'detected_ecosystems':receipt['detected_ecosystems'],'source_kind':source_kind,'release_blockers':blockers,'manifest':str(manifest)},indent=2))
    raise SystemExit(0 if receipt['pass'] else 2)
if __name__=='__main__':main()
