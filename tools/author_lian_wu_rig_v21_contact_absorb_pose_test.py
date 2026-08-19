#!/usr/bin/env python3
from __future__ import annotations
import json, math, subprocess
from pathlib import Path
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
RIG_DIR=ROOT/'production/first_playable/lian_wu/rig_v2'
GEN=RIG_DIR/'generated'
SOURCE=ROOT/'production/first_playable/lian_wu/first_playable_lot_01/animations/guard/char_lian_wu__guard__f01.png'
JOINTS=RIG_DIR/'joint-anchors-v1.json'
OUT=Path('/tmp/lian_wu_rig_v21_contact_absorb_pose_test')
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
    moved=translate(layer,carry[0],carry[1]); p=(pivot[0]+carry[0],pivot[1]+carry[1])
    return rotate_about(moved,p,deg), p

def joint_cap(src,center,radius):
    mask=Image.new('L',CANVAS,0); d=ImageDraw.Draw(mask)
    x,y=center; d.ellipse((x-radius,y-radius,x+radius,y+radius),fill=255)
    cap=Image.new('RGBA',CANVAS,(0,0,0,0)); cap.paste(src,(0,0),mask)
    return cap

def alpha_bbox(im): return im.getchannel('A').getbbox()

def main():
    subprocess.run(['python3',str(ROOT/'tools/build_lian_wu_rig_v2_segmentation.py')],check=True)
    j=json.loads(JOINTS.read_text(encoding='utf-8'))['joints']
    src=Image.open(SOURCE).convert('RGBA')
    names=STATIC+['upper_arm_left','forearm_left','hand_left','upper_arm_right','forearm_right','hand_right']
    parts={name:Image.open(GEN/f'{name}.png').convert('RGBA') for name in names}
    pose=Image.new('RGBA',CANVAS,(0,0,0,0))
    for name in STATIC: pose=Image.alpha_composite(pose,parts[name])

    configs={'left':{'ua':18,'fa':44,'hand':6},'right':{'ua':-18,'fa':-44,'hand':-6}}
    repair_radii={'shoulder':34,'elbow':30,'wrist':24}
    repair_layers=[]

    for side in ('left','right'):
        shoulder=tuple(j[f'shoulder_{side}']); elbow=tuple(j[f'elbow_{side}']); wrist=tuple(j[f'wrist_{side}']); c=configs[side]

        ua=rotate_about(parts[f'upper_arm_{side}'],shoulder,c['ua'])
        shoulder_cap=rotate_about(joint_cap(src,shoulder,repair_radii['shoulder']),shoulder,c['ua'])

        new_elbow=rotpt(elbow,shoulder,c['ua']); carry_elbow=(new_elbow[0]-elbow[0],new_elbow[1]-elbow[1])
        fa,fa_pivot=chain(parts[f'forearm_{side}'],elbow,carry_elbow,c['fa'])
        elbow_cap=translate(joint_cap(src,elbow,repair_radii['elbow']),carry_elbow[0],carry_elbow[1])
        elbow_cap=rotate_about(elbow_cap,fa_pivot,c['fa']*0.5)

        wrist_carried=(wrist[0]+carry_elbow[0],wrist[1]+carry_elbow[1]); new_wrist=rotpt(wrist_carried,fa_pivot,c['fa'])
        carry_hand=(new_wrist[0]-wrist[0],new_wrist[1]-wrist[1])
        hand,hand_pivot=chain(parts[f'hand_{side}'],wrist,carry_hand,c['hand'])
        wrist_cap=translate(joint_cap(src,wrist,repair_radii['wrist']),carry_hand[0],carry_hand[1])
        wrist_cap=rotate_about(wrist_cap,hand_pivot,c['hand']*0.5)

        pose=Image.alpha_composite(pose,ua)
        pose=Image.alpha_composite(pose,shoulder_cap)
        pose=Image.alpha_composite(pose,fa)
        pose=Image.alpha_composite(pose,elbow_cap)
        pose=Image.alpha_composite(pose,hand)
        pose=Image.alpha_composite(pose,wrist_cap)
        repair_layers += [f'shoulder_{side}',f'elbow_{side}',f'wrist_{side}']

    OUT.mkdir(parents=True,exist_ok=True)
    p=OUT/'char_lian_wu__contact_absorb__pose_test_v2.png'; pose.save(p,optimize=True)
    board=Image.new('RGBA',(2048,1024),(0,0,0,0)); board.alpha_composite(src,(0,0)); board.alpha_composite(pose,(1024,0)); board.save(OUT/'comparison-canonical-vs-contact-absorb-v2.png',optimize=True)
    b=alpha_bbox(pose); foot=b[3] if b else None
    report={
      'schema':'tehkne/taijifu-lian-wu-rig-v21-pose-test/v2','signature':'Tehkné Solutions','pose':'contact_absorb','source':'canonical_guard_lfs','joint_manifest':'joint-anchors-v1.json','canvas':[1024,1024],
      'joint_repair_method':'canonical_joint_caps_parent_child_overlap','joint_repair_layers':repair_layers,
      'bbox':list(b) if b else None,'footline':foot,'footline_target':FOOTLINE,'footline_pass':foot is not None and abs(foot-FOOTLINE)<=3,
      'human_review':'PENDING','animation_authoring_allowed':False,'pack04_promotion_allowed':False,'counts_toward_pack04':False
    }
    (OUT/'pose-test-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    ok=report['footline_pass'] and pose.mode=='RGBA' and pose.size==CANVAS and len(repair_layers)==6
    print('LIAN_WU_RIG_V21_CONTACT_ABSORB_POSE_TEST='+('PASS' if ok else 'FAIL'))
    print('JOINT_OCCLUSION_REPAIR=CANONICAL_CAPS')
    print('PACK04_PROMOTION_ALLOWED=false')
    return 0 if ok else 1
if __name__=='__main__': raise SystemExit(main())
