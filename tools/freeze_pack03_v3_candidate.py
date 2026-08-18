#!/usr/bin/env python3
"""Freeze machine-verifiable PACK 03 v3 candidate state without human promotion."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image

SIGNATURE = "Tehkné Solutions"
ROOT = Path("production/first_playable/stages/mountain_dojo_night/art_pass_v3")
STATUS_PATH = ROOT / "review-status.json"
LAYERS = ("background.png", "midground.png", "foreground.png")
EXPECTED_SIZE = (1920, 1080)
SAFE_BOX = (280, 80, 1640, 820)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def nontransparent_fraction(image: Image.Image, box: tuple[int, int, int, int] | None = None) -> float:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    region = alpha.crop(box) if box else alpha
    hist = region.histogram()
    total = region.width * region.height
    if total <= 0:
        return 0.0
    near_transparent = sum(hist[:9])
    return 1.0 - near_transparent / total


def main() -> int:
    if not STATUS_PATH.is_file():
        print("PACK03_V3_FREEZE=BLOCKED reason=review_status_missing")
        return 2

    missing = [name for name in LAYERS if not (ROOT / name).is_file()]
    if missing:
        print("PACK03_V3_FREEZE=WAITING missing=" + ",".join(missing))
        print(f"SIGNATURE={SIGNATURE}")
        return 0

    status = json.loads(STATUS_PATH.read_text(encoding="utf-8-sig"))
    if status.get("signature") != SIGNATURE:
        print("PACK03_V3_FREEZE=BLOCKED reason=signature")
        return 2

    layer_state: dict[str, dict[str, str]] = {}
    for name in LAYERS:
        path = ROOT / name
        with Image.open(path) as image:
            if image.size != EXPECTED_SIZE:
                print(f"PACK03_V3_FREEZE=BLOCKED reason=size layer={name} actual={image.size}")
                return 2
            if name == "foreground.png":
                if image.mode != "RGBA":
                    print(f"PACK03_V3_FREEZE=BLOCKED reason=foreground_mode actual={image.mode}")
                    return 2
                overall_nontransparent = nontransparent_fraction(image)
                safe_nontransparent = nontransparent_fraction(image, SAFE_BOX)
                if 1.0 - overall_nontransparent < 0.50:
                    print("PACK03_V3_FREEZE=BLOCKED reason=foreground_transparency")
                    return 2
                if overall_nontransparent < 0.005:
                    print("PACK03_V3_FREEZE=BLOCKED reason=foreground_empty")
                    return 2
                if safe_nontransparent > 0.03:
                    print(f"PACK03_V3_FREEZE=BLOCKED reason=safe_zone coverage={safe_nontransparent:.6f}")
                    return 2
        layer_state[name] = {"state": "frozen", "sha256": sha256(path)}

    status["status"] = "technical_frozen"
    status["layers"] = layer_state
    status["automated_validation"] = "pass"
    status["foreground_transparency"] = "pass"
    status["safe_zone"] = "pass"

    # Human/runtime gates remain fail-closed by design.
    status["manual_visual_review"] = "pending"
    status["godot_runtime_capture"] = "pending"
    status["c30_materialization"] = "pending"
    status["stage_premium_runtime_review"] = "pending"
    status["vertical_slice_asset_truth"] = "pending"
    status["promotion"] = False
    status["canonical_replacement_authorized"] = False

    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("PACK03_V3_FREEZE=PASS layers=3 hashes=frozen human_review=pending promotion=false")
    print(f"SIGNATURE={SIGNATURE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
