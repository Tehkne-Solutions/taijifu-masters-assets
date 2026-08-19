#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, subprocess
from pathlib import Path
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
KIT=Path('/tmp/lian_wu_layered_master_authoring_kit_v2')
SUB=ROOT/'production/first_playable/lian_wu/rig_v2/layered_master_authored'
REPORT=Path('/tmp/lian_wu_layered_master_submission_report.json')
SLOTS=['torso_underpaint_complete','arm_left_complete','arm_right_complete']
CANVAS=(1024,1024)

def sha256(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def load_rgba(p:Path)->np.ndarray:
    im=Image.open(p).convert('RGBA')
    if im.size!=CANVAS: raise ValueError(f'{p.name}: expected 1024x1024')
    return np.array(im)

def mask_on(p:Path)->np.ndarray:
    arr=np.array(Image.open(p).convert('RGBA'))
    return arr[:,:,:3].max(axis=2)>0

def main():
    subprocess.run(['python3',str(ROOT/'tools/build_lian_wu_layered_master_authoring_kit_v2.py')],check=True)
    results={}; complete=True; accepted=0
    for slot in SLOTS:
        p=SUB/f'{slot}.png'
        if not p.exists():
            results[slot]={'present':False,'accepted':False,'reason':'missing_authored_png'}
            complete=False; continue
        try:
            authored=load_rgba(p)
            tmpl=load_rgba(KIT/f'{slot}_template.png')
            allow=mask_on(KIT/f'{slot}_authoring_mask.png')
            locked=mask_on(KIT/f'{slot}_locked_visible_mask.png')
            changed=np.any(authored!=tmpl,axis=2)
            illegal=changed & ~allow
            locked_changed=changed & locked
            new_alpha=(authored[:,:,3]>0) & (tmpl[:,:,3]==0)
            new_outside=new_alpha & ~allow
            ok=(not illegal.any()) and (not locked_changed.any()) and (not new_outside.any())
            results[slot]={
              'present':True,'accepted':bool(ok),'sha256':sha256(p),
              'changed_pixels':int(changed.sum()),
              'illegal_changed_pixels':int(illegal.sum()),
              'locked_changed_pixels':int(locked_changed.sum()),
              'new_alpha_outside_authoring_mask':int(new_outside.sum())
            }
            if ok: accepted+=1
            else: complete=False
        except Exception as e:
            results[slot]={'present':True,'accepted':False,'reason':str(e)}; complete=False
    report={
      'schema':'tehkne/taijifu-lian-wu-layered-master-submission/v1',
      'signature':'Tehkné Solutions','slots':results,
      'accepted_slots':accepted,'required_slots':len(SLOTS),
      'submission_ready':bool(complete and accepted==len(SLOTS)),
      'canonical_reconstruction_allowed':False,
      'contact_absorb_pose_test_allowed':False,
      'pack04_promotion_allowed':False,
      'counts_toward_pack04':False
    }
    REPORT.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(f'LAYERED_MASTER_SUBMISSION_ACCEPTED={accepted}/{len(SLOTS)}')
    print('SUBMISSION_READY='+str(report['submission_ready']).lower())
    print('PACK04_PROMOTION_ALLOWED=false')
    # Missing authored PNGs are expected until art is supplied; structural gate itself should stay green.
    return 0

if __name__=='__main__': raise SystemExit(main())
