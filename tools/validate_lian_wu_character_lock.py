#!/usr/bin/env python3
"""Validate VM01-A1 without ever approving missing or synthetic evidence."""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_ROOT = ROOT / "production/first_playable/lian_wu/character_lock_v1"
MANIFEST_PATH = LOCK_ROOT / "character-lock.manifest.json"
REVIEW_PATH = LOCK_ROOT / "visual-review.json"
REQUIRED_PNGS = {
    "lian_wu_neutral.png": None,
    "lian_wu_combat_stance.png": None,
    "lian_wu_silhouette_25pct.png": None,
    "godot-bench-1920x1080.png": (1920, 1080),
}
PASS_KEYS = {
    "neutral_pose",
    "combat_stance",
    "identity_continuity",
    "weapon_continuity",
    "silhouette_25pct",
    "transparent_background",
    "pivot_bottom_center",
    "godot_scale_bench",
    "fallback_replacement_ready",
}


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise ValueError(f"missing JSON: {path.relative_to(ROOT)}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path.relative_to(ROOT)}")
    return data


def read_png_ihdr(path: Path) -> tuple[int, int, int]:
    raw = path.read_bytes()
    if len(raw) < 33 or raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG: {path.relative_to(ROOT)}")
    if raw[12:16] != b"IHDR":
        raise ValueError(f"missing IHDR: {path.relative_to(ROOT)}")
    width, height, bit_depth, color_type = struct.unpack(">IIBB", raw[16:26])
    if bit_depth != 8:
        raise ValueError(f"PNG must use 8-bit channels: {path.relative_to(ROOT)}")
    if color_type != 6:
        raise ValueError(f"PNG must be truecolor RGBA: {path.relative_to(ROOT)}")
    if width < 1 or height < 1:
        raise ValueError(f"invalid dimensions: {path.relative_to(ROOT)}")
    return width, height, color_type


def main() -> int:
    errors: list[str] = []
    try:
        manifest = load_json(MANIFEST_PATH)
        review = load_json(REVIEW_PATH)
    except ValueError as exc:
        print(f"VM01_A1_CHARACTER_LOCK=FAIL {exc}")
        return 2

    if manifest.get("signature") != "Tehkné Solutions":
        errors.append("manifest signature mismatch")
    if review.get("signature") != "Tehkné Solutions":
        errors.append("review signature mismatch")

    dimensions: dict[str, tuple[int, int]] = {}
    for filename, exact_size in REQUIRED_PNGS.items():
        path = LOCK_ROOT / filename
        if not path.is_file():
            errors.append(f"missing {filename}")
            continue
        try:
            width, height, _ = read_png_ihdr(path)
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
            continue
        dimensions[filename] = (width, height)
        if exact_size and (width, height) != exact_size:
            errors.append(f"{filename} must be {exact_size[0]}x{exact_size[1]}")

    neutral = dimensions.get("lian_wu_neutral.png")
    stance = dimensions.get("lian_wu_combat_stance.png")
    silhouette = dimensions.get("lian_wu_silhouette_25pct.png")
    if neutral and stance and neutral != stance:
        errors.append("neutral and combat stance canvases must match")
    if neutral and silhouette:
        expected = (max(1, round(neutral[0] * 0.25)), max(1, round(neutral[1] * 0.25)))
        if silhouette != expected:
            errors.append(
                f"silhouette must be exactly 25% of neutral canvas: expected {expected}, got {silhouette}"
            )

    acceptance = manifest.get("acceptance", {})
    if not isinstance(acceptance, dict):
        errors.append("manifest acceptance must be an object")
        acceptance = {}
    criteria = review.get("criteria", {})
    if not isinstance(criteria, dict):
        errors.append("review criteria must be an object")
        criteria = {}

    missing_pass_keys = sorted(PASS_KEYS - set(acceptance))
    if missing_pass_keys:
        errors.append(f"manifest missing acceptance keys: {', '.join(missing_pass_keys)}")

    all_manifest_pass = all(acceptance.get(key) == "pass" for key in PASS_KEYS)
    review_decision = review.get("decision", {})
    review_approved = isinstance(review_decision, dict) and review_decision.get("approved") is True
    promotion = manifest.get("promotion", {})
    promotion_approved = isinstance(promotion, dict) and promotion.get("approved") is True

    if errors:
        if all_manifest_pass or review_approved or promotion_approved:
            errors.append("approval is forbidden while required evidence is invalid or missing")
        print("VM01_A1_CHARACTER_LOCK=BLOCKED")
        for error in errors:
            print(f"- {error}")
        return 1

    if not all_manifest_pass:
        errors.append("all manifest acceptance criteria must be 'pass'")
    if not review_approved:
        errors.append("visual review decision must be approved")
    if not promotion_approved:
        errors.append("manifest promotion.approved must be true")
    for name, item in criteria.items():
        if not isinstance(item, dict) or item.get("status") != "pass":
            errors.append(f"review criterion not passed: {name}")

    if errors:
        print("VM01_A1_CHARACTER_LOCK=BLOCKED")
        for error in errors:
            print(f"- {error}")
        return 1

    print("VM01_A1_CHARACTER_LOCK=PASS")
    for key in sorted(PASS_KEYS):
        print(f"{key}=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
