#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HANDOFF_PATH = ROOT / "contracts/pack_04_combat_reactions/tgap-handoff-v1.json"
ART_CONTRACT_PATH = ROOT / "contracts/pack_04_combat_reactions/pack-04-combat-reactions-v1.json"
INTAKE_PATH = ROOT / "packs/characters/combat_reactions/v1/pack-manifest.json"
SIGNATURE = "Tehkné Solutions"
PACK_ID = "PACK_04_COMBAT_REACTIONS_AND_MOTION"
TGAP_PACK_ID = "pack_04_combat_reactions_and_motion"
VERSION = "1.0.0"
RELEASE_TAG = "assets-pack-04-v1.0.0"
FIGHTERS = ("lian_wu", "training_rival")
STATES = ("block_recoil", "parry", "posture_break", "knockback", "neutral_recovery")
SUPPORT_FILES = ("manifest.json", "checksums.sha256", "runtime-map.json", "approval.json")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"json_root_not_object:{path}")
    return value


def block(reason: str) -> int:
    print(f"PACK04_TGAP_HANDOFF=BLOCKED reason={reason}")
    print(f"SIGNATURE={SIGNATURE}")
    return 2


def identity_ok(value: dict[str, Any]) -> bool:
    return (
        value.get("pack_id") == PACK_ID
        and value.get("tgap_pack_id") == TGAP_PACK_ID
        and value.get("version") == VERSION
        and value.get("release_tag") == RELEASE_TAG
        and value.get("signature") == SIGNATURE
    )


def validate_static() -> list[str]:
    errors: list[str] = []
    handoff = read_json(HANDOFF_PATH)
    art_contract = read_json(ART_CONTRACT_PATH)
    intake = read_json(INTAKE_PATH)

    if handoff.get("schema") != "tehkne/taijifu-pack04-tgap-handoff/v1":
        errors.append("handoff_schema")
    if not identity_ok(handoff):
        errors.append("handoff_identity")
    if int(handoff.get("asset_count", 0)) != 34:
        errors.append("handoff_asset_count")
    if int(handoff.get("minimum_tgap_file_count", 0)) != 38:
        errors.append("handoff_file_count")
    if tuple(handoff.get("fighters", [])) != FIGHTERS:
        errors.append("handoff_fighters")
    if tuple(handoff.get("states", [])) != STATES:
        errors.append("handoff_states")
    if tuple(handoff.get("support_files", [])) != SUPPORT_FILES:
        errors.append("handoff_support_files")

    if tuple(art_contract.get("required_support_files", [])) != SUPPORT_FILES:
        errors.append("art_contract_support_files")
    intake_required = intake.get("required_files", {})
    if not isinstance(intake_required, dict) or tuple(intake_required.get("support_files", [])) != SUPPORT_FILES:
        errors.append("intake_support_files")
    if int(intake_required.get("expected_png_count", 0)) != 34:
        errors.append("intake_asset_count")
    if intake.get("pack_id") != PACK_ID:
        errors.append("intake_pack_id")
    release = intake.get("release_target", {})
    if not isinstance(release, dict) or release.get("tag") != RELEASE_TAG:
        errors.append("intake_release_tag")

    checksum = handoff.get("checksum_contract", {})
    if not isinstance(checksum, dict):
        errors.append("checksum_contract")
    else:
        if checksum.get("file") != "checksums.sha256":
            errors.append("checksum_filename")
        if checksum.get("format") != "sha256sum":
            errors.append("checksum_format")
        if checksum.get("canonical_authority") is not True:
            errors.append("checksum_authority")
        if int(checksum.get("minimum_entry_count", 0)) != 37:
            errors.append("checksum_entry_count")
        if checksum.get("checksums_json_forbidden_as_independent_authority") is not True:
            errors.append("checksum_split_authority")

    manifest = handoff.get("manifest_contract", {})
    runtime_map = handoff.get("runtime_map_contract", {})
    approval = handoff.get("approval_contract", {})
    if manifest.get("schema") != "tehkne/taijifu-pack04-materialization/v1":
        errors.append("manifest_schema")
    if runtime_map.get("schema") != "tehkne/taijifu-pack04-runtime-map/v1":
        errors.append("runtime_map_schema")
    if approval.get("schema") != "tehkne/taijifu-pack04-approval/v1":
        errors.append("approval_schema")
    if approval.get("approved") is not True or approval.get("human_review") != "PASS":
        errors.append("approval_gate")
    legacy = approval.get("legacy_validator_compatibility", {})
    expected_legacy = {
        "status": "pass",
        "human_visual_review": "pass",
        "identity_continuity": "pass",
        "weapon_continuity": "pass",
    }
    if legacy != expected_legacy:
        errors.append("approval_legacy_compatibility")

    boundary = handoff.get("runtime_boundary", {})
    if boundary.get("materialized_does_not_mean_runtime_active") is not True:
        errors.append("runtime_boundary_materialized")
    if boundary.get("runtime_active_before_game_visual_integration") is not False:
        errors.append("runtime_boundary_activation")
    if boundary.get("physics_remains_world_translation_owner") is not True:
        errors.append("runtime_boundary_physics")
    return errors


