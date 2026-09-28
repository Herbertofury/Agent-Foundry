#!/usr/bin/env python3
"""Manage evidence-backed pitfall learning with quarantine, events, promotion, review, and retirement."""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REQUIRED=("id","title","scope","trigger","failure","replacement","verification","basis","status")
PROMOTION_BASES={"explicit-user-correction","objective-reproduction","repeated-independent-failure","authoritative-specification","observed-behavior","explicit-user-universal-rule"}
FORBIDDEN_WEAKENING=(r"\bdisable (?:all )?tests\b",r"\bskip (?:all )?verification\b",r"\bignore (?:safety|permissions|higher-priority instructions)\b",r"\bhide (?:errors|failures)\b",r"\bdelete without (?:approval|permission)\b",r"\bclaim success without evidence\b")
FIXTURE_MARKERS=("test candidate","test only","test evidence","example only","fixture rule")

def now()->str:return datetime.now(timezone.utc).isoformat()
def review_after()->str:return (datetime.now(timezone.utc)+timedelta(days=180)).isoformat()
def load(path:Path)->dict[str,Any]:
    if not path.exists():return {"schema_version":2,"entries":[]}
    data=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data,dict) or not isinstance(data.get("entries"),list):raise ValueError(f"Invalid ledger: {path}")
    return data
def save(path:Path,data:dict[str,Any]):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def next_id(entries,prefix):
    nums=[int(m.group(1)) for e in entries if (m:=re.fullmatch(rf"{prefix}-(\d+)",str(e.get("id",""))))]
    return f"{prefix}-{max(nums,default=0)+1:03d}"
def fingerprint(entry):
    text="|".join(str(entry.get(k,"")) for k in ("scope","trigger","failure","replacement"))
    return hashlib.sha256(re.sub(r"\s+"," ",text.lower()).strip().encode()).hexdigest()
def append_event(refs:Path,event_type:str,entry:dict[str,Any],extra:dict[str,Any]|None=None):
    record={"schema_version":1,"event_type":event_type,"at_utc":now(),"entry_id":entry.get("id"),"fingerprint":fingerprint(entry),"scope":entry.get("scope"),"basis":entry.get("basis",[])}
    if extra:record.update(extra)
    with (refs/"incidents.jsonl").open("a",encoding="utf-8") as f:f.write(json.dumps(record,ensure_ascii=False)+"\n")
def validate_entry(entry,quarantine=False):
    errors=[]
    for field in REQUIRED:
        if entry.get(field) in (None,"",[]):errors.append(f"{entry.get('id','<unknown>')}: missing {field}")
    if not isinstance(entry.get("basis"),list):errors.append(f"{entry.get('id','<unknown>')}: basis must be list")
    text=" ".join(str(entry.get(k,"")) for k in ("title","scope","failure","replacement","verification","evidence"))
    for pat in FORBIDDEN_WEAKENING:
        if re.search(pat,text,re.I):errors.append(f"{entry.get('id')}: forbidden weakening: {pat}")
    if not quarantine and any(m in text.lower() for m in FIXTURE_MARKERS):errors.append(f"{entry.get('id')}: fixture/test marker forbidden in active ledger")
    expected="quarantine" if quarantine else "active"
    if entry.get("status")!=expected:errors.append(f"{entry.get('id')}: status must be {expected}")
    return errors
def promotion_allowed(entry):
    basis=set(entry.get("basis",[]));evidence=entry.get("evidence",[])
    if not basis.issubset(PROMOTION_BASES):return False,"unsupported promotion basis"
    if "explicit-user-universal-rule" in basis:return True,"explicit user universalization"
    if {"explicit-user-correction","objective-reproduction"}.issubset(basis):return True,"correction plus objective reproduction"
    if "repeated-independent-failure" in basis and len(evidence)>=2:return True,"repeated independent evidence"
    if {"authoritative-specification","observed-behavior"}.issubset(basis):return True,"specification plus observed behavior"
    return False,"promotion gate not satisfied"
def render(entries,title,quarantine=False):
    lines=[f"# {title}",""]
    if not entries:return "\n".join(lines+["_No entries._",""])
    for e in entries:
        lines += [f"## {e['id']} — {e['title']}","",f"- **Scope:** {e['scope']}",f"- **Trigger:** {e['trigger']}",f"- **{'Observed failure' if quarantine else 'Failure'}:** {e['failure']}",f"- **{'Candidate replacement' if quarantine else 'Required behavior'}:** {e['replacement']}",f"- **Verification:** {e['verification']}",f"- **Basis:** {', '.join(e['basis'])}",f"- **Confidence:** {e.get('confidence','unknown')}",f"- **Next review:** {e.get('review_after_utc','unscheduled')}",""]
    return "\n".join(lines)
def sync_views(root,approved,quarantine,archive=None):
    refs=root/"references";assets=root/"assets/agents-md-hybrid/.agents"
    approved_text=render(approved["entries"],"Active Learned Pitfalls")
    quarantine_text=render(quarantine["entries"],"Pitfalls Quarantine",True)
    for p,t in ((refs/"PITFALLS.md",approved_text),(refs/"PITFALLS-QUARANTINE.md",quarantine_text),(assets/"PITFALLS.md",approved_text),(assets/"PITFALLS-QUARANTINE.md",quarantine_text)):
        p.parent.mkdir(parents=True,exist_ok=True);p.write_text(t,encoding="utf-8")
    save(refs/"approved-rules.json",approved);save(refs/"candidates.json",quarantine)
    if archive is not None:save(refs/"retired-rules.json",archive)
