#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageChops, ImageDraw
import hashlib, json

SOURCE = Path('production/first_playable/lian_wu/first_playable_lot_01/animations/guard/char_lian_wu__guard__f01.png')
OUTPUT = Path('production/first_playable/lian_wu/rig_v2/generated')
SOURCE_SHA256 = 'c8e6cd1feece7c2a54cf2279085c2a4bb33338dd6a3dcb3e4d5a2402b537631c'
PARTS = [
    'head_hair','torso','upper_arm_left','forearm_left','hand_left',
    'upper_arm_right','forearm_right','hand_right','waist_sash',
    'upper_leg_left','lower_leg_left','foot_left',
    'upper_leg_right','lower_leg_right','foot_right','weapon'
]

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def classify(x:int,y:int)->str:
    # Deterministic first-pass masks from the current canonical guard raster.
    # Priority matters: weapon and hands are carved before larger body regions.
    if 300 <= x <= 430 and 590 <= y <= 740: return 'weapon'
    if 320 <= x <= 455 and 520 <= y <= 685: return 'hand_left'
    if 580 <= x <= 735 and 520 <= y <= 690: return 'hand_right'
    if y < 390: return 'head_hair'
    if y < 590 and x < 425: return 'upper_arm_left'
    if y < 705 and x < 455: return 'forearm_left'
    if y < 590 and x > 610: return 'upper_arm_right'
    if y < 705 and x > 580: return 'forearm_right'
    if y < 555: return 'torso'
    if y < 735: return 'waist_sash'
    if x < 515:
        if y < 830: return 'upper_leg_left'
        if y < 915: return 'lower_leg_left'
        return 'foot_left'
    else:
        if y < 830: return 'upper_leg_right'
        if y < 915: return 'lower_leg_right'
        return 'foot_right'

def main()->int:
    if not SOURCE.exists():
        print(f'RIG_V2_SEGMENTATION=BLOCKED missing={SOURCE}')
        return 2
    if sha256(SOURCE) != SOURCE_SHA256:
        print('RIG_V2_SEGMENTATION=BLOCKED source_sha256_mismatch')
        return 3
    src = Image.open(SOURCE).convert('RGBA')
    if src.size != (1024,1024):
        print('RIG_V2_SEGMENTATION=BLOCKED source_canvas')
        return 4
    OUTPUT.mkdir(parents=True, exist_ok=True)
    layers = {p:Image.new('RGBA',src.size,(0,0,0,0)) for p in PARTS}
    src_px = src.load(); dst = {p:im.load() for p,im in layers.items()}
    opaque = assigned = 0
    counts = {p:0 for p in PARTS}
    for y in range(src.height):
        for x in range(src.width):
            px = src_px[x,y]
            if px[3] == 0: continue
            opaque += 1
            part = classify(x,y)
            dst[part][x,y] = px
            assigned += 1; counts[part] += 1
    reconstructed = Image.new('RGBA',src.size,(0,0,0,0))
    for p in PARTS:
        layers[p].save(OUTPUT/f'{p}.png', optimize=True)
        reconstructed = Image.alpha_composite(reconstructed,layers[p])
    reconstructed.save(OUTPUT/'lian_wu_rig_v2_reconstructed.png', optimize=True)
    exact = ImageChops.difference(src,reconstructed).getbbox() is None
    # Visual mask board for human review; generated only as CI artifact.
    board = Image.new('RGBA',(2048,2048),(0,0,0,0))
    for i,p in enumerate(PARTS):
        thumb = layers[p].copy(); thumb.thumbnail((480,480),Image.Resampling.NEAREST)
        cellx=(i%4)*512; celly=(i//4)*512
        board.alpha_composite(thumb,(cellx+(512-thumb.width)//2,celly+(512-thumb.height)//2))
    board.save(OUTPUT/'segmentation-board.png', optimize=True)
    report = {
        'schema':'tehkne/taijifu-lian-wu-rig-v2-segmentation/v1',
        'signature':'Tehkné Solutions','source_sha256':SOURCE_SHA256,
        'parts':PARTS,'opaque_source_pixels':opaque,'assigned_pixels':assigned,
        'assigned_exactly_once':assigned==opaque,'reconstruction_pixel_exact':exact,
        'part_pixel_counts':counts,'promotion_allowed':False,'runtime_authority':False,
        'human_mask_review':'PENDING'
    }
    (OUTPUT/'segmentation-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    ok = exact and assigned == opaque and all(counts[p] > 0 for p in PARTS)
    print('RIG_V2_SEGMENTATION=' + ('PASS' if ok else 'FAIL'))
    return 0 if ok else 1

if __name__ == '__main__': raise SystemExit(main())
