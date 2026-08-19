#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
RIG=ROOT/'production/first_playable/lian_wu/rig_v2'
GEN=RIG/'generated'
SRC=ROOT/'production/first_playable/lian_wu/first_playable_lot_01/animations/guard/char_lian_wu__guard__f01.png'
JOINTS=RIG/'joint-anchors-v1.json'
OUT=Path('/tmp/lian_wu_rig_v25_contact_absorb_v6')
CANVAS=(1024,1024); FOOTLINE=969
STATIC=['head_hair','torso','waist_sash','upper_leg_left','lower_leg_left','foot_left','upper_leg_right','lower_leg_right','foot_right']
ARM_POLYGONS={
 'left': [(338,405),(442,398),(466,458),(444,525),(412,592),(382,675),(321,688),(300,630),(314,555),(327,478)],
 'right':[(586,402),(690,404),(716,470),(719,548),(734,628),(705,689),(645,680),(618,602),(598,530),(572,460)],
}

def bbox(im): return im.getchannel('A').getbbox()

def anatomical_arm_from_source(src:Image.Image,side:str)->Image.Image:
    arr=np.array(src.convert('RGBA'))
    mask=np.zeros((1024,1024),dtype=np.uint8)
    cv2.fillPoly(mask,[np.array(ARM_POLYGONS[side],dtype=np.int32)],255)
    mask=cv2.bitwise_and(mask,arr[:,:,3])
    out=np.zeros_like(arr); out[:,:,:3]=arr[:,:,:3]; out[:,:,3]=mask
    return Image.fromarray(out,'RGBA')

def dense_inverse_warp(im,src_pts,deltas):
    h,w=CANVAS[1],CANVAS[0]
    yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
    weights=[]
    for px,py in src_pts:
        dist2=(xx-float(px))**2+(yy-float(py))**2
        weights.append(1.0/np.maximum(24.0**2,dist2))
    ws=np.stack(weights,axis=0); ws/=np.sum(ws,axis=0,keepdims=True)
    dx=sum(ws[i]*float(deltas[i][0]) for i in range(3)); dy=sum(ws[i]*float(deltas[i][1]) for i in range(3))
    map_x=(xx-dx).astype(np.float32); map_y=(yy-dy).astype(np.float32)
    arr=np.array(im.convert('RGBA'))
    warped=cv2.remap(arr,map_x,map_y,interpolation=cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT,borderValue=(0,0,0,0))
    return Image.fromarray(warped,'RGBA')

def build_static(parts):
    pose=Image.new('RGBA',CANVAS,(0,0,0,0))
    for n in STATIC: pose=Image.alpha_composite(pose,parts[n])
    return pose

def canonical_body_underpaint(src:Image.Image,static:Image.Image):
    src_arr=np.array(src.convert('RGBA')); st_arr=np.array(static.convert('RGBA'))
    src_a=src_arr[:,:,3]; st_a=st_arr[:,:,3]
    missing=((src_a>0)&(st_a==0)).astype(np.uint8)*255
    # Only restore vacated pixels near the existing static body. This avoids ghost arms.
    inv=(st_a==0).astype(np.uint8)
    dist=cv2.distanceTransform(inv,cv2.DIST_L2,5)
    near=((missing>0)&(dist<=28.0)).astype(np.uint8)*255
    # Inpaint RGB from the visible static body into the near-body hidden zones.
    base_rgb=st_arr[:,:,:3].copy()
    filled=cv2.inpaint(base_rgb,near,5,cv2.INPAINT_TELEA)
    out=st_arr.copy()
    sel=near>0
    out[sel,:3]=filled[sel]
    out[sel,3]=255
    return Image.fromarray(out,'RGBA'), int(np.count_nonzero(sel))

def main():
    subprocess.run(['python3',str(ROOT/'tools/build_lian_wu_rig_v2_segmentation.py')],check=True)
    j=json.loads(JOINTS.read_text(encoding='utf-8'))['joints']
    src=Image.open(SRC).convert('RGBA')
    parts={n:Image.open(GEN/f'{n}.png').convert('RGBA') for n in STATIC+['weapon']}
    static=build_static(parts)
    pose,underpaint_pixels=canonical_body_underpaint(src,static)
    targets={'left':{'shoulder':tuple(j['shoulder_left']),'elbow':(430,500),'wrist':(500,520)},'right':{'shoulder':tuple(j['shoulder_right']),'elbow':(595,500),'wrist':(525,520)}}
    source_arm_stats={}
    for side in ('left','right'):
        src_pts=[tuple(j[f'shoulder_{side}']),tuple(j[f'elbow_{side}']),tuple(j[f'wrist_{side}'])]
        t=targets[side]; dst_pts=[t['shoulder'],t['elbow'],t['wrist']]
        deltas=[(dst_pts[i][0]-src_pts[i][0],dst_pts[i][1]-src_pts[i][1]) for i in range(3)]
        env=anatomical_arm_from_source(src,side)
        source_arm_stats[side]={'bbox':list(bbox(env)) if bbox(env) else None,'alpha_pixels':int(np.count_nonzero(np.array(env)[:,:,3]))}
        pose=Image.alpha_composite(pose,dense_inverse_warp(env,src_pts,deltas))
    pose=Image.alpha_composite(pose,parts['weapon'])
    OUT.mkdir(parents=True,exist_ok=True)
    p=OUT/'char_lian_wu__contact_absorb__pose_test_v6.png'; pose.save(p,optimize=True)
    board=Image.new('RGBA',(2048,1024),(0,0,0,0)); board.alpha_composite(src,(0,0)); board.alpha_composite(pose,(1024,0)); board.save(OUT/'comparison-canonical-vs-contact-absorb-v6.png',optimize=True)
    b=bbox(pose); foot=b[3] if b else None
    report={'schema':'tehkne/taijifu-lian-wu-rig-v25-pose-test/v6','signature':'Tehkné Solutions','pose':'contact_absorb','method':'direct_canonical_arm_mask_dense_remap_with_body_underpaint','body_underpaint_method':'near_static_body_cv2_telea','underpaint_pixels':underpaint_pixels,'source_arm_stats':source_arm_stats,'bbox':list(b) if b else None,'footline':foot,'footline_target':FOOTLINE,'footline_pass':foot is not None and abs(foot-FOOTLINE)<=3,'visible_canonical_pixels_repainted':False,'human_review':'PENDING','animation_authoring_allowed':False,'pack04_promotion_allowed':False,'counts_toward_pack04':False}
    (OUT/'pose-test-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    ok=pose.size==CANVAS and pose.mode=='RGBA' and report['footline_pass'] and underpaint_pixels>0
    print('LIAN_WU_RIG_V25_CONTACT_ABSORB_POSE_TEST='+('PASS' if ok else 'FAIL')); print('UNDERPAINT_PIXELS='+str(underpaint_pixels)); print('PACK04_PROMOTION_ALLOWED=false')
    return 0 if ok else 1
if __name__=='__main__': raise SystemExit(main())
