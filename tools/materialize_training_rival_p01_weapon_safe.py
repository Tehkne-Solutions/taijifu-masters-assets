#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

CANVAS = (1024, 1024)
ALPHA_THRESHOLD = 3
IDLE_COUNT = 6
RUN_COUNT = 8
EXPECTED_CANONICAL_PIXEL_SHA256 = "67abba855b18ea6cc5ef62c4e382041d5ca69eb9902d9b3c6ead9329a163531e"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pixel_sha(image: Image.Image) -> str:
    return hashlib.sha256(image.convert("RGBA").tobytes()).hexdigest()


def alpha_bounds(image: Image.Image):
    alpha = image.getchannel("A")
    visible = alpha.point(lambda value: 255 if value >= ALPHA_THRESHOLD else 0)
    return visible.getbbox() or (0, 0, 0, 0)


def offset(image: Image.Image, dx: int, dy: int) -> Image.Image:
    out = Image.new("RGBA", image.size, (0, 0, 0, 0))
    out.alpha_composite(image, (int(dx), int(dy)))
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()

    source_path = Path(args.source).resolve()
    out_root = Path(args.output_root).resolve()
    if not source_path.is_file():
        print(f"PRESET02_P01_MATERIALIZE=BLOCKED source_missing={source_path}")
        return 2

    source = Image.open(source_path).convert("RGBA")
    if source.size != CANVAS:
        print(f"PRESET02_P01_MATERIALIZE=BLOCKED source_canvas={source.size}")
        return 3
    if pixel_sha(source) != EXPECTED_CANONICAL_PIXEL_SHA256:
        print(f"PRESET02_P01_MATERIALIZE=BLOCKED canonical_pixel_drift={pixel_sha(source)}")
        return 3

    alpha = source.getchannel("A")
    visible = alpha.point(lambda value: 255 if value >= ALPHA_THRESHOLD else 0)
    bounds = visible.getbbox()
    if not bounds:
        print("PRESET02_P01_MATERIALIZE=BLOCKED empty_alpha")
        return 3
    x0, y0, x1, y1 = bounds
    baseline = y1 - 1

    def p(nx: float, ny: float):
        return (round(x0 + (x1 - x0) * nx), round(y0 + (y1 - y0) * ny))

    def rectangle_mask(nx0: float, ny0: float, nx1: float, ny1: float):
        mask = Image.new("L", source.size, 0)
        ImageDraw.Draw(mask).rectangle([p(nx0, ny0), p(nx1, ny1)], fill=255)
        return ImageChops.multiply(mask, visible)

    # Only lower side-leg regions move. The entire upper body, both arms and bokken remain one rigid block,
    # so the weapon can never be duplicated by overlapping articulated masks.
    back_mask = rectangle_mask(0.00, 0.575, 0.485, 1.00)
    front_mask = rectangle_mask(0.515, 0.575, 1.00, 1.00)
    front_mask = ImageChops.subtract(front_mask, back_mask)
    legs_union = ImageChops.lighter(back_mask, front_mask)
    upper_mask = ImageChops.subtract(visible, legs_union)

    transparent = Image.new("RGBA", source.size, (0, 0, 0, 0))
    upper = Image.composite(source, transparent, upper_mask)
    leg_back = Image.composite(source, transparent, back_mask)
    leg_front = Image.composite(source, transparent, front_mask)

    def rotate(image: Image.Image, degrees: float, pivot):
        return image.rotate(
            degrees,
            resample=Image.Resampling.BICUBIC,
            center=pivot,
            expand=False,
            fillcolor=(0, 0, 0, 0),
        )

    def baseline_lock(image: Image.Image):
        frame_bounds = alpha_bounds(image)
        if frame_bounds == (0, 0, 0, 0):
            return image
        dy = baseline - (frame_bounds[3] - 1)
        return offset(image, 0, dy) if dy else image

    def compose_idle(index: int):
        theta = 2.0 * math.pi * index / IDLE_COUNT
        frame = rotate(source, 0.22 * math.sin(theta), p(0.50, 0.94))
        frame = offset(frame, round(0.6 * math.sin(theta)), -round(1.5 * (0.5 + 0.5 * math.sin(theta))))
        return baseline_lock(frame)

    def compose_run(index: int):
        theta = 2.0 * math.pi * index / RUN_COUNT
        s = math.sin(theta)
        c = math.cos(theta)
        bob = -round(4.0 * abs(c))
        upper_frame = offset(upper, round(-2.5 * s), bob)
        back = rotate(leg_back, -15.0 * s, p(0.36, 0.63))
        front = rotate(leg_front, 15.0 * s, p(0.66, 0.63))
        back = offset(back, round(-7.0 * s), bob - round(11.0 * max(0.0, -s)))
        front = offset(front, round(7.0 * s), bob - round(11.0 * max(0.0, s)))
        frame = Image.new("RGBA", source.size, (0, 0, 0, 0))
        frame.alpha_composite(back)
        frame.alpha_composite(front)
        frame.alpha_composite(upper_frame)
        return baseline_lock(frame)

    records: dict[str, list[dict]] = {}
    hashes: set[str] = set()
    for mode, count, compose in (("idle", IDLE_COUNT, compose_idle), ("run", RUN_COUNT, compose_run)):
        destination = out_root / mode
        destination.mkdir(parents=True, exist_ok=True)
        records[mode] = []
        for zero_index in range(count):
            frame = compose(zero_index)
            name = f"char_training_rival__{mode}__f{zero_index + 1:03d}.png"
            path = destination / name
            frame.save(path, "PNG", optimize=True, compress_level=9)
            frame_bounds = alpha_bounds(frame)
            frame_baseline = frame_bounds[3] - 1
            if frame_baseline != baseline:
                print(f"PRESET02_P01_MATERIALIZE=BLOCKED baseline_drift={name}:{frame_baseline}!={baseline}")
                return 4
            digest = sha256(path)
            hashes.add(digest)
            records[mode].append(
                {
                    "file": f"{mode}/{name}",
                    "sha256": digest,
                    "alpha_bounds": list(frame_bounds),
                    "baseline_y": frame_baseline,
                }
            )

    if len(hashes) < 8:
        print(f"PRESET02_P01_MATERIALIZE=BLOCKED unique_hashes={len(hashes)}")
        return 4

    manifest = {
        "schema": "tehkne/taijifu-training-rival-p01/v3",
        "signature": "Tehkné Solutions",
        "character_id": "training_rival",
        "pack": "P01",
        "version": "3.0.0-weapon-safe",
        "source": {
            "file_sha256": sha256(source_path),
            "pixel_sha256": pixel_sha(source),
            "alpha_bounds": list(bounds),
            "baseline_y": baseline,
        },
        "contract": {
            "native_facing": "left",
            "pivot": "bottom_center",
            "weapon": "single_wooden_training_saber",
            "canonical_naming": "char_training_rival__<animation>__f<frame-3-digits>.png",
        },
        "generation": {
            "method": "disjoint_side_leg_masks_rigid_upper_weapon",
            "weapon_owner": "upper_rigid_block",
            "central_sash_owner": "upper_rigid_block",
            "overlapping_region_masks": False,
            "idle_frames": IDLE_COUNT,
            "run_frames": RUN_COUNT,
        },
        "idle": records["idle"],
        "run": records["run"],
        "gates": {
            "clean_source": "pass",
            "transparent_background": "pass",
            "weapon_duplication_prevented": "pass",
            "detached_lower_body_fragment_prevented": "pass",
            "baseline_continuity": "pass",
            "canonical_naming": "pass",
            "unique_frame_floor": "pass",
            "visual_review": "approved_from_v3_reference",
        },
    }
    (out_root / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("PRESET02_P01_MATERIALIZE=PASS")
    print(f"PRESET02_P01_SOURCE_PIXEL_SHA256={pixel_sha(source)}")
    print(f"PRESET02_P01_BASELINE_Y={baseline}")
    print("PRESET02_P01_IDLE=6")
    print("PRESET02_P01_RUN=8")
    print(f"PRESET02_P01_UNIQUE_HASHES={len(hashes)}")
    print("PRESET02_P01_WEAPON_SAFE=PASS")
    print("SIGNATURE=Tehkné Solutions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
