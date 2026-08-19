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
OUT=Path('/tmp/lian_wu_rig_v23_contact_absorb_v4')
CANVAS=(1024,1024); FOOTLINE=969
STATIC=['head_hair','torso','waist_sash','upper_leg_left','lower_leg_left','foot_left','upper_leg_right','lower_leg_right','foot_right']

def combine(parts,names):
    out=Image.new('RGBA',CANVAS,(0,0,0,0))
    for n in names: out=Image.alpha_composite(out,parts[n])
    return out

def dense_inverse_warp(im,src_pts,deltas):
    h,w=CANVAS[1],CANVAS[0]
    yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
    weights=[]
    for px,py in src_pts:
        dist2=(xx-float(px))**2+(yy-float(py))**2
        weights.append(1.0/np.maximum(18.0**2,dist2))
    ws=np.stack(weights,axis=0)
    ws/=np.sum(ws,axis=0,keepdims=True)
    dx=sum(ws[i]*float(deltas[i][0]) for i in range(3))
    dy=sum(ws[i]*float(deltas[i][1]) for i in range(3))
    map_x=(xx-dx).astype(np.float32)
    map_y=(yy-dy).astype(np.float32)
    arr=np.array(im.convert('RGBA'))
    warped=cv2.remap(arr,map_x,map_y,interpolation=cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT,borderValue=(0,0,0,0))
    return Image.fromarray(warped,'RGBA')

def bbox(im): return im.getchannel('A').getbbox()

def main():
    subprocess.run(['python3',str(ROOT/'tools/build_lian_wu_rig_v2_segmentation.py')],check=True)
    j=json.loads(JOINTS.read_text(encoding='utf-8'))['joints']
    names=STATIC+['weapon','upper_arm_left','forearm_left','hand_left','upper_arm_right','forearm_right','hand_right']
    parts={n:Image.open(GEN/f'{n}.png').convert('RGBA') for n in names}
    pose=Image.new('RGBA',CANVAS,(0,0,0,0))
    for n in STATIC: pose=Image.alpha_composite(pose,parts[n])

    targets={
      'left': {'shoulder':tuple(j['shoulder_left']), 'elbow':(430,500), 'wrist':(500,520)},
      'right':{'shoulder':tuple(j['shoulder_right']),'elbow':(595,500), 'wrist':(525,520)},
    }
    for side in ('left','right'):
        src_pts=[tuple(j[f'shoulder_{side}']),tuple(j[f'elbow_{side}']),tuple(j[f'wrist_{side}'])]
        t=targets[side]; dst_pts=[t['shoulder'],t['elbow'],t['wrist']]
        deltas=[(dst_pts[i][0]-src_pts[i][0],dst_pts[i][1]-src_pts[i][1]) for i in range(3)]
        env=combine(parts,[f'upper_arm_{side}',f'forearm_{side}',f'hand_{side}'])
        pose=Image.alpha_composite(pose,dense_inverse_warp(env,src_pts,deltas))

    pose=Image.alpha_composite(pose,parts['weapon'])
    OUT.mkdir(parents=True,exist_ok=True)
    p=OUT/'char_lian_wu__contact_absorb__pose_test_v4.png'; pose.save(p,optimize=True)
    src=Image.open(SRC).convert('RGBA')
    board=Image.new('RGBA',(2048,1024),(0,0,0,0)); board.alpha_composite(src,(0,0)); board.alpha_composite(pose,(1024,0)); board.save(OUT/'comparison-canonical-vs-contact-absorb-v4.png',optimize=True)
    b=bbox(pose); foot=b[3] if b else None
    report={'schema':'tehkne/taijifu-lian-wu-rig-v23-pose-test/v4','signature':'Tehkné Solutions','pose':'contact_absorb','method':'continuous_arm_envelope_dense_inverse_remap','bbox':list(b) if b else None,'footline':foot,'footline_target':FOOTLINE,'footline_pass':foot is not None and abs(foot-FOOTLINE)<=3,'mesh_cells_used':False,'joint_caps_used':False,'human_review':'PENDING','animation_authoring_allowed':False,'pack04_promotion_allowed':False,'counts_toward_pack04':False}
    (OUT/'pose-test-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    ok=pose.size==CANVAS and pose.mode=='RGBA' and report['footline_pass']
    print('LIAN_WU_RIG_V23_CONTACT_ABSORB_POSE_TEST='+('PASS' if ok else 'FAIL')); print('PACK04_PROMOTION_ALLOWED=false')
    return 0 if ok else 1
if __name__=='__main__': raise SystemExit(main())
