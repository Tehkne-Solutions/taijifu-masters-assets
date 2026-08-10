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
REVIEW = RIVAL / "source/PRESET02_P03_REVIEW.json"
P01 = LOT / "p01-manifest.json"
P02 = LOT / "p02-manifest.json"
P03 = LOT / "p03-manifest.json"
DISPOSABLE_WRITER = ROOT / ".github/workflows/materialize-preset02-p03-attack-light.yml"
EXPECTED_PIXEL_SHA = "67abba855b18ea6cc5ef62c4e382041d5ca69eb9902d9b3c6ead9329a163531e"
SAFE_MARGIN = 3
BEATS = ["guard", "chamber", "release", "impact", "follow_through", "recover"]
EXPECTED_REVIEW_RUN = 31441547569
EXPECTED_REVIEW_ARTIFACT = 9083015383
EXPECTED_REVIEW_DIGEST = "sha256:c9c70ae0442525efd8a83ce6f655ee0fbadc00d3d731558e22612c8d7c94819b"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pixel_sha(path: Path) -> str:
    return hashlib.sha256(Image.open(path).convert("RGBA").tobytes()).hexdigest()


def alpha_bounds(path: Path) -> tuple[int, int, int, int]:
    image = Image.open(path).convert("RGBA")
    alpha = image.getchannel("A").point(lambda v: 255 if v >= 3 else 0)
    return alpha.getbbox() or (0, 0, 0, 0)


def block(reason: str) -> int:
    print(f"PRESET02_P03=BLOCKED {reason}")
    return 2


def main() -> int:
    for path in (SOURCE, REVIEW, P01, P02, P03):
        if not path.is_file():
            return block(f"missing={path.relative_to(ROOT).as_posix()}")
    if DISPOSABLE_WRITER.exists():
        return block("disposable_writer_present")
    if pixel_sha(SOURCE) != EXPECTED_PIXEL_SHA:
        return block("source_pixel_identity")

    review = json.loads(REVIEW.read_text(encoding="utf-8"))
    if review.get("schema") != "tehkne/taijifu-training-rival-p03-review/v1":
        return block("review_schema")
    if review.get("status") != "visually_approved_attack_light_v2":
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
    p03 = json.loads(P03.read_text(encoding="utf-8"))
    if p03.get("schema") != "tehkne/taijifu-training-rival-p03/v1":
        return block("schema")
    if p03.get("signature") != "Tehkné Solutions" or p03.get("character_id") != "training_rival":
        return block("identity")
    if p03.get("version") != review.get("manifest_version"):
        return block("review_manifest_version_drift")
    if p03.get("source", {}).get("pixel_sha256") != EXPECTED_PIXEL_SHA:
        return block("manifest_source_pixel_identity")
    contract = p03.get("contract", {})
    if contract.get("upper_and_weapon_rigid_block") is not True:
        return block("weapon_owner")
    if contract.get("leg_masks_mutually_exclusive") is not True:
        return block("leg_mask_overlap")
    if contract.get("safe_canvas_margin_px") != SAFE_MARGIN:
        return block("safe_margin_contract")
    if contract.get("beats") != BEATS:
        return block("attack_beats")

    records = p03.get("attack_light", [])
    if len(records) != 6:
        return block(f"manifest_count={len(records)}/6")
    unique: set[str] = set()
    for index, record in enumerate(records, 1):
        name = f"char_training_rival__attack_light__f{index:03d}.png"
        if record.get("file") != f"attack_light/{name}":
            return block(f"manifest_name=f{index:03d}")
        path = LOT / "animations" / "attack_light" / name
        if not path.is_file():
            return block(f"missing_frame={name}")
        image = Image.open(path)
        if image.size != (1024, 1024) or image.mode != "RGBA":
            return block(f"frame_contract={name}:{image.size}:{image.mode}")
        file_sha = digest(path)
        if file_sha != record.get("sha256"):
            return block(f"frame_hash={name}")
        bounds = alpha_bounds(path)
        if list(bounds) != record.get("alpha_bounds"):
            return block(f"frame_bounds_manifest={name}")
        if bounds[0] <= SAFE_MARGIN or bounds[1] <= SAFE_MARGIN or bounds[2] >= 1024 - SAFE_MARGIN or bounds[3] >= 1024 - SAFE_MARGIN:
            return block(f"unsafe_canvas_margin={name}:{bounds}")
        unique.add(file_sha)
    if len(unique) != 6:
        return block(f"unique_hashes={len(unique)}/6")

    p01_count = len(p01.get("idle", [])) + len(p01.get("run", []))
    p02_count = sum(len(p02.get("frames", {}).get(mode, [])) for mode in ("jump_start", "airborne", "fall"))
    if p01_count != 14:
        return block(f"p01_regression={p01_count}/14")
    if p02_count != 7:
        return block(f"p02_regression={p02_count}/7")
    all_rival = list((LOT / "animations").glob("*/*.png"))
    if len(all_rival) != 27:
        return block(f"global_progress={len(all_rival)}/27_expected")

    print("PRESET02_P03_FRAME_COUNT=6/6")
    print("PRESET02_P03_BEATS=guard+chamber+release+impact+follow_through+recover")
    print("PRESET02_P03_UNIQUE_HASHES=6")
    print("PRESET02_P03_SAFE_CANVAS_MARGIN=PASS")
    print("PRESET02_P03_WEAPON_SAFE=PASS")
    print("PRESET02_P03_VISUAL_REVIEW=PASS evidence_frozen=true")
    print("PRESET02_P03_DISPOSABLE_WRITER=ABSENT")
    print("PRESET02_P01_REGRESSION=PASS frames=14/14")
    print("PRESET02_P02_REGRESSION=PASS frames=7/7")
    print("PRESET02_RIVAL_GLOBAL_PROGRESS=27/44")
    print("PRESET02_P03=PASS")
    print("PRESET02_RUNTIME_PROMOTION=BLOCKED requires_44_of_44=true")
    print("SIGNATURE=Tehkné Solutions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
