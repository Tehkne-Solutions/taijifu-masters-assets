#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/pack_04_combat_reactions/pack-04-combat-reactions-v1.json"
INTAKE_PATH = ROOT / "packs/characters/combat_reactions/v1/pack-manifest.json"
SIGNATURE = "Tehkné Solutions"
SCHEMA = "tehkne/taijifu-combat-reaction-pack/v1"
PACK_ID = "PACK_04_COMBAT_REACTIONS_AND_MOTION"
STATES = {
    "block_recoil": 3,
    "parry": 3,
    "posture_break": 4,
    "knockback": 4,
    "neutral_recovery": 3,
}
CHARACTERS = {
    "lian_wu": {"footline": 969, "native_facing": "right"},
    "training_rival": {"footline": 970, "native_facing": "left"},
}
SUPPORT_FILES = ("manifest.json", "checksums.sha256", "runtime-map.json", "approval.json")
EXPECTED_TOTAL = sum(STATES.values()) * len(CHARACTERS)


def block(reason: str) -> int:
    print(f"PACK04_GATE=BLOCKED reason={reason}")
    print(f"SIGNATURE={SIGNATURE}")
    return 2


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"json_invalid:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"json_root_not_object:{path}")
    return value


def validate_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if contract.get("schema") != SCHEMA:
        errors.append("schema")
    if contract.get("signature") != SIGNATURE:
        errors.append("signature")
    if contract.get("pack_id") != PACK_ID:
        errors.append("pack_id")
    if contract.get("version") != "1.0.0":
        errors.append("version")
    if contract.get("status") != "art_required_fail_closed":
        errors.append("status")

    source_release = contract.get("source_release", {})
    if not isinstance(source_release, dict):
        errors.append("source_release")
    else:
        if source_release.get("tag") != "assets-pack-04-v1.0.0":
            errors.append("release_tag")
        if source_release.get("archive") != "PACK_04_COMBAT_REACTIONS_v1.0.0.zip":
            errors.append("release_archive")
        if source_release.get("binary_storage") != "github_release_only":
            errors.append("binary_storage")
        if source_release.get("required") is not True:
            errors.append("release_required")
        if source_release.get("must_not_exist_before_art_approval") is not True:
            errors.append("premature_release_policy")

    characters = contract.get("characters", {})
    if not isinstance(characters, dict) or set(characters) != set(CHARACTERS):
        errors.append("characters")
    else:
        for character_id, expected in CHARACTERS.items():
            spec = characters.get(character_id, {})
            if not isinstance(spec, dict):
                errors.append(f"character:{character_id}")
                continue
            if spec.get("native_facing") != expected["native_facing"]:
                errors.append(f"native_facing:{character_id}")
            if int(spec.get("canonical_footline_y", -1)) != expected["footline"]:
                errors.append(f"footline:{character_id}")
            if int(spec.get("feet_baseline_tolerance_px", -1)) != 3:
                errors.append(f"feet_tolerance:{character_id}")
            if int(spec.get("max_frame_bounds_variation_percent", -1)) != 8:
                errors.append(f"bounds_variation:{character_id}")
        if characters.get("lian_wu", {}).get("pivot") != {"x": 0.5, "y": 0.92}:
            errors.append("lian_pivot")
        rival = characters.get("training_rival", {})
        if rival.get("pivot") != "bottom_center":
            errors.append("rival_pivot")
        if rival.get("weapon_continuity") != "single_wooden_training_saber":
            errors.append("rival_weapon_continuity")
        if rival.get("reaction_art_must_not_silently_switch_to_gauntlets") is not True:
            errors.append("rival_gauntlet_guardrail")
        if rival.get("combat_loadout_mismatch_issue") != "Tehkne-Solutions/taijifu-masters#515":
            errors.append("rival_mismatch_issue")

    states = contract.get("required_states", {})
    if not isinstance(states, dict) or set(states) != set(STATES):
        errors.append("required_states")
    else:
        for state, expected_frames in STATES.items():
            spec = states.get(state, {})
            if not isinstance(spec, dict):
                errors.append(f"state:{state}")
                continue
            if int(spec.get("minimum_frames", 0)) != expected_frames:
                errors.append(f"state_frames:{state}")
            if int(spec.get("fps", 0)) <= 0:
                errors.append(f"state_fps:{state}")
            if spec.get("loop") is not False:
                errors.append(f"state_loop:{state}")
            if not str(spec.get("semantic", "")).strip():
                errors.append(f"state_semantic:{state}")

    naming = contract.get("naming", {})
    if not isinstance(naming, dict):
        errors.append("naming")
    else:
        if naming.get("lian_wu") != "char_lian_wu__<state>__f<frame-3-digits>.png":
            errors.append("lian_naming")
        if naming.get("training_rival") != "char_training_rival__<state>__f<frame-3-digits>.png":
            errors.append("rival_naming")
    if int(contract.get("minimum_pngs_per_character", 0)) != 17:
        errors.append("minimum_pngs_per_character")
    if int(contract.get("minimum_total_pngs", 0)) != EXPECTED_TOTAL:
        errors.append("minimum_total_pngs")
    if tuple(contract.get("required_support_files", [])) != SUPPORT_FILES:
        errors.append("required_support_files")

    image_rules = contract.get("image_rules", {})
    if not isinstance(image_rules, dict):
        errors.append("image_rules")
    else:
        if image_rules.get("format") != "png":
            errors.append("image_format")
        if image_rules.get("canvas") != {"width": 1024, "height": 1024}:
            errors.append("canvas")
        for key in (
            "rgba",
            "alpha",
            "single_fighter_per_file",
            "forbid_embedded_background",
            "forbid_text",
            "forbid_logo",
            "forbid_border",
            "forbid_contact_sheet_as_runtime_asset",
            "forbid_relabelled_existing_frame_as_new_state",
        ):
            if image_rules.get(key) is not True:
                errors.append(f"image_rule:{key}")
        if image_rules.get("premultiplied_alpha") is not False:
            errors.append("premultiplied_alpha")

    authorship = contract.get("authorship_rules", {})
    if not isinstance(authorship, dict) or any(value is not True for value in authorship.values()):
        errors.append("authorship_rules")

    review = contract.get("review_requirements", {})
    if not isinstance(review, dict) or any(value != "pass_required" for value in review.values()):
        errors.append("review_requirements")

    integration = contract.get("game_integration", {})
    if not isinstance(integration, dict):
        errors.append("game_integration")
    else:
        if integration.get("repository") != "Tehkne-Solutions/taijifu-masters":
            errors.append("game_repository")
        for key in (
            "required_before_pack_release",
            "physics_owns_world_translation",
            "animation_may_not_fake_world_translation",
            "preserve_collision",
            "preserve_damage_frame_data_ai",
            "authored_visual_state_authority_required",
            "fallback_must_be_observable",
        ):
            if integration.get(key) is not True:
                errors.append(f"integration:{key}")

    promotion = contract.get("promotion_policy", {})
    if not isinstance(promotion, dict):
        errors.append("promotion_policy")
    else:
        if promotion.get("pack_release_allowed_before_all_states") is not False:
            errors.append("partial_release_policy")
        if promotion.get("playtest_02_visual_completion_allowed_before_release") is not False:
            errors.append("playtest_policy")
        if promotion.get("runtime_infrastructure_may_land_before_art") is not True:
            errors.append("runtime_infrastructure_policy")
        if promotion.get("art_completion_may_not_be_inferred_from_runtime_infrastructure") is not True:
            errors.append("false_completion_policy")
        if promotion.get("contract_ci_may_pass_while_art_status_is_blocked") is not True:
            errors.append("contract_ci_policy")
    return errors


