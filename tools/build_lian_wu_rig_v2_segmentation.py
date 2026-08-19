#!/usr/bin/env python3
from __future__ import annotations

from collections import deque
from pathlib import Path
from PIL import Image, ImageChops
import hashlib, json, math

SOURCE = Path('production/first_playable/lian_wu/first_playable_lot_01/animations/guard/char_lian_wu__guard__f01.png')
OUTPUT = Path('production/first_playable/lian_wu/rig_v2/generated')
SOURCE_SHA256 = 'c8e6cd1feece7c2a54cf2279085c2a4bb33338dd6a3dcb3e4d5a2402b537631c'
PARTS = [
    'head_hair','torso','upper_arm_left','forearm_left','hand_left',
    'upper_arm_right','forearm_right','hand_right','waist_sash',
    'upper_leg_left','lower_leg_left','foot_left',
    'upper_leg_right','lower_leg_right','foot_right','weapon'
]

# Seeds are measured against the verified canonical guard raster.  They are not
# animation anchors; they are only ownership centers for visible pixels.
SEEDS = {
    'head_hair': (512, 255),
    'torso': (515, 485),
    'upper_arm_left': (410, 500),
    'forearm_left': (372, 590),
    'hand_left': (348, 676),
    'upper_arm_right': (616, 505),
    'forearm_right': (660, 590),
    'hand_right': (690, 675),
    'waist_sash': (512, 675),
    'upper_leg_left': (450, 770),
    'lower_leg_left': (430, 870),
    'foot_left': (410, 950),
    'upper_leg_right': (575, 770),
    'lower_leg_right': (602, 870),
    'foot_right': (625, 950),
    'weapon': (350, 680),
}

# Weighting prevents the central torso/waist seeds from swallowing limbs while
# keeping the split deterministic and continuous around the actual silhouette.
WEIGHT = {
    'head_hair': (1.0, 0.8), 'torso': (1.0, 1.0), 'waist_sash': (1.0, 1.15),
    'upper_arm_left': (0.9, 1.0), 'forearm_left': (0.85, 1.0), 'hand_left': (0.8, 0.9),
    'upper_arm_right': (0.9, 1.0), 'forearm_right': (0.85, 1.0), 'hand_right': (0.8, 0.9),
    'upper_leg_left': (0.95, 0.9), 'lower_leg_left': (0.9, 0.85), 'foot_left': (0.8, 0.7),
    'upper_leg_right': (0.95, 0.9), 'lower_leg_right': (0.9, 0.85), 'foot_right': (0.8, 0.7),
    'weapon': (0.72, 0.82),
}

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def weapon_override(x:int,y:int)->bool:
    # The sword/scabbard is visually distinct and must remain one rigid piece.
    return 305 <= x <= 430 and 610 <= y <= 735

def owner(x:int,y:int)->str:
    if weapon_override(x,y):
        return 'weapon'
    best = None
    best_d = float('inf')
    for part,(sx,sy) in SEEDS.items():
        if part == 'weapon':
            continue
        wx,wy = WEIGHT[part]
        d = ((x-sx)*wx)**2 + ((y-sy)*wy)**2
        if d < best_d:
            best_d = d; best = part
    return best or 'torso'

def component_stats(layer:Image.Image)->dict:
    alpha = layer.getchannel('A')
    px = alpha.load(); w,h = layer.size
    seen=set(); sizes=[]
    for y in range(h):
        for x in range(w):
            if px[x,y] == 0 or (x,y) in seen:
                continue
            q=deque([(x,y)]); seen.add((x,y)); n=0
            while q:
                cx,cy=q.popleft(); n+=1
                for nx,ny in ((cx+1,cy),(cx-1,cy),(cx,cy+1),(cx,cy-1)):
                    if 0 <= nx < w and 0 <= ny < h and px[nx,ny] > 0 and (nx,ny) not in seen:
                        seen.add((nx,ny)); q.append((nx,ny))
            sizes.append(n)
    sizes.sort(reverse=True)
    total=sum(sizes)
    return {
        'components': len(sizes),
        'largest_component_pixels': sizes[0] if sizes else 0,
        'largest_component_ratio': round((sizes[0]/total),6) if total else 0.0,
    }

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
    opaque = assigned = 0; counts = {p:0 for p in PARTS}

    for y in range(src.height):
        for x in range(src.width):
            px = src_px[x,y]
            if px[3] == 0: continue
            opaque += 1
            part = owner(x,y)
            dst[part][x,y] = px
            assigned += 1; counts[part] += 1

    reconstructed = Image.new('RGBA',src.size,(0,0,0,0))
    stats={}
    for p in PARTS:
        layers[p].save(OUTPUT/f'{p}.png', optimize=True)
        reconstructed = Image.alpha_composite(reconstructed,layers[p])
        stats[p]=component_stats(layers[p])
    reconstructed.save(OUTPUT/'lian_wu_rig_v2_reconstructed.png', optimize=True)
    exact = ImageChops.difference(src,reconstructed).getbbox() is None

    board = Image.new('RGBA',(2048,2048),(0,0,0,0))
    for i,p in enumerate(PARTS):
        thumb = layers[p].copy(); thumb.thumbnail((480,480),Image.Resampling.NEAREST)
        cellx=(i%4)*512; celly=(i//4)*512
        board.alpha_composite(thumb,(cellx+(512-thumb.width)//2,celly+(512-thumb.height)//2))
    board.save(OUTPUT/'segmentation-board.png', optimize=True)

    report = {
        'schema':'tehkne/taijifu-lian-wu-rig-v2-segmentation/v2',
        'signature':'Tehkné Solutions','source_sha256':SOURCE_SHA256,
        'method':'anatomical_weighted_seed_partition_with_weapon_override',
        'parts':PARTS,'seeds':SEEDS,
        'opaque_source_pixels':opaque,'assigned_pixels':assigned,
        'assigned_exactly_once':assigned==opaque,'reconstruction_pixel_exact':exact,
        'part_pixel_counts':counts,'component_stats':stats,
        'promotion_allowed':False,'runtime_authority':False,
        'human_mask_review':'PENDING'
    }
    (OUTPUT/'segmentation-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    ok = exact and assigned == opaque and all(counts[p] > 0 for p in PARTS)
    print('RIG_V2_SEGMENTATION=' + ('PASS' if ok else 'FAIL'))
    print('RIG_V2_SEGMENTATION_METHOD=ANATOMICAL_SEEDS_V2')
    return 0 if ok else 1

if __name__ == '__main__': raise SystemExit(main())
