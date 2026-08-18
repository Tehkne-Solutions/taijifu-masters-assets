#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from PIL import Image
SIGNATURE='Tehkné Solutions'; CANVAS=(1024,1024); FOOTLINE=969
PARTS=('head_hair','torso','arm_left','arm_right','waist_sash','leg_left','leg_right','weapon')
SHOULDER_LEFT=(420,435); SHOULDER_RIGHT=(610,435)
def sha256(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def bbox(im): return im.getchannel('A').getbbox()
def shift(im,dx,dy):
 out=Image.new('RGBA',CANVAS,(0,0,0,0)); out.alpha_composite(im,(dx,dy)); return out
def rotate(im,angle,center):
 return im.rotate(angle,resample=Image.Resampling.BICUBIC,center=center,expand=False)
def normalize(im):
 b=bbox(im); drift=FOOTLINE-b[3]
 if not drift:return im
 return shift(im,0,drift)
def validate(im,label):
 if im.size!=CANVAS or im.mode!='RGBA': raise ValueError(label+':canvas_or_mode')
 b=bbox(im)
 if not b or abs(b[3]-FOOTLINE)>3: raise ValueError(label+':footline')
 return {'bbox':list(b),'footline':b[3],'width':b[2]-b[0],'height':b[3]-b[1]}
def frame_from_layers(layers,idx):
 # Distinct authored poses: contact absorb -> yield -> guard recover.
 cfg={
  1:{'la':-42,'ra':42,'arm_dx':12,'upper':(-7,4)},
  2:{'la':-58,'ra':58,'arm_dx':20,'upper':(-15,10)},
  3:{'la':-30,'ra':30,'arm_dx':8,'upper':(-4,2)},
 }[idx]
 out=Image.new('RGBA',CANVAS,(0,0,0,0))
 # Planted legs first.
 out=Image.alpha_composite(out,layers['leg_left']); out=Image.alpha_composite(out,layers['leg_right'])
 ux,uy=cfg['upper']
 for name in ('waist_sash','torso','weapon','head_hair'):
  out=Image.alpha_composite(out,shift(layers[name],ux,uy))
 left=rotate(layers['arm_left'],cfg['la'],SHOULDER_LEFT); left=shift(left,cfg['arm_dx'],0)
 right=rotate(layers['arm_right'],cfg['ra'],SHOULDER_RIGHT); right=shift(right,-cfg['arm_dx'],0)
 # Arms render above torso to read as a real blocking guard.
 out=Image.alpha_composite(out,left); out=Image.alpha_composite(out,right)
 return normalize(out)
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--rig-root',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
 layers={}
 for name in PARTS:
  p=a.rig_root/f'{name}.png'
  if not p.is_file(): raise SystemExit(f'PACK04_LIAN_BLOCK_RECOIL=BLOCKED missing_rig_part={name}')
  layers[name]=Image.open(p).convert('RGBA')
 a.output.mkdir(parents=True,exist_ok=True); frames=[]; stats=[]
 for i in (1,2,3):
  im=frame_from_layers(layers,i); name=f'char_lian_wu__block_recoil__f{i:03d}.png'; p=a.output/name; im.save(p,optimize=True)
  s=validate(im,name); s.update(file=name,sha256=sha256(p)); stats.append(s); frames.append(im)
 widths=[s['width'] for s in stats]; heights=[s['height'] for s in stats]
 if (max(widths)-min(widths))/max(widths)>.08 or (max(heights)-min(heights))/max(heights)>.08: raise SystemExit('PACK04_LIAN_BLOCK_RECOIL=BLOCKED bounds_variation')
 sheet=Image.new('RGBA',(3072,1024),(0,0,0,0))
 for n,im in enumerate(frames): sheet.alpha_composite(im,(n*1024,0))
 sheet.save(a.output/'contact-sheet-candidate-e.png',optimize=True)
 report={'schema':'tehkne/taijifu-pack04-authoring-candidate/v1','signature':SIGNATURE,'candidate':'E','fighter':'lian_wu','state':'block_recoil','method':'articulated_rig_v1_layers_with_shoulder_pivot_rotation','candidate_history':{'A':'REJECTED seams','B':'REJECTED insufficient motion','C':'REJECTED idle-like','D':'REJECTED anatomically weak warp'},'promoted':False,'human_review':'PENDING','runtime_authority':False,'frames':stats}
 (a.output/'candidate-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 print('PACK04_LIAN_BLOCK_RECOIL_CANDIDATE_E=PASS frames=3 promoted=false'); print('SIGNATURE='+SIGNATURE)
if __name__=='__main__': main()
