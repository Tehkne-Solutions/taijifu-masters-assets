#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
RIVAL = ROOT / "production/first_playable/training_rival"
LOT = RIVAL / "first_playable_lot_01"
SOURCE = RIVAL / "source/training_rival_master.png"
REVIEW = RIVAL / "source/PRESET02_P02_REVIEW.json"
P01 = LOT / "p01-manifest.json"
P02 = LOT / "p02-manifest.json"
EXPECTED_PIXEL_SHA = "67abba855b18ea6cc5ef62c4e382041d5ca69eb9902d9b3c6ead9329a163531e"
EXPECTED = {"jump_start": 3, "airborne": 2, "fall": 2}
SAFE_MARGIN = 3
EXPECTED_REVIEW_RUN = 31441065672
EXPECTED_REVIEW_ARTIFACT = 9082846418
EXPECTED_REVIEW_DIGEST = "sha256:8495648995d8f379cad4b5ab99532d054cc825c543c445a8549d4666d0a818a4"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pixel_sha(path: Path) -> str:
    return hashlib.sha256(Image.open(path).convert("RGBA").tobytes()).hexdigest()


def alpha_bounds(path: Path) -> tuple[int, int, int, int]:
    image = Image.open(path).convert("RGBA")
    alpha = image.getchannel("A").point(lambda v: 255 if v >= 3 else 0)
    return alpha.getbbox() or (0, 0, 0, 0)


def block(reason: str) -> int:
    print(f"PRESET02_P02=BLOCKED {reason}")
    return 2


def main() -> int:
    for path in (SOURCE, REVIEW, P01, P02):
        if not path.is_file():
            return block(f"missing={path.relative_to(ROOT).as_posix()}")

    if pixel_sha(SOURCE) != EXPECTED_PIXEL_SHA:
        return block("source_pixel_identity")

    review = json.loads(REVIEW.read_text(encoding="utf-8"))
    if review.get("schema") != "tehkne/taijifu-training-rival-p02-review/v1":
        return block("review_schema")
    if review.get("signature") != "Tehkné Solutions" or review.get("character_id") != "training_rival":
        return block("review_identity")
    if review.get("status") != "visually_approved_safe_margin":
        return block("review_status")
    if review.get("source_pixel_sha256") != EXPECTED_PIXEL_SHA:
        return block("review_source_identity")
    if review.get("visual_review", {}).get("approved_for_next_pack") is not True:
        return block("review_not_approved")
    if review.get("runtime_ready") is not False:
        return block("review_runtime_must_remain_blocked")
    evidence = review.get("evidence", {})
    if evidence.get("workflow_run_id") != EXPECTED_REVIEW_RUN:
        return block("review_run_id")
    if evidence.get("artifact_id") != EXPECTED_REVIEW_ARTIFACT:
        return block("review_artifact_id")
    if evidence.get("artifact_digest") != EXPECTED_REVIEW_DIGEST:
        return block("review_artifact_digest")

    p01 = json.loads(P01.read_text(encoding="utf-8"))
    p02 = json.loads(P02.read_text(encoding="utf-8"))
    if p02.get("schema") != "tehkne/taijifu-training-rival-p02/v1":
        return block("schema")
    if p02.get("signature") != "Tehkné Solutions" or p02.get("character_id") != "training_rival":
        return block("identity")
    if p02.get("version") != review.get("manifest_version"):
        return block("review_manifest_version_drift")
    if p02.get("source", {}).get("pixel_sha256") != EXPECTED_PIXEL_SHA:
        return block("manifest_source_pixel_identity")

    contract = p02.get("contract", {})
    if contract.get("upper_and_weapon_rigid_block") is not True:
        return block("weapon_owner")
    if contract.get("leg_masks_mutually_exclusive") is not True:
        return block("leg_mask_overlap")
    if contract.get("safe_canvas_margin_px") != SAFE_MARGIN:
        return block("safe_margin_contract")

    unique: set[str] = set()
    total = 0
    frames = p02.get("frames", {})
    for mode, expected_count in EXPECTED.items():
        items = frames.get(mode, [])
        if len(items) != expected_count:
            return block(f"manifest_count={mode}:{len(items)}/{expected_count}")
        for index, record in enumerate(items, 1):
            expected_name = f"char_training_rival__{mode}__f{index:03d}.png"
            expected_rel = f"{mode}/{expected_name}"
            if record.get("file") != expected_rel:
                return block(f"manifest_name={mode}/f{index:03d}")
            path = LOT / "animations" / mode / expected_name
            if not path.is_file():
                return block(f"missing_frame={expected_rel}")
            image = Image.open(path)
            if image.size != (1024, 1024) or image.mode != "RGBA":
                return block(f"frame_contract={expected_rel}:{image.size}:{image.mode}")
            file_sha = digest(path)
            if record.get("sha256") != file_sha:
                return block(f"frame_hash={expected_rel}")
            bounds = alpha_bounds(path)
            if list(bounds) != record.get("alpha_bounds"):
                return block(f"frame_bounds_manifest={expected_rel}")
            if bounds[0] <= SAFE_MARGIN or bounds[1] <= SAFE_MARGIN or bounds[2] >= 1024 - SAFE_MARGIN or bounds[3] >= 1024 - SAFE_MARGIN:
                return block(f"unsafe_canvas_margin={expected_rel}:{bounds}")
            unique.add(file_sha)
            total += 1

    if total != 7 or len(unique) < 6:
        return block(f"frame_or_unique_count={total}/7:{len(unique)}")

    p01_count = sum(len(p01.get(k, [])) for k in ("idle", "run"))
    if p01_count != 14:
        return block(f"p01_regression={p01_count}/14")

    all_rival = list((LOT / "animations").glob("*/*.png"))
    if len(all_rival) != 21:
        return block(f"global_progress={len(all_rival)}/21_expected")

    print("PRESET02_P02_FRAME_COUNT=7/7")
    print("PRESET02_P02_SEQUENCE=jump_start3+airborne2+fall2")
    print(f"PRESET02_P02_UNIQUE_HASHES={len(unique)}")
    print("PRESET02_P02_SAFE_CANVAS_MARGIN=PASS")
    print("PRESET02_P02_WEAPON_SAFE=PASS")
    print("PRESET02_P02_VISUAL_REVIEW=PASS evidence_frozen=true")
    print("PRESET02_P01_REGRESSION=PASS frames=14/14")
    print("PRESET02_RIVAL_GLOBAL_PROGRESS=21/44")
    print("PRESET02_P02=PASS")
    print("PRESET02_RUNTIME_PROMOTION=BLOCKED requires_44_of_44=true")
    print("SIGNATURE=Tehkné Solutions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
