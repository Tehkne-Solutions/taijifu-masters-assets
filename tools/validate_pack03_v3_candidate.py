#!/usr/bin/env python3
"""Validate PACK 03 Mountain Dojo Night art-pass v3 candidates without promoting them."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

SIGNATURE = "Tehkné Solutions"
ROOT = Path("production/first_playable/stages/mountain_dojo_night/art_pass_v3")
CONTRACT_PATH = ROOT / "candidate-contract.json"
STATUS_PATH = ROOT / "review-status.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fraction_nontransparent(alpha: Image.Image, box: tuple[int, int, int, int] | None = None) -> float:
    region = alpha.crop(box) if box else alpha
    hist = region.histogram()
    total = region.width * region.height
    transparent_or_near = sum(hist[:9])
    return 0.0 if total <= 0 else 1.0 - (transparent_or_near / total)


def fail(reason: str) -> int:
    print(f"PACK03_V3_CANDIDATE=BLOCKED reason={reason}")
    print(f"SIGNATURE={SIGNATURE}")
    return 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Return WAITING rather than failure while the authored PNGs have not been delivered.",
    )
    args = parser.parse_args()

    if not CONTRACT_PATH.is_file() or not STATUS_PATH.is_file():
        return fail("metadata_missing")

    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8-sig"))
    status = json.loads(STATUS_PATH.read_text(encoding="utf-8-sig"))

    if contract.get("signature") != SIGNATURE or status.get("signature") != SIGNATURE:
        return fail("signature")
    if contract.get("arena_id") != "mountain_dojo_night" or status.get("arena_id") != "mountain_dojo_night":
        return fail("arena_identity")
    if contract.get("status") != "art_pending" or status.get("status") != "art_pending":
        return fail("candidate_status_must_remain_art_pending")
    if status.get("promotion") is not False or status.get("canonical_replacement_authorized") is not False:
        return fail("premature_promotion")

    layers = contract.get("layers", {})
    required_names = ["background.png", "midground.png", "foreground.png"]
    missing = [name for name in required_names if not (ROOT / name).is_file()]
    if missing:
        if args.allow_missing:
            print("PACK03_V3_METADATA=PASS")
            print(f"PACK03_V3_CANDIDATE=WAITING missing={','.join(missing)}")
            print("PACK03_V3_PROMOTION=BLOCKED art_pending=true")
            print(f"SIGNATURE={SIGNATURE}")
            return 0
        return fail("missing_layers:" + ",".join(missing))

    hashes: dict[str, str] = {}
    for name in required_names:
        path = ROOT / name
        spec = layers.get(name, {})
        try:
            with Image.open(path) as image:
                if image.format != "PNG":
                    return fail(f"format:{name}:{image.format}")
                expected_size = tuple(spec.get("size", [1920, 1080]))
                if image.size != expected_size:
                    return fail(f"size:{name}:{image.size[0]}x{image.size[1]}")
                if image.mode not in set(spec.get("allowed_modes", [])):
                    return fail(f"mode:{name}:{image.mode}")

                if name == "foreground.png":
                    if image.mode != "RGBA":
                        return fail("foreground_requires_rgba")
                    alpha = image.getchannel("A")
                    overall_nontransparent = fraction_nontransparent(alpha)
                    overall_transparent = 1.0 - overall_nontransparent
                    min_transparent = float(spec.get("min_overall_transparent_fraction", 0.50))
                    min_nontransparent = float(spec.get("min_nontransparent_fraction", 0.005))
                    if overall_transparent < min_transparent:
                        return fail(f"foreground_transparency:{overall_transparent:.4f}")
                    if overall_nontransparent < min_nontransparent:
                        return fail(f"foreground_empty:{overall_nontransparent:.4f}")

                    safe_x = contract["runtime_contract"]["safe_fighter_zone_x"]
                    safe_y = spec.get("safe_zone_y", [80, 820])
                    box = (int(safe_x[0]), int(safe_y[0]), int(safe_x[1]), int(safe_y[1]))
                    safe_coverage = fraction_nontransparent(alpha, box)
                    max_safe = float(spec.get("max_safe_zone_nontransparent_fraction", 0.03))
                    if safe_coverage > max_safe:
                        return fail(f"foreground_safe_zone_coverage:{safe_coverage:.4f}")
                    print(
                        "PACK03_V3_FOREGROUND=PASS "
                        f"transparent={overall_transparent:.4f} safe_coverage={safe_coverage:.4f}"
                    )
        except OSError as exc:
            return fail(f"image_open:{name}:{exc.__class__.__name__}")

        hashes[name] = sha256(path)
        frozen = status.get("layers", {}).get(name, {}).get("sha256")
        if frozen not in (None, hashes[name]):
            return fail(f"status_hash_mismatch:{name}")

    required_runtime_passes = [
        "manual_visual_review",
        "godot_runtime_capture",
        "c30_materialization",
        "stage_premium_runtime_review",
        "vertical_slice_asset_truth",
    ]
    promotion_ready = all(status.get(key) == "pass" for key in required_runtime_passes)
    if status.get("promotion") is True and not promotion_ready:
        return fail("promotion_without_runtime_evidence")

    print("PACK03_V3_METADATA=PASS")
    print("PACK03_V3_LAYER_FILES=PASS count=3")
    for name in required_names:
        print(f"PACK03_V3_SHA256 file={name} sha256={hashes[name]}")
    print(f"PACK03_V3_PROMOTION_READY={'true' if promotion_ready else 'false'}")
    print("PACK03_V3_CANDIDATE=PASS")
    print(f"SIGNATURE={SIGNATURE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
