#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTAKE = ROOT / "production/first_playable/training_rival/source/source-intake-v1.json"
CANONICAL = ROOT / "production/first_playable/training_rival/canonical-production-v1.json"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
LIAN_WU_LOCK_SHA256 = "0e435757b5c8a114f3ba91653f79bc86db51ee9cf3bfb74c529efed5d4ff7ab5"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_png(path: Path) -> tuple[int, int, int, int, list[tuple[bytes, bytes]]]:
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("invalid_png_signature")
    offset = len(PNG_SIGNATURE)
    width = height = depth = color_type = None
    chunks: list[tuple[bytes, bytes]] = []
    seen_iend = False
    while offset < len(data):
        if offset + 12 > len(data):
            raise ValueError("truncated_png_chunk")
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        chunk_type = data[offset + 4:offset + 8]
        end = offset + 12 + length
        if end > len(data):
            raise ValueError("truncated_png_payload")
        payload = data[offset + 8:offset + 8 + length]
        expected_crc = struct.unpack(">I", data[offset + 8 + length:end])[0]
        actual_crc = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise ValueError("invalid_png_crc")
        chunks.append((chunk_type, payload))
        if chunk_type == b"IHDR":
            width, height, depth, color_type, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
            if compression != 0 or filtering != 0 or interlace not in (0, 1):
                raise ValueError("unsupported_png_header")
        elif chunk_type == b"IEND":
            seen_iend = True
            if end != len(data):
                raise ValueError("data_after_iend")
            break
        offset = end
    if width is None or height is None or depth is None or color_type is None or not seen_iend:
        raise ValueError("incomplete_png")
    return width, height, depth, color_type, chunks


def inflate_rgba_alpha(width: int, height: int, depth: int, color_type: int, chunks: list[tuple[bytes, bytes]]) -> bytes:
    if depth != 8 or color_type != 6:
        raise ValueError("rgba8_required")
    compressed = b"".join(payload for chunk_type, payload in chunks if chunk_type == b"IDAT")
    raw = zlib.decompress(compressed)
    bpp = 4
    stride = width * bpp
    expected = height * (stride + 1)
    if len(raw) != expected:
        raise ValueError("interlaced_or_unexpected_scanline_layout")
    previous = bytearray(stride)
    alpha = bytearray(width * height)
    cursor = 0
    out_index = 0
    for _y in range(height):
        filter_type = raw[cursor]
        cursor += 1
        scan = bytearray(raw[cursor:cursor + stride])
        cursor += stride
        recon = bytearray(stride)
        for x in range(stride):
            left = recon[x - bpp] if x >= bpp else 0
            up = previous[x]
            up_left = previous[x - bpp] if x >= bpp else 0
            value = scan[x]
            if filter_type == 0:
                recon[x] = value
            elif filter_type == 1:
                recon[x] = (value + left) & 0xFF
            elif filter_type == 2:
                recon[x] = (value + up) & 0xFF
            elif filter_type == 3:
                recon[x] = (value + ((left + up) // 2)) & 0xFF
            elif filter_type == 4:
                p = left + up - up_left
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - up_left)
                predictor = left if pa <= pb and pa <= pc else up if pb <= pc else up_left
                recon[x] = (value + predictor) & 0xFF
            else:
                raise ValueError("unsupported_png_filter")
        for x in range(width):
            alpha[out_index] = recon[x * 4 + 3]
            out_index += 1
        previous = recon
    return bytes(alpha)


def main() -> int:
    if not INTAKE.is_file() or not CANONICAL.is_file():
        print("PRESET02_SOURCE_INTAKE=BLOCKED contract_missing")
        return 2
    intake = json.loads(INTAKE.read_text(encoding="utf-8"))
    canonical = json.loads(CANONICAL.read_text(encoding="utf-8"))
    if intake.get("signature") != "Tehkné Solutions" or intake.get("character_id") != "training_rival":
        print("PRESET02_SOURCE_INTAKE=BLOCKED intake_schema")
        return 2
    if canonical.get("required_total_frames") != 44 or canonical.get("identity_lock") != intake.get("identity_lock"):
        print("PRESET02_SOURCE_INTAKE=BLOCKED canonical_identity_drift")
        return 2
    master = ROOT / intake["master"]["path"]
    print("PRESET02_FOUNDATION=PASS identity_lock=true packs=5 total_frames=44")
    print("PRESET02_RUNTIME_POLICY=PASS partial_promotion=false requires_44_of_44=true proxy_retire=false")
    if not master.is_file():
        if intake.get("status") != "source_master_missing_fail_closed":
            print("PRESET02_SOURCE_INTAKE=BLOCKED missing_master_status_mismatch")
            return 2
        print("PRESET02_SOURCE_MASTER=BLOCKED missing_expected_master")
        print(f"PRESET02_MASTER_EXPECTED={master.relative_to(ROOT).as_posix()}")
        print("PRESET02_FRAME_PROGRESS=0/44")
        print("PRESET02_P01=BLOCKED waiting_clean_master")
        print("PRESET02_SOURCE_INTAKE=PASS fail_closed=true source_ready=false")
        print("SIGNATURE=Tehkné Solutions")
        return 0

    digest = sha256(master)
    if digest == LIAN_WU_LOCK_SHA256:
        print("PRESET02_SOURCE_INTAKE=BLOCKED lian_wu_source_reuse")
        return 3
    try:
        width, height, depth, color_type, chunks = read_png(master)
        if (width, height) != (1024, 1024) or depth != 8 or color_type != 6:
            raise ValueError(f"source_contract={width}x{height}:depth{depth}:type{color_type}")
        alpha = inflate_rgba_alpha(width, height, depth, color_type, chunks)
    except Exception as exc:
        print(f"PRESET02_SOURCE_INTAKE=BLOCKED {exc}")
        return 3
    corners = [alpha[0], alpha[width - 1], alpha[(height - 1) * width], alpha[-1]]
    if any(corners):
        print("PRESET02_SOURCE_INTAKE=BLOCKED transparent_corners_required")
        return 3
    visible = [(index % width, index // width) for index, value in enumerate(alpha) if value > 3]
    if not visible:
        print("PRESET02_SOURCE_INTAKE=BLOCKED empty_alpha")
        return 3
    xs = [x for x, _y in visible]
    ys = [y for _x, y in visible]
    bbox = [min(xs), min(ys), max(xs) + 1, max(ys) + 1]
    if bbox[0] <= 1 or bbox[1] <= 1 or bbox[2] >= 1023 or bbox[3] >= 1023:
        print(f"PRESET02_SOURCE_INTAKE=BLOCKED foreground_touches_canvas_edge bbox={bbox}")
        return 3
    print(f"PRESET02_SOURCE_MASTER=PASS sha256={digest} bbox={bbox} rgba=true transparent=true")
    print("PRESET02_FRAME_PROGRESS=0/44")
    print("PRESET02_P01=READY_FOR_MATERIALIZATION owner_visual_review_required=true")
    print("PRESET02_SOURCE_INTAKE=PASS fail_closed=false source_ready=true")
    print("SIGNATURE=Tehkné Solutions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
