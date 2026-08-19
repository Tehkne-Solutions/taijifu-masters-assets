#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
PATCH_KIT=Path('/tmp/lian_wu_remaining_hidden_patch_kit_v1')
SUBMISSION=ROOT/'production/first_playable/lian_wu/layered_master/hidden_patch_submission_v1'
OUT=Path('/tmp/lian_wu_hidden_patch_submission_gate_v1')
SLOTS=['torso_underpaint_complete','arm_left_complete','arm_right_complete']

def sha256(p:Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()
def rgba(p:Path)->np.ndarray: return np.array(Image.open(p).convert('RGBA'))

def main()->int:
    OUT.mkdir(parents=True,exist_ok=True)
    report={'schema':'tehkne/taijifu-lian-wu-hidden-patch-submission-gate/v1','signature':'Tehkné Solutions','accepted_slots':0,'required_slots':3,'submission_complete':False,'canonical_reconstruction_allowed':False,'contact_absorb_allowed':False,'pack04_promotion_allowed':False,'counts_toward_pack04':False,'slots':{}}
    for slot in SLOTS:
        d=PATCH_KIT/slot
        meta=json.loads((d/'patch-manifest.json').read_text(encoding='utf-8'))
        mask=np.array(Image.open(d/'remaining_hidden_mask.png').convert('L'))>0
        expected=tuple(meta['crop_size'])
        p=SUBMISSION/f'{slot}.png'
        s={'present':p.exists(),'accepted':False,'expected_size':list(expected),'remaining_hidden_px':int(mask.sum()),'opaque_inside_mask_px':0,'opaque_outside_mask_px':0,'missing_required_px':int(mask.sum()),'sha256':None}
        if p.exists():
            a=rgba(p)
            if (a.shape[1],a.shape[0])!=expected: raise SystemExit(f'{slot}: size mismatch')
            opaque=a[:,:,3]>0; inside=opaque&mask; outside=opaque&~mask; missing=mask&~opaque
            s.update({'opaque_inside_mask_px':int(inside.sum()),'opaque_outside_mask_px':int(outside.sum()),'missing_required_px':int(missing.sum()),'sha256':sha256(p)})
            if outside.any(): raise SystemExit(f'{slot}: opaque pixels outside remaining_hidden_mask')
            if missing.any(): raise SystemExit(f'{slot}: {int(missing.sum())} required pixels missing')
            s['accepted']=True; report['accepted_slots']+=1
        report['slots'][slot]=s
    report['submission_complete']=report['accepted_slots']==report['required_slots']
    (OUT/'hidden-patch-submission-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('LIAN_WU_HIDDEN_PATCH_SUBMISSION_GATE=PASS')
    print(f"ACCEPTED_SLOTS={report['accepted_slots']}/{report['required_slots']}")
    print(f"SUBMISSION_COMPLETE={str(report['submission_complete']).lower()}")
    print('CANONICAL_RECONSTRUCTION_ALLOWED=false')
    print('CONTACT_ABSORB_ALLOWED=false')
    print('PACK04_PROMOTION_ALLOWED=false')
    return 0
if __name__=='__main__': raise SystemExit(main())
