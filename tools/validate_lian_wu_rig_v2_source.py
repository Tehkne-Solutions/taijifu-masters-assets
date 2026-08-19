from __future__ import annotations
from pathlib import Path
from PIL import Image
import hashlib, json, sys

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/'production/first_playable/lian_wu/rig_v2/rig-contract.json'

def sha256(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main()->int:
    c=json.loads(CONTRACT.read_text(encoding='utf-8'))
    s=c['source']; p=ROOT/s['path']
    if not p.exists():
        print(f'LIAN_WU_RIG_V2_SOURCE=BLOCKED missing={p}'); return 2
    if sha256(p)!=s['sha256']:
        print('LIAN_WU_RIG_V2_SOURCE=FAIL sha256'); return 1
    if p.stat().st_size!=s['size_bytes']:
        print('LIAN_WU_RIG_V2_SOURCE=FAIL size'); return 1
    im=Image.open(p)
    cv=c['canvas']
    if im.size!=(cv['width'],cv['height']) or im.mode!=cv['mode']:
        print('LIAN_WU_RIG_V2_SOURCE=FAIL canvas'); return 1
    bbox=im.getchannel('A').getbbox()
    if not bbox or abs(bbox[3]-cv['footline'])>cv['footline_tolerance']:
        print(f'LIAN_WU_RIG_V2_SOURCE=FAIL footline bbox={bbox}'); return 1
    if c['gates']['regeneration_from_scratch'] or c['gates']['runtime_promotion']:
        print('LIAN_WU_RIG_V2_SOURCE=FAIL fail_closed_contract'); return 1
    print(f'LIAN_WU_RIG_V2_SOURCE=PASS sha256={s["sha256"]} bbox={bbox}')
    print('RIG_V2_RUNTIME_PROMOTION=BLOCKED')
    print('SIGNATURE=Tehkné Solutions')
    return 0

if __name__=='__main__': raise SystemExit(main())
