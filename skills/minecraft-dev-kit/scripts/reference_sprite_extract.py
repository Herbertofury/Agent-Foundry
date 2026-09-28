#!/usr/bin/env python3
"""Extract pixel-art icons/sprites from an authorized reference sheet.

Supports explicit grid extraction or alpha/background connected components. Output scaling
uses nearest-neighbor only. If the marketplace/reference preview has already been filtered,
compressed or rescaled non-integrally, source pixels are not uniquely recoverable; the
manifest records that the result is a reconstruction from observed pixels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
    return h.hexdigest()


def foreground(rgba: np.ndarray, alpha_threshold: int) -> np.ndarray:
    a=rgba[:,:,3]
    if int(a.min())<250:
        m=a>alpha_threshold
        if .0001<float(m.mean())<.9999:return m
    rgb=rgba[:,:,:3].astype(np.float32);h,w=rgb.shape[:2];b=max(1,min(h,w)//40)
    border=np.concatenate([rgb[:b].reshape(-1,3),rgb[-b:].reshape(-1,3),rgb[:,:b].reshape(-1,3),rgb[:,-b:].reshape(-1,3)])
    bg=np.median(border,axis=0);bd=np.linalg.norm(border-bg,axis=1);dist=np.linalg.norm(rgb-bg.reshape(1,1,3),axis=2);t=max(12.,float(np.percentile(bd,97))+8.)
    return dist>t


def trim_box(alpha_or_mask: np.ndarray, pad: int=0) -> tuple[int,int,int,int] | None:
    ys,xs=np.nonzero(alpha_or_mask)
    if len(xs)==0:return None
    h,w=alpha_or_mask.shape;x0=max(0,int(xs.min())-pad);y0=max(0,int(ys.min())-pad);x1=min(w,int(xs.max())+1+pad);y1=min(h,int(ys.max())+1+pad);return x0,y0,x1,y1


def centered_resize(crop: Image.Image, size: int) -> Image.Image:
    if size<=0:return crop
    w,h=crop.size;scale=min(size/max(1,w),size/max(1,h));nw=max(1,int(round(w*scale)));nh=max(1,int(round(h*scale)))
    rs=crop.resize((nw,nh),Image.Resampling.NEAREST);out=Image.new('RGBA',(size,size),(0,0,0,0));out.alpha_composite(rs,((size-nw)//2,(size-nh)//2));return out


def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('image',type=Path);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--mode',choices=['auto','grid','components'],default='auto');ap.add_argument('--rows',type=int,default=0);ap.add_argument('--cols',type=int,default=0);ap.add_argument('--target-size',type=int,default=0);ap.add_argument('--padding',type=int,default=0);ap.add_argument('--min-area',type=int,default=16);ap.add_argument('--alpha-threshold',type=int,default=8);ap.add_argument('--prefix',default='icon');args=ap.parse_args()
    src=Image.open(args.image).convert('RGBA');arr=np.asarray(src,dtype=np.uint8);h,w=arr.shape[:2];mask=foreground(arr,args.alpha_threshold)
    mode=args.mode
    if mode=='auto': mode='grid' if args.rows>0 and args.cols>0 else 'components'
    boxes=[]
    if mode=='grid':
        if args.rows<=0 or args.cols<=0:print('grid mode requires --rows and --cols');return 2
        for r in range(args.rows):
            y0=round(r*h/args.rows);y1=round((r+1)*h/args.rows)
            for c in range(args.cols):
                x0=round(c*w/args.cols);x1=round((c+1)*w/args.cols);sub=mask[y0:y1,x0:x1];tb=trim_box(sub,args.padding)
                if tb:
                    a,b,cc,d=tb;boxes.append((x0+a,y0+b,x0+cc,y0+d,r,c))
    else:
        m=(mask.astype(np.uint8)*255);n,lab,stats,_=cv2.connectedComponentsWithStats(m,8);raw=[]
        for i in range(1,n):
            x,y,bw,bh,area=map(int,stats[i])
            if area>=args.min_area:raw.append((x,y,x+bw,y+bh,area))
        raw.sort(key=lambda q:(q[1],q[0]));boxes=[(x0,y0,x1,y1,None,None) for x0,y0,x1,y1,_ in raw]
    if not boxes:print('No sprites detected');return 2
    args.out.mkdir(parents=True,exist_ok=True);records=[]
    for i,(x0,y0,x1,y1,row,col) in enumerate(boxes,1):
        crop=src.crop((x0,y0,x1,y1));out=centered_resize(crop,args.target_size);name=f'{args.prefix}_{i:03d}.png';p=args.out/name;out.save(p)
        pix=np.asarray(out,dtype=np.uint8);alpha=pix[:,:,3]>0;unique=int(len(np.unique(pix[:,:,:3][alpha],axis=0))) if np.any(alpha) else 0
        records.append({'id':i,'file':name,'source_box':[x0,y0,x1,y1],'grid':[row,col] if row is not None else None,'output_size':list(out.size),'opaque_fraction':round(float(alpha.mean()),6),'unique_rgb_colors':unique,'sha256':sha256(p)})
    manifest={'schema_version':1,'source':str(args.image.resolve()),'source_sha256':sha256(args.image),'mode':mode,'source_size':[w,h],'target_size':args.target_size or None,'sprite_count':len(records),'sprites':records,'note':'Outputs preserve observed pixels with nearest-neighbor scaling. A filtered/compressed/non-integrally-scaled preview cannot reveal exact original source pixels.'}
    (args.out/'SPRITES.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8');print(json.dumps({'result':'pass','sprites':len(records),'manifest':str(args.out/'SPRITES.json')},indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
