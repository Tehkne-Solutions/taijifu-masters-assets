#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path

from PIL import Image

RAW_SHA256 = "de532ea47c0b16921bfb84d3826fe1a2a51cf9f10aa8f6d8b98a90d9a457be6d"
RAW_BYTES = 1_273_838
RAW_SIZE = (1254, 1254)
CANONICAL_FILE_SHA256 = "ce76243a4b89147a4900e823041b5392e2b19b13549aaa9fcd95cbf3e34d3fe3"
CANONICAL_FILE_BYTES = 747_624
CANONICAL_PIXEL_SHA256 = "67abba855b18ea6cc5ef62c4e382041d5ca69eb9902d9b3c6ead9329a163531e"
CANVAS = (1024, 1024)
FIT_BOX = (940, 980)
ALPHA_THRESHOLD = 3


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def alpha_bounds(image: Image.Image):
    alpha = image.getchannel("A")
    visible = alpha.point(lambda value: 255 if value >= ALPHA_THRESHOLD else 0)
    return visible.getbbox()


def validate_canonical(path: Path) -> None:
    image = Image.open(path).convert("RGBA")
    if image.size != CANVAS:
        raise RuntimeError(f"canonical_canvas={image.size} expected={CANVAS}")
    pixel_sha = sha256_bytes(image.tobytes())
    if pixel_sha != CANONICAL_PIXEL_SHA256:
        raise RuntimeError(f"canonical_pixel_sha256={pixel_sha} expected={CANONICAL_PIXEL_SHA256}")
    alpha = image.getchannel("A")
    corners = [alpha.getpixel((0, 0)), alpha.getpixel((1023, 0)), alpha.getpixel((0, 1023)), alpha.getpixel((1023, 1023))]
    if any(corners):
        raise RuntimeError(f"canonical_transparent_corners={corners}")
    bounds = alpha_bounds(image)
    if not bounds:
        raise RuntimeError("canonical_empty_alpha")
    x0, y0, x1, y1 = bounds
    if x0 <= 1 or y0 <= 1 or x1 >= 1023 or y1 >= 1023:
        raise RuntimeError(f"canonical_foreground_touches_edge={bounds}")
    print(f"PRESET02_CANONICAL_PIXEL_SHA256={pixel_sha}")
    print(f"PRESET02_CANONICAL_FILE_SHA256={file_sha(path)}")
    print(f"PRESET02_CANONICAL_BYTES={path.stat().st_size}")
    print(f"PRESET02_CANONICAL_BOUNDS={bounds}")
    print("PRESET02_CANONICAL_MASTER=PASS")


def canonicalize(source: Path, output: Path) -> None:
    source_bytes = source.read_bytes()
    source_sha = sha256_bytes(source_bytes)
    source_len = len(source_bytes)
    output.parent.mkdir(parents=True, exist_ok=True)

    print(f"PRESET02_INPUT_BYTES={source_len}")
    print(f"PRESET02_INPUT_SHA256={source_sha}")

    if source_sha == CANONICAL_FILE_SHA256 and source_len == CANONICAL_FILE_BYTES:
        if source.resolve() != output.resolve():
            shutil.copyfile(source, output)
        print("PRESET02_INPUT_KIND=canonical_exact")
        validate_canonical(output)
        return

    if source_sha != RAW_SHA256 or source_len != RAW_BYTES:
        raise RuntimeError(
            "input_not_approved_original_or_canonical "
            f"raw_expected={RAW_SHA256}/{RAW_BYTES} canonical_expected={CANONICAL_FILE_SHA256}/{CANONICAL_FILE_BYTES}"
        )

    image = Image.open(source)
    if image.size != RAW_SIZE:
        raise RuntimeError(f"raw_canvas={image.size} expected={RAW_SIZE}")
    image = image.convert("RGBA")
    alpha = image.getchannel("A")
    if any(alpha.getpixel(xy) for xy in ((0, 0), (RAW_SIZE[0] - 1, 0), (0, RAW_SIZE[1] - 1), (RAW_SIZE[0] - 1, RAW_SIZE[1] - 1))):
        raise RuntimeError("raw_transparent_corners_required")

    scale = min(FIT_BOX[0] / image.width, FIT_BOX[1] / image.height)
    new_size = (round(image.width * scale), round(image.height * scale))
    resized = image.resize(new_size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    x = (CANVAS[0] - new_size[0]) // 2
    y = (CANVAS[1] - new_size[1]) // 2
    canvas.alpha_composite(resized, (x, y))
    canvas.save(output, "PNG", optimize=True, compress_level=9)
    print(f"PRESET02_INPUT_KIND=approved_original_raw")
    print(f"PRESET02_CANONICALIZATION=PASS resize={new_size} offset=({x},{y})")
    validate_canonical(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    source = Path(args.source).resolve()
    output = Path(args.output).resolve()
    if not source.is_file():
        print(f"PRESET02_CANONICAL_MASTER=BLOCKED source_missing={source}")
        return 2
    try:
        canonicalize(source, output)
    except Exception as exc:
        print(f"PRESET02_CANONICAL_MASTER=BLOCKED {exc}")
        return 3
    print("SIGNATURE=Tehkné Solutions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
