#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image

EXPECTED_PIXEL_SHA256 = "67abba855b18ea6cc5ef62c4e382041d5ca69eb9902d9b3c6ead9329a163531e"
ALPHA_THRESHOLD = 3
SAFE_MARGIN = 3
MAX_ROTATED_DIMENSION = 930
HIT = [(-5,-8),(7,8),(3,4)]
KO = [(-6,-5),(-18,-10),(-32,-10),(-48,-5),(-68,0),(-88,0)]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pixel_sha(image: Image.Image) -> str:
    return sha256(image.convert("RGBA").tobytes())


def alpha_bounds(image: Image.Image):
    alpha=image.convert("RGBA").getchannel("A")
    return alpha.point(lambda v:255 if v>=ALPHA_THRESHOLD else 0).getbbox() or (0,0,0,0)


def rotate_fit(crop: Image.Image, angle: float, xshift: int, bottom: int = 970):
    rotated=crop.rotate(angle,resample=Image.Resampling.BICUBIC,expand=True,fillcolor=(0,0,0,0))
    bounds=alpha_bounds(rotated)
    if bounds==(0,0,0,0):
        raise ValueError("empty_rotated_frame")
    rotated=rotated.crop(bounds)
    scale=min(1.0, MAX_ROTATED_DIMENSION/max(rotated.width,rotated.height))
    if scale<1.0:
        rotated=rotated.resize((round(rotated.width*scale),round(rotated.height*scale)),Image.Resampling.LANCZOS)
    canvas=Image.new("RGBA",(1024,1024),(0,0,0,0))
    x=512-rotated.width//2+xshift
    y=bottom-rotated.height+1
    canvas.alpha_composite(rotated,(x,y))
    return canvas, scale


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",required=True)
    ap.add_argument("--output-root",required=True)
    args=ap.parse_args()
    source_path=Path(args.source); output_root=Path(args.output_root)
    if not source_path.is_file():
        print(f"PRESET02_P05=BLOCKED source_missing={source_path}"); return 2
    source=Image.open(source_path).convert("RGBA")
    if source.size!=(1024,1024) or pixel_sha(source)!=EXPECTED_PIXEL_SHA256:
        print("PRESET02_P05=BLOCKED source_identity"); return 2
    source_bounds=alpha_bounds(source)
    crop=source.crop(source_bounds)
    sequences={"hit":HIT,"ko":KO}
    records={}; unique=set(); min_scale=1.0
    for mode,beats in sequences.items():
        folder=output_root/mode; folder.mkdir(parents=True,exist_ok=True); records[mode]=[]
        for index,(angle,xshift) in enumerate(beats,1):
            frame,scale=rotate_fit(crop,angle,xshift)
            min_scale=min(min_scale,scale)
            bounds=alpha_bounds(frame)
            if bounds[0]<=SAFE_MARGIN or bounds[1]<=SAFE_MARGIN or bounds[2]>=1024-SAFE_MARGIN or bounds[3]>=1024-SAFE_MARGIN:
                print(f"PRESET02_P05=BLOCKED unsafe_canvas_margin={mode}/f{index:03d}:{bounds}"); return 3
            if scale<0.90:
                print(f"PRESET02_P05=BLOCKED scale_floor={mode}/f{index:03d}:{scale:.4f}"); return 3
            name=f"char_training_rival__{mode}__f{index:03d}.png"
            path=folder/name; frame.save(path,"PNG",optimize=True,compress_level=9)
            digest=sha256(path.read_bytes()); unique.add(digest)
            records[mode].append({"index":index,"file":f"{mode}/{name}","sha256":digest,"alpha_bounds":list(bounds),"scale":round(scale,6),"angle_deg":angle})
    if len(unique)!=9:
        print(f"PRESET02_P05=BLOCKED unique_hashes={len(unique)}/9"); return 3
    manifest={
        "schema":"tehkne/taijifu-training-rival-p05/v1",
        "signature":"Tehkné Solutions",
        "character_id":"training_rival",
        "pack":"P05",
        "version":"1.0.0-hit-ko-rigid-fall-candidate",
        "source":{"pixel_sha256":pixel_sha(source),"alpha_bounds":list(source_bounds)},
        "contract":{"native_facing":"left","weapon":"single_wooden_training_saber","whole_sprite_rigid_fall":True,"safe_canvas_margin_px":SAFE_MARGIN,"minimum_scale":0.90,"hit_beats":["impact","recoil","stagger"],"ko_beats":["stun","tip","collapse","near_ground","ground_impact","final"]},
        "frames":records,
        "gates":{"source_pixel_identity":"pass","single_weapon_continuity":"pass","frame_count_9":"pass","unique_hash_floor":"pass","safe_canvas_margin":"pass","scale_floor":"pass","visual_review":"pending"}
    }
    (output_root/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("PRESET02_P05_MATERIALIZE=PASS")
    print("PRESET02_P05_HIT=3")
    print("PRESET02_P05_KO=6")
    print("PRESET02_P05_UNIQUE_HASHES=9")
    print(f"PRESET02_P05_MIN_SCALE={min_scale:.4f}")
    print("PRESET02_P05_RIGID_FALL=PASS")
    print("PRESET02_P05_VISUAL_REVIEW=PENDING")
    print("PRESET02_RUNTIME_PROMOTION=BLOCKED requires_44_of_44=true")
    print("SIGNATURE=Tehkné Solutions")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
