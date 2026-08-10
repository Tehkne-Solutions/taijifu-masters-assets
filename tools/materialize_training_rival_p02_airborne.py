#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

CANVAS = (1024, 1024)
ALPHA_THRESHOLD = 3
SAFE_MARGIN = 3
EXPECTED_PIXEL_SHA256 = "67abba855b18ea6cc5ef62c4e382041d5ca69eb9902d9b3c6ead9329a163531e"
COUNTS = {"jump_start": 3, "airborne": 2, "fall": 2}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pixel_sha(image: Image.Image) -> str:
    return sha256_bytes(image.convert("RGBA").tobytes())


def alpha_bounds(image: Image.Image) -> tuple[int, int, int, int]:
    alpha = image.convert("RGBA").getchannel("A")
    visible = alpha.point(lambda v: 255 if v >= ALPHA_THRESHOLD else 0)
    return visible.getbbox() or (0, 0, 0, 0)


def offset(layer: Image.Image, dx: int, dy: int) -> Image.Image:
    out = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    out.alpha_composite(layer, (int(dx), int(dy)))
    return out


def rotate(layer: Image.Image, degrees: float, pivot: tuple[int, int]) -> Image.Image:
    return layer.rotate(degrees, resample=Image.Resampling.BICUBIC, center=pivot, expand=False, fillcolor=(0, 0, 0, 0))


def build_regions(source: Image.Image):
    visible = source.getchannel("A").point(lambda v: 255 if v >= ALPHA_THRESHOLD else 0)
    bounds = visible.getbbox()
    if not bounds:
        raise ValueError("empty_alpha")
    x0, y0, x1, y1 = bounds

    def p(nx: float, ny: float) -> tuple[int, int]:
        return (round(x0 + (x1 - x0) * nx), round(y0 + (y1 - y0) * ny))

    def rect_mask(nx0: float, ny0: float, nx1: float, ny1: float) -> Image.Image:
        mask = Image.new("L", source.size, 0)
        ImageDraw.Draw(mask).rectangle([p(nx0, ny0), p(nx1, ny1)], fill=255)
        return ImageChops.multiply(mask, visible)

    back_mask = rect_mask(0.00, 0.575, 0.485, 1.00)
    front_mask = rect_mask(0.515, 0.575, 1.00, 1.00)
    front_mask = ImageChops.subtract(front_mask, back_mask)
    legs_union = ImageChops.lighter(back_mask, front_mask)
    upper_mask = ImageChops.subtract(visible, legs_union)

    def extract(mask: Image.Image) -> Image.Image:
        return Image.composite(source, Image.new("RGBA", source.size, (0, 0, 0, 0)), mask)

    return bounds, p, extract(upper_mask), extract(back_mask), extract(front_mask)


