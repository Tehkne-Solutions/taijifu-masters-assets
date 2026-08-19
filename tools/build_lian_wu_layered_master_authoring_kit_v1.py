#!/usr/bin/env python3
from __future__ import annotations
import json, hashlib
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'production/first_playable/lian_wu/first_playable_lot_01/animations/guard/char_lian_wu__guard__f01.png'
OUT=Path('/tmp/lian_wu_layered_master_authoring_kit_v1')
CANVAS=(1024,1024)
EXPECTED_SHA='c8e6cd1feece7c2a54cf2279085c2a4bb33338dd6a3dcb3e4d5a2402b537631c'
ARM_POLYGONS={
 'left': [(338,405),(442,398),(466,458),(444,525),(412,592),(382,675),(321,688),(300,630),(314,555),(327,478)],
 'right':[(586,402),(690,404),(716,470),(719,548),(734,628),(705,689),(645,680),(618,602),(598,530),(572,460)],
}
TORSO_GUIDE=[(390,360),(635,360),(666,470),(644,610),(607,680),(420,680),(382,612),(360,474)]

def sha256(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def masked(src:Image.Image, poly):
    arr=np.array(src.convert('RGBA'))
    mask=np.zeros((1024,1024),dtype=np.uint8)
    cv2.fillPoly(mask,[np.array(poly,dtype=np.int32)],255)
    mask=cv2.bitwise_and(mask,arr[:,:,3])
    out=np.zeros_like(arr)
    out[:,:,:3]=arr[:,:,:3]
    out[:,:,3]=mask
    return Image.fromarray(out,'RGBA')

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if sha256(SRC)!=EXPECTED_SHA:
        raise SystemExit('canonical source hash mismatch')
    src=Image.open(SRC).convert('RGBA')
    if src.size!=CANVAS or src.mode!='RGBA':
        raise SystemExit('canonical source format mismatch')

    src.save(OUT/'canonical-source.png',optimize=True)
    left=masked(src,ARM_POLYGONS['left']); left.save(OUT/'arm_left_visible_reference.png',optimize=True)
    right=masked(src,ARM_POLYGONS['right']); right.save(OUT/'arm_right_visible_reference.png',optimize=True)
    torso=masked(src,TORSO_GUIDE); torso.save(OUT/'torso_visible_reference.png',optimize=True)

    guide=src.copy()
    d=ImageDraw.Draw(guide,'RGBA')
    d.polygon(TORSO_GUIDE,fill=(255,215,0,35),outline=(255,215,0,220),width=3)
    for side,poly in ARM_POLYGONS.items():
        d.polygon(poly,fill=(0,180,255,28),outline=(0,180,255,220),width=3)
    d.text((28,28),'Lian Wu Layered Master Authoring Kit v1 — Tehkné Solutions',fill=(255,255,255,255))
    d.text((28,58),'Gold: torso authored completion zone | Blue: complete arm layer extraction zones',fill=(255,255,255,255))
    guide.save(OUT/'authoring-guide-overlay.png',optimize=True)

    manifest={
      'schema':'tehkne/taijifu-lian-wu-layered-master-authoring-kit/v1',
      'signature':'Tehkné Solutions',
      'source_sha256':EXPECTED_SHA,
      'purpose':'visual_authoring_reference_only',
      'authored_pixels_generated':False,
      'required_first_layers':['torso_underpaint_complete','arm_left_complete','arm_right_complete'],
      'references':{
        'canonical':'canonical-source.png',
        'torso_visible':'torso_visible_reference.png',
        'arm_left_visible':'arm_left_visible_reference.png',
        'arm_right_visible':'arm_right_visible_reference.png',
        'guide':'authoring-guide-overlay.png'
      },
      'rules':[
        'preserve all currently visible canonical pixels exactly',
        'author only hidden surfaces needed behind moving limbs',
        'do not regenerate the character',
        'do not use automatic inpainting',
        'do not mark any layer authored until a human-reviewed PNG exists'
      ],
      'authoring_ready':False,
      'pack04_promotion_allowed':False,
      'counts_toward_pack04':False
    }
    (OUT/'authoring-kit-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print('LAYERED_MASTER_AUTHORING_KIT=PASS')
    print('AUTHORED_PIXELS_GENERATED=false')
    print('PACK04_PROMOTION_ALLOWED=false')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
