#!/usr/bin/env python3
"""Strict canonical First Playable art validator: released Lian Wu 45 + Training Rival 44.

This validator intentionally does not inherit the historical 44/44 contract.
Signature: Tehkné Solutions
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_ROOT = ROOT / "production" / "first_playable"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
SIGNATURE = "Tehkné Solutions"

EXPECTED = {
    "lian_wu": {
        "prefix": "char_lian_wu",
        "digits": 2,
        "frames": 45,
        "animations": {
            "idle": 6,
            "run": 8,
            "jump_start": 4,
            "airborne": 3,
            "fall": 3,
            "attack_light": 6,
            "guard": 1,
            "dodge": 5,
            "hit": 4,
            "ko": 5,
        },
    },
    "training_rival": {
        "prefix": "char_training_rival",
        "digits": 3,
        "frames": 44,
        "animations": {
            "idle": 6,
            "run": 8,
            "jump_start": 3,
            "airborne": 2,
            "fall": 2,
            "attack_light": 6,
            "guard": 3,
            "dodge": 5,
            "hit": 3,
            "ko": 6,
        },
    },
}


def read_png(path: Path) -> tuple[int, int, int]:
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("invalid_png_signature")
    offset = len(PNG_SIGNATURE)
    width = height = color_type = None
    seen_ihdr = seen_idat = seen_iend = False
    while offset < len(data):
        if offset + 12 > len(data):
            raise ValueError("truncated_png_chunk")
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        chunk_type = data[offset + 4:offset + 8]
        chunk_end = offset + 12 + length
        if chunk_end > len(data):
            raise ValueError("truncated_png_payload")
        payload = data[offset + 8:offset + 8 + length]
        expected_crc = struct.unpack(">I", data[offset + 8 + length:chunk_end])[0]
        actual_crc = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise ValueError("invalid_png_crc")
        if chunk_type == b"IHDR":
            if seen_ihdr or length != 13:
                raise ValueError("invalid_ihdr")
            width, height, _depth, color_type, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
            if compression != 0 or filtering != 0 or interlace not in (0, 1):
                raise ValueError("invalid_ihdr_parameters")
            seen_ihdr = True
        elif chunk_type == b"IDAT":
            seen_idat = True
        elif chunk_type == b"IEND":
            if length != 0 or chunk_end != len(data):
                raise ValueError("invalid_iend")
            seen_iend = True
            break
        offset = chunk_end
    if not (seen_ihdr and seen_idat and seen_iend):
        raise ValueError("incomplete_png")
    assert width is not None and height is not None and color_type is not None
    return width, height, color_type


def validate_character(character: str, spec: dict) -> dict:
    lot_root = PRODUCTION_ROOT / character / "first_playable_lot_01"
    manifest_path = lot_root / "work-manifest.json"
    errors: list[str] = []
    present = 0
    animation_complete = 0

    if not manifest_path.exists():
        return {"character": character, "frames": 0, "expected_frames": spec["frames"], "animations": 0, "expected_animations": len(spec["animations"]), "errors": ["manifest_missing"], "complete": False}

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"character": character, "frames": 0, "expected_frames": spec["frames"], "animations": 0, "expected_animations": len(spec["animations"]), "errors": [f"manifest_invalid:{exc}"], "complete": False}

    if manifest.get("signature") != SIGNATURE:
        errors.append("signature_invalid")
    if manifest.get("required_frames") != spec["frames"]:
        errors.append(f"required_frames_invalid:{manifest.get('required_frames')}")
    if manifest.get("animations") != spec["animations"]:
        errors.append("animation_contract_invalid")

    canvas = manifest.get("canvas") or {"min": 128, "max": 1024}
    minimum = int(canvas.get("min", 128))
    maximum = int(canvas.get("max", 1024))
    dimensions: set[tuple[int, int]] = set()
    animation_root = lot_root / "animations"
    digits = int(spec["digits"])

    for animation, expected_count in spec["animations"].items():
        folder = animation_root / animation
        expected_names = {
            f"{spec['prefix']}__{animation}__f{index:0{digits}d}.png"
            for index in range(1, expected_count + 1)
        }
        actual_files = sorted(folder.glob("*.png")) if folder.exists() else []
        actual_names = {path.name for path in actual_files}
        present += len(actual_files)
        missing = expected_names - actual_names
        unexpected = actual_names - expected_names
        if missing:
            errors.append(f"{animation}:missing:{','.join(sorted(missing))}")
        if unexpected:
            errors.append(f"{animation}:unexpected:{','.join(sorted(unexpected))}")
        if not missing and not unexpected and len(actual_files) == expected_count:
            animation_complete += 1

        pattern = re.compile(rf"^{re.escape(spec['prefix'])}__{re.escape(animation)}__f\d{{{digits}}}\.png$")
        for frame in actual_files:
            if not pattern.match(frame.name):
                errors.append(f"filename_invalid:{frame.name}")
                continue
            try:
                width, height, color_type = read_png(frame)
            except Exception as exc:
                errors.append(f"png_invalid:{frame.name}:{exc}")
                continue
            if not (minimum <= width <= maximum and minimum <= height <= maximum):
                errors.append(f"dimensions_out_of_bounds:{frame.name}:{width}x{height}")
            else:
                dimensions.add((width, height))
            if color_type not in (4, 6):
                errors.append(f"alpha_required:{frame.name}:color_type={color_type}")

    if len(dimensions) > 1:
        errors.append(f"dimensions_inconsistent:{sorted(dimensions)}")

    complete = present == spec["frames"] and animation_complete == len(spec["animations"]) and not errors
    return {
        "character": character,
        "frames": present,
        "expected_frames": spec["frames"],
        "animations": animation_complete,
        "expected_animations": len(spec["animations"]),
        "errors": errors,
        "complete": complete,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="artifacts/first-playable-art-preflight-v3.json")
    args = parser.parse_args()

    characters = [validate_character(character, spec) for character, spec in EXPECTED.items()]
    present_total = sum(item["frames"] for item in characters)
    expected_total = sum(spec["frames"] for spec in EXPECTED.values())
    ready = all(item["complete"] for item in characters) and present_total == expected_total

    report = {
        "gate_id": "taijifu-first-playable-art-preflight-v3",
        "signature": SIGNATURE,
        "expected_total": expected_total,
        "present_total": present_total,
        "ready": ready,
        "characters": characters,
    }
    report_path = ROOT / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"FIRST_PLAYABLE_ART_PRODUCTION_READY={'true' if ready else 'false'}")
    print(f"FIRST_PLAYABLE_ART_PROGRESS={present_total}/{expected_total}")
    for item in characters:
        print(
            f"FIRST_PLAYABLE_CHARACTER={item['character']} "
            f"frames={item['frames']}/{item['expected_frames']} "
            f"animations={item['animations']}/{item['expected_animations']} "
            f"complete={'true' if item['complete'] else 'false'}"
        )
        for error in item["errors"]:
            print(f"FIRST_PLAYABLE_ERROR={item['character']}:{error}")
    print(f"SIGNATURE={SIGNATURE}")
    print(f"REPORT={report_path.relative_to(ROOT)}")
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
