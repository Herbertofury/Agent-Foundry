#!/usr/bin/env python3
"""Parse MythicMobs/ModelEngine-style skill lines into a migration-friendly IR."""
from __future__ import annotations
import argparse, json, re, zipfile
from pathlib import Path, PurePosixPath

TEXT_SUFFIXES=(".yml",".yaml",".txt",".conf",".cfg")
MAX_BYTES=4*1024*1024
STATE_NAMES={"state","modelstate"}
MODSTATE_NAMES={"modstate","modifystate","modifyanimation"}
META_NAMES={"skill","metaskill"}

ALIASES={
    "modelid": ("modelid","model","mid","m"),
    "state": ("state","s"),
    "speed": ("speed","sp"),
    "lerpin": ("lerpin","li"),
    "lerpout": ("lerpout","lo"),
    "force": ("force","f"),
    "priority": ("priority","pr","p"),
    "loop": ("loop","l"),
    "override": ("override","ov"),
    "skiplastframe": ("skiplastframe","skip"),
    "remove": ("remove","r"),
    "ignorelerp": ("ignorelerp","i"),
}

def parse_kv(body: str):
    out={}; positional=[]
    # Mythic args convention uses semicolons; keep bare tokens rather than dropping them.
    for token in [x.strip() for x in body.split(';') if x.strip()]:
        if '=' in token:
            k,v=token.split('=',1); out[k.strip()]=v.strip()
        else: positional.append(token)
    return out,positional

def extract_braced(s: str, start: int):
    # start points at '{'. Allow nested braces conservatively.
    depth=0; quote=None; esc=False
    for i in range(start,len(s)):
        c=s[i]
        if esc: esc=False; continue
        if c=='\\': esc=True; continue
        if quote:
            if c==quote: quote=None
            continue
        if c in "'\"": quote=c; continue
        if c=='{': depth+=1
        elif c=='}':
            depth-=1
            if depth==0:return s[start+1:i],i+1
    return s[start+1:],len(s)

def parse_head(s: str, sigil: str | None=None):
    pos=0
    if sigil and s.startswith(sigil):pos=1
    m=re.match(r'[A-Za-z0-9_.:-]+',s[pos:])
    if not m:return None,pos
    name=m.group(0); pos += len(name)
    args={}; positional=[]
    if pos < len(s) and s[pos]=='{':
        body,pos=extract_braced(s,pos); args,positional=parse_kv(body)
    return {'name':name,'args':args,'positional_args':positional},pos

def consume_ws(s,pos):
    while pos<len(s) and s[pos].isspace():pos+=1
    return pos

def canonical(args: dict, key: str):
    low={str(k).lower():v for k,v in args.items()}
    for alias in ALIASES[key]:
        if alias in low:return low[alias]
    return None

def normalize_state(mech):
    name=mech['name'].lower(); args=mech['args']
    if name not in STATE_NAMES|MODSTATE_NAMES:return None
    out={k:canonical(args,k) for k in ALIASES}
    out={k:v for k,v in out.items() if v is not None}
    out['operation']='modify' if name in MODSTATE_NAMES else ('remove' if str(out.get('remove','')).lower()=='true' else 'play')
    if 'loop' in out:out['loop_normalized']=str(out['loop']).upper()
    return out

def parse_line(raw: str):
    # Strip YAML list prefix but preserve raw for traceability.
    s=raw.strip()
    if s.startswith('-'):s=s[1:].strip()
    if not s or s.startswith('#'):return None
    mech,pos=parse_head(s)
    if not mech:return None
    pos=consume_ws(s,pos)
    targeter=None; trigger=None
    if pos<len(s) and s[pos]=='@':
        targeter,used=parse_head(s[pos:],'@'); pos += used; pos=consume_ws(s,pos)
    if pos<len(s) and s[pos]=='~':
        trigger,used=parse_head(s[pos:],'~'); pos += used; pos=consume_ws(s,pos)
    tail=s[pos:].strip()
    # Extract common terminal chance without pretending every numeric tail token is chance.
    chance=None; health_modifier=None; conditions=[]
    toks=tail.split() if tail else []
    if toks and re.fullmatch(r'(?:0(?:\.\d+)?|1(?:\.0+)?)',toks[-1]):
        chance=toks.pop()
    if toks and re.fullmatch(r'(?:[<>=].*%?|[0-9.]+%)(?:to[0-9.]+%)?',toks[0],re.I):
        health_modifier=toks.pop(0)
    conditions=toks
    ir={'raw':raw.rstrip('\n'),'mechanic':mech,'targeter':targeter,'trigger':trigger,'health_modifier':health_modifier,'chance':chance,'tail_conditions':conditions}
    state=normalize_state(mech)
    if state: ir['model_state']=state
    lname=mech['name'].lower()
    if lname in META_NAMES:
        ref=None
        for k in ('skill','s','name','meta'):
            if k in {x.lower():x for x in mech['args']}:
                real=next(x for x in mech['args'] if x.lower()==k); ref=mech['args'][real]; break
        if not ref and mech['positional_args']:ref=mech['positional_args'][0]
        ir['meta_skill_reference']=ref
        # Preserve all non-selector args as passed parameters.
        ir['meta_skill_parameters']={k:v for k,v in mech['args'].items() if k.lower() not in {'s','skill','name','meta'}}
    return ir

