#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw

EXPECTED_PIXEL_SHA256 = "67abba855b18ea6cc5ef62c4e382041d5ca69eb9902d9b3c6ead9329a163531e"
ALPHA_THRESHOLD = 3
SAFE_MARGIN = 3
BEATS = [
    (0, 0, 0, 0, 0),
    (10, 10, 4, -3, 3),
    (4, 2, -1, 4, -4),
    (-14, -20, -6, 6, -6),
    (-10, -14, 2, 4, -4),
    (-3, -4, 1, 1, -1),
]


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
    front_mask = ImageChops.subtract(rect_mask(0.515, 0.575, 1.00, 1.00), back_mask)
    upper_mask = ImageChops.subtract(visible, ImageChops.lighter(back_mask, front_mask))

    def extract(mask: Image.Image) -> Image.Image:
        return Image.composite(source, Image.new("RGBA", source.size, (0, 0, 0, 0)), mask)

    return bounds, p, extract(upper_mask), extract(back_mask), extract(front_mask)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()

    source_path = Path(args.source)
    output_root = Path(args.output_root)
    if not source_path.is_file():
        print(f"PRESET02_P03=BLOCKED source_missing={source_path}")
        return 2

    source = Image.open(source_path).convert("RGBA")
    if source.size != (1024, 1024):
        print(f"PRESET02_P03=BLOCKED canvas={source.size}")
        return 2
    actual_pixel_sha = pixel_sha(source)
    if actual_pixel_sha != EXPECTED_PIXEL_SHA256:
        print(f"PRESET02_P03=BLOCKED source_pixel_sha={actual_pixel_sha}")
        return 2

    _bounds, p, upper_base, back_base, front_base = build_regions(source)
    folder = output_root / "attack_light"
    folder.mkdir(parents=True, exist_ok=True)
    records = []
    unique = set()

    for index, (upper_deg, dx, dy, back_deg, front_deg) in enumerate(BEATS, 1):
        upper = offset(rotate(upper_base, upper_deg, p(.54, .72)), dx, dy)
        back = rotate(back_base, back_deg, p(.36, .66))
        front = rotate(front_base, front_deg, p(.66, .66))
        frame = Image.new("RGBA", source.size, (0, 0, 0, 0))
        frame.alpha_composite(back)
        frame.alpha_composite(front)
        frame.alpha_composite(upper)
        bounds = alpha_bounds(frame)
        if bounds[0] <= SAFE_MARGIN or bounds[1] <= SAFE_MARGIN or bounds[2] >= 1024 - SAFE_MARGIN or bounds[3] >= 1024 - SAFE_MARGIN:
            print(f"PRESET02_P03=BLOCKED unsafe_canvas_margin=f{index:03d}:{bounds}")
            return 3
        name = f"char_training_rival__attack_light__f{index:03d}.png"
        path = folder / name
        frame.save(path, "PNG", optimize=True, compress_level=9)
        digest = sha256_bytes(path.read_bytes())
        unique.add(digest)
        records.append({"index": index, "file": f"attack_light/{name}", "sha256": digest, "alpha_bounds": list(bounds)})

    if len(unique) < 6:
        print(f"PRESET02_P03=BLOCKED unique_hashes={len(unique)}/6")
        return 3

    manifest = {
        "schema": "tehkne/taijifu-training-rival-p03/v1",
        "signature": "Tehkné Solutions",
        "character_id": "training_rival",
        "pack": "P03",
        "version": "1.0.0-attack-light-v2-candidate",
        "source": {"pixel_sha256": actual_pixel_sha, "alpha_bounds": list(alpha_bounds(source))},
        "contract": {
            "native_facing": "left",
            "weapon": "single_wooden_training_saber",
            "upper_and_weapon_rigid_block": True,
            "leg_masks_mutually_exclusive": True,
            "safe_canvas_margin_px": SAFE_MARGIN,
            "beats": ["guard", "chamber", "release", "impact", "follow_through", "recover"],
            "canonical_naming": "char_training_rival__attack_light__f<frame-3-digits>.png"
        },
        "attack_light": records,
        "gates": {
            "source_pixel_identity": "pass",
            "weapon_duplication_structurally_prevented": "pass",
            "frame_count_6": "pass",
            "unique_frame_floor": "pass",
            "safe_canvas_margin": "pass",
            "visual_review": "pending"
        }
    }
    (output_root / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("PRESET02_P03_MATERIALIZE=PASS")
    print("PRESET02_P03_ATTACK_LIGHT=6")
    print("PRESET02_P03_BEATS=guard+chamber+release+impact+follow_through+recover")
    print(f"PRESET02_P03_UNIQUE_HASHES={len(unique)}")
    print("PRESET02_P03_WEAPON_SAFE=PASS")
    print("PRESET02_P03_VISUAL_REVIEW=PENDING")
    print("PRESET02_RUNTIME_PROMOTION=BLOCKED requires_44_of_44=true")
    print("SIGNATURE=Tehkné Solutions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