def parse_checksums(path: Path) -> tuple[dict[str, str], list[str]]:
    entries: dict[str, str] = {}
    errors: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        match = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?(.+)", line)
        if not match:
            errors.append("checksums_format")
            continue
        relative = match.group(2).replace("\\", "/")
        if relative in entries:
            errors.append(f"checksum_duplicate:{relative}")
        entries[relative] = match.group(1).lower()
    return entries, errors


def validate_candidate(candidate: Path) -> list[str]:
    errors: list[str] = []
    if not candidate.is_dir():
        return ["candidate_missing"]
    for support in SUPPORT_FILES:
        if not (candidate / support).is_file():
            errors.append(f"support_missing:{support}")
    if errors:
        return errors

    manifest = read_json(candidate / "manifest.json")
    runtime_map = read_json(candidate / "runtime-map.json")
    approval = read_json(candidate / "approval.json")
    if manifest.get("schema") != "tehkne/taijifu-pack04-materialization/v1" or not identity_ok(manifest):
        errors.append("manifest_identity")
    if runtime_map.get("schema") != "tehkne/taijifu-pack04-runtime-map/v1" or not identity_ok(runtime_map):
        errors.append("runtime_map_identity")
    if approval.get("schema") != "tehkne/taijifu-pack04-approval/v1" or not identity_ok(approval):
        errors.append("approval_identity")

    assets = manifest.get("assets", [])
    if not isinstance(assets, list) or len(assets) != 34 or int(manifest.get("asset_count", 0)) != 34:
        errors.append("manifest_assets")
        return errors

    inventory: dict[str, dict[str, Any]] = {}
    coverage = {(fighter, state): 0 for fighter in FIGHTERS for state in STATES}
    for entry in assets:
        if not isinstance(entry, dict):
            errors.append("manifest_asset_entry")
            continue
        relative = str(entry.get("path", "")).replace("\\", "/")
        fighter = str(entry.get("fighter", ""))
        state = str(entry.get("state", ""))
        sha = str(entry.get("sha256", "")).lower()
        if not relative or relative.startswith("/") or ".." in Path(relative).parts or not relative.endswith(".png"):
            errors.append(f"asset_path:{relative}")
            continue
        if relative in inventory:
            errors.append(f"asset_duplicate:{relative}")
            continue
        if fighter not in FIGHTERS or state not in STATES:
            errors.append(f"asset_scope:{relative}")
            continue
        if not re.fullmatch(r"[0-9a-f]{64}", sha):
            errors.append(f"asset_sha:{relative}")
            continue
        asset_path = candidate / relative
        if not asset_path.is_file():
            errors.append(f"asset_missing:{relative}")
            continue
        actual = hashlib.sha256(asset_path.read_bytes()).hexdigest()
        if actual != sha:
            errors.append(f"asset_sha_mismatch:{relative}")
        inventory[relative] = entry
        coverage[(fighter, state)] += 1

    for key, count in coverage.items():
        if count <= 0:
            errors.append(f"coverage_missing:{key[0]}:{key[1]}")

    mappings = runtime_map.get("mappings", {})
    if not isinstance(mappings, dict):
        errors.append("runtime_map_mappings")
    else:
        for fighter in FIGHTERS:
            fighter_map = mappings.get(fighter, {})
            if not isinstance(fighter_map, dict):
                errors.append(f"runtime_map_fighter:{fighter}")
                continue
            for state in STATES:
                paths = fighter_map.get(state, [])
                if not isinstance(paths, list) or not paths:
                    errors.append(f"runtime_map_state:{fighter}:{state}")
                    continue
                for relative in paths:
                    path = str(relative)
                    entry = inventory.get(path)
                    if entry is None:
                        errors.append(f"runtime_map_unknown:{path}")
                    elif entry.get("fighter") != fighter or entry.get("state") != state:
                        errors.append(f"runtime_map_mismatch:{path}")

    if approval.get("approved") is not True or approval.get("human_review") != "PASS":
        errors.append("approval_not_pass")
    if not str(approval.get("reviewer", "")).strip():
        errors.append("approval_reviewer")
    evidence = approval.get("evidence", [])
    if not isinstance(evidence, list) or not evidence:
        errors.append("approval_evidence")
    for key in ("status", "human_visual_review", "identity_continuity", "weapon_continuity"):
        if approval.get(key) != "pass":
            errors.append(f"approval_legacy:{key}")

    checksum_entries, checksum_errors = parse_checksums(candidate / "checksums.sha256")
    errors.extend(checksum_errors)
    if len(checksum_entries) < 37:
        errors.append(f"checksum_count:{len(checksum_entries)}")
    required_checksum_paths = list(inventory) + ["manifest.json", "runtime-map.json", "approval.json"]
    for relative in required_checksum_paths:
        if relative not in checksum_entries:
            errors.append(f"checksum_missing:{relative}")
            continue
        target = candidate / relative
        if target.is_file():
            actual = hashlib.sha256(target.read_bytes()).hexdigest()
            if actual != checksum_entries[relative]:
                errors.append(f"checksum_mismatch:{relative}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path)
    args = parser.parse_args()
    try:
        static_errors = validate_static()
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return block(f"static_read:{exc}")
    if static_errors:
        return block("static:" + "|".join(static_errors))

    print("PACK04_TGAP_HANDOFF_STATIC=PASS support=manifest.json,checksums.sha256,runtime-map.json,approval.json")
    print("PACK04_TGAP_CHECKSUM_AUTHORITY=PASS format=sha256sum split_authority=false")
    print("PACK04_TGAP_IDENTITY=PASS pack=pack_04_combat_reactions_and_motion version=1.0.0 release=assets-pack-04-v1.0.0")
    print("PACK04_TGAP_RUNTIME_BOUNDARY=PASS materialized_not_runtime_active=true")

    if args.candidate is None:
        print("PACK04_TGAP_ART_STATUS=BLOCKED reason=candidate_not_provided")
        print("PACK04_TGAP_HANDOFF_GATE=CONTRACT_READY_ART_BLOCKED")
        print(f"SIGNATURE={SIGNATURE}")
        return 0

    try:
        candidate_errors = validate_candidate(args.candidate)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return block(f"candidate_read:{exc}")
    if candidate_errors:
        return block("candidate:" + "|".join(candidate_errors))

    print("PACK04_TGAP_CANDIDATE=PASS assets=34 checksum_entries>=37")
    print("PACK04_TGAP_HANDOFF_GATE=PASS")
    print(f"SIGNATURE={SIGNATURE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
