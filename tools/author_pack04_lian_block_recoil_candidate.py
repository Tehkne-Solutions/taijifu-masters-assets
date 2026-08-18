#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
from PIL import Image
SIGNATURE='Tehkné Solutions'; CANVAS=(1024,1024); FOOTLINE=969
SOURCE_SHA256='c8e6cd1feece7c2a54cf2279085c2a4bb33338dd6a3dcb3e4d5a2402b537631c'
def sha256(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def bbox(im): return im.getchannel('A').getbbox()
def g(x,y,cx,cy,rx,ry): return math.exp(-3.2*(((x-cx)/rx)**2+((y-cy)/ry)**2))
def field(frame,x,y):
 cfg={
  1:{'torso':(-8,5),'lw':(75,-180),'le':(42,-100),'rw':(-75,-180),'re':(-42,-100),'head':(-5,5)},
  2:{'torso':(-18,12),'lw':(95,-230),'le':(55,-135),'rw':(-95,-230),'re':(-55,-135),'head':(-12,12)},
  3:{'torso':(-4,3),'lw':(65,-155),'le':(35,-85),'rw':(-65,-155),'re':(-35,-85),'head':(-3,3)},
 }[frame]
 dx=dy=0.0
 w=g(x,y,512,550,250,260); dx+=cfg['torso'][0]*w; dy+=cfg['torso'][1]*w
 w=g(x,y,512,300,205,180); dx+=cfg['head'][0]*w; dy+=cfg['head'][1]*w
 # Recalibrated against the current canonical guard raster: elbows ~y500, hands/wrists ~y620.
 for (cx,cy),(vx,vy),rx,ry in [((395,500),cfg['le'],105,115),((365,620),cfg['lw'],105,125)]:
  w=g(x,y,cx,cy,rx,ry); dx+=vx*w; dy+=vy*w
 for (cx,cy),(vx,vy),rx,ry in [((635,500),cfg['re'],105,115),((665,620),cfg['rw'],105,125)]:
  w=g(x,y,cx,cy,rx,ry); dx+=vx*w; dy+=vy*w
 # Shoulder anchoring prevents detachment while allowing the forearms to fold in front of the torso.
 pin=max(g(x,y,420,390,95,95),g(x,y,610,390,95,95))*0.42
 dx*=1-pin; dy*=1-pin
 foot=max(0.0,min(1.0,(y-820)/149.0)); dx*=1-foot; dy*=1-foot
 return dx,dy
def build_mesh(frame,cell=12):
 out=[]
 for y0 in range(0,1024,cell):
  for x0 in range(0,1024,cell):
   x1=min(x0+cell,1024); y1=min(y0+cell,1024); q=[]
   for x,y in ((x0,y0),(x0,y1),(x1,y1),(x1,y0)):
    dx,dy=field(frame,x,y); q.extend((x-dx,y-dy))
   out.append(((x0,y0,x1,y1),tuple(q)))
 return out
def normalize(im):
 b=bbox(im); drift=FOOTLINE-b[3]
 if not drift:return im
 out=Image.new('RGBA',CANVAS,(0,0,0,0)); out.alpha_composite(im,(0,drift)); return out
def validate(im,label):
 if im.size!=CANVAS or im.mode!='RGBA': raise ValueError(label+':canvas_or_mode')
 b=bbox(im)
 if not b or abs(b[3]-FOOTLINE)>3: raise ValueError(label+':footline')
 return {'bbox':list(b),'footline':b[3],'width':b[2]-b[0],'height':b[3]-b[1]}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--source',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
 if sha256(a.source)!=SOURCE_SHA256: raise SystemExit('PACK04_LIAN_BLOCK_RECOIL=BLOCKED source_sha256_mismatch')
 src=Image.open(a.source).convert('RGBA')
 if src.size!=CANVAS: raise SystemExit('PACK04_LIAN_BLOCK_RECOIL=BLOCKED source_canvas')
 a.output.mkdir(parents=True,exist_ok=True); frames=[]; stats=[]
 for i in (1,2,3):
  im=src.transform(CANVAS,Image.Transform.MESH,build_mesh(i),resample=Image.Resampling.BICUBIC); im=normalize(im)
  name=f'char_lian_wu__block_recoil__f{i:03d}.png'; p=a.output/name; im.save(p,optimize=True); s=validate(im,name); s.update(file=name,sha256=sha256(p)); stats.append(s); frames.append(im)
 widths=[s['width'] for s in stats]; heights=[s['height'] for s in stats]; wv=(max(widths)-min(widths))/max(widths); hv=(max(heights)-min(heights))/max(heights)
 print('PACK04_CANDIDATE_G_BOUNDS='+json.dumps([{'frame':i+1,'bbox':s['bbox'],'width':s['width'],'height':s['height']} for i,s in enumerate(stats)])); print(f'PACK04_CANDIDATE_G_VARIATION width={wv:.6f} height={hv:.6f}')
 if wv>.08 or hv>.08: raise SystemExit('PACK04_LIAN_BLOCK_RECOIL=BLOCKED bounds_variation')
 sheet=Image.new('RGBA',(3072,1024),(0,0,0,0))
 for n,im in enumerate(frames): sheet.alpha_composite(im,(n*1024,0))
 sheet.save(a.output/'contact-sheet-candidate-g.png',optimize=True)
 report={'schema':'tehkne/taijifu-pack04-authoring-candidate/v1','signature':SIGNATURE,'candidate':'G','fighter':'lian_wu','state':'block_recoil','source_sha256':SOURCE_SHA256,'method':'continuous_12px_joint_field_recalibrated_on_current_guard_raster','candidate_history':{'A':'REJECTED seams','B':'REJECTED insufficient motion','C':'REJECTED idle-like','D':'REJECTED anatomically weak warp','E':'REJECTED segmentation holes','F':'REJECTED stale joint coordinates / insufficient block read'},'promoted':False,'human_review':'PENDING','runtime_authority':False,'frames':stats}
 (a.output/'candidate-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 print('PACK04_LIAN_BLOCK_RECOIL_CANDIDATE_G=PASS frames=3 promoted=false'); print('SIGNATURE='+SIGNATURE)
if __name__=='__main__': main()
