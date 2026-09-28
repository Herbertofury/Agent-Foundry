#!/usr/bin/env python3
"""Map reference-vs-candidate silhouette residuals into actionable connected regions."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import cv2,numpy as np
from PIL import Image


def load_mask(path:Path)->np.ndarray:
    im=cv2.imread(str(path),cv2.IMREAD_UNCHANGED)
    if im is None: raise ValueError(f'could not read {path}')
    if im.ndim==3 and im.shape[2]==4 and im[:,:,3].min()<250: m=im[:,:,3]>8
    else:
        if im.ndim==3: gray=cv2.cvtColor(im[:,:,:3],cv2.COLOR_BGR2GRAY)
        else: gray=im
        # binary masks usually have dark bg/bright fg; rendered previews are handled conservatively.
        vals=np.unique(gray)
        if len(vals)<=3: m=gray>127
        else: m=gray<245
    return m.astype(np.uint8)


def comps(mask:np.ndarray,min_area:int)->list[dict]:
    n,lab,stats,cent=cv2.connectedComponentsWithStats(mask.astype(np.uint8),8); out=[]
    for i in range(1,n):
        x,y,w,h,a=map(int,stats[i]);
        if a<min_area: continue
        out.append({'area':a,'bbox':[x,y,x+w,y+h],'centroid':[round(float(cent[i][0]),3),round(float(cent[i][1]),3)]})
    return sorted(out,key=lambda x:x['area'],reverse=True)


def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('reference',type=Path); ap.add_argument('candidate',type=Path); ap.add_argument('--out',type=Path,required=True); ap.add_argument('--report',type=Path,required=True); ap.add_argument('--min-area',type=int,default=4); a=ap.parse_args()
    r=load_mask(a.reference); c=load_mask(a.candidate)
    if c.shape!=r.shape: c=cv2.resize(c,(r.shape[1],r.shape[0]),interpolation=cv2.INTER_NEAREST)
    missing=(r>0)&~(c>0); excess=(c>0)&~(r>0); inter=(r>0)&(c>0); union=(r>0)|(c>0); iou=1.0 if not union.any() else float(inter.sum()/union.sum())
    vis=np.zeros((r.shape[0],r.shape[1],4),dtype=np.uint8); vis[:,:,3]=255; vis[inter]=[70,180,90,255]; vis[missing]=[40,70,255,255]; vis[excess]=[255,70,50,255]
    a.out.parent.mkdir(parents=True,exist_ok=True); Image.fromarray(vis,'RGBA').save(a.out)
    report={'silhouette_iou':round(iou,6),'missing_pixels':int(missing.sum()),'excess_pixels':int(excess.sum()),'missing_regions':comps(missing,a.min_area),'excess_regions':comps(excess,a.min_area),'overlay':str(a.out),'legend':{'green':'agreement','blue':'reference missing from candidate','red':'candidate excess'},'next_action':'Fix the largest coherent missing/excess region at the earliest causal geometry/camera owner; do not hide silhouette residuals with texture.'}
    a.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8'); print(json.dumps(report,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