def validate_intake(manifest: dict[str, Any], contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if manifest.get("signature") != SIGNATURE:
        errors.append("signature")
    if manifest.get("pack_id") != PACK_ID:
        errors.append("pack_id")
    if manifest.get("status") != "art_required_fail_closed":
        errors.append("status")
    if manifest.get("contract") != "contracts/pack_04_combat_reactions/pack-04-combat-reactions-v1.json":
        errors.append("contract_ref")

    release_target = manifest.get("release_target", {})
    source_release = contract.get("source_release", {})
    if not isinstance(release_target, dict):
        errors.append("release_target")
    else:
        if release_target.get("tag") != source_release.get("tag"):
            errors.append("release_tag")
        if release_target.get("archive") != source_release.get("archive"):
            errors.append("release_archive")
        if release_target.get("binary_storage") != "github_release_only":
            errors.append("binary_storage")
        if release_target.get("published") is not False:
            errors.append("premature_published")

    state_rows = manifest.get("new_authored_states", [])
    if not isinstance(state_rows, list) or len(state_rows) != len(STATES):
        errors.append("state_rows")
    else:
        rows_by_state = {str(row.get("state", "")): row for row in state_rows if isinstance(row, dict)}
        if set(rows_by_state) != set(STATES):
            errors.append("states")
        else:
            for state, expected_frames in STATES.items():
                if int(rows_by_state[state].get("frames_per_character", 0)) != expected_frames:
                    errors.append(f"state_frames:{state}")

    budget = manifest.get("frame_budget", {})
    if not isinstance(budget, dict):
        errors.append("frame_budget")
    else:
        if int(budget.get("new_frames_per_character", 0)) != 17:
            errors.append("per_character_budget")
        if int(budget.get("character_count", 0)) != 2:
            errors.append("character_count")
        if int(budget.get("total_new_frames", 0)) != EXPECTED_TOTAL:
            errors.append("total_budget")

    required_files = manifest.get("required_files", {})
    if not isinstance(required_files, dict):
        errors.append("required_files")
    else:
        if required_files.get("pattern") != "{character}/{state}/char_{character}__{state}__fNNN.png":
            errors.append("filename_pattern")
        if int(required_files.get("expected_png_count", 0)) != EXPECTED_TOTAL:
            errors.append("expected_png_count")
        if tuple(required_files.get("support_files", [])) != SUPPORT_FILES:
            errors.append("support_files")

    chars = manifest.get("characters", {})
    if not isinstance(chars, dict):
        errors.append("characters")
    else:
        rival = chars.get("training_rival", {})
        if rival.get("weapon_lock") != "one wooden training saber; single-weapon continuity preserved":
            errors.append("rival_weapon_lock")
        if rival.get("reaction_art_must_not_silently_switch_to_gauntlets") is not True:
            errors.append("rival_gauntlet_guardrail")

    promotion = manifest.get("promotion", {})
    if not isinstance(promotion, dict):
        errors.append("promotion")
    else:
        if promotion.get("canonical_ready") is not False:
            errors.append("premature_canonical_ready")
        if promotion.get("release_allowed") is not False:
            errors.append("premature_release_allowed")
        if promotion.get("playtest_02_visual_completion_allowed") is not False:
            errors.append("premature_playtest_completion")
        if promotion.get("contract_ci_may_pass_while_art_status_is_blocked") is not True:
            errors.append("contract_ci_policy")
    return errors


def expected_frame_paths(contract: dict[str, Any]) -> list[Path]:
    paths: list[Path] = []
    naming = contract["naming"]
    for character in CHARACTERS:
        pattern = naming[character]
        for state, count in STATES.items():
            for frame in range(1, count + 1):
                filename = pattern.replace("<state>", state).replace("<frame-3-digits>", f"{frame:03d}")
                paths.append(Path(character) / state / filename)
    return paths


def validate_png(path: Path, character: str) -> str | None:
    try:
        with Image.open(path) as image:
            image.load()
            if image.size != (1024, 1024):
                return f"dimensions:{path}:{image.size}"
            if image.mode != "RGBA":
                return f"mode:{path}:{image.mode}"
            alpha = image.getchannel("A")
            lo, hi = alpha.getextrema()
            if lo != 0:
                return f"alpha_background_not_transparent:{path}:min={lo}"
            if hi == 0:
                return f"empty_frame:{path}"
            bbox = alpha.getbbox()
            if bbox is None:
                return f"empty_bbox:{path}"
            bottom = bbox[3]
            expected_footline = int(CHARACTERS[character]["footline"])
            if abs(bottom - expected_footline) > 3:
                return f"footline:{path}:actual={bottom}:expected={expected_footline}"
    except Exception as exc:  # Pillow reports format/decode failures here.
        return f"png_read:{path}:{exc}"
    return None


def validate_checksums(candidate: Path, required: list[Path]) -> list[str]:
    checksum_path = candidate / "checksums.sha256"
    if not checksum_path.is_file():
        return ["checksums_missing"]
    entries: dict[str, str] = {}
    for raw in checksum_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        match = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?(.+)", line)
        if not match:
            return ["checksums_format"]
        entries[match.group(2).replace("\\", "/")] = match.group(1).lower()

    errors: list[str] = []
    for relative in required:
        rel = relative.as_posix()
        path = candidate / relative
        if rel not in entries:
            errors.append(f"checksum_entry_missing:{rel}")
            continue
        if not path.is_file():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != entries[rel]:
            errors.append(f"checksum_mismatch:{rel}")
    return errors


def validate_candidate(candidate: Path, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not candidate.is_dir():
        return ["candidate_directory_missing"]

    for support in SUPPORT_FILES:
        if not (candidate / support).is_file():
            errors.append(f"support_missing:{support}")

    frame_paths = expected_frame_paths(contract)
    bounds: dict[tuple[str, str], list[tuple[int, int]]] = {}
    for relative in frame_paths:
        path = candidate / relative
        parts = relative.parts
        character, state = parts[0], parts[1]
        if not path.is_file():
            errors.append(f"frame_missing:{relative.as_posix()}")
            continue
        image_error = validate_png(path, character)
        if image_error:
            errors.append(image_error)
            continue
        with Image.open(path) as image:
            bbox = image.getchannel("A").getbbox()
            assert bbox is not None
            bounds.setdefault((character, state), []).append((bbox[2] - bbox[0], bbox[3] - bbox[1]))

    if errors:
        return errors

    for (character, state), samples in bounds.items():
        widths = [w for w, _ in samples]
        heights = [h for _, h in samples]
        for values, axis in ((widths, "width"), (heights, "height")):
            smallest = max(1, min(values))
            largest = max(values)
            variation = (largest - smallest) / smallest
            if variation > 0.08:
                errors.append(f"bounds_variation:{character}/{state}/{axis}:{variation:.4f}>0.08")

    if errors:
        return errors

    try:
        candidate_manifest = read_json(candidate / "manifest.json")
        runtime_map = read_json(candidate / "runtime-map.json")
        approval = read_json(candidate / "approval.json")
    except ValueError as exc:
        return [str(exc)]

    if candidate_manifest.get("signature") != SIGNATURE or candidate_manifest.get("pack_id") != PACK_ID:
        errors.append("candidate_manifest_identity")
    if runtime_map.get("signature") != SIGNATURE:
        errors.append("runtime_map_signature")
    if set(runtime_map.get("states", [])) != set(STATES):
        errors.append("runtime_map_states")
    if set(runtime_map.get("characters", [])) != set(CHARACTERS):
        errors.append("runtime_map_characters")
    if approval.get("signature") != SIGNATURE:
        errors.append("approval_signature")
    if approval.get("status") != "pass":
        errors.append("approval_not_pass")
    if approval.get("human_visual_review") != "pass":
        errors.append("human_visual_review_not_pass")
    if approval.get("identity_continuity") != "pass":
        errors.append("identity_continuity_not_pass")
    if approval.get("weapon_continuity") != "pass":
        errors.append("weapon_continuity_not_pass")

    checksum_required = frame_paths + [Path("manifest.json"), Path("runtime-map.json"), Path("approval.json")]
    errors.extend(validate_checksums(candidate, checksum_required))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, help="Path to an extracted PACK 04 release candidate")
    args = parser.parse_args()

    try:
        contract = read_json(CONTRACT_PATH)
        intake = read_json(INTAKE_PATH)
    except ValueError as exc:
        return block(str(exc))

    contract_errors = validate_contract(contract)
    if contract_errors:
        return block("contract:" + "|".join(contract_errors))
    intake_errors = validate_intake(intake, contract)
    if intake_errors:
        return block("intake:" + "|".join(intake_errors))

    print(f"PACK04_CONTRACT=PASS states=5 characters=2 minimum_pngs={EXPECTED_TOTAL}")
    print("PACK04_INTAKE_MANIFEST=PASS binary_storage=github_release_only naming=fNNN")
    print("PACK04_RIVAL_VISUAL_IDENTITY=PASS weapon=wooden_training_saber mismatch_issue=taijifu-masters#515")
    print("PACK04_RELEASE_POLICY=PASS partial_release=false playtest_completion_before_release=false")
    print(f"SIGNATURE={SIGNATURE}")

    if args.candidate is None:
        print("PACK04_ART_STATUS=BLOCKED reason=candidate_not_provided")
        print("PACK04_GATE=CONTRACT_READY_ART_BLOCKED")
        return 0

    candidate_errors = validate_candidate(args.candidate, contract)
    if candidate_errors:
        return block("candidate:" + "|".join(candidate_errors))

    print(f"PACK04_REQUIRED_FILES=PASS {EXPECTED_TOTAL}/{EXPECTED_TOTAL}")
    print("PACK04_RGBA=PASS")
    print("PACK04_ALPHA=PASS")
    print("PACK04_FOOTLINE=PASS tolerance=3px")
    print("PACK04_STATE_BOUNDS=PASS max_variation=8pct")
    print("PACK04_CANDIDATE=PASS support=4 states=5 characters=2")
    print("PACK04_ART_STATUS=PASS human_visual_review=pass")
    print("PACK04_GATE=PASS")
    print(f"SIGNATURE={SIGNATURE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
