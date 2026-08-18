#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
from PIL import Image
SIGNATURE='Tehkné Solutions'; CANVAS=(1024,1024); FOOTLINE=969
SOURCE_SHA256='c8e6cd1feece7c2a54cf2279085c2a4bb33338dd6a3dcb3e4d5a2402b537631c'
def sha256(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def bbox(im): return im.getchannel('A').getbbox()
def g(x,y,cx,cy,rx,ry): return math.exp(-2.8*(((x-cx)/rx)**2+((y-cy)/ry)**2))
def displacement(frame,x,y):
 k={1:0.78,2:1.0,3:0.38}[frame]
 dx=0.0; dy=0.0
 upper=max(0.0,min(1.0,(900-y)/560.0)); dx += -24*k*upper*upper; dy += 12*k*upper
 for cx,cy,mx,my,rx,ry in [(420,435,28,-42,105,115),(385,545,58,-92,115,135),(365,655,92,-166,120,150)]:
  w=g(x,y,cx,cy,rx,ry); dx += k*mx*w; dy += k*my*w
 for cx,cy,mx,my,rx,ry in [(610,435,-24,-38,105,115),(655,545,-58,-88,115,135),(665,655,-96,-160,120,150)]:
  w=g(x,y,cx,cy,rx,ry); dx += k*mx*w; dy += k*my*w
 w=g(x,y,512,300,190,190); dx += -16*k*w; dy += 18*k*w
 w=g(x,y,512,650,220,150); dx += -16*k*w; dy += 14*k*w
 if frame==3: dx*=0.82; dy*=0.82
 foot=max(0.0,min(1.0,(y-820)/149.0)); dx*=1-foot; dy*=1-foot
 return dx,dy
def mesh(frame,cell=24):
 out=[]
 for y0 in range(0,1024,cell):
  for x0 in range(0,1024,cell):
   x1=min(x0+cell,1024); y1=min(y0+cell,1024); q=[]
   for x,y in ((x0,y0),(x0,y1),(x1,y1),(x1,y0)):
    dx,dy=displacement(frame,x,y); q.extend((x-dx,y-dy))
   out.append(((x0,y0,x1,y1),tuple(q)))
 return out
def normalize(im):
 b=bbox(im); drift=FOOTLINE-b[3]
 if not drift:return im
 o=Image.new('RGBA',CANVAS,(0,0,0,0)); o.alpha_composite(im,(0,drift)); return o
def validate(im,label):
 if im.size!=CANVAS or im.mode!='RGBA': raise ValueError(label+':canvas_or_mode')
 b=bbox(im)
 if not b or abs(b[3]-FOOTLINE)>3: raise ValueError(label+':footline')
 return {'bbox':list(b),'footline':b[3],'width':b[2]-b[0],'height':b[3]-b[1]}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--source',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
 if sha256(a.source)!=SOURCE_SHA256: raise SystemExit('PACK04_LIAN_BLOCK_RECOIL=BLOCKED source_sha256_mismatch')
 src=Image.open(a.source).convert('RGBA'); a.output.mkdir(parents=True,exist_ok=True); frames=[]; stats=[]
 for i in (1,2,3):
  im=src.transform(CANVAS,Image.Transform.MESH,mesh(i),resample=Image.Resampling.BICUBIC); im=normalize(im)
  name=f'char_lian_wu__block_recoil__f{i:03d}.png'; p=a.output/name; im.save(p,optimize=True); s=validate(im,name); s.update(file=name,sha256=sha256(p)); stats.append(s); frames.append(im)
 widths=[s['width'] for s in stats]; heights=[s['height'] for s in stats]
 if (max(widths)-min(widths))/max(widths)>.08 or (max(heights)-min(heights))/max(heights)>.08: raise SystemExit('PACK04_LIAN_BLOCK_RECOIL=BLOCKED bounds_variation')
 sheet=Image.new('RGBA',(3072,1024),(0,0,0,0))
 for n,im in enumerate(frames): sheet.alpha_composite(im,(n*1024,0))
 sheet.save(a.output/'contact-sheet-candidate-d.png',optimize=True)
 report={'schema':'tehkne/taijifu-pack04-authoring-candidate/v1','signature':SIGNATURE,'candidate':'D','fighter':'lian_wu','state':'block_recoil','source_sha256':SOURCE_SHA256,'method':'continuous_24px_mesh_from_rig_v1_shoulder_elbow_wrist_anchors','candidate_a':'REJECTED seams','candidate_b':'REJECTED insufficient semantic motion','candidate_c':'REJECTED arms remained low / idle-like','promoted':False,'human_review':'PENDING','runtime_authority':False,'frames':stats}
 (a.output/'candidate-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 print('PACK04_LIAN_BLOCK_RECOIL_CANDIDATE_D=PASS frames=3 promoted=false'); print('SIGNATURE='+SIGNATURE)
if __name__=='__main__': main()
