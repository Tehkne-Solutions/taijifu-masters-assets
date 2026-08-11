#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
RIVAL=ROOT/'production/first_playable/training_rival'
LOT=RIVAL/'first_playable_lot_01'
SOURCE=RIVAL/'source/training_rival_master.png'
REVIEW=RIVAL/'source/PRESET02_P05_REVIEW.json'
P01=LOT/'p01-manifest.json'; P02=LOT/'p02-manifest.json'; P03=LOT/'p03-manifest.json'; P04=LOT/'p04-manifest.json'; P05=LOT/'p05-manifest.json'
WRITER=ROOT/'.github/workflows/materialize-preset02-p05-hit-ko.yml'
EXPECTED_PIXEL_SHA='67abba855b18ea6cc5ef62c4e382041d5ca69eb9902d9b3c6ead9329a163531e'
SAFE_MARGIN=3
EXPECTED={'hit':3,'ko':6}
EXPECTED_REVIEW_RUN=31444693299
EXPECTED_REVIEW_ARTIFACT=9084067772
EXPECTED_REVIEW_DIGEST='sha256:50d742cf09ae4968a2fa7fa40c79d1edb11b2d26b41a17c8cb97936bb6fd91b9'


def digest(path:Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()
def pixel_sha(path:Path)->str: return hashlib.sha256(Image.open(path).convert('RGBA').tobytes()).hexdigest()
def alpha_bounds(path:Path):
    image=Image.open(path).convert('RGBA'); alpha=image.getchannel('A').point(lambda v:255 if v>=3 else 0); return alpha.getbbox() or (0,0,0,0)
def block(reason:str)->int:
    print(f'PRESET02_P05=BLOCKED {reason}'); return 2


def main()->int:
    for path in (SOURCE,REVIEW,P01,P02,P03,P04,P05):
        if not path.is_file(): return block(f'missing={path.relative_to(ROOT).as_posix()}')
    if WRITER.exists(): return block('disposable_writer_present')
    if pixel_sha(SOURCE)!=EXPECTED_PIXEL_SHA: return block('source_pixel_identity')
    review=json.loads(REVIEW.read_text(encoding='utf-8'))
    if review.get('schema')!='tehkne/taijifu-training-rival-p05-review/v1' or review.get('status')!='visually_approved_hit_ko_v1': return block('review_contract')
    if review.get('source_pixel_sha256')!=EXPECTED_PIXEL_SHA or review.get('runtime_ready') is not False: return block('review_source_or_runtime')
    if review.get('visual_review',{}).get('approved_for_completion') is not True: return block('review_not_approved')
    evidence=review.get('evidence',{})
    if evidence.get('workflow_run_id')!=EXPECTED_REVIEW_RUN or evidence.get('artifact_id')!=EXPECTED_REVIEW_ARTIFACT or evidence.get('artifact_digest')!=EXPECTED_REVIEW_DIGEST: return block('review_evidence')
    p01=json.loads(P01.read_text(encoding='utf-8')); p02=json.loads(P02.read_text(encoding='utf-8')); p03=json.loads(P03.read_text(encoding='utf-8')); p04=json.loads(P04.read_text(encoding='utf-8')); p05=json.loads(P05.read_text(encoding='utf-8'))
    if p05.get('schema')!='tehkne/taijifu-training-rival-p05/v1' or p05.get('signature')!='Tehkné Solutions': return block('manifest_identity')
    if p05.get('version')!=review.get('manifest_version') or p05.get('source',{}).get('pixel_sha256')!=EXPECTED_PIXEL_SHA: return block('manifest_or_review_drift')
    contract=p05.get('contract',{})
    if contract.get('whole_sprite_rigid_fall') is not True or contract.get('safe_canvas_margin_px')!=SAFE_MARGIN: return block('rigid_fall_or_margin')
    if contract.get('minimum_scale')!=0.90: return block('scale_contract')
    if contract.get('hit_beats')!=['impact','recoil','stagger'] or contract.get('ko_beats')!=['stun','tip','collapse','near_ground','ground_impact','final']: return block('beat_contract')
    unique=set(); total=0; min_scale=1.0
    for mode,count in EXPECTED.items():
        records=p05.get('frames',{}).get(mode,[])
        if len(records)!=count: return block(f'{mode}_manifest_count={len(records)}/{count}')
        for index,record in enumerate(records,1):
            name=f'char_training_rival__{mode}__f{index:03d}.png'; path=LOT/'animations'/mode/name
            if record.get('file')!=f'{mode}/{name}' or not path.is_file(): return block(f'{mode}_frame={index}')
            image=Image.open(path)
            if image.size!=(1024,1024) or image.mode!='RGBA': return block(f'frame_contract={name}')
            file_sha=digest(path); bounds=alpha_bounds(path); scale=float(record.get('scale',0.0)); min_scale=min(min_scale,scale)
            if file_sha!=record.get('sha256') or list(bounds)!=record.get('alpha_bounds'): return block(f'frame_integrity={name}')
            if bounds[0]<=SAFE_MARGIN or bounds[1]<=SAFE_MARGIN or bounds[2]>=1024-SAFE_MARGIN or bounds[3]>=1024-SAFE_MARGIN: return block(f'unsafe_canvas_margin={name}:{bounds}')
            if scale<0.90: return block(f'scale_floor={name}:{scale}')
            unique.add(file_sha); total+=1
    if total!=9 or len(unique)!=9: return block(f'frame_or_unique_count={total}/9 unique={len(unique)}/9')
    p01_count=len(p01.get('idle',[]))+len(p01.get('run',[])); p02_count=sum(len(p02.get('frames',{}).get(m,[])) for m in ('jump_start','airborne','fall')); p03_count=len(p03.get('attack_light',[])); p04_count=sum(len(p04.get('frames',{}).get(m,[])) for m in ('guard','dodge'))
    if (p01_count,p02_count,p03_count,p04_count)!=(14,7,6,8): return block(f'prior_regression={p01_count},{p02_count},{p03_count},{p04_count}')
    all_rival=list((LOT/'animations').glob('*/*.png'))
    if len(all_rival)!=44: return block(f'global_progress={len(all_rival)}/44_expected')
    print('PRESET02_P05_FRAME_COUNT=9/9')
    print('PRESET02_P05_HIT=3/3')
    print('PRESET02_P05_KO=6/6')
    print('PRESET02_P05_UNIQUE_HASHES=9')
    print(f'PRESET02_P05_MIN_SCALE={min_scale:.4f}')
    print('PRESET02_P05_SAFE_CANVAS_MARGIN=PASS')
    print('PRESET02_P05_RIGID_FALL=PASS')
    print('PRESET02_P05_VISUAL_REVIEW=PASS evidence_frozen=true')
    print('PRESET02_P05_DISPOSABLE_WRITER=ABSENT')
    print('PRESET02_P01_REGRESSION=PASS frames=14/14')
    print('PRESET02_P02_REGRESSION=PASS frames=7/7')
    print('PRESET02_P03_REGRESSION=PASS frames=6/6')
    print('PRESET02_P04_REGRESSION=PASS frames=8/8')
    print('PRESET02_RIVAL_GLOBAL_PROGRESS=44/44')
    print('PRESET02_CANONICAL_COMPLETION=PASS frames=44/44')
    print('PRESET02_P05=PASS')
    print('PRESET02_RUNTIME_PROMOTION=BLOCKED requires_game_c28_import_and_godot_runtime_bench=true')
    print('SIGNATURE=Tehkné Solutions')
    return 0

if __name__=='__main__': raise SystemExit(main())
