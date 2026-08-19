#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RIG = ROOT / 'production/first_playable/lian_wu/rig_v2'
CONTRACT = RIG / 'layered-master-authored-v1.json'
SLOTS = RIG / 'layered-master-authoring-slots-v1.json'
SRC = ROOT / 'production/first_playable/lian_wu/first_playable_lot_01/animations/guard/char_lian_wu__guard__f01.png'
EXPECTED_SHA = 'c8e6cd1feece7c2a54cf2279085c2a4bb33338dd6a3dcb3e4d5a2402b537631c'
EXPECTED_LAYERS = [
    'head_hair','torso_underpaint_complete','arm_left_complete','arm_right_complete',
    'waist_sash','leg_left_complete','leg_right_complete','weapon_rigid'
]
FORBIDDEN = {
    'regeneration_from_scratch','automatic_inpainting','joint_caps',
    'fragmented_segment_union','independent_segment_rotation'
}

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def main() -> int:
    contract = json.loads(CONTRACT.read_text(encoding='utf-8'))
    slots = json.loads(SLOTS.read_text(encoding='utf-8'))
    errors = []
    if contract.get('source_sha256') != EXPECTED_SHA or slots.get('source_sha256') != EXPECTED_SHA:
        errors.append('canonical source hash contract mismatch')
    if set(contract.get('required_layers', [])) != set(EXPECTED_LAYERS):
        errors.append('required layer set mismatch')
    if set(slots.get('slots', {}).keys()) != set(EXPECTED_LAYERS):
        errors.append('authoring slot set mismatch')
    if not FORBIDDEN.issubset(set(contract.get('forbidden_methods', []))):
        errors.append('forbidden methods contract incomplete')
    if slots.get('automatic_hidden_surface_generation_allowed') is not False:
        errors.append('automatic hidden-surface generation must remain forbidden')
    if SRC.exists() and sha256(SRC) != EXPECTED_SHA:
        errors.append('checked-out canonical raster hash mismatch')

    authored = []
    missing = []
    for name in EXPECTED_LAYERS:
        entry = slots['slots'][name]
        if entry.get('authored'):
            path = entry.get('path')
            declared = entry.get('sha256')
            if not path or not declared:
                errors.append(f'{name}: authored slot requires path and sha256')
                continue
            fp = ROOT / path
            if not fp.exists():
                errors.append(f'{name}: authored file missing: {path}')
            elif sha256(fp) != declared:
                errors.append(f'{name}: authored file hash mismatch')
            else:
                authored.append(name)
        else:
            missing.append(name)

    ready = not errors and len(authored) == len(EXPECTED_LAYERS)
    print('LAYERED_MASTER_CONTRACT=' + ('PASS' if not errors else 'FAIL'))
    print('AUTHORING_READY=' + ('true' if ready else 'false'))
    print('AUTHORED_SLOTS=' + str(len(authored)) + '/8')
    print('MISSING_SLOTS=' + (','.join(missing) if missing else 'NONE'))
    print('ANIMATION_AUTHORING_ALLOWED=false' if not ready else 'ANIMATION_AUTHORING_ALLOWED=pending_reconstruction_gate')
    print('PACK04_PROMOTION_ALLOWED=false')
    if errors:
        for err in errors:
            print('ERROR=' + err)
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
