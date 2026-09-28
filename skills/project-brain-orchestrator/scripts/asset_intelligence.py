#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_HUBS=ROOT/'assets/memory/FEATURE-FOUNDRY-SOURCE-HUBS.seed.json'
DEFAULT_OBJECTS=ROOT/'assets/memory/FEATURE-FOUNDRY-OBJECT-INTELLIGENCE.seed.json'
DEFAULT_OUTPUT=ROOT/'references/FEATURE-FOUNDRY-ASSET-INTELLIGENCE.md'
MODES={'official_api','oauth_api','public_api','oembed','browser_clipper','manual_import','launcher','legacy_existing_clients'}
STATUSES={'active','restricted','legacy_existing_clients','clipper_only','manual_only','verify_before_enable'}
TOOL_STATUS={'candidate','recommended','experimental','rejected'}
MATURITY={'production','production-capable','mature-research','active-research','research-grade','experimental'}

def load(path:Path): return json.loads(path.read_text(encoding='utf-8'))
def https(url:str)->bool:
    try:
        p=urlparse(url); return p.scheme=='https' and bool(p.netloc)
    except Exception: return False

def validate_hubs(data):
    e=[]
    if data.get('schema_version')!=1: e.append('source hubs schema_version must be 1')
    hubs=data.get('hubs')
    if not isinstance(hubs,list) or not hubs: return e+['source hubs must be a non-empty list']
    ids=[]
    required=('id','name','media_types','adapter_modes','preferred_mode','status','auth','rate_limit','attribution','rights_policy','moderation','cache_policy','fallback','official_docs','verified_at','review_due')
    for h in hubs:
        if not isinstance(h,dict): e.append('source hub entry must be an object'); continue
        missing=[k for k in required if not h.get(k)]
        if missing: e.append(f"hub {h.get('id','?')} missing {', '.join(missing)}")
        iid=h.get('id'); ids.append(iid)
        modes=set(h.get('adapter_modes') or [])
        if not modes or not modes<=MODES: e.append(f'hub {iid} has invalid adapter_modes')
        if h.get('preferred_mode') not in modes: e.append(f'hub {iid} preferred_mode is not enabled')
        if h.get('status') not in STATUSES: e.append(f'hub {iid} has invalid status')
        docs=h.get('official_docs') or []
        if not docs or any(not https(x) for x in docs): e.append(f'hub {iid} official_docs must be HTTPS URLs')
        if h.get('status') in {'clipper_only','manual_only'} and modes & {'official_api','oauth_api','public_api'}:
            e.append(f'hub {iid} cannot claim an API while status is {h.get("status")}')
        if h.get('status')=='legacy_existing_clients' and 'legacy_existing_clients' not in modes:
            e.append(f'hub {iid} legacy status requires legacy adapter mode')
        for field in ('rights_policy','attribution','fallback','cache_policy'):
            if len(str(h.get(field,'')))<12: e.append(f'hub {iid} has weak {field}')
    if len(ids)!=len(set(ids)): e.append('duplicate source hub IDs')
    return e

def validate_objects(data):
    e=[]
    if data.get('schema_version')!=1: e.append('object intelligence schema_version must be 1')
    lanes=data.get('quality_lanes') or []
    if [x.get('id') for x in lanes] != ['instant-preview','interactive-draft','high-fidelity']:
        e.append('quality lanes must be instant-preview, interactive-draft, high-fidelity')
    stages=data.get('derivation_pipeline') or []
    orders=[x.get('order') for x in stages]
    if orders!=list(range(1,len(stages)+1)) or len(stages)<12: e.append('derivation pipeline must be ordered and have at least 12 stages')
    ids=[]
    for s in stages:
        iid=s.get('id'); ids.append(iid)
        if not s.get('title') or not s.get('outputs'): e.append(f'stage {iid} missing title/outputs')
        if s.get('reversible') is not True: e.append(f'stage {iid} must be reversible')
    if len(ids)!=len(set(ids)): e.append('duplicate derivation stage IDs')
    tools=data.get('tools') or []
    tids=[]
    for t in tools:
        iid=t.get('id'); tids.append(iid)
        if t.get('status') not in TOOL_STATUS: e.append(f'tool {iid} has invalid status')
        if t.get('maturity') not in MATURITY: e.append(f'tool {iid} has invalid maturity')
        src=t.get('official_sources') or []
        if not src or any(not https(x) for x in src): e.append(f'tool {iid} requires HTTPS official_sources')
        for field in ('role','license_review','strengths','constraints','fallbacks'):
            if not t.get(field): e.append(f'tool {iid} missing {field}')
    if len(tids)!=len(set(tids)): e.append('duplicate tool IDs')
    corpus=json.dumps(data,ensure_ascii=False).lower()
    for phrase in ('immutable original','reversible','simplest truthful representation','visible uncertainty','blender','rights'):
        if phrase not in corpus: e.append(f'object intelligence missing required concept: {phrase}')
    return e

