#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from PIL import Image, ImageChops
SIGNATURE='Tehkné Solutions'; CANVAS=(1024,1024); FOOTLINE=969
SOURCE_SHA256='c8e6cd1feece7c2a54cf2279085c2a4bb33338dd6a3dcb3e4d5a2402b537631c'
PARTS=('head_hair','torso','arm_left','arm_right','waist_sash','leg_left','leg_right','weapon')
SHOULDER_LEFT=(420,435); SHOULDER_RIGHT=(610,435)
def sha256(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def bbox(im): return im.getchannel('A').getbbox()
def region_name(x,y):
 if 315<=x<=390 and 620<=y<=735:return 'weapon'
 if y<385:return 'head_hair'
 if y<705 and x<425:return 'arm_left'
 if y<705 and x>610:return 'arm_right'
 if y<555:return 'torso'
 if y<755:return 'waist_sash'
 if x<515:return 'leg_left'
 return 'leg_right'
def segment(source):
 layers={n:Image.new('RGBA',source.size,(0,0,0,0)) for n in PARTS}; sp=source.load(); lp={n:im.load() for n,im in layers.items()}; opaque=assigned=0
 for y in range(source.height):
  for x in range(source.width):
   px=sp[x,y]
   if px[3]==0:continue
   opaque+=1; n=region_name(x,y); lp[n][x,y]=px; assigned+=1
 recon=Image.new('RGBA',source.size,(0,0,0,0))
 for n in PARTS: recon=Image.alpha_composite(recon,layers[n])
 exact=ImageChops.difference(source,recon).getbbox() is None
 if assigned!=opaque or not exact: raise SystemExit('PACK04_LIAN_BLOCK_RECOIL=BLOCKED rig_reconstruction_not_exact')
 return layers,{'opaque_source_pixels':opaque,'assigned_pixels':assigned,'assigned_exactly_once':assigned==opaque,'reconstruction_pixel_exact':exact}
def shift(im,dx,dy):
 out=Image.new('RGBA',CANVAS,(0,0,0,0)); out.alpha_composite(im,(dx,dy)); return out
def rotate(im,angle,center): return im.rotate(angle,resample=Image.Resampling.BICUBIC,center=center,expand=False)
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
 cfg={1:{'la':35,'ra':-35,'arm_dx':10,'upper':(-7,4)},2:{'la':45,'ra':-45,'arm_dx':14,'upper':(-15,10)},3:{'la':30,'ra':-30,'arm_dx':8,'upper':(-4,2)}}[idx]
 out=Image.new('RGBA',CANVAS,(0,0,0,0)); out=Image.alpha_composite(out,layers['leg_left']); out=Image.alpha_composite(out,layers['leg_right'])
 ux,uy=cfg['upper']
 for n in ('waist_sash','torso','weapon','head_hair'): out=Image.alpha_composite(out,shift(layers[n],ux,uy))
 left=shift(rotate(layers['arm_left'],cfg['la'],SHOULDER_LEFT),cfg['arm_dx'],0)
 right=shift(rotate(layers['arm_right'],cfg['ra'],SHOULDER_RIGHT),-cfg['arm_dx'],0)
 out=Image.alpha_composite(out,left); out=Image.alpha_composite(out,right)
 return normalize(out)
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--source',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
 if sha256(a.source)!=SOURCE_SHA256: raise SystemExit('PACK04_LIAN_BLOCK_RECOIL=BLOCKED source_sha256_mismatch')
 src=Image.open(a.source).convert('RGBA')
 if src.size!=CANVAS: raise SystemExit('PACK04_LIAN_BLOCK_RECOIL=BLOCKED source_canvas')
 layers,rig_report=segment(src); a.output.mkdir(parents=True,exist_ok=True); frames=[]; stats=[]
 for i in (1,2,3):
  im=frame_from_layers(layers,i); name=f'char_lian_wu__block_recoil__f{i:03d}.png'; p=a.output/name; im.save(p,optimize=True); s=validate(im,name); s.update(file=name,sha256=sha256(p)); stats.append(s); frames.append(im)
 widths=[s['width'] for s in stats]; heights=[s['height'] for s in stats]
 print('PACK04_CANDIDATE_E_BOUNDS='+json.dumps([{'frame':i+1,'bbox':s['bbox'],'width':s['width'],'height':s['height']} for i,s in enumerate(stats)]))
 wv=(max(widths)-min(widths))/max(widths); hv=(max(heights)-min(heights))/max(heights)
 print(f'PACK04_CANDIDATE_E_VARIATION width={wv:.6f} height={hv:.6f}')
 if wv>.08 or hv>.08: raise SystemExit('PACK04_LIAN_BLOCK_RECOIL=BLOCKED bounds_variation')
 sheet=Image.new('RGBA',(3072,1024),(0,0,0,0))
 for n,im in enumerate(frames): sheet.alpha_composite(im,(n*1024,0))
 sheet.save(a.output/'contact-sheet-candidate-e.png',optimize=True)
 report={'schema':'tehkne/taijifu-pack04-authoring-candidate/v1','signature':SIGNATURE,'candidate':'E','fighter':'lian_wu','state':'block_recoil','source_sha256':SOURCE_SHA256,'method':'pixel_exact_guard_segmentation_plus_shoulder_pivot_articulation','rig_reconstruction':rig_report,'candidate_history':{'A':'REJECTED seams','B':'REJECTED insufficient motion','C':'REJECTED idle-like','D':'REJECTED anatomically weak warp'},'promoted':False,'human_review':'PENDING','runtime_authority':False,'frames':stats}
 (a.output/'candidate-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 print('PACK04_RIG_RECONSTRUCTION=PASS pixel_exact=true'); print('PACK04_LIAN_BLOCK_RECOIL_CANDIDATE_E=PASS frames=3 promoted=false'); print('SIGNATURE='+SIGNATURE)
if __name__=='__main__': main()