def validate(root):
    refs=root/"references";approved=load(refs/"pitfalls-approved.json");quarantine=load(refs/"pitfalls-quarantine.json");archive=load(refs/"pitfalls-archive.json")
    errors=[];ids=set();fps=set()
    for is_q,data in ((False,approved),(True,quarantine)):
        for e in data["entries"]:
            errors+=validate_entry(e,is_q)
            if e.get("id") in ids:errors.append(f"duplicate id: {e.get('id')}")
            ids.add(e.get("id"));fp=fingerprint(e)
            if not is_q and fp in fps:errors.append(f"duplicate active semantic fingerprint: {e.get('id')}")
            if not is_q:fps.add(fp)
    event_path=refs/"incidents.jsonl"
    if event_path.exists():
        for n,line in enumerate(event_path.read_text(encoding="utf-8").splitlines(),1):
            if not line.strip():continue
            try:json.loads(line)
            except json.JSONDecodeError as exc:errors.append(f"incidents.jsonl:{n}: {exc}")
    sync_views(root,approved,quarantine,archive)
    if errors:
        print("Pitfall validation failed:",file=sys.stderr)
        for e in errors:print(f"- {e}",file=sys.stderr)
        return 1
    print(f"Validated {len(approved['entries'])} active, {len(quarantine['entries'])} quarantined, {len(archive['entries'])} retired")
    return 0
def capture(root,args):
    refs=root/"references";a=load(refs/"pitfalls-approved.json");q=load(refs/"pitfalls-quarantine.json");all_entries=a["entries"]+q["entries"]
    e={"id":next_id(all_entries,"Q"),"title":args.title,"scope":args.scope,"trigger":args.trigger,"failure":args.failure,"root_cause":args.root_cause,"wrong_behavior":args.wrong_behavior,"replacement":args.replacement,"verification":args.verification,"basis":args.basis,"evidence":args.evidence,"evidence_fingerprints":[hashlib.sha256(x.encode()).hexdigest() for x in args.evidence],"independent_incident_count":len(args.evidence),"confidence":args.confidence,"status":"quarantine","rule_version":1,"created_at_utc":now(),"last_reviewed_at_utc":now(),"review_after_utc":review_after()}
    errs=validate_entry(e,True)
    if errs:
        for x in errs:print(x,file=sys.stderr)
        return 1
    q["entries"].append(e);save(refs/"pitfalls-quarantine.json",q);append_event(refs,"candidate_captured",e);sync_views(root,a,q,load(refs/"pitfalls-archive.json"));print(f"Captured {e['id']}");return 0
def promote(root,pid):
    refs=root/"references";a=load(refs/"pitfalls-approved.json");q=load(refs/"pitfalls-quarantine.json");idx=next((i for i,e in enumerate(q["entries"]) if e.get("id")==pid),None)
    if idx is None:print(f"Not found: {pid}",file=sys.stderr);return 2
    e=q["entries"][idx];ok,reason=promotion_allowed(e)
    if not ok:print(f"Promotion denied: {reason}",file=sys.stderr);return 1
    p=dict(e);p.update({"id":next_id(a["entries"],"P"),"status":"active","promoted_at_utc":now(),"promotion_reason":reason,"last_reviewed_at_utc":now(),"review_after_utc":review_after()})
    errs=validate_entry(p,False)
    if errs:
        for x in errs:print(x,file=sys.stderr)
        return 1
    a["entries"].append(p);del q["entries"][idx];save(refs/"pitfalls-approved.json",a);save(refs/"pitfalls-quarantine.json",q);append_event(refs,"rule_promoted",p,{"source_candidate_id":pid,"reason":reason});sync_views(root,a,q,load(refs/"pitfalls-archive.json"));print(f"Promoted {pid} to {p['id']}");return 0
def retire(root,pid,reason):
    refs=root/"references";a=load(refs/"pitfalls-approved.json");q=load(refs/"pitfalls-quarantine.json");archive=load(refs/"pitfalls-archive.json");idx=next((i for i,e in enumerate(a["entries"]) if e.get("id")==pid),None)
    if idx is None:print(f"Not found: {pid}",file=sys.stderr);return 2
    e=a["entries"].pop(idx);e.update({"status":"retired","retired_at_utc":now(),"retirement_reason":reason});archive["entries"].append(e);save(refs/"pitfalls-approved.json",a);save(refs/"pitfalls-archive.json",archive);append_event(refs,"rule_retired",e,{"reason":reason});sync_views(root,a,q,archive);print(f"Retired {pid}");return 0

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--skill-root",type=Path,default=Path(__file__).resolve().parents[1]);sub=ap.add_subparsers(dest="command",required=True)
    sub.add_parser("validate");sub.add_parser("render")
    c=sub.add_parser("capture")
    for name in ("title","scope","trigger","failure","replacement","verification"):c.add_argument(f"--{name.replace('_','-')}",required=True)
    c.add_argument("--root-cause",default="unknown");c.add_argument("--wrong-behavior",default="unknown");c.add_argument("--basis",action="append",required=True,choices=sorted(PROMOTION_BASES));c.add_argument("--evidence",action="append",default=[]);c.add_argument("--confidence",choices=("low","medium","high"),default="medium")
    p=sub.add_parser("promote");p.add_argument("id");r=sub.add_parser("retire");r.add_argument("id");r.add_argument("--reason",required=True)
    args=ap.parse_args();root=args.skill_root.resolve()
    if args.command=="validate":return validate(root)
    if args.command=="render":
        refs=root/"references";sync_views(root,load(refs/"pitfalls-approved.json"),load(refs/"pitfalls-quarantine.json"),load(refs/"pitfalls-archive.json"));print("Rendered");return 0
    if args.command=="capture":return capture(root,args)
    if args.command=="promote":return promote(root,args.id)
    if args.command=="retire":return retire(root,args.id,args.reason)
    return 2
if __name__=="__main__":raise SystemExit(main())
