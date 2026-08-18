#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACK_ROOT = ROOT / "packs/characters/combat_reactions/v1"
KIT_PATH = ROOT / "production/pack04/production-reference-kit-v1.json"
SIGNATURE = "Tehkné Solutions"
PACK_ID = "PACK_04_COMBAT_REACTIONS_AND_MOTION"
TGAP_PACK_ID = "pack_04_combat_reactions_and_motion"
EXPECTED_CHARACTERS = ("lian_wu", "training_rival")
EXPECTED_STATES = ("block_recoil", "parry", "posture_break", "knockback", "neutral_recovery")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"json_root:{path}")
    return value


def fail(reason: str) -> int:
    print(f"PACK04_INTAKE_GATE=BLOCKED reason={reason}")
    print(f"SIGNATURE={SIGNATURE}")
    return 2


def require_identity(data: dict[str, Any], name: str) -> None:
    if data.get("pack_id") != PACK_ID:
        raise ValueError(f"{name}:pack_id")
    if data.get("tgap_pack_id") != TGAP_PACK_ID:
        raise ValueError(f"{name}:tgap_pack_id")
    if data.get("signature") != SIGNATURE:
        raise ValueError(f"{name}:signature")


def main() -> int:
    try:
        required = {
            "pack-manifest.json",
            "manifest.json",
            "runtime-map.json",
            "approval.json",
        }
        missing = sorted(name for name in required if not (PACK_ROOT / name).is_file())
        if missing:
            raise ValueError("support_missing:" + ",".join(missing))

        kit = read_json(KIT_PATH)
        if kit.get("pack_id") != PACK_ID or int(kit.get("slot_count", 0)) != 34:
            raise ValueError("reference_kit_identity")
        if kit.get("production_policy", {}).get("art_generation_may_begin") is not True:
            raise ValueError("reference_kit_authoring_not_ready")

        manifest = read_json(PACK_ROOT / "manifest.json")
        runtime_map = read_json(PACK_ROOT / "runtime-map.json")
        approval = read_json(PACK_ROOT / "approval.json")
        require_identity(manifest, "manifest")
        require_identity(runtime_map, "runtime_map")
        require_identity(approval, "approval")

        if int(manifest.get("asset_count", -1)) != 0:
            raise ValueError("manifest_asset_count_must_be_zero_before_authored_materialization")
        if int(manifest.get("expected_asset_count", -1)) != 34:
            raise ValueError("manifest_expected_asset_count")
        if manifest.get("assets") not in ([], None):
            raise ValueError("manifest_assets_must_be_empty")
        if manifest.get("status") not in ("art_required_fail_closed", "pending_authored_art", "intake"):
            raise ValueError("manifest_status_not_fail_closed")

        characters = runtime_map.get("characters")
        states = runtime_map.get("states")
        if characters != list(EXPECTED_CHARACTERS):
            raise ValueError("runtime_characters")
        if states != list(EXPECTED_STATES):
            raise ValueError("runtime_states")
        mappings = runtime_map.get("mappings")
        if not isinstance(mappings, dict):
            raise ValueError("runtime_mappings")
        for fighter in EXPECTED_CHARACTERS:
            fighter_map = mappings.get(fighter)
            if not isinstance(fighter_map, dict):
                raise ValueError(f"runtime_fighter_missing:{fighter}")
            for state in EXPECTED_STATES:
                if fighter_map.get(state) != []:
                    raise ValueError(f"runtime_mapping_must_be_empty:{fighter}:{state}")

        if approval.get("approved") is not False:
            raise ValueError("approval_must_be_false")
        if str(approval.get("human_review", "")).upper() != "PENDING":
            raise ValueError("human_review_must_be_pending")

        promotion = approval.get("promotion")
        if not isinstance(promotion, dict):
            raise ValueError("approval_promotion_missing")
        if promotion.get("canonical_ready") is not False:
            raise ValueError("canonical_ready_must_be_false")
        if promotion.get("release_allowed") is not False:
            raise ValueError("release_allowed_must_be_false")
        if promotion.get("playtest_02_visual_completion_allowed") is not False:
            raise ValueError("playtest02_must_be_false")

        pngs = sorted(PACK_ROOT.rglob("*.png"))
        if pngs:
            raise ValueError(f"authored_png_present_without_rc_materialization:{len(pngs)}")
        if (PACK_ROOT / "checksums.sha256").exists():
            raise ValueError("checksums_must_not_exist_before_full_34_frame_rc")

    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return fail(str(exc))

    print("PACK04_INTAKE_GATE=PASS assets=0 expected=34 mappings=10_empty")
    print("PACK04_AUTHORING_READY=PASS reference_slots=34")
    print("PACK04_RC_BUILD=BLOCKED reason=authored_frames_missing")
    print("PACK04_RUNTIME_ACTIVATION=BLOCKED")
    print("PACK04_PLAYTEST_02_VISUAL_COMPLETION=BLOCKED")
    print(f"SIGNATURE={SIGNATURE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
