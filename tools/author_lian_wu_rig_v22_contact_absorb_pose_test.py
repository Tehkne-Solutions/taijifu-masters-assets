#!/usr/bin/env python3
from __future__ import annotations
import json, math, subprocess
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
RIG=ROOT/'production/first_playable/lian_wu/rig_v2'
GEN=RIG/'generated'
SRC=ROOT/'production/first_playable/lian_wu/first_playable_lot_01/animations/guard/char_lian_wu__guard__f01.png'
JOINTS=RIG/'joint-anchors-v1.json'
OUT=Path('/tmp/lian_wu_rig_v22_contact_absorb_v3')
CANVAS=(1024,1024); FOOTLINE=969; CELL=24
STATIC=['head_hair','torso','waist_sash','upper_leg_left','lower_leg_left','foot_left','upper_leg_right','lower_leg_right','foot_right']

def combine(parts,names):
    out=Image.new('RGBA',CANVAS,(0,0,0,0))
    for n in names: out=Image.alpha_composite(out,parts[n])
    return out

def weights(x,y,pts):
    vals=[]
    for px,py in pts:
        d=((x-px)**2+(y-py)**2)**0.5
        vals.append(1.0/max(18.0,d)**2)
    s=sum(vals)
    return [v/s for v in vals]

def disp(x,y,src_pts,deltas):
    w=weights(x,y,src_pts)
    dx=sum(w[i]*deltas[i][0] for i in range(3)); dy=sum(w[i]*deltas[i][1] for i in range(3))
    return dx,dy

def mesh_for(src_pts,deltas):
    mesh=[]
    for y0 in range(0,1024,CELL):
        for x0 in range(0,1024,CELL):
            x1=min(x0+CELL,1024); y1=min(y0+CELL,1024); q=[]
            for x,y in ((x0,y0),(x0,y1),(x1,y1),(x1,y0)):
                dx,dy=disp(x,y,src_pts,deltas); q.extend((x-dx,y-dy))
            mesh.append(((x0,y0,x1,y1),tuple(q)))
    return mesh

def warp(im,src_pts,deltas):
    return im.transform(CANVAS,Image.Transform.MESH,mesh_for(src_pts,deltas),resample=Image.Resampling.BICUBIC)

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
        pose=Image.alpha_composite(pose,warp(env,src_pts,deltas))

    pose=Image.alpha_composite(pose,parts['weapon'])
    OUT.mkdir(parents=True,exist_ok=True)
    p=OUT/'char_lian_wu__contact_absorb__pose_test_v3.png'; pose.save(p,optimize=True)
    src=Image.open(SRC).convert('RGBA')
    board=Image.new('RGBA',(2048,1024),(0,0,0,0)); board.alpha_composite(src,(0,0)); board.alpha_composite(pose,(1024,0)); board.save(OUT/'comparison-canonical-vs-contact-absorb-v3.png',optimize=True)
    b=bbox(pose); foot=b[3] if b else None
    report={'schema':'tehkne/taijifu-lian-wu-rig-v22-pose-test/v3','signature':'Tehkné Solutions','pose':'contact_absorb','method':'continuous_arm_envelope_mesh','cell':CELL,'bbox':list(b) if b else None,'footline':foot,'footline_target':FOOTLINE,'footline_pass':foot is not None and abs(foot-FOOTLINE)<=3,'human_review':'PENDING','animation_authoring_allowed':False,'pack04_promotion_allowed':False,'counts_toward_pack04':False}
    (OUT/'pose-test-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    ok=pose.size==CANVAS and pose.mode=='RGBA' and report['footline_pass']
    print('LIAN_WU_RIG_V22_CONTACT_ABSORB_POSE_TEST='+('PASS' if ok else 'FAIL')); print('PACK04_PROMOTION_ALLOWED=false')
    return 0 if ok else 1
if __name__=='__main__': raise SystemExit(main())
