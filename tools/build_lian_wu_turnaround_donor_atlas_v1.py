#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
from PIL import Image

PATCH_ROOT = Path('/tmp/lian_wu_remaining_hidden_patch_kit_v1')
TURN_ROOT = Path('/tmp/lian_wu_turnaround_raw')
OUT = Path('/tmp/lian_wu_turnaround_donor_atlas_v1')
SLOTS = ['torso_underpaint_complete','arm_left_complete','arm_right_complete']
VIEWS = ['front','side_left','back','side_right']


def load_rgba(path: Path) -> np.ndarray:
    return np.array(Image.open(path).convert('RGBA'))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    views = {
        name: load_rgba(TURN_ROOT / f'char_lian_wu__{name}_raw.png')
        for name in VIEWS
    }
    report = {
        'schema':'tehkne/taijifu-lian-wu-turnaround-donor-atlas/v1',
        'signature':'Tehkné Solutions',
        'classification':'CANDIDATE_DONOR_ONLY',
        'same_xy_donor_is_authoritative':False,
        'notes':[
            'Different turnaround views are different projections; same XY overlap is only a candidate signal.',
            'No pixel from side/back views may be promoted to the front layered master without human-authored remapping/review.',
            'No generative pixels are created by this atlas.'
        ],
        'slots':{},
        'pack04_promotion_allowed':False,
        'counts_toward_pack04':False,
    }
    for slot in SLOTS:
        d = PATCH_ROOT / slot
        manifest = json.loads((d/'patch-manifest.json').read_text())
        x0,y0,x1,y1 = manifest['crop_box_xyxy']
        remaining = np.array(Image.open(d/'remaining_hidden_mask.png').convert('L')) > 0
        union = np.zeros_like(remaining)
        slot_out = OUT / slot
        slot_out.mkdir(exist_ok=True)
        per_view = {}
        for name,arr in views.items():
            crop = arr[y0:y1,x0:x1]
            candidate = remaining & (crop[:,:,3] > 0)
            union |= candidate
            rgba = np.zeros_like(crop)
            rgba[candidate] = crop[candidate]
            Image.fromarray(rgba,'RGBA').save(slot_out/f'{name}__same_xy_candidate.png', optimize=True)
            Image.fromarray((candidate.astype(np.uint8)*255),'L').save(slot_out/f'{name}__candidate_mask.png', optimize=True)
            per_view[name] = int(candidate.sum())
        Image.fromarray((union.astype(np.uint8)*255),'L').save(slot_out/'same_xy_candidate_union_mask.png', optimize=True)
        unresolved = remaining & ~union
        Image.fromarray((unresolved.astype(np.uint8)*255),'L').save(slot_out/'unresolved_after_same_xy_union.png', optimize=True)
        report['slots'][slot] = {
            'remaining_hidden_px': int(remaining.sum()),
            'candidate_px_by_view': per_view,
            'same_xy_union_candidate_px': int(union.sum()),
            'unresolved_after_same_xy_union_px': int(unresolved.sum()),
            'candidate_union_pct': round(float(union.sum())/max(1,int(remaining.sum()))*100,3),
        }
    (OUT/'donor-atlas-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('LIAN_WU_TURNAROUND_DONOR_ATLAS_V1=PASS')
    print('CLASSIFICATION=CANDIDATE_DONOR_ONLY')
    print('PACK04_PROMOTION_ALLOWED=false')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
