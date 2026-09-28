#!/usr/bin/env python3
"""Export the canonical server-plugin conversion registry to Markdown and CSV."""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
DEFAULT=Path(__file__).resolve().parent.parent/'references'/'server-plugin-registry.json'

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--registry',type=Path,default=DEFAULT);ap.add_argument('--md-out',type=Path);ap.add_argument('--csv-out',type=Path);args=ap.parse_args()
    reg=json.loads(args.registry.read_text(encoding='utf-8'));es=reg.get('entries') or []
    if args.md_out:
        lines=['# Minecraft Server Plugin Conversion Coverage Atlas','',f"Research/registry snapshot: **{reg.get('snapshot_date')}**.",'',f"Canonical registry entries: **{len(es)}**.",'', '> This is a conversion coverage atlas, not permission to copy or redistribute proprietary plugins/assets. Unknown plugins are surfaced by the inventory/coverage gate instead of being silently ignored.','', '## Coverage levels','', '- **first-class** — dedicated semantic adapter exists.','- **generic** — normalized adapter covers the family with unclassified-key preservation.','- **detect-only** — recognized and risk-classified; inspect/translate source semantics when present.','- **context-only** — tracked as dependency/environment context, not normally converted as content.','', '## Registry','', '|Tier|Plugin/system|Category|Impact|Coverage|Era|Notes|','|---|---|---|---|---|---|---|']
        for e in es:
            name=f"[{e['name']}]({e['source']})" if e.get('source') else e['name']
            note=(e.get('notes') or '').replace('|','\\|')
            lines.append(f"|{e.get('tier','')}|{name}|{e.get('category','')}|{e.get('impact','')}|{e.get('adapter','')}|{e.get('era','')}|{note}|")
        args.md_out.parent.mkdir(parents=True,exist_ok=True);args.md_out.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    if args.csv_out:
        args.csv_out.parent.mkdir(parents=True,exist_ok=True)
        with args.csv_out.open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=['tier','name','aliases','category','impact','adapter','era','source','notes','markers']);w.writeheader()
            for e in es:
                row=dict(e);row['aliases']='; '.join(e.get('aliases') or []);row['markers']='; '.join(e.get('markers') or []);w.writerow({k:row.get(k,'') for k in w.fieldnames})
    print(json.dumps({'entries':len(es),'snapshot':reg.get('snapshot_date'),'md':str(args.md_out) if args.md_out else None,'csv':str(args.csv_out) if args.csv_out else None},indent=2))
if __name__=='__main__':main()
