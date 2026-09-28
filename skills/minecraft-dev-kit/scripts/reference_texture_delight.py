#!/usr/bin/env python3
"""Create a conservative draft albedo/palette from a reference-baked texture atlas.

Low-frequency luminance is treated as probable preview illumination and normalized before
palette reduction. This is a draft material-recovery aid, not proof of the artist's source
albedo. Preserve the original recovered atlas and coverage/confidence evidence beside it.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import cv2,numpy as np
from PIL import Image


def quantize_covered(rgb:np.ndarray,mask:np.ndarray,count:int)->np.ndarray:
    out=rgb.copy(); pix=rgb[mask]
    if len(pix)==0:return out
    im=Image.fromarray(pix.reshape(1,-1,3).astype(np.uint8),'RGB'); q=im.quantize(colors=max(2,count),method=Image.Quantize.MEDIANCUT).convert('RGB'); qp=np.asarray(q).reshape(-1,3); out[mask]=qp; return out

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('texture',type=Path);ap.add_argument('--coverage',type=Path);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--emissive',type=Path);ap.add_argument('--report',type=Path,required=True);ap.add_argument('--palette',type=int,default=24);ap.add_argument('--sigma',type=float,default=3.0);ap.add_argument('--gain-min',type=float,default=.65);ap.add_argument('--gain-max',type=float,default=1.55);ap.add_argument('--emissive-percentile',type=float,default=98.5);a=ap.parse_args()
    rgba=np.asarray(Image.open(a.texture).convert('RGBA'),dtype=np.uint8); rgb=rgba[:,:,:3].astype(np.float32); mask=(np.asarray(Image.open(a.coverage).convert('L'))>0) if a.coverage else rgba[:,:,3]>0
    if not np.any(mask): print('coverage is empty'); return 2
    lum=cv2.cvtColor(rgb.astype(np.uint8),cv2.COLOR_RGB2GRAY).astype(np.float32)+1.0; m=mask.astype(np.float32); sigma=max(.5,float(a.sigma)); num=cv2.GaussianBlur(lum*m,(0,0),sigma); den=cv2.GaussianBlur(m,(0,0),sigma); illum=num/np.maximum(den,.05); target=float(np.median(lum[mask])); gain=np.clip(target/np.maximum(illum,1.0),a.gain_min,a.gain_max); flat=np.clip(rgb*gain[:,:,None],0,255).astype(np.uint8); flat=quantize_covered(flat,mask,int(a.palette)); out=np.dstack([flat,np.where(mask,255,0).astype(np.uint8)])
    a.output.parent.mkdir(parents=True,exist_ok=True);Image.fromarray(out,'RGBA').save(a.output)
    em_path=None
    if a.emissive:
        vals=lum[mask]; thresh=float(np.percentile(vals,a.emissive_percentile)); sat=(rgb.max(axis=2)-rgb.min(axis=2)); em=mask&(lum>=thresh)&(sat>=np.percentile(sat[mask],60)); Image.fromarray((em.astype(np.uint8)*255),'L').save(a.emissive); em_path=str(a.emissive)
    before=float(np.std(lum[mask])); after_l=cv2.cvtColor(flat,cv2.COLOR_RGB2GRAY).astype(np.float32); after=float(np.std(after_l[mask])); report={'result':'pass','coverage_fraction':round(float(mask.mean()),6),'palette_target':int(a.palette),'input_luma_std':round(before,4),'draft_luma_std':round(after,4),'median_luma':round(target,4),'output':str(a.output),'emissive_candidate_mask':em_path,'note':'Low-frequency de-lighting is only a draft albedo hypothesis. Validate material clusters against multiple views and native Minecraft lighting.'};a.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