class Bundle:
    def __init__(self,p:Path):
        self.p=p; self.z=zipfile.ZipFile(p) if p.is_file() and zipfile.is_zipfile(p) else None
        if not self.z and not p.is_dir() and not p.is_file():raise SystemExit('input must be file, directory, or ZIP')
    def items(self):
        if self.z:
            for n in self.z.namelist():
                if not n.endswith('/') and n.lower().endswith(TEXT_SUFFIXES):
                    with self.z.open(n) as f:yield n,f.read(MAX_BYTES).decode('utf-8',errors='ignore')
        elif self.p.is_dir():
            for x in self.p.rglob('*'):
                if x.is_file() and x.name.lower().endswith(TEXT_SUFFIXES):
                    yield x.relative_to(self.p).as_posix(),x.read_text(encoding='utf-8',errors='ignore')
        else:
            yield self.p.name,self.p.read_text(encoding='utf-8',errors='ignore')
    def close(self):
        if self.z:self.z.close()

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('input',type=Path);ap.add_argument('--json-out',type=Path);ap.add_argument('--md-out',type=Path);args=ap.parse_args()
    b=Bundle(args.input); rows=[]
    try:
        for fn,text in b.items():
            for lineno,line in enumerate(text.splitlines(),1):
                stripped=line.lstrip()
                if not stripped.startswith('-'):continue
                parsed=parse_line(stripped)
                if parsed:
                    parsed['file']=fn;parsed['line']=lineno;rows.append(parsed)
    finally:b.close()
    state_rows=[x for x in rows if x.get('model_state')]
    meta_rows=[x for x in rows if x.get('meta_skill_reference')]
    report={
        'input':str(args.input),'skill_line_count':len(rows),'model_state_line_count':len(state_rows),'meta_skill_call_count':len(meta_rows),
        'mechanics':sorted({x['mechanic']['name'] for x in rows},key=str.lower),
        'triggers':sorted({x['trigger']['name'] for x in rows if x.get('trigger')},key=str.lower),
        'targeters':sorted({x['targeter']['name'] for x in rows if x.get('targeter')},key=str.lower),
        'lines':rows,
        'migration_notes':[
            'Preserve source line order and meta-skill references; do not flatten delayed/cancelled/state-mutating graphs blindly.',
            'Treat model_state fields as animation-controller semantics, including loop/override/priority/lerp/speed mutations.',
            'Resolve targeters, triggers, conditions, chance, and passed meta-skill parameters independently in native mod logic.'
        ]
    }
    text=json.dumps(report,indent=2)
    if args.json_out:args.json_out.parent.mkdir(parents=True,exist_ok=True);args.json_out.write_text(text+'\n',encoding='utf-8')
    if args.md_out:
        lines=['# Mythic Skill IR','',f"- Skill lines: **{len(rows)}**",f"- Model state lines: **{len(state_rows)}**",f"- Meta-skill calls: **{len(meta_rows)}**",f"- Mechanics: {', '.join(report['mechanics']) or '(none)'}",f"- Triggers: {', '.join(report['triggers']) or '(none)'}",f"- Targeters: {', '.join(report['targeters']) or '(none)'}",'', '## Parsed lines']
        for x in rows:
            lines.append(f"- `{x['file']}:{x['line']}` `{x['mechanic']['name']}` target=`{(x.get('targeter') or {}).get('name','-')}` trigger=`{(x.get('trigger') or {}).get('name','-')}`")
        args.md_out.parent.mkdir(parents=True,exist_ok=True);args.md_out.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(text)
if __name__=='__main__':main()
