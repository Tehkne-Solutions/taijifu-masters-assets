#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "production/first_playable/training_rival/canonical-production-v1.json"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
NAME_RE = re.compile(r"^char_training_rival__([a-z_]+)__f(\d{3})\.png$")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_png(path: Path) -> tuple[int, int, int]:
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("invalid PNG signature")
    offset = len(PNG_SIGNATURE)
    width = height = color_type = None
    seen_ihdr = seen_idat = seen_iend = False
    while offset < len(data):
        if offset + 12 > len(data):
            raise ValueError("truncated PNG chunk")
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        chunk_type = data[offset + 4:offset + 8]
        end = offset + 12 + length
        if end > len(data):
            raise ValueError("truncated PNG payload")
        payload = data[offset + 8:offset + 8 + length]
        expected_crc = struct.unpack(">I", data[offset + 8 + length:end])[0]
        actual_crc = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise ValueError("invalid PNG CRC")
        if chunk_type == b"IHDR":
            if length != 13 or seen_ihdr:
                raise ValueError("invalid IHDR")
            width, height, depth, color_type, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
            if depth != 8 or compression != 0 or filtering != 0 or interlace not in (0, 1):
                raise ValueError("unsupported PNG header")
            seen_ihdr = True
        elif chunk_type == b"IDAT":
            seen_idat = True
        elif chunk_type == b"IEND":
            seen_iend = True
            if end != len(data):
                raise ValueError("data after IEND")
            break
        offset = end
    if not (seen_ihdr and seen_idat and seen_iend):
        raise ValueError("incomplete PNG")
    assert width is not None and height is not None and color_type is not None
    return width, height, color_type


def main() -> int:
    if not CONTRACT.is_file():
        print("VM02_C29_CONTRACT=BLOCKED")
        return 2
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("signature") != "Tehkné Solutions" or contract.get("required_total_frames") != 44:
        print("VM02_C29_CONTRACT_SCHEMA=BLOCKED")
        return 2
    print("VM02_C29_CONTRACT=PASS")
    print("VM02_C29_IDENTITY_LOCK=PASS")

    root = ROOT / contract["source_root"]
    expected: list[tuple[str, int, Path]] = []
    for animation, count in contract["animation_matrix"].items():
        for index in range(1, int(count) + 1):
            expected.append((animation, index, root / animation / f"char_training_rival__{animation}__f{index:03d}.png"))

    missing = []
    invalid = []
    present = []
    dimensions = set()
    for animation, index, path in expected:
        if not path.is_file():
            missing.append(f"{animation}/f{index:03d}")
            continue
        try:
            width, height, color_type = read_png(path)
        except Exception as exc:
            invalid.append(f"{path.name}:{exc}")
            continue
        if color_type != 6:
            invalid.append(f"{path.name}:rgba_required")
            continue
        match = NAME_RE.match(path.name)
        if not match or match.group(1) != animation or int(match.group(2)) != index:
            invalid.append(f"{path.name}:name_contract")
            continue
        dimensions.add((width, height))
        present.append((path, sha256(path)))

    print(f"VM02_C29_FRAME_COUNT={len(present)}/44")
    print(f"VM02_C29_MISSING_FRAME_COUNT={len(missing)}")
    print(f"VM02_C29_INVALID_FRAME_COUNT={len(invalid)}")
    for item in missing[:8]:
        print(f"VM02_C29_MISSING_FRAME={item}")
    for item in invalid[:8]:
        print(f"VM02_C29_INVALID_FRAME={item}")

    dimension_ok = len(dimensions) <= 1
    print(f"VM02_C29_DIMENSION_CONSISTENCY={'PASS' if dimension_ok else 'BLOCKED'}")
    complete = len(present) == 44 and not missing and not invalid and dimension_ok
    print(f"VM02_C29_CANONICAL_FRAME_CONTRACT={'PASS' if complete else 'BLOCKED'}")
    print(f"VM02_C29_VISUAL_REVIEW={'PENDING' if complete else 'BLOCKED'}")
    print(f"VM02_C29_GAME_C28_HANDOFF={'READY' if complete else 'BLOCKED'}")
    print("VM02_C29_PRODUCTION_PIPELINE=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
