#!/usr/bin/env python3
"""Propose independently moving visible regions from a staged GIF/reference sequence.

This is a rigging aid: optical flow is clustered with spatial context on the highest-motion
frame pair. It does not name bones automatically or override semantic/artistic judgment.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import cv2,numpy as np
from PIL import Image


def load_gray(path:Path):
    x=cv2.imread(str(path),cv2.IMREAD_GRAYSCALE)
    if x is None: raise ValueError(path)
    return x

def load_mask(path:Path): return load_gray(path)>127

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('manifest',type=Path);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--labels',type=Path,required=True);ap.add_argument('--clusters',type=int,default=4);ap.add_argument('--min-motion',type=float,default=.35);ap.add_argument('--spatial-weight',type=float,default=.55);a=ap.parse_args()
    d=json.loads(a.manifest.read_text(encoding='utf-8')); frames=d.get('frames',[]); root=a.manifest.parent.parent
    if not isinstance(frames,list) or len(frames)<2: print('needs >=2 frames'); return 2
    pairs=[]
    for i in range(1,len(frames)):
        g0=load_gray(root/frames[i-1]['frame']); g1=load_gray(root/frames[i]['frame']); m=load_mask(root/frames[i-1]['mask'])|load_mask(root/frames[i]['mask'])
        flow=cv2.calcOpticalFlowFarneback(g0,g1,None,.5,3,15,3,5,1.2,0); mag=np.linalg.norm(flow,axis=2); energy=float(mag[m].mean()) if np.any(m) else 0
        pairs.append((energy,i-1,i,flow,m))
    energy,i0,i1,flow,mask=max(pairs,key=lambda x:x[0]); mag=np.linalg.norm(flow,axis=2); moving=mask&(mag>=a.min_motion)
    ys,xs=np.nonzero(moving)
    if len(xs)<max(8,a.clusters*2): print('not enough moving pixels for partition'); return 2
    h,w=mask.shape; f=flow[ys,xs]; scale=max(1.0,float(np.percentile(np.linalg.norm(f,axis=1),90)))
    features=np.column_stack([xs/w*a.spatial_weight,ys/h*a.spatial_weight,f[:,0]/scale,f[:,1]/scale]).astype(np.float32)
    k=max(2,min(int(a.clusters),len(features)//4)); cv2.setRNGSeed(1337)
    criteria=(cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER,80,.001);_,labels,centers=cv2.kmeans(features,k,None,criteria,12,cv2.KMEANS_PP_CENTERS); labels=labels.ravel()
    label_img=np.zeros((h,w),dtype=np.uint8); regions=[]
    for ci in range(k):
        sel=labels==ci; xx=xs[sel]; yy=ys[sel]; ff=f[sel]
        if len(xx)==0: continue
        label_img[yy,xx]=ci+1
        mean=ff.mean(axis=0); spread=np.sqrt(np.mean(np.sum((ff-mean)**2,axis=1)))
        regions.append({'cluster':ci+1,'pixels':int(len(xx)),'bbox':[int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1],'centroid':[round(float(xx.mean()),3),round(float(yy.mean()),3)],'mean_flow':[round(float(mean[0]),4),round(float(mean[1]),4)],'flow_spread':round(float(spread),4),'mean_speed':round(float(np.linalg.norm(mean)),4)})
    # Separation score: large differences between region mean motions support separate articulation.
    means=[np.asarray(r['mean_flow'],float) for r in regions]; sep=[]
    for i in range(len(means)):
        for j in range(i+1,len(means)): sep.append(float(np.linalg.norm(means[i]-means[j])))
    result={'result':'pass','source':d.get('source'),'frame_pair':[i0,i1],'time_ms':[int(frames[i0].get('time_ms',0)),int(frames[i1].get('time_ms',0))],'motion_energy':round(energy,6),'clusters':regions,'mean_pairwise_motion_separation':round(float(np.mean(sep)) if sep else 0.0,6),'labels':str(a.labels),'note':'Treat these as candidate visible motion groups. Merge/split using anatomy, occlusion, pivots and multi-frame evidence before creating bones.'}
    a.labels.parent.mkdir(parents=True,exist_ok=True); Image.fromarray(label_img,'L').save(a.labels); a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8'); print(json.dumps(result,indent=2)); return 0
if __name__=='__main__':raise SystemExit(main())
