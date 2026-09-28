#!/usr/bin/env python3
"""Deterministically render actual creature-spec cuboids + PNG texels for visual QA.

Lightweight orthographic QA renderer: real project geometry, UV atlas, emissive atlas and
sampled animation pose. It is intentionally not Minecraft's renderer; native client QA remains
release authority. Requires Pillow + NumPy only.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw

FACES={'front':(0,1,3,2),'back':(4,6,7,5),'left':(0,2,6,4),'right':(1,5,7,3),'up':(2,3,7,6),'down':(0,4,5,1)}
SHADE={'front':1.00,'right':.86,'left':.72,'up':1.10,'down':.55,'back':.66}

def T(x,y,z):m=np.eye(4);m[:3,3]=[x,y,z];return m
def S(x,y,z):m=np.eye(4);m[0,0]=x;m[1,1]=y;m[2,2]=z;return m
def R(rx,ry,rz):
 rx,ry,rz=(math.radians(v) for v in (rx,ry,rz));cx,sx=math.cos(rx),math.sin(rx);cy,sy=math.cos(ry),math.sin(ry);cz,sz=math.cos(rz),math.sin(rz)
 mx=np.array([[1,0,0,0],[0,cx,-sx,0],[0,sx,cx,0],[0,0,0,1]],float);my=np.array([[cy,0,sy,0],[0,1,0,0],[-sy,0,cy,0],[0,0,0,1]],float);mz=np.array([[cz,-sz,0,0],[sz,cz,0,0],[0,0,1,0],[0,0,0,1]],float);return mz@my@mx

def box_faces(uv,size):
 u,v=(int(round(x)) for x in uv);x,y,z=(max(1,int(round(abs(float(q))))) for q in size)
 return {'up':(u+z,v,x,z),'down':(u+z+x,v,x,z),'left':(u,v+z,z,y),'front':(u+z,v+z,x,y),'right':(u+z+x,v+z,z,y),'back':(u+2*z+x,v+z,x,y)}
def lerp(a,b,t):return [a[i]+(b[i]-a[i])*t for i in range(3)]
def sample(keys,time):
 if not keys:return [0,0,0]
 q=sorted(keys,key=lambda k:float(k.get('time',0)))
 if time<=float(q[0].get('time',0)):return list(map(float,q[0].get('value',[0,0,0])))
 if time>=float(q[-1].get('time',0)):return list(map(float,q[-1].get('value',[0,0,0])))
 for a,b in zip(q,q[1:]):
  ta,tb=float(a['time']),float(b['time'])
  if ta<=time<=tb:return lerp(list(map(float,a['value'])),list(map(float,b['value'])),0 if tb==ta else (time-ta)/(tb-ta))
 return [0,0,0]
def pose_for(spec,name,time):
 pose={};anim=next((x for x in spec.get('animations',[]) if isinstance(x,dict) and x.get('name')==name),None)
 if not anim:return pose
 L=float(anim.get('length',0) or 0)
 if L and anim.get('loop') is True:time%=L
 for bid,ch in (anim.get('bones') or {}).items():
  if not isinstance(ch,dict):continue
  pose[bid]={k:sample(ch[k],time) for k in ('rotation','position','scale') if isinstance(ch.get(k),list)}
 return pose
def boneM(bones,bid,pose,cache):
 if bid in cache:return cache[bid]
 b=bones[bid];pv=np.array(b.get('pivot',[0,0,0]),float);bp=np.array(b.get('rotation',[0,0,0]),float);p=pose.get(bid,{});rot=bp+np.array(p.get('rotation',[0,0,0]),float);pos=np.array(p.get('position',[0,0,0]),float);sc=np.array(p.get('scale',[1,1,1]),float)
 local=T(*(pv+pos))@R(*rot)@S(*sc)@T(*(-pv));par=b.get('parent');m=boneM(bones,par,pose,cache)@local if par in bones else local;cache[bid]=m;return m
def cubepts(c):
 o=np.array(c['origin'],float);s=np.array(c['size'],float);x0,y0,z0=o;x1,y1,z1=o+s
 pts=np.array([[x0,y0,z0,1],[x1,y0,z0,1],[x0,y1,z0,1],[x1,y1,z0,1],[x0,y0,z1,1],[x1,y0,z1,1],[x0,y1,z1,1],[x1,y1,z1,1]],float)
 if c.get('rotation') is not None:
  pv=np.array(c.get('pivot',o+s/2),float);pts=(T(*pv)@R(*c['rotation'])@T(*(-pv))@pts.T).T
 return pts

def raster_tri(canvas,tex,em,pts,uvs,shade):
 # canvas RGBA uint8; pts shape 3x2 float, uvs 3x2 float
 h,w=canvas.shape[:2];minx=max(0,int(math.floor(pts[:,0].min())));maxx=min(w-1,int(math.ceil(pts[:,0].max())));miny=max(0,int(math.floor(pts[:,1].min())));maxy=min(h-1,int(math.ceil(pts[:,1].max())))
 if minx>maxx or miny>maxy:return
 x=np.arange(minx,maxx+1)+.5;y=np.arange(miny,maxy+1)+.5;xx,yy=np.meshgrid(x,y);p=np.stack([xx,yy],axis=-1)
 a,b,c=pts;v0=b-a;v1=c-a;den=v0[0]*v1[1]-v1[0]*v0[1]
 if abs(den)<1e-8:return
 v2=p-a;u=(v2[...,0]*v1[1]-v1[0]*v2[...,1])/den;v=(v0[0]*v2[...,1]-v2[...,0]*v0[1])/den;mask=(u>=-1e-6)&(v>=-1e-6)&((u+v)<=1+1e-6)
 if not mask.any():return
 uv=uvs[0]+u[...,None]*(uvs[1]-uvs[0])+v[...,None]*(uvs[2]-uvs[0]);tx=np.clip(np.floor(uv[...,0]).astype(int),0,tex.shape[1]-1);ty=np.clip(np.floor(uv[...,1]).astype(int),0,tex.shape[0]-1);src=tex[ty,tx].astype(np.float32)
 src[...,:3]*=shade
 if em is not None:
  es=em[ty,tx].astype(np.float32);emask=(es[...,3:4]/255.0);src[...,:3]=np.maximum(src[...,:3],src[...,:3]*.45+es[...,:3]*emask*.85)
 src=np.clip(src,0,255).astype(np.uint8);dest=canvas[miny:maxy+1,minx:maxx+1];alpha=(src[...,3:4].astype(np.float32)/255.0);m=mask[...,None].astype(np.float32);a2=alpha*m;dest[...,:3]=np.clip(src[...,:3]*a2+dest[...,:3]*(1-a2),0,255).astype(np.uint8);dest[...,3]=np.where(mask,np.maximum(dest[...,3],src[...,3]),dest[...,3])

def render(spec,texture,output,animation,time,yaw,pitch,size,bg,emissive=None,flat=False):
 texim=Image.open(texture).convert('RGBA');tex=np.asarray(texim,dtype=np.uint8);em=np.asarray(Image.open(emissive).convert('RGBA'),dtype=np.uint8) if emissive and Path(emissive).is_file() else None;bones={str(x['id']):x for x in spec.get('bones',[]) if isinstance(x,dict) and x.get('id')};pose=pose_for(spec,animation,time);cache={};cam=R(pitch,yaw,0);faces=[];allxy=[]
 for c in spec.get('cubes',[]):
  if not isinstance(c,dict) or c.get('bone') not in bones:continue
  world=(boneM(bones,str(c['bone']),pose,cache)@cubepts(c).T).T;view=(cam@world.T).T;uvr=box_faces(c.get('uv',[0,0]),c.get('size',[1,1,1]))
  for fn,idxs in FACES.items():
   p=view[list(idxs),:3];n=np.cross(p[1]-p[0],p[2]-p[0])
   if n[2]>=0:continue
   xy=np.array([[float(q[0]),float(q[1])] for q in p]);allxy.extend(xy.tolist());x,y,ww,hh=uvr[fn];uv=np.array([[x,y],[x+ww-1,y],[x+ww-1,y+hh-1],[x,y+hh-1]],float);faces.append((float(p[:,2].mean()),xy,uv,fn))
 if not allxy:raise SystemExit('no renderable geometry')
 arr=np.array(allxy,float);mn=arr.min(0);mx=arr.max(0);span=max(*(mx-mn),1);pad=size*.08;scale=(size-2*pad)/span
 def scr(xy):
  q=np.empty_like(xy);q[:,0]=pad+(xy[:,0]-mn[0])*scale;q[:,1]=size-(pad+(xy[:,1]-mn[1])*scale);return q
 canvas=np.zeros((size,size,4),dtype=np.uint8);canvas[:]=np.array(bg,dtype=np.uint8)
 # shadow first
 base=Image.fromarray(canvas,'RGBA');dr=ImageDraw.Draw(base,'RGBA');ground=size-(pad+(0-mn[1])*scale) if mn[1]<=0<=mx[1] else size-pad;dr.ellipse((size*.22,ground-7,size*.78,ground+10),fill=(0,0,0,42));canvas=np.asarray(base).copy()
 for _,xy,uv,fn in sorted(faces,key=lambda z:z[0],reverse=True):
  q=scr(xy)
  if flat:
   col=tex[int(np.clip(uv[:,1].mean(),0,tex.shape[0]-1)),int(np.clip(uv[:,0].mean(),0,tex.shape[1]-1))].astype(float);col[:3]*=SHADE[fn];im=Image.fromarray(canvas,'RGBA');d=ImageDraw.Draw(im,'RGBA');d.polygon([tuple(x) for x in q],fill=tuple(np.clip(col,0,255).astype(int)));canvas=np.asarray(im).copy()
  else:
   raster_tri(canvas,tex,em,q[[0,1,2]],uv[[0,1,2]],SHADE[fn]);raster_tri(canvas,tex,em,q[[0,2,3]],uv[[0,2,3]],SHADE[fn])
 Image.fromarray(canvas,'RGBA').save(output)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('spec',type=Path);ap.add_argument('--texture',type=Path,required=True);ap.add_argument('--emissive',type=Path);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--animation');ap.add_argument('--time',type=float,default=0);ap.add_argument('--yaw',type=float,default=-35);ap.add_argument('--pitch',type=float,default=18);ap.add_argument('--size',type=int,default=800);ap.add_argument('--background',default='#d9dde3');ap.add_argument('--flat',action='store_true');a=ap.parse_args();bg=a.background.lstrip('#');rgba=tuple(int(bg[i:i+2],16) for i in (0,2,4))+(255,);spec=json.loads(a.spec.read_text(encoding='utf-8'));a.output.parent.mkdir(parents=True,exist_ok=True);render(spec,a.texture,a.output,a.animation,a.time,a.yaw,a.pitch,a.size,rgba,a.emissive,a.flat);print(a.output)
if __name__=='__main__':main()
