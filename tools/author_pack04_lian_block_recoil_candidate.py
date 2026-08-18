#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

SIGNATURE = "Tehkné Solutions"
CANVAS = (1024, 1024)
FOOTLINE = 969
SOURCE_SHA256 = "c8e6cd1feece7c2a54cf2279085c2a4bb33338dd6a3dcb3e4d5a2402b537631c"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def alpha_bbox(image: Image.Image):
    return image.getchannel("A").getbbox()


def displacement(frame: int, x: float, y: float) -> tuple[float, float]:
    # Continuous authored recoil deformation. Native facing is right, so the
    # guarded torso yields left while the feet remain effectively anchored.
    t = max(0.0, min(1.0, (930.0 - y) / 650.0))
    upper = t * t
    mid = max(0.0, 1.0 - abs(y - 650.0) / 300.0)
    side = (x - 512.0) / 512.0
    if frame == 1:  # contact absorb
        dx = -10.0 * upper - 3.0 * mid + 1.5 * side * upper
        dy = 4.0 * upper + 4.0 * mid
    elif frame == 2:  # yield
        dx = -18.0 * upper - 7.0 * mid + 2.0 * side * upper
        dy = 8.0 * upper + 8.0 * mid
    else:  # guard recover
        dx = -5.0 * upper - 2.0 * mid + 1.0 * side * upper
        dy = 2.0 * upper + 3.0 * mid
    return dx, dy


def build_mesh(frame: int, cell: int = 64):
    mesh = []
    for y0 in range(0, CANVAS[1], cell):
        for x0 in range(0, CANVAS[0], cell):
            x1 = min(x0 + cell, CANVAS[0])
            y1 = min(y0 + cell, CANVAS[1])
            # Pillow QUAD order is upper-left, lower-left, lower-right, upper-right.
            corners = [(x0, y0), (x0, y1), (x1, y1), (x1, y0)]
            quad = []
            for x, y in corners:
                dx, dy = displacement(frame, x, y)
                quad.extend((x - dx, y - dy))
            mesh.append(((x0, y0, x1, y1), tuple(quad)))
    return mesh


def normalize_footline(image: Image.Image) -> Image.Image:
    bbox = alpha_bbox(image)
    if bbox is None:
        raise ValueError("empty_alpha")
    drift = FOOTLINE - bbox[3]
    if drift == 0:
        return image
    out = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    out.alpha_composite(image, (0, drift))
    return out


def validate(image: Image.Image, label: str) -> dict:
    if image.size != CANVAS or image.mode != "RGBA":
        raise ValueError(f"{label}:canvas_or_mode")
    alpha = image.getchannel("A")
    lo, hi = alpha.getextrema()
    if lo != 0 or hi == 0:
        raise ValueError(f"{label}:alpha")
    bbox = alpha_bbox(image)
    if bbox is None:
        raise ValueError(f"{label}:empty")
    if abs(bbox[3] - FOOTLINE) > 3:
        raise ValueError(f"{label}:footline:{bbox[3]}")
    return {"bbox": list(bbox), "footline": bbox[3], "width": bbox[2] - bbox[0], "height": bbox[3] - bbox[1]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if sha256(args.source) != SOURCE_SHA256:
        raise SystemExit("PACK04_LIAN_BLOCK_RECOIL=BLOCKED source_sha256_mismatch")

    source = Image.open(args.source).convert("RGBA")
    if source.size != CANVAS:
        raise SystemExit(f"PACK04_LIAN_BLOCK_RECOIL=BLOCKED source_canvas={source.size}")

    args.output.mkdir(parents=True, exist_ok=True)
    frames = []
    stats = []
    for index in (1, 2, 3):
        warped = source.transform(CANVAS, Image.Transform.MESH, build_mesh(index), resample=Image.Resampling.BICUBIC)
        warped = normalize_footline(warped)
        filename = f"char_lian_wu__block_recoil__f{index:03d}.png"
        target = args.output / filename
        warped.save(target, optimize=True)
        frame_stats = validate(warped, filename)
        frame_stats.update({"file": filename, "sha256": sha256(target)})
        stats.append(frame_stats)
        frames.append(warped)

    widths = [s["width"] for s in stats]
    heights = [s["height"] for s in stats]
    if (max(widths) - min(widths)) / max(widths) > 0.08 or (max(heights) - min(heights)) / max(heights) > 0.08:
        raise SystemExit("PACK04_LIAN_BLOCK_RECOIL=BLOCKED bounds_variation")

    sheet = Image.new("RGBA", (1024 * 3, 1024), (0, 0, 0, 0))
    for i, frame in enumerate(frames):
        sheet.alpha_composite(frame, (i * 1024, 0))
    sheet.save(args.output / "contact-sheet-candidate-b.png", optimize=True)

    report = {
        "schema": "tehkne/taijifu-pack04-authoring-candidate/v1",
        "signature": SIGNATURE,
        "candidate": "B",
        "fighter": "lian_wu",
        "state": "block_recoil",
        "source": str(args.source),
        "source_sha256": SOURCE_SHA256,
        "method": "continuous_mesh_warp_from_canonical_guard",
        "candidate_a_rejected_reason": "incorrect Pillow QUAD corner order caused visible tile seams",
        "promoted": False,
        "human_review": "PENDING",
        "runtime_authority": False,
        "frames": stats,
    }
    (args.output / "candidate-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print("PACK04_LIAN_BLOCK_RECOIL_CANDIDATE_B=PASS frames=3 promoted=false")
    print("PACK04_LIAN_BLOCK_RECOIL_FOOTLINE=PASS target=969 tolerance=3")
    print("PACK04_LIAN_BLOCK_RECOIL_BOUNDS=PASS max_variation=8pct")
    print("PACK04_LIAN_BLOCK_RECOIL_HUMAN_REVIEW=PENDING")
    print(f"SIGNATURE={SIGNATURE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
