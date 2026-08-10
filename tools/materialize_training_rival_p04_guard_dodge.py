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
GUARD_BEATS = [(-2,-2,0,-2,2),(-6,-8,-2,-4,4),(-4,-5,0,-3,3)]
DODGE_BEATS = [(3,6,1,2,-2),(8,24,-2,6,-6),(12,42,-5,9,-9),(7,27,-2,5,-5),(2,8,0,2,-2)]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pixel_sha(image: Image.Image) -> str:
    return sha256(image.convert("RGBA").tobytes())


def alpha_bounds(image: Image.Image):
    alpha = image.convert("RGBA").getchannel("A")
    return alpha.point(lambda v: 255 if v >= ALPHA_THRESHOLD else 0).getbbox() or (0,0,0,0)


def offset(layer: Image.Image, dx: int, dy: int) -> Image.Image:
    out = Image.new("RGBA", layer.size, (0,0,0,0))
    out.alpha_composite(layer, (int(dx), int(dy)))
    return out


def rotate(layer: Image.Image, degrees: float, pivot):
    return layer.rotate(degrees, resample=Image.Resampling.BICUBIC, center=pivot, expand=False, fillcolor=(0,0,0,0))


def regions(source: Image.Image):
    visible = source.getchannel("A").point(lambda v: 255 if v >= ALPHA_THRESHOLD else 0)
    bounds = visible.getbbox()
    if not bounds:
        raise ValueError("empty_alpha")
    x0,y0,x1,y1 = bounds
    def p(nx, ny): return (round(x0+(x1-x0)*nx), round(y0+(y1-y0)*ny))
    def rect(a,b,c,d):
        mask = Image.new("L", source.size, 0)
        ImageDraw.Draw(mask).rectangle([p(a,b), p(c,d)], fill=255)
        return ImageChops.multiply(mask, visible)
    back = rect(0.00,0.575,0.485,1.00)
    front = ImageChops.subtract(rect(0.515,0.575,1.00,1.00), back)
    upper = ImageChops.subtract(visible, ImageChops.lighter(back, front))
    def extract(mask): return Image.composite(source, Image.new("RGBA", source.size, (0,0,0,0)), mask)
    return p, extract(upper), extract(back), extract(front)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--output-root", required=True)
    args = ap.parse_args()
    source_path = Path(args.source)
    output_root = Path(args.output_root)
    if not source_path.is_file():
        print(f"PRESET02_P04=BLOCKED source_missing={source_path}")
        return 2
    source = Image.open(source_path).convert("RGBA")
    if source.size != (1024,1024) or pixel_sha(source) != EXPECTED_PIXEL_SHA256:
        print("PRESET02_P04=BLOCKED source_identity")
        return 2
    p, upper_base, back_base, front_base = regions(source)
    sequences = {"guard": GUARD_BEATS, "dodge": DODGE_BEATS}
    records = {}
    unique = set()
    for mode, beats in sequences.items():
        folder = output_root / mode
        folder.mkdir(parents=True, exist_ok=True)
        records[mode] = []
        for index, (ud,dx,dy,bd,fd) in enumerate(beats,1):
            upper = offset(rotate(upper_base, ud, p(.53,.72)), dx, dy)
            back = offset(rotate(back_base, bd, p(.36,.66)), round(dx*.25), 0)
            front = offset(rotate(front_base, fd, p(.66,.66)), round(dx*.25), 0)
            frame = Image.new("RGBA", source.size, (0,0,0,0))
            frame.alpha_composite(back); frame.alpha_composite(front); frame.alpha_composite(upper)
            bounds = alpha_bounds(frame)
            if bounds[0] <= SAFE_MARGIN or bounds[1] <= SAFE_MARGIN or bounds[2] >= 1024-SAFE_MARGIN or bounds[3] >= 1024-SAFE_MARGIN:
                print(f"PRESET02_P04=BLOCKED unsafe_canvas_margin={mode}/f{index:03d}:{bounds}")
                return 3
            name = f"char_training_rival__{mode}__f{index:03d}.png"
            path = folder / name
            frame.save(path, "PNG", optimize=True, compress_level=9)
            digest = sha256(path.read_bytes())
            unique.add(digest)
            records[mode].append({"index":index,"file":f"{mode}/{name}","sha256":digest,"alpha_bounds":list(bounds)})
    if len(unique) < 8:
        print(f"PRESET02_P04=BLOCKED unique_hashes={len(unique)}/8")
        return 3
    manifest = {
        "schema":"tehkne/taijifu-training-rival-p04/v1",
        "signature":"Tehkné Solutions",
        "character_id":"training_rival",
        "pack":"P04",
        "version":"1.0.0-guard-dodge-candidate",
        "source":{"pixel_sha256":pixel_sha(source),"alpha_bounds":list(alpha_bounds(source))},
        "contract":{"native_facing":"left","weapon":"single_wooden_training_saber","upper_and_weapon_rigid_block":True,"leg_masks_mutually_exclusive":True,"safe_canvas_margin_px":SAFE_MARGIN,"guard_beats":["ready","brace","settle"],"dodge_beats":["anticipation","shift","peak_evade","return","recover"]},
        "frames":records,
        "gates":{"source_pixel_identity":"pass","weapon_duplication_structurally_prevented":"pass","frame_count_8":"pass","unique_hash_floor":"pass","safe_canvas_margin":"pass","visual_review":"pending"}
    }
    (output_root/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("PRESET02_P04_MATERIALIZE=PASS")
    print("PRESET02_P04_GUARD=3")
    print("PRESET02_P04_DODGE=5")
    print(f"PRESET02_P04_UNIQUE_HASHES={len(unique)}")
    print("PRESET02_P04_WEAPON_SAFE=PASS")
    print("PRESET02_P04_VISUAL_REVIEW=PENDING")
    print("PRESET02_RUNTIME_PROMOTION=BLOCKED requires_44_of_44=true")
    print("SIGNATURE=Tehkné Solutions")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
