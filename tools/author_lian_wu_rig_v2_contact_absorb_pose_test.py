#!/usr/bin/env python3
from __future__ import annotations
import json, math, subprocess
from pathlib import Path
from PIL import Image, ImageChops

ROOT=Path(__file__).resolve().parents[1]
RIG_DIR=ROOT/'production/first_playable/lian_wu/rig_v2'
GEN=RIG_DIR/'generated'
SOURCE=ROOT/'production/first_playable/lian_wu/first_playable_lot_01/animations/guard/char_lian_wu__guard__f01.png'
JOINTS=RIG_DIR/'joint-anchors-v1.json'
OUT=Path('/tmp/lian_wu_rig_v2_contact_absorb_pose_test')
CANVAS=(1024,1024); FOOTLINE=969
STATIC=['head_hair','torso','waist_sash','upper_leg_left','lower_leg_left','foot_left','upper_leg_right','lower_leg_right','foot_right','weapon']

def rotpt(pt,pivot,deg):
    a=math.radians(deg); x,y=pt; px,py=pivot; dx=x-px; dy=y-py
    return (px+dx*math.cos(a)-dy*math.sin(a), py+dx*math.sin(a)+dy*math.cos(a))

def translate(im,dx,dy):
    return im.transform(CANVAS,Image.Transform.AFFINE,(1,0,-dx,0,1,-dy),resample=Image.Resampling.BICUBIC)

def rotate_about(im,pivot,deg):
    return im.rotate(deg,resample=Image.Resampling.BICUBIC,center=pivot,expand=False)

def chain(layer,pivot,carry,deg):
    moved=translate(layer,carry[0],carry[1])
    p=(pivot[0]+carry[0],pivot[1]+carry[1])
    return rotate_about(moved,p,deg), p

def alpha_bbox(im): return im.getchannel('A').getbbox()

def main():
    subprocess.run(['python3',str(ROOT/'tools/build_lian_wu_rig_v2_segmentation.py')],check=True)
    j=json.loads(JOINTS.read_text(encoding='utf-8'))['joints']
    parts={name:Image.open(GEN/f'{name}.png').convert('RGBA') for name in STATIC+['upper_arm_left','forearm_left','hand_left','upper_arm_right','forearm_right','hand_right']}
    pose=Image.new('RGBA',CANVAS,(0,0,0,0))
    for name in STATIC: pose=Image.alpha_composite(pose,parts[name])

    # Contact-absorb pose: shoulders close inward, forearms rise across torso.
    configs={
      'left': {'ua':24,'fa':58,'hand':8},
      'right':{'ua':-22,'fa':-56,'hand':-8},
    }
    for side in ('left','right'):
        shoulder=tuple(j[f'shoulder_{side}']); elbow=tuple(j[f'elbow_{side}']); wrist=tuple(j[f'wrist_{side}']); c=configs[side]
        ua=rotate_about(parts[f'upper_arm_{side}'],shoulder,c['ua'])
        new_elbow=rotpt(elbow,shoulder,c['ua']); carry_elbow=(new_elbow[0]-elbow[0],new_elbow[1]-elbow[1])
        fa,fa_pivot=chain(parts[f'forearm_{side}'],elbow,carry_elbow,c['fa'])
        wrist_carried=(wrist[0]+carry_elbow[0],wrist[1]+carry_elbow[1]); new_wrist=rotpt(wrist_carried,fa_pivot,c['fa'])
        carry_hand=(new_wrist[0]-wrist[0],new_wrist[1]-wrist[1])
        hand,hand_pivot=chain(parts[f'hand_{side}'],wrist,carry_hand,c['hand'])
        pose=Image.alpha_composite(pose,ua); pose=Image.alpha_composite(pose,fa); pose=Image.alpha_composite(pose,hand)

    OUT.mkdir(parents=True,exist_ok=True)
    p=OUT/'char_lian_wu__contact_absorb__pose_test_v1.png'; pose.save(p,optimize=True)
    src=Image.open(SOURCE).convert('RGBA')
    board=Image.new('RGBA',(2048,1024),(0,0,0,0)); board.alpha_composite(src,(0,0)); board.alpha_composite(pose,(1024,0)); board.save(OUT/'comparison-canonical-vs-contact-absorb.png',optimize=True)
    b=alpha_bbox(pose); foot=b[3] if b else None
    report={
      'schema':'tehkne/taijifu-lian-wu-rig-v2-pose-test/v1','signature':'Tehkné Solutions','pose':'contact_absorb','source':'canonical_guard_lfs','joint_manifest':'joint-anchors-v1.json','canvas':[1024,1024],
      'bbox':list(b) if b else None,'footline':foot,'footline_target':FOOTLINE,'footline_pass':foot is not None and abs(foot-FOOTLINE)<=3,
      'human_review':'PENDING','animation_authoring_allowed':False,'pack04_promotion_allowed':False,'counts_toward_pack04':False
    }
    (OUT/'pose-test-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    ok=report['footline_pass'] and pose.mode=='RGBA' and pose.size==CANVAS
    print('LIAN_WU_RIG_V2_CONTACT_ABSORB_POSE_TEST='+('PASS' if ok else 'FAIL'))
    print('PACK04_PROMOTION_ALLOWED=false')
    return 0 if ok else 1
if __name__=='__main__': raise SystemExit(main())
