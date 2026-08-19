#!/usr/bin/env python3
from __future__ import annotations
from collections import deque
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw
import hashlib, json

SOURCE=Path('production/first_playable/lian_wu/first_playable_lot_01/animations/guard/char_lian_wu__guard__f01.png')
OUTPUT=Path('production/first_playable/lian_wu/rig_v2/generated')
SOURCE_SHA256='c8e6cd1feece7c2a54cf2279085c2a4bb33338dd6a3dcb3e4d5a2402b537631c'
PARTS=['head_hair','torso','upper_arm_left','forearm_left','hand_left','upper_arm_right','forearm_right','hand_right','waist_sash','upper_leg_left','lower_leg_left','foot_left','upper_leg_right','lower_leg_right','foot_right','weapon']
POLYGONS={
'head_hair':[(360,60),(700,60),(710,385),(625,405),(390,390),(345,290)],
'torso':[(390,365),(630,360),(640,590),(585,660),(430,655),(380,540)],
'upper_arm_left':[(355,405),(435,395),(455,535),(405,575),(350,530)],
'forearm_left':[(330,515),(410,525),(405,650),(345,675),(310,625)],
'hand_left':[(305,625),(372,625),(380,705),(315,725),(292,680)],
'upper_arm_right':[(590,380),(685,395),(720,520),(660,555),(600,515)],
'forearm_right':[(640,505),(715,515),(735,645),(675,665),(640,610)],
'hand_right':[(655,630),(725,630),(740,710),(675,735),(650,690)],
'waist_sash':[(375,555),(650,555),(665,735),(595,785),(425,780),(360,700)],
'upper_leg_left':[(345,700),(520,700),(520,840),(455,865),(360,835)],
'lower_leg_left':[(360,815),(475,820),(470,930),(390,945),(350,900)],
'foot_left':[(335,905),(475,905),(490,985),(335,985)],
'upper_leg_right':[(505,700),(680,700),(690,840),(600,865),(515,835)],
'lower_leg_right':[(560,815),(685,820),(700,930),(615,945),(555,900)],
'foot_right':[(555,905),(720,905),(735,985),(555,985)],
'weapon':[(285,595),(430,595),(430,745),(300,745)],
}
# Hands must own overlapping visible hand pixels before the rigid weapon region.
PRIORITY=['hand_left','hand_right','weapon','forearm_left','forearm_right','upper_arm_left','upper_arm_right','head_hair','foot_left','foot_right','lower_leg_left','lower_leg_right','upper_leg_left','upper_leg_right','waist_sash','torso']

def sha256(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def make_masks(size):
    masks={p:Image.new('1',size,0) for p in PARTS}
    for p,poly in POLYGONS.items(): ImageDraw.Draw(masks[p]).polygon(poly,fill=1)
    return masks

def fallback(x,y):
    if y<390:return 'head_hair'
    if y<555:return 'torso'
    if y<735:return 'waist_sash'
    if x<515:
        return 'upper_leg_left' if y<835 else ('lower_leg_left' if y<925 else 'foot_left')
    return 'upper_leg_right' if y<835 else ('lower_leg_right' if y<925 else 'foot_right')

def component_stats(layer):
    a=layer.getchannel('A'); px=a.load(); w,h=layer.size; seen=set(); sizes=[]
    for y in range(h):
      for x in range(w):
        if px[x,y]==0 or (x,y) in seen: continue
        q=deque([(x,y)]); seen.add((x,y)); n=0
        while q:
          cx,cy=q.popleft(); n+=1
          for nx,ny in ((cx+1,cy),(cx-1,cy),(cx,cy+1),(cx,cy-1)):
            if 0<=nx<w and 0<=ny<h and px[nx,ny]>0 and (nx,ny) not in seen:
              seen.add((nx,ny)); q.append((nx,ny))
        sizes.append(n)
    sizes.sort(reverse=True); total=sum(sizes)
    return {'components':len(sizes),'largest_component_pixels':sizes[0] if sizes else 0,'largest_component_ratio':round(sizes[0]/total,6) if total else 0.0}

def main():
    if not SOURCE.exists(): print(f'RIG_V2_SEGMENTATION=BLOCKED missing={SOURCE}'); return 2
    if sha256(SOURCE)!=SOURCE_SHA256: print('RIG_V2_SEGMENTATION=BLOCKED source_sha256_mismatch'); return 3
    src=Image.open(SOURCE).convert('RGBA'); masks=make_masks(src.size)
    layers={p:Image.new('RGBA',src.size,(0,0,0,0)) for p in PARTS}; dst={p:im.load() for p,im in layers.items()}; sp=src.load(); mp={p:m.load() for p,m in masks.items()}
    counts={p:0 for p in PARTS}; opaque=assigned=0
    for y in range(src.height):
      for x in range(src.width):
        px=sp[x,y]
        if px[3]==0: continue
        opaque+=1; part=next((p for p in PRIORITY if mp[p][x,y]),None) or fallback(x,y)
        dst[part][x,y]=px; counts[part]+=1; assigned+=1
    OUTPUT.mkdir(parents=True,exist_ok=True); recon=Image.new('RGBA',src.size,(0,0,0,0)); stats={}
    for p in PARTS:
      layers[p].save(OUTPUT/f'{p}.png',optimize=True); recon=Image.alpha_composite(recon,layers[p]); stats[p]=component_stats(layers[p])
    recon.save(OUTPUT/'lian_wu_rig_v2_reconstructed.png',optimize=True); exact=ImageChops.difference(src,recon).getbbox() is None
    board=Image.new('RGBA',(2048,2048),(0,0,0,0))
    for i,p in enumerate(PARTS):
      thumb=layers[p].copy(); thumb.thumbnail((480,480),Image.Resampling.NEAREST); cx=(i%4)*512; cy=(i//4)*512; board.alpha_composite(thumb,(cx+(512-thumb.width)//2,cy+(512-thumb.height)//2))
    board.save(OUTPUT/'segmentation-board.png',optimize=True)
    zero_parts=[p for p in PARTS if counts[p]==0]
    report={'schema':'tehkne/taijifu-lian-wu-rig-v2-segmentation/v3','signature':'Tehkné Solutions','source_sha256':SOURCE_SHA256,'method':'authored_anatomical_polygon_masks_v3','ownership_priority':PRIORITY,'parts':PARTS,'opaque_source_pixels':opaque,'assigned_pixels':assigned,'assigned_exactly_once':assigned==opaque,'reconstruction_pixel_exact':exact,'part_pixel_counts':counts,'zero_parts':zero_parts,'component_stats':stats,'human_mask_review':'PENDING','joint_anchor_freeze_allowed':False,'animation_authoring_allowed':False,'pack04_promotion_allowed':False}
    (OUTPUT/'segmentation-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    ok=exact and assigned==opaque and not zero_parts
    print('RIG_V2_SEGMENTATION='+('PASS' if ok else 'FAIL'))
    print('RIG_V2_ZERO_PARTS='+(','.join(zero_parts) if zero_parts else 'NONE'))
    print('RIG_V2_SEGMENTATION_METHOD=AUTHORED_POLYGONS_V3')
    return 0 if ok else 1
if __name__=='__main__': raise SystemExit(main())
