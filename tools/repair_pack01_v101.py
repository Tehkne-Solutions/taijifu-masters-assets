#!/usr/bin/env python3
"""Deterministic non-destructive repair helper for Pack 01 v1.0.1.

This script fixes measurable canvas defects only:
- rescales portrait artwork to occupy the declared framing range;
- replaces the promotional master with a clean full-body front reference;
- preserves all original files in the source directory;
- emits a machine-readable report.

It intentionally does NOT synthesize or paint missing turnaround details. Weapon
continuity remains a manual art gate and must be reviewed before publication.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from PIL import Image

PORTRAITS = (
    "portrait_lian_wu__neutral_raw.png",
    "portrait_lian_wu__happy_raw.png",
    "portrait_lian_wu__battle_raw.png",
)


def alpha_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("image has no visible pixels")
    return bbox


def reframe_portrait(source: Path, target: Path, occupancy: float = 0.72) -> dict:
    image = Image.open(source).convert("RGBA")
    width, height = image.size
    bbox = alpha_bbox(image)
    crop = image.crop(bbox)

    target_extent = int(min(width, height) * occupancy)
    scale = min(target_extent / crop.width, target_extent / crop.height)
    resized = crop.resize(
        (max(1, round(crop.width * scale)), max(1, round(crop.height * scale))),
        Image.Resampling.LANCZOS,
    )

    canvas = Image.new("RGBA", image.size, (0, 0, 0, 0))
    x = (width - resized.width) // 2
    y = max(int(height * 0.08), (height - resized.height) // 2)
    if y + resized.height > height - int(height * 0.06):
        y = height - int(height * 0.06) - resized.height
    canvas.alpha_composite(resized, (x, y))
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target)

    new_bbox = alpha_bbox(canvas)
    return {
        "source": str(source),
        "target": str(target),
        "canvas": [width, height],
        "before_bbox": list(bbox),
        "after_bbox": list(new_bbox),
        "width_occupancy": (new_bbox[2] - new_bbox[0]) / width,
        "height_occupancy": (new_bbox[3] - new_bbox[1]) / height,
    }


def build_clean_master(front: Path, target: Path) -> dict:
    image = Image.open(front).convert("RGBA")
    bbox = alpha_bbox(image)
    crop = image.crop(bbox)
    canvas = Image.new("RGBA", image.size, (0, 0, 0, 0))
    max_w = int(image.width * 0.72)
    max_h = int(image.height * 0.86)
    scale = min(max_w / crop.width, max_h / crop.height)
    resized = crop.resize(
        (max(1, round(crop.width * scale)), max(1, round(crop.height * scale))),
        Image.Resampling.LANCZOS,
    )
    x = (image.width - resized.width) // 2
    y = image.height - int(image.height * 0.07) - resized.height
    canvas.alpha_composite(resized, (x, y))
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target)
    return {
        "source": str(front),
        "target": str(target),
        "strategy": "clean_front_reference",
        "bbox": list(alpha_bbox(canvas)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="extracted v1.0.0 pack root")
    parser.add_argument("output", type=Path, help="v1.0.1 staging directory")
    args = parser.parse_args()

    if args.output.exists():
        shutil.rmtree(args.output)
    shutil.copytree(args.source, args.output)

    report: dict[str, object] = {
        "schema": "taijifu/pack-repair-report/v1",
        "pack_id": "pack_01_lian_wu_base",
        "target_version": "1.0.1",
        "automatic_repairs": [],
        "manual_gates": [
            "turnaround weapon continuity",
            "left/right sheath and blade consistency",
            "final visual approval",
        ],
    }

    repairs = report["automatic_repairs"]
    assert isinstance(repairs, list)
    for name in PORTRAITS:
        repairs.append(
            reframe_portrait(
                args.source / "portraits" / name,
                args.output / "portraits" / name,
            )
        )

    repairs.append(
        build_clean_master(
            args.source / "turnaround" / "char_lian_wu__front_raw.png",
            args.output / "source" / "char_lian_wu__master_raw.png",
        )
    )

    report_path = args.output / "repair-report-v1.0.1.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
