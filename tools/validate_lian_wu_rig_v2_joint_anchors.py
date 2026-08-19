#!/usr/bin/env python3
from __future__ import annotations
import json, hashlib
from pathlib import Path
from PIL import Image

ROOT = Path('production/first_playable/lian_wu')
SOURCE = ROOT/'first_playable_lot_01/animations/guard/char_lian_wu__guard__f01.png'
JOINTS = ROOT/'rig_v2/joint-anchors-v1.json'
EXPECTED_SHA = 'c8e6cd1feece7c2a54cf2279085c2a4bb33338dd6a3dcb3e4d5a2402b537631c'
EXPECTED = {
    'neck','shoulder_left','elbow_left','wrist_left','shoulder_right','elbow_right','wrist_right',
    'hip_left','knee_left','ankle_left','hip_right','knee_right','ankle_right'
}

def sha256(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main()->int:
    if not SOURCE.exists() or not JOINTS.exists():
        print('RIG_V2_JOINTS=BLOCKED missing_source_or_manifest'); return 2
    if sha256(SOURCE) != EXPECTED_SHA:
        print('RIG_V2_JOINTS=BLOCKED source_sha256_mismatch'); return 3
    src = Image.open(SOURCE).convert('RGBA')
    data = json.loads(JOINTS.read_text(encoding='utf-8'))
    joints = data.get('joints', {})
    if set(joints) != EXPECTED or data.get('joint_count') != 13:
        print('RIG_V2_JOINTS=FAIL joint_set'); return 4
    if data.get('canvas') != [1024,1024] or src.size != (1024,1024):
        print('RIG_V2_JOINTS=FAIL canvas'); return 5
    bad=[]
    for name,xy in joints.items():
        if not isinstance(xy,list) or len(xy)!=2: bad.append(name); continue
        x,y = xy
        if not (0 <= x < 1024 and 0 <= y < 1024): bad.append(name)
    if bad:
        print('RIG_V2_JOINTS=FAIL bad='+','.join(bad)); return 6
    # Kinematic ordering sanity checks.
    j=joints
    checks = [
        j['shoulder_left'][1] < j['elbow_left'][1] < j['wrist_left'][1],
        j['shoulder_right'][1] < j['elbow_right'][1] < j['wrist_right'][1],
        j['hip_left'][1] < j['knee_left'][1] < j['ankle_left'][1] <= 969,
        j['hip_right'][1] < j['knee_right'][1] < j['ankle_right'][1] <= 969,
        j['neck'][1] < j['shoulder_left'][1] and j['neck'][1] < j['shoulder_right'][1]
    ]
    if not all(checks):
        print('RIG_V2_JOINTS=FAIL kinematic_order'); return 7
    if data.get('animation_authoring_allowed') is not False or data.get('pack04_promotion_allowed') is not False:
        print('RIG_V2_JOINTS=FAIL fail_closed_flags'); return 8
    print('RIG_V2_JOINTS=PASS count=13 source=canonical')
    print('SIGNATURE=Tehkné Solutions')
    return 0

if __name__=='__main__': raise SystemExit(main())
