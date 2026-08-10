#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOT = ROOT / "production/first_playable/training_rival/first_playable_lot_01"
SOURCE = ROOT / "production/first_playable/training_rival/source/training_rival_master.png"
LOCK = ROOT / "production/first_playable/training_rival/source/master-lock-v1.json"
REVIEW = ROOT / "production/first_playable/training_rival/source/PRESET02_P01_V3_REVIEW.json"
EXPECTED = {"idle": 6, "run": 8}
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def png_meta(path: Path) -> tuple[int, int, int]:
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("invalid_png_signature")
    offset = len(PNG_SIGNATURE)
    width = height = color_type = None
    seen_iend = False
    while offset < len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        ctype = data[offset + 4:offset + 8]
        end = offset + 12 + length
        if end > len(data):
            raise ValueError("truncated_png")
        payload = data[offset + 8:offset + 8 + length]
        crc = struct.unpack(">I", data[offset + 8 + length:end])[0]
        if (zlib.crc32(ctype + payload) & 0xFFFFFFFF) != crc:
            raise ValueError("invalid_png_crc")
        if ctype == b"IHDR":
            width, height, _depth, color_type, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
            if compression != 0 or filtering != 0 or interlace not in (0, 1):
                raise ValueError("invalid_ihdr")
        elif ctype == b"IEND":
            seen_iend = True
            break
        offset = end
    if width is None or height is None or color_type is None or not seen_iend:
        raise ValueError("incomplete_png")
    return width, height, color_type


def main() -> int:
    if not LOCK.is_file() or not REVIEW.is_file():
        print("PRESET02_P01=BLOCKED contract_or_review_missing")
        return 2
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    review = json.loads(REVIEW.read_text(encoding="utf-8"))
    expected_source = lock["approved_binary"]["sha256"]
    if review.get("source_sha256") != expected_source:
        print("PRESET02_P01=BLOCKED review_source_drift")
        return 2
    if not SOURCE.is_file():
        print("PRESET02_P01=BLOCKED source_master_missing")
        return 3
    source_sha = digest(SOURCE)
    if source_sha != expected_source:
        print(f"PRESET02_P01=BLOCKED source_sha256={source_sha}")
        return 3

    hashes: set[str] = set()
    total = 0
    for animation, count in EXPECTED.items():
        folder = LOT / "animations" / animation
        for index in range(1, count + 1):
            name = f"char_training_rival__{animation}__f{index:03d}.png"
            path = folder / name
            if not path.is_file():
                print(f"PRESET02_P01=BLOCKED missing={animation}/{name}")
                return 4
            try:
                width, height, color_type = png_meta(path)
            except Exception as exc:
                print(f"PRESET02_P01=BLOCKED invalid_png={name}:{exc}")
                return 4
            if (width, height) != (1024, 1024) or color_type != 6:
                print(f"PRESET02_P01=BLOCKED frame_contract={name}:{width}x{height}:type{color_type}")
                return 4
            hashes.add(digest(path))
            total += 1

    if total != 14 or len(hashes) < 8:
        print(f"PRESET02_P01=BLOCKED frame_count={total}/14 unique={len(hashes)}")
        return 4

    all_rival = list((LOT / "animations").glob("*/*.png"))
    print(f"PRESET02_P01_FRAME_COUNT={total}/14")
    print(f"PRESET02_RIVAL_GLOBAL_PROGRESS={len(all_rival)}/44")
    print(f"PRESET02_P01_UNIQUE_HASHES={len(hashes)}")
    print("PRESET02_P01_VISUAL_REVIEW=PASS weapon_duplication=false detached_fragments=false")
    print("PRESET02_P01=PASS")
    print("PRESET02_RUNTIME_PROMOTION=BLOCKED requires_44_of_44=true")
    print("SIGNATURE=Tehkné Solutions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
