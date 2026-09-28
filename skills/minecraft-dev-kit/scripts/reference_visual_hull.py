#!/usr/bin/env python3
"""Reconstruct a conservative Minecraft-space visual hull from calibrated silhouettes.

Each occupied voxel must project inside every supplied silhouette. The hull is then
compressed into deterministic axis-aligned cuboids and UV-packed into a creature spec.
This produces a zero-start blockout, not hidden-surface ground truth: silhouette visual
hulls cannot recover concavities that no supplied view exposes.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from creature_uv_packer import pack, next_pow2
from reference_cuboid_fit import project, render_mask, metrics


def vec3(value: Any, name: str) -> np.ndarray:
    if not isinstance(value, list) or len(value) != 3 or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in value):
        raise ValueError(f"{name} must be three finite numbers")
    return np.asarray(value, dtype=np.float64)


def read_mask(path: Path) -> np.ndarray:
    m = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if m is None:
        raise ValueError(f"could not read mask {path}")
    return (m > 127).astype(np.uint8)


def inside_mask(mask: np.ndarray, xy: np.ndarray) -> np.ndarray:
    x = np.rint(xy[:, 0]).astype(np.int64); y = np.rint(xy[:, 1]).astype(np.int64)
    valid = (x >= 0) & (x < mask.shape[1]) & (y >= 0) & (y < mask.shape[0])
    out = np.zeros(len(x), dtype=bool)
    out[valid] = mask[y[valid], x[valid]] > 0
    return out


def centers(bounds_min: np.ndarray, shape: tuple[int, int, int], voxel: float) -> np.ndarray:
    nx, ny, nz = shape
    gx, gy, gz = np.meshgrid(np.arange(nx), np.arange(ny), np.arange(nz), indexing="ij")
    idx = np.stack([gx.ravel(), gy.ravel(), gz.ravel()], axis=1).astype(np.float64)
    return bounds_min.reshape(1, 3) + (idx + 0.5) * voxel


def occupancy_from_views(cfg: dict[str, Any], root: Path) -> tuple[np.ndarray, np.ndarray, float, list[dict]]:
    bounds = cfg.get("bounds", {})
    bmin = vec3(bounds.get("min"), "bounds.min"); bmax = vec3(bounds.get("max"), "bounds.max")
    if np.any(bmax <= bmin): raise ValueError("bounds.max must be greater than bounds.min")
    voxel = float(cfg.get("voxel", 1.0))
    if not math.isfinite(voxel) or voxel <= 0: raise ValueError("voxel must be finite and > 0")
    shape = tuple(int(math.ceil((bmax[i] - bmin[i]) / voxel)) for i in range(3))
    if np.prod(shape) > int(cfg.get("max_voxels", 2_000_000)):
        raise ValueError(f"visual hull grid {shape} exceeds max_voxels")
    pts = centers(bmin, shape, voxel)
    keep = np.ones(len(pts), dtype=bool); views=[]
    refs = cfg.get("references", [])
    if not isinstance(refs, list) or len(refs) < 2:
        raise ValueError("visual hull requires at least two calibrated silhouette references")
    for idx, r in enumerate(refs):
        if not isinstance(r, dict): raise ValueError("references entries must be objects")
        mp = Path(str(r["mask"])); mp = mp if mp.is_absolute() else (root / mp).resolve(); mask = read_mask(mp)
        camera = r.get("camera") if isinstance(r.get("camera"), dict) else {}
        xy = project(pts, camera, mask.shape[1], mask.shape[0]); in_view = inside_mask(mask, xy)
        keep &= in_view
        views.append({"id": str(r.get("id", f"view_{idx}")), "mask": str(mp), "camera": camera, "accepted_fraction_alone": round(float(in_view.mean()), 6)})
    return keep.reshape(shape), bmin, voxel, views


def greedy_boxes(occ: np.ndarray, bmin: np.ndarray, voxel: float) -> list[dict]:
    """Partition occupied cells into deterministic rectangular cuboids."""
    used = np.zeros_like(occ, dtype=bool); nx, ny, nz = occ.shape; boxes=[]; counter=0
    for ix in range(nx):
        for iy in range(ny):
            for iz in range(nz):
                if not occ[ix, iy, iz] or used[ix, iy, iz]: continue
                x2=ix
                while x2+1<nx and occ[x2+1,iy,iz] and not used[x2+1,iy,iz]: x2+=1
                y2=iy
                while y2+1<ny and np.all(occ[ix:x2+1,y2+1,iz] & ~used[ix:x2+1,y2+1,iz]): y2+=1
                z2=iz
                while z2+1<nz and np.all(occ[ix:x2+1,iy:y2+1,z2+1] & ~used[ix:x2+1,iy:y2+1,z2+1]): z2+=1
                used[ix:x2+1,iy:y2+1,iz:z2+1]=True; counter+=1
                lo=bmin+np.array([ix,iy,iz],dtype=float)*voxel; size=np.array([x2-ix+1,y2-iy+1,z2-iz+1],dtype=float)*voxel
                boxes.append({"id":f"hull_{counter:04d}","bone":"root","origin":[round(float(x),6) for x in lo],"size":[round(float(x),6) for x in size]})
    return boxes


def merge_adjacent(boxes: list[dict]) -> list[dict]:
    """Conservative post-merge of exactly co-planar adjacent cuboids."""
    changed=True
    while changed:
        changed=False; out=[]; taken=[False]*len(boxes)
        for i,a in enumerate(boxes):
            if taken[i]: continue
            ao=np.asarray(a["origin"],float); asz=np.asarray(a["size"],float); merged=a
            for j in range(i+1,len(boxes)):
                if taken[j]: continue
                b=boxes[j]; bo=np.asarray(b["origin"],float); bsz=np.asarray(b["size"],float)
                for axis in range(3):
                    other=[q for q in range(3) if q!=axis]
                    same=all(abs(ao[q]-bo[q])<1e-8 and abs(asz[q]-bsz[q])<1e-8 for q in other)
                    adjacent=abs((ao[axis]+asz[axis])-bo[axis])<1e-8 or abs((bo[axis]+bsz[axis])-ao[axis])<1e-8
                    if same and adjacent:
                        no=np.minimum(ao,bo); hi=np.maximum(ao+asz,bo+bsz); ns=hi-no
                        merged={**a,"origin":[round(float(x),6) for x in no],"size":[round(float(x),6) for x in ns]}; ao,asz=no,ns; taken[j]=True; changed=True; break
            taken[i]=True; out.append(merged)
        boxes=out
    for i,b in enumerate(boxes,1): b["id"]=f"hull_{i:04d}"
    return boxes


def uv_pack(cubes: list[dict], start: int, padding: int, max_size: int) -> tuple[list[dict], int, int]:
    w=h=max(16,next_pow2(start))
    while True:
        attempt=json.loads(json.dumps(cubes)); ok,packed,_,_=pack(attempt,w,h,padding,True)
        if ok: return packed,w,h
        if w>=max_size and h>=max_size: raise ValueError(f"hull UVs exceed {max_size}x{max_size}")
        if w<=h: w=next_pow2(w+1)
        else: h=next_pow2(h+1)


def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("manifest",type=Path); ap.add_argument("--output",type=Path,required=True); ap.add_argument("--report",type=Path,required=True); ap.add_argument("--render-dir",type=Path); ap.add_argument("--min-iou",type=float,default=0.90); args=ap.parse_args()
    cfg=json.loads(args.manifest.read_text(encoding="utf-8")); occ,bmin,voxel,views=occupancy_from_views(cfg,args.manifest.parent)
    count=int(occ.sum())
    if count==0: print("visual hull is empty"); return 2
    boxes=merge_adjacent(greedy_boxes(occ,bmin,voxel)); boxes,tw,th=uv_pack(boxes,int(cfg.get("texture",64)),int(cfg.get("uv_padding",1)),int(cfg.get("max_texture",512)))
    shape=np.asarray(occ.shape,dtype=float); extent=shape*voxel
    spec={"schema_version":1,"id":str(cfg.get("id","reference-hull")),"archetype":"reference_visual_hull","texture":{"width":tw,"height":th},"visible_bounds":{"width":round(float(max(extent[0],extent[2])/16*2.0),4),"height":round(float(extent[1]/16*1.4),4),"offset":[0,round(float((bmin[1]+extent[1]/2)/16),4),0]},"bones":[{"id":"root","pivot":[0,0,0]}],"cubes":boxes,"animations":[],"reconstruction":{"method":"multi-view silhouette visual hull","voxel":voxel,"bounds":{"min":bmin.tolist(),"shape":list(map(int,occ.shape))},"evidence":"hidden concavities not visible in silhouettes remain unknowable"}}
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(spec,indent=2)+"\n",encoding="utf-8")
    rows=[]
    if args.render_dir: args.render_dir.mkdir(parents=True,exist_ok=True)
    for v in views:
        target=read_mask(Path(v["mask"])) * 255; cam=v["camera"]; cand=render_mask(spec,cam,(target.shape[1],target.shape[0])); m=metrics(target,cand); rows.append({"id":v["id"],**m})
        if args.render_dir: cv2.imwrite(str(args.render_dir/f"{v['id']}.png"),cand)
    mean_iou=float(np.mean([x["iou"] for x in rows])) if rows else 0.0; passed=mean_iou>=args.min_iou
    report={"result":"pass" if passed else "fail","occupied_voxels":count,"grid_shape":list(map(int,occ.shape)),"voxel":voxel,"cuboids":len(boxes),"texture":[tw,th],"mean_iou":round(mean_iou,6),"min_iou":args.min_iou,"views":rows,"output":str(args.output),"note":"Visual hull matches silhouettes but cannot recover silhouette-invisible concavities or semantic joints by itself."}
    args.report.parent.mkdir(parents=True,exist_ok=True); args.report.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8"); print(json.dumps(report,indent=2)); return 0 if passed else 2
if __name__=="__main__": raise SystemExit(main())
