#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
KIT_DIR = Path('/tmp/lian_wu_layered_master_authoring_kit_v2')
OUT = Path('/tmp/lian_wu_remaining_hidden_patch_kit_v1')
CANONICAL = KIT_DIR / 'canonical-source.png'
FRONT_URL = 'https://raw.githubusercontent.com/Tehkne-Solutions/taijifu-masters/main/assets/characters/lian_wu/character_lock/lian_wu_neutral.png'
EXPECTED_FRONT_SHA = '0e435757b5c8a114f3ba91653f79bc86db51ee9cf3bfb74c529efed5d4ff7ab5'
EXPECTED_CANONICAL_SHA = 'c8e6cd1feece7c2a54cf2279085c2a4bb33338dd6a3dcb3e4d5a2402b537631c'
SLOTS = ['torso_underpaint_complete', 'arm_left_complete', 'arm_right_complete']
PADDING = 28


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download(url: str, dest: Path) -> None:
    dest.write_bytes(urlopen(url, timeout=30).read())


def crop_box(mask: np.ndarray, padding: int = PADDING) -> tuple[int, int, int, int]:
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        raise RuntimeError('empty remaining mask')
    x0 = max(0, int(xs.min()) - padding)
    y0 = max(0, int(ys.min()) - padding)
    x1 = min(mask.shape[1], int(xs.max()) + 1 + padding)
    y1 = min(mask.shape[0], int(ys.max()) + 1 + padding)
    return x0, y0, x1, y1


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if not CANONICAL.exists():
        raise SystemExit('authoring kit v2 canonical-source.png missing')
    if sha256(CANONICAL) != EXPECTED_CANONICAL_SHA:
        raise SystemExit('canonical source hash mismatch')

    front_path = OUT / 'char_lian_wu__front_clean_recovered.png'
    download(FRONT_URL, front_path)
    if sha256(front_path) != EXPECTED_FRONT_SHA:
        raise SystemExit('front clean source hash mismatch')

    canonical = np.array(Image.open(CANONICAL).convert('RGBA'))
    front = np.array(Image.open(front_path).convert('RGBA'))
    manifest = {
        'schema': 'tehkne/taijifu-lian-wu-remaining-hidden-patch-kit/v1',
        'signature': 'Tehkné Solutions',
        'canonical_sha256': EXPECTED_CANONICAL_SHA,
        'front_clean_sha256': EXPECTED_FRONT_SHA,
        'generative_pixels_created': False,
        'automatic_inpainting_used': False,
        'slots': {},
        'pack04_promotion_allowed': False,
        'counts_toward_pack04': False,
    }

    total_remaining = 0
    for slot in SLOTS:
        author_path = KIT_DIR / f'{slot}_authoring_mask.png'
        locked_path = KIT_DIR / f'{slot}_locked_visible_mask.png'
        if not author_path.exists() or not locked_path.exists():
            raise SystemExit(f'missing masks for {slot}')

        author = np.array(Image.open(author_path).convert('L')) > 0
        locked = np.array(Image.open(locked_path).convert('L')) > 0
        hidden = author & (canonical[:, :, 3] == 0)
        recovered = hidden & (front[:, :, 3] > 0)
        remaining = hidden & ~recovered

        if np.any(remaining & locked):
            raise SystemExit(f'locked overlap in {slot}')

        n, labels, stats, _ = cv2.connectedComponentsWithStats(remaining.astype(np.uint8), 8)
        components = []
        for i in range(1, n):
            x, y, w, h, area = [int(v) for v in stats[i]]
            components.append({'area_px': area, 'bbox': [x, y, w, h]})
        components.sort(key=lambda c: c['area_px'], reverse=True)

        box = crop_box(remaining)
        x0, y0, x1, y1 = box
        crop = canonical[y0:y1, x0:x1].copy()
        front_crop = front[y0:y1, x0:x1].copy()
        rem_crop = remaining[y0:y1, x0:x1]
        rec_crop = recovered[y0:y1, x0:x1]

        # Context image: canonical visible pixels + recovered real pixels + red outline for remaining region.
        context = crop.copy()
        context[rec_crop] = front_crop[rec_crop]
        ctx_img = Image.fromarray(context, 'RGBA')
        draw = ImageDraw.Draw(ctx_img, 'RGBA')
        contours, _ = cv2.findContours(rem_crop.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            pts = [(int(p[0][0]), int(p[0][1])) for p in contour]
            if len(pts) >= 2:
                draw.line(pts + [pts[0]], fill=(255, 64, 64, 255), width=2)

        slot_dir = OUT / slot
        slot_dir.mkdir(exist_ok=True)
        ctx_img.save(slot_dir / 'context_crop.png', optimize=True)
        Image.fromarray((rem_crop.astype(np.uint8) * 255), 'L').save(slot_dir / 'remaining_hidden_mask.png', optimize=True)
        Image.fromarray((rec_crop.astype(np.uint8) * 255), 'L').save(slot_dir / 'recovered_real_mask.png', optimize=True)

        partial = np.zeros_like(crop)
        partial[rec_crop] = front_crop[rec_crop]
        Image.fromarray(partial, 'RGBA').save(slot_dir / 'recovered_real_pixels.png', optimize=True)

        blank = np.zeros_like(crop)
        Image.fromarray(blank, 'RGBA').save(slot_dir / 'authoring_patch_blank.png', optimize=True)

        slot_info = {
            'crop_box_xyxy': list(box),
            'crop_size': [x1 - x0, y1 - y0],
            'hidden_target_px': int(hidden.sum()),
            'recovered_real_px': int(recovered.sum()),
            'remaining_hidden_px': int(remaining.sum()),
            'locked_overlap_px': int((remaining & locked).sum()),
            'connected_components': components,
            'largest_component_px': components[0]['area_px'] if components else 0,
            'largest_component_bbox': components[0]['bbox'] if components else None,
            'files': {
                p.name: sha256(p)
                for p in sorted(slot_dir.glob('*')) if p.is_file()
            },
        }
        (slot_dir / 'patch-manifest.json').write_text(json.dumps(slot_info, indent=2) + '\n', encoding='utf-8')
        manifest['slots'][slot] = slot_info
        total_remaining += int(remaining.sum())

    manifest['total_remaining_hidden_px'] = total_remaining
    manifest['authoring_complete'] = False
    (OUT / 'remaining-hidden-patch-kit-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print('LIAN_WU_REMAINING_HIDDEN_PATCH_KIT_V1=PASS')
    print(f'TOTAL_REMAINING_HIDDEN_PIXELS={total_remaining}')
    print('GENERATIVE_PIXELS_CREATED=false')
    print('PACK04_PROMOTION_ALLOWED=false')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