def render(hubs,objects):
    out=['# Feature Foundry Asset Intelligence','','**Verified:** '+hubs.get('verified_at_utc',''), '**Review due:** '+str(hubs.get('review_due','')),'',
         'This document is generated from the machine-readable source-hub and object-intelligence catalogs. It is a capability and design registry, not a promise that every adapter is already implemented.','',
         '## Source capability matrix','',
         '| Source | Media | Preferred route | Status | Auth / access | Rights and attribution | Fallback |','|---|---|---|---|---|---|---|']
    for h in hubs['hubs']:
        out.append('| {name} | {media} | `{preferred}` | `{status}` | {auth} | {rights} {attrib} | {fallback} |'.format(
            name=h['name'].replace('|','/'), media=', '.join(h['media_types']), preferred=h['preferred_mode'],status=h['status'],
            auth=h['auth'].replace('|','/'),rights=h['rights_policy'].replace('|','/'),attrib=h['attribution'].replace('|','/'),fallback=h['fallback'].replace('|','/')))
    out += ['', '### Adapter contract','']
    for r in hubs['adapter_contract']['requirements']: out.append(f'- {r}')
    out += ['', '## Progressive object quality lanes','']
    for lane in objects['quality_lanes']:
        out += [f"### {lane['id']}",f"- **Target:** {lane['latency_target']}",f"- **Purpose:** {lane['purpose']}",f"- **Promotion gate:** {lane['promotion_gate']}",'']
    out += ['## Reversible derivation graph','']
    for s in objects['derivation_pipeline']:
        out.append(f"{s['order']}. **{s['title']}** (`{s['id']}`) — {', '.join(s['outputs'])}")
    out += ['', '## Candidate tool and runtime registry','', '| Tool | Role | Status | Maturity | Key constraints / fallback |','|---|---|---|---|---|']
    for t in objects['tools']:
        out.append(f"| {t['name']} | {t['role']} | `{t['status']}` | `{t['maturity']}` | {'; '.join(t['constraints'])}; fallback: {'; '.join(t['fallbacks'])} |")
    out += ['', '## Runtime rules','']
    for r in objects['runtime_rules']: out.append(f'- {r}')
    return '\n'.join(out)+'\n'

def command_validate(args):
    hubs=load(args.hubs); objects=load(args.objects)
    errors=validate_hubs(hubs)+validate_objects(objects)
    if errors:
        print('\n'.join(errors)); return 1
    print(f"Asset intelligence valid: {len(hubs['hubs'])} hubs, {len(objects['derivation_pipeline'])} stages, {len(objects['tools'])} tools")
    return 0

def command_render(args):
    hubs=load(args.hubs); objects=load(args.objects)
    errors=validate_hubs(hubs)+validate_objects(objects)
    if errors:
        print('\n'.join(errors)); return 1
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(render(hubs,objects),encoding='utf-8')
    print(args.output); return 0

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='command',required=True)
    for name,fn in [('validate',command_validate),('render',command_render)]:
        s=sub.add_parser(name); s.add_argument('--hubs',type=Path,default=DEFAULT_HUBS); s.add_argument('--objects',type=Path,default=DEFAULT_OBJECTS)
        if name=='render': s.add_argument('--output',type=Path,default=DEFAULT_OUTPUT)
        s.set_defaults(fn=fn)
    a=p.parse_args(); return a.fn(a)
if __name__=='__main__': raise SystemExit(main())
