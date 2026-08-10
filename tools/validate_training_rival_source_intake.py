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
EXPECTED_PACKS = {
    "P01": 14,
    "P02": 7,
    "P03": 6,
    "P04": 8,
    "P05": 9,
}


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


def validate_identity_core(canonical: dict, intake: dict) -> list[str]:
    canonical_lock = canonical.get("identity_lock", {})
    intake_lock = intake.get("identity_lock", {})
    failures: list[str] = []
    if not isinstance(canonical_lock, dict) or not isinstance(intake_lock, dict):
        return ["identity_lock_not_dictionary"]
    for key, expected in canonical_lock.items():
        if key not in intake_lock:
            failures.append(f"identity_missing:{key}")
        elif intake_lock[key] != expected:
            failures.append(f"identity_drift:{key}")
    for key in intake_lock:
        if key not in canonical_lock:
            failures.append(f"identity_extra_noncanonical:{key}")
    return failures


def validate_plan(canonical: dict, intake: dict) -> list[str]:
    failures: list[str] = []
    if canonical.get("required_total_frames") != 44 or intake.get("required_total_frames") != 44:
        failures.append("required_total_frames")
    canonical_matrix = canonical.get("animation_matrix", {})
    plan = intake.get("production_plan", {})
    if not isinstance(plan, dict) or set(plan) != set(EXPECTED_PACKS):
        failures.append("pack_set")
        return failures
    total = 0
    flattened: dict[str, int] = {}
    for pack_id, expected_frames in EXPECTED_PACKS.items():
        pack = plan.get(pack_id, {})
        frames = int(pack.get("frames", -1)) if isinstance(pack, dict) else -1
        animations = pack.get("animations", {}) if isinstance(pack, dict) else {}
        if frames != expected_frames:
            failures.append(f"pack_frames:{pack_id}")
        if not isinstance(animations, dict) or sum(int(v) for v in animations.values()) != expected_frames:
            failures.append(f"pack_animation_sum:{pack_id}")
        total += max(frames, 0)
        if isinstance(animations, dict):
            for name, count in animations.items():
                if name in flattened:
                    failures.append(f"animation_duplicate:{name}")
                flattened[name] = int(count)
    if total != 44:
        failures.append("plan_total")
    if flattened != canonical_matrix:
        failures.append("animation_matrix_drift")
    promotion = intake.get("runtime_promotion", {})
    canonical_promotion = canonical.get("promotion", {})
    for key in ("current_proxy_may_be_removed", "requires_44_of_44", "requires_visual_review", "requires_godot_runtime_bench", "requires_game_c28_import_gate"):
        if promotion.get(key) != canonical_promotion.get(key):
            failures.append(f"promotion_drift:{key}")
    if promotion.get("partial_pack_promotion_allowed") is not False:
        failures.append("partial_pack_promotion_allowed")
    return failures


def main() -> int:
    if not INTAKE.is_file() or not CANONICAL.is_file():
        print("PRESET02_SOURCE_INTAKE=BLOCKED contract_missing")
        return 2
    intake = json.loads(INTAKE.read_text(encoding="utf-8"))
    canonical = json.loads(CANONICAL.read_text(encoding="utf-8"))
    if intake.get("signature") != "Tehkné Solutions" or intake.get("character_id") != "training_rival":
        print("PRESET02_SOURCE_INTAKE=BLOCKED intake_schema")
        return 2

    identity_failures = validate_identity_core(canonical, intake)
    plan_failures = validate_plan(canonical, intake)
    failures = identity_failures + plan_failures
    if failures:
        for failure in failures:
            print(f"PRESET02_CONTRACT_DRIFT={failure}")
        print("PRESET02_SOURCE_INTAKE=BLOCKED canonical_contract_drift")
        return 2

    print("PRESET02_FOUNDATION=PASS identity_lock=true packs=5 total_frames=44")
    print("PRESET02_CANONICAL_CORE=PASS source=C29 identity_fields=%d" % len(canonical.get("identity_lock", {})))
    print("PRESET02_RUNTIME_POLICY=PASS partial_promotion=false requires_44_of_44=true proxy_retire=false")

    master = ROOT / intake["master"]["path"]
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
    visible_indices = [index for index, value in enumerate(alpha) if value > 3]
    if not visible_indices:
        print("PRESET02_SOURCE_INTAKE=BLOCKED empty_alpha")
        return 3
    xs = [index % width for index in visible_indices]
    ys = [index // width for index in visible_indices]
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
