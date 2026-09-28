#!/usr/bin/env python3
"""Retarget creature-spec animations by stable semantic bone IDs."""
from __future__ import annotations
import argparse,json
from pathlib import Path

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('source',type=Path);ap.add_argument('target',type=Path);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--replace',action='store_true');ap.add_argument('--position-scale',type=float,default=1.0);a=ap.parse_args();src=json.loads(a.source.read_text());dst=json.loads(a.target.read_text());tb={str(b.get('id')) for b in dst.get('bones',[]) if isinstance(b,dict)};missing=set();copied=[]
    arr=dst.setdefault('animations',[]);byname={str(x.get('name')):i for i,x in enumerate(arr) if isinstance(x,dict) and x.get('name')}
    for anim in src.get('animations',[]):
        if not isinstance(anim,dict):continue
        clone=json.loads(json.dumps(anim));tracks=clone.get('bones',{}) if isinstance(clone.get('bones'),dict) else {}
        for bid in list(tracks):
            if bid not in tb:missing.add(bid);del tracks[bid];continue
            for channel,keys in tracks[bid].items():
                if channel=='position' and isinstance(keys,list):
                    for k in keys:
                        if isinstance(k,dict) and isinstance(k.get('value'),list):k['value']=[float(v)*a.position_scale for v in k['value']]
        name=str(clone.get('name'))
        if name in byname:
            if a.replace:arr[byname[name]]=clone;copied.append(name)
        else:arr.append(clone);copied.append(name)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(dst,indent=2)+'\n',encoding='utf-8');print(json.dumps({'result':'pass','animations_copied':copied,'source_bones_missing_on_target':sorted(missing),'position_scale':a.position_scale,'note':'semantic-ID retarget only; native visual QA must repair proportion/contact/arc differences'},indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
