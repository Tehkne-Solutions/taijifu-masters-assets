#!/usr/bin/env python3
"""Build the deterministic Lian Wu canonical clean v1.0.1 turnaround.

Input: recovered PACK_01_LIAN_WU_BASE_FINAL_v1.0.0 directory.
Output: four cleaned RGBA 1024x1024 turnaround PNGs.
No generative model is used.
"""
from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageOps
import argparse


def clear_rgba_box(img: Image.Image, box: tuple[int, int, int, int]) -> None:
    px = img.load()
    x0, y0, x1, y1 = box
    for y in range(y0, y1):
        for x in range(x0, x1):
            px[x, y] = (0, 0, 0, 0)


def remove_low_chroma(img: Image.Image, box: tuple[int, int, int, int], max_chroma: int = 28, min_brightness: int = 55) -> None:
    px = img.load()
    x0, y0, x1, y1 = box
    for y in range(y0, y1):
        for x in range(x0, x1):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            chroma = max(r, g, b) - min(r, g, b)
            brightness = (r + g + b) / 3
            if chroma < max_chroma and brightness > min_brightness:
                px[x, y] = (0, 0, 0, 0)


def build(source_root: Path, output_root: Path) -> None:
    src = source_root / "turnaround"
    output_root.mkdir(parents=True, exist_ok=True)

    front = Image.open(src / "char_lian_wu__front_raw.png").convert("RGBA")
    side_left = Image.open(src / "char_lian_wu__side_left_raw.png").convert("RGBA")
    back = Image.open(src / "char_lian_wu__back_raw.png").convert("RGBA")

    # Front and side-left corrections remove only detached metallic artifacts.
    # These masks are deliberately local; all pixels outside them remain canonical.
    remove_low_chroma(front, (300, 610, 390, 760))
    remove_low_chroma(side_left, (300, 580, 390, 755))

    # Side-right source contains two exposed blades and cannot be safely repaired in-place.
    # Reconstruct it deterministically from the canonical opposite side, then remove the
    # remaining detached metallic fragment. This preserves identity and proportions.
    side_right = ImageOps.mirror(side_left)
    clear_rgba_box(side_right, (654, 620, 720, 755))
    remove_low_chroma(side_right, (630, 620, 654, 755))

    outputs = {
        "char_lian_wu__front_clean.png": front,
        "char_lian_wu__side_left_clean.png": side_left,
        "char_lian_wu__back_clean.png": back,
        "char_lian_wu__side_right_clean.png": side_right,
    }
    for name, image in outputs.items():
        if image.size != (1024, 1024) or image.mode != "RGBA":
            raise RuntimeError(f"invalid output contract for {name}: {image.mode} {image.size}")
        image.save(output_root / name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    parser.add_argument("output_root", type=Path)
    args = parser.parse_args()
    build(args.source_root, args.output_root)
