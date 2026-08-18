#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
from PIL import Image
SIGNATURE='Tehkné Solutions'; CANVAS=(1024,1024); FOOTLINE=969
SOURCE_SHA256='c8e6cd1feece7c2a54cf2279085c2a4bb33338dd6a3dcb3e4d5a2402b537631c'
def sha256(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def bbox(im): return im.getchannel('A').getbbox()
def bump(x,y,cx,cy,rx,ry):
 d=((x-cx)/rx)**2+((y-cy)/ry)**2
 return math.exp(-2.6*d)
def displacement(frame,x,y):
 # Stronger authored silhouette: compact high guard + recoil/yield while feet stay anchored.
 strength={1:1.0,2:1.55,3:0.45}[frame]
 upper=max(0.0,min(1.0,(900-y)/620.0)); anchor=max(0.0,min(1.0,(969-y)/110.0))
 dx=-strength*(18*upper*upper+7*bump(x,y,500,560,260,240))
 dy=strength*(8*upper+8*bump(x,y,500,650,250,210))
 # Pull both forearm/hand zones inward and upward to read as a compact block.
 for cx,cy,sign in ((405,545,1),(610,545,-1)):
  w=bump(x,y,cx,cy,155,180)
  dx += strength*sign*24*w
  dy -= strength*30*w
 # Head/shoulder tuck on impact, strongest on yield.
 w=bump(x,y,505,390,210,180); dx-=strength*8*w; dy+=strength*12*w
 # Preserve planted feet.
 foot=max(0.0,min(1.0,(y-850)/119.0)); dx*=1-foot; dy*=1-foot
 return dx,dy
def mesh(frame,cell=32):
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
 sheet.save(a.output/'contact-sheet-candidate-c.png',optimize=True)
 report={'schema':'tehkne/taijifu-pack04-authoring-candidate/v1','signature':SIGNATURE,'candidate':'C','fighter':'lian_wu','state':'block_recoil','source_sha256':SOURCE_SHA256,'method':'continuous_32px_mesh_high_guard_recoil_from_canonical_guard','candidate_a':'REJECTED seams','candidate_b':'REJECTED insufficient semantic motion','promoted':False,'human_review':'PENDING','runtime_authority':False,'frames':stats}
 (a.output/'candidate-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 print('PACK04_LIAN_BLOCK_RECOIL_CANDIDATE_C=PASS frames=3 promoted=false'); print('SIGNATURE='+SIGNATURE)
if __name__=='__main__': main()