def compose(source: Image.Image, mode: str, index: int) -> Image.Image:
    _bounds, p, upper_base, back_base, front_base = build_regions(source)

    if mode == "jump_start":
        if index == 0:
            upper, back, front = upper_base, back_base, front_base
        elif index == 1:
            upper = offset(upper_base, 0, 14)
            back = offset(rotate(back_base, 9, p(.36, .64)), 5, 6)
            front = offset(rotate(front_base, -10, p(.66, .64)), -5, 6)
        else:
            upper = offset(rotate(upper_base, -1.8, p(.50, .72)), -3, -22)
            back = offset(rotate(back_base, -15, p(.36, .64)), -4, -8)
            front = offset(rotate(front_base, 18, p(.66, .64)), 7, -15)
    elif mode == "airborne":
        if index == 0:
            upper = offset(rotate(upper_base, -3.5, p(.50, .70)), -6, -36)
            back = offset(rotate(back_base, 28, p(.36, .64)), 5, -22)
            front = offset(rotate(front_base, -30, p(.66, .64)), -4, -28)
        else:
            upper = offset(rotate(upper_base, -1.5, p(.50, .70)), 2, -40)
            back = offset(rotate(back_base, 20, p(.36, .64)), 9, -24)
            front = offset(rotate(front_base, -22, p(.66, .64)), -8, -28)
    elif mode == "fall":
        if index == 0:
            upper = offset(rotate(upper_base, 2.5, p(.50, .70)), 4, -30)
            back = offset(rotate(back_base, 10, p(.36, .64)), 2, -16)
            front = offset(rotate(front_base, -12, p(.66, .64)), -2, -18)
        else:
            upper = offset(rotate(upper_base, 1.0, p(.50, .76)), 1, -12)
            back = offset(rotate(back_base, 4, p(.36, .64)), 0, -6)
            front = offset(rotate(front_base, -5, p(.66, .64)), 0, -8)
    else:
        raise ValueError(mode)

    out = Image.new("RGBA", source.size, (0, 0, 0, 0))
    out.alpha_composite(back)
    out.alpha_composite(front)
    out.alpha_composite(upper)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()

    source_path = Path(args.source)
    output_root = Path(args.output_root)
    if not source_path.is_file():
        print(f"PRESET02_P02=BLOCKED source_missing={source_path}")
        return 2

    source = Image.open(source_path).convert("RGBA")
    if source.size != CANVAS:
        print(f"PRESET02_P02=BLOCKED canvas={source.size}")
        return 2
    actual_pixel_sha = pixel_sha(source)
    if actual_pixel_sha != EXPECTED_PIXEL_SHA256:
        print(f"PRESET02_P02=BLOCKED source_pixel_sha={actual_pixel_sha}")
        return 2

    records: dict[str, list[dict]] = {}
    unique_hashes: set[str] = set()
    for mode, count in COUNTS.items():
        folder = output_root / mode
        folder.mkdir(parents=True, exist_ok=True)
        records[mode] = []
        for index in range(count):
            frame = compose(source, mode, index)
            frame_bounds = alpha_bounds(frame)
            if (
                frame_bounds[0] <= SAFE_MARGIN
                or frame_bounds[1] <= SAFE_MARGIN
                or frame_bounds[2] >= CANVAS[0] - SAFE_MARGIN
                or frame_bounds[3] >= CANVAS[1] - SAFE_MARGIN
            ):
                print(f"PRESET02_P02=BLOCKED unsafe_canvas_margin={mode}/f{index + 1:03d}:{frame_bounds}")
                return 3
            name = f"char_training_rival__{mode}__f{index + 1:03d}.png"
            path = folder / name
            frame.save(path, "PNG", optimize=True, compress_level=9)
            digest = sha256_bytes(path.read_bytes())
            unique_hashes.add(digest)
            records[mode].append({
                "index": index + 1,
                "file": f"{mode}/{name}",
                "sha256": digest,
                "alpha_bounds": list(frame_bounds),
            })

    if len(unique_hashes) < 6:
        print(f"PRESET02_P02=BLOCKED insufficient_unique_frames={len(unique_hashes)}/7")
        return 3

    manifest = {
        "schema": "tehkne/taijifu-training-rival-p02/v1",
        "signature": "Tehkné Solutions",
        "character_id": "training_rival",
        "pack": "P02",
        "version": "1.0.1-airborne-candidate-safe-margin",
        "source": {"pixel_sha256": actual_pixel_sha, "alpha_bounds": list(alpha_bounds(source))},
        "contract": {
            "native_facing": "left",
            "pivot": "bottom_center_runtime",
            "weapon": "single_wooden_training_saber",
            "upper_and_weapon_rigid_block": True,
            "leg_masks_mutually_exclusive": True,
            "safe_canvas_margin_px": SAFE_MARGIN,
            "canonical_naming": "char_training_rival__<animation>__f<frame-3-digits>.png",
        },
        "frames": records,
        "gates": {
            "source_pixel_identity": "pass",
            "weapon_duplication_structurally_prevented": "pass",
            "frame_count_7": "pass",
            "safe_canvas_margin": "pass",
            "unique_frame_floor": "pass",
            "visual_review": "pending",
        },
    }
    (output_root / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("PRESET02_P02_MATERIALIZE=PASS")
    print(f"PRESET02_P02_SOURCE_PIXEL_SHA256={actual_pixel_sha}")
    print("PRESET02_P02_JUMP_START=3")
    print("PRESET02_P02_AIRBORNE=2")
    print("PRESET02_P02_FALL=2")
    print(f"PRESET02_P02_UNIQUE_HASHES={len(unique_hashes)}")
    print("PRESET02_P02_SAFE_CANVAS_MARGIN=PASS")
    print("PRESET02_P02_WEAPON_SAFE=PASS")
    print("PRESET02_P02_VISUAL_REVIEW=PENDING")
    print("SIGNATURE=Tehkné Solutions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
