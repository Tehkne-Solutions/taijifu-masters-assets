#!/usr/bin/env python3
from __future__ import annotations
import json, hashlib
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'production/first_playable/lian_wu/first_playable_lot_01/animations/guard/char_lian_wu__guard__f01.png'
OUT=Path('/tmp/lian_wu_layered_master_authoring_kit_v2')
CANVAS=(1024,1024)
EXPECTED_SHA='c8e6cd1feece7c2a54cf2279085c2a4bb33338dd6a3dcb3e4d5a2402b537631c'
ARM_POLYGONS={
 'left': [(338,405),(442,398),(466,458),(444,525),(412,592),(382,675),(321,688),(300,630),(314,555),(327,478)],
 'right':[(586,402),(690,404),(716,470),(719,548),(734,628),(705,689),(645,680),(618,602),(598,530),(572,460)],
}
TORSO_GUIDE=[(390,360),(635,360),(666,470),(644,610),(607,680),(420,680),(382,612),(360,474)]


def sha256(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def poly_mask(poly):
    m=np.zeros((1024,1024),dtype=np.uint8)
    cv2.fillPoly(m,[np.array(poly,dtype=np.int32)],255)
    return m


def masked_visible(src:Image.Image, poly):
    arr=np.array(src.convert('RGBA'))
    mask=cv2.bitwise_and(poly_mask(poly),arr[:,:,3])
    out=np.zeros_like(arr)
    out[:,:,:3]=arr[:,:,:3]
    out[:,:,3]=mask
    return Image.fromarray(out,'RGBA'), mask


def write_template(src:Image.Image, visible_mask:np.ndarray, authoring_mask:np.ndarray, stem:str):
    arr=np.array(src.convert('RGBA'))
    tpl=np.zeros_like(arr)
    tpl[:,:,:3]=arr[:,:,:3]
    tpl[:,:,3]=visible_mask
    Image.fromarray(tpl,'RGBA').save(OUT/f'{stem}_template.png',optimize=True)
    Image.fromarray(authoring_mask,'L').save(OUT/f'{stem}_authoring_mask.png',optimize=True)
    locked=((arr[:,:,3]>0)&(authoring_mask==0)).astype(np.uint8)*255
    Image.fromarray(locked,'L').save(OUT/f'{stem}_locked_visible_mask.png',optimize=True)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if sha256(SRC)!=EXPECTED_SHA:
        raise SystemExit('canonical source hash mismatch')
    src=Image.open(SRC).convert('RGBA')
    if src.size!=CANVAS or src.mode!='RGBA':
        raise SystemExit('canonical source format mismatch')

    src.save(OUT/'canonical-source.png',optimize=True)
    alpha=np.array(src)[:,:,3]
    torso_visible, torso_vis_mask=masked_visible(src,TORSO_GUIDE)
    left_visible, left_vis_mask=masked_visible(src,ARM_POLYGONS['left'])
    right_visible, right_vis_mask=masked_visible(src,ARM_POLYGONS['right'])

    # Authored zones are explicit geometric envelopes only. No hidden pixel content is generated.
    torso_author=np.maximum(poly_mask(TORSO_GUIDE), cv2.dilate(torso_vis_mask,np.ones((31,31),np.uint8),iterations=1))
    left_author=np.maximum(poly_mask(ARM_POLYGONS['left']), cv2.dilate(left_vis_mask,np.ones((25,25),np.uint8),iterations=1))
    right_author=np.maximum(poly_mask(ARM_POLYGONS['right']), cv2.dilate(right_vis_mask,np.ones((25,25),np.uint8),iterations=1))

    torso_visible.save(OUT/'torso_visible_reference.png',optimize=True)
    left_visible.save(OUT/'arm_left_visible_reference.png',optimize=True)
    right_visible.save(OUT/'arm_right_visible_reference.png',optimize=True)

    write_template(src,torso_vis_mask,torso_author,'torso_underpaint_complete')
    write_template(src,left_vis_mask,left_author,'arm_left_complete')
    write_template(src,right_vis_mask,right_author,'arm_right_complete')

    guide=src.copy()
    d=ImageDraw.Draw(guide,'RGBA')
    d.polygon(TORSO_GUIDE,fill=(255,215,0,30),outline=(255,215,0,230),width=3)
    d.polygon(ARM_POLYGONS['left'],fill=(0,180,255,24),outline=(0,180,255,230),width=3)
    d.polygon(ARM_POLYGONS['right'],fill=(0,180,255,24),outline=(0,180,255,230),width=3)
    d.text((28,28),'Lian Wu Layered Master Authoring Kit v2 — Tehkné Solutions',fill=(255,255,255,255))
    d.text((28,58),'Templates preserve canonical visible pixels; *_authoring_mask.png defines the only writable zone.',fill=(255,255,255,255))
    guide.save(OUT/'authoring-guide-overlay.png',optimize=True)

    files={p.name:sha256(p) for p in sorted(OUT.glob('*.png'))}
    manifest={
      'schema':'tehkne/taijifu-lian-wu-layered-master-authoring-kit/v2',
      'signature':'Tehkné Solutions',
      'source_sha256':EXPECTED_SHA,
      'authored_pixels_generated':False,
      'templates':{
        'torso_underpaint_complete':{
          'template':'torso_underpaint_complete_template.png',
          'authoring_mask':'torso_underpaint_complete_authoring_mask.png',
          'locked_visible_mask':'torso_underpaint_complete_locked_visible_mask.png'
        },
        'arm_left_complete':{
          'template':'arm_left_complete_template.png',
          'authoring_mask':'arm_left_complete_authoring_mask.png',
          'locked_visible_mask':'arm_left_complete_locked_visible_mask.png'
        },
        'arm_right_complete':{
          'template':'arm_right_complete_template.png',
          'authoring_mask':'arm_right_complete_authoring_mask.png',
          'locked_visible_mask':'arm_right_complete_locked_visible_mask.png'
        }
      },
      'rules':[
        'only pixels inside the matching authoring mask may change',
        'all existing canonical visible pixels must remain byte-identical',
        'hidden surfaces require authored art; no automatic inpainting',
        'do not regenerate or restyle the character',
        'do not promote until reconstruction and contact_absorb human review pass'
      ],
      'file_sha256':files,
      'authoring_ready':False,
      'pack04_promotion_allowed':False,
      'counts_toward_pack04':False
    }
    (OUT/'authoring-kit-v2-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print('LAYERED_MASTER_AUTHORING_KIT_V2=PASS')
    print('AUTHORED_PIXELS_GENERATED=false')
    print('PACK04_PROMOTION_ALLOWED=false')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
