#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "production/pack04/production-reference-kit-v1.json"
SIGNATURE = "Tehkné Solutions"
PACK_ID = "PACK_04_COMBAT_REACTIONS_AND_MOTION"
EXPECTED_SCHEMA = "tehkne/taijifu-pack04-production-reference-kit/v1"
EXPECTED_STATES = {
    "block_recoil": 3,
    "parry": 3,
    "posture_break": 4,
    "knockback": 4,
    "neutral_recovery": 3,
}
EXPECTED_FIGHTERS = {
    "lian_wu": {"facing": "right", "footline": 969},
    "training_rival": {"facing": "left", "footline": 970},
}
EXPECTED_TOTAL = 34


def fail(reason: str) -> int:
    print(f"PACK04_REFERENCE_KIT=BLOCKED reason={reason}")
    print(f"SIGNATURE={SIGNATURE}")
    return 2


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), "root_not_object")
    return value


def main() -> int:
    if not KIT.is_file():
        return fail("kit_missing")

    try:
        kit = load_json(KIT)
        require(kit.get("schema") == EXPECTED_SCHEMA, "schema")
        require(kit.get("signature") == SIGNATURE, "signature")
        require(kit.get("pack_id") == PACK_ID, "pack_id")
        require(kit.get("version") == "1.0.0", "version")
        require(kit.get("status") == "production_reference_ready_art_not_authored", "status")

        authorities = kit.get("authorities", {})
        require(isinstance(authorities, dict), "authorities")
        for key in ("assets_main_commit", "game_main_commit", "art_contract", "tgap_handoff_contract", "intake_manifest"):
            require(bool(str(authorities.get(key, "")).strip()), f"authority:{key}")
        require(re.fullmatch(r"[0-9a-f]{40}", str(authorities["assets_main_commit"])) is not None, "assets_commit")
        require(re.fullmatch(r"[0-9a-f]{40}", str(authorities["game_main_commit"])) is not None, "game_commit")

        rules = kit.get("global_rules", {})
        require(isinstance(rules, dict), "global_rules")
        canvas = rules.get("canvas", {})
        require(canvas == {"width": 1024, "height": 1024, "format": "PNG_RGBA", "transparent_background": True}, "canvas")
        for key in (
            "one_fighter_per_file",
            "physics_owns_world_translation",
            "new_art_only_for_pack04_states",
            "existing_good_states_must_not_be_regenerated",
            "placeholder_promotion_forbidden",
            "existing_frame_relabeling_forbidden",
            "contact_sheet_runtime_asset_forbidden",
            "human_visual_review_required",
        ):
            require(rules.get(key) is True, f"rule:{key}")
        for key in ("embedded_background", "embedded_text", "embedded_logo", "border"):
            require(rules.get(key) is False, f"rule:{key}")
        require(int(rules.get("max_footline_drift_px", -1)) == 3, "footline_tolerance")
        require(int(rules.get("max_alpha_bounds_variation_percent_within_state", -1)) == 8, "bounds_tolerance")

        fighters = kit.get("fighters", {})
        require(isinstance(fighters, dict) and set(fighters) == set(EXPECTED_FIGHTERS), "fighters")
        lian = fighters["lian_wu"]
        rival = fighters["training_rival"]
        require(lian.get("native_facing") == "right", "lian_facing")
        require(lian.get("pivot") == {"x": 0.5, "y": 0.92}, "lian_pivot")
        require(int(lian.get("canonical_footline_y", -1)) == 969, "lian_footline")
        li = lian.get("identity_authority", {})
        for key, expected in {
            "game_runtime": "production_default_base01",
            "skin": "skin_tone_03_warm",
            "face": "face_01_balanced",
            "eyes": "eyes_01_focused",
            "brows": "brows_01_focused",
            "hair": "hair_01_lian_topknot",
            "uniform": "uniform_01_lian_martial",
            "armor": "armor_01_taijifu_guard",
            "back": "back_01_guardian_panel",
            "weapon_main": "katana_lian_wu",
            "weapon_back": "sheath_lian_wu_blue",
            "combat_reference": "serene_katana",
        }.items():
            require(li.get(key) == expected, f"lian_identity:{key}")
        require(int(li.get("weapon_count", 0)) == 1, "lian_weapon_count")
        require("whole_old_lian_sprite_as_pack04_identity_authority" in lian.get("forbidden_identity_regressions", []), "lian_old_sprite_guardrail")

        require(rival.get("native_facing") == "left", "rival_facing")
        require(rival.get("pivot") == "bottom_center", "rival_pivot")
        require(int(rival.get("canonical_footline_y", -1)) == 970, "rival_footline")
        ri = rival.get("identity_authority", {})
        require(ri.get("canonical") == "production/first_playable/training_rival/canonical-production-v1.json", "rival_canonical")
        require(ri.get("weapon") == "wooden_training_saber", "rival_weapon")
        require(int(ri.get("weapon_count", 0)) == 1, "rival_weapon_count")
        require("breaker_gauntlets_in_reaction_frames" in rival.get("forbidden_identity_regressions", []), "rival_gauntlet_guardrail")

        semantics = kit.get("state_semantics", {})
        require(isinstance(semantics, dict) and set(semantics) == set(EXPECTED_STATES), "state_semantics")
        for state, count in EXPECTED_STATES.items():
            require(int(semantics[state].get("frames", 0)) == count, f"semantic_frames:{state}")
            require(int(semantics[state].get("fps", 0)) > 0, f"semantic_fps:{state}")
            require(bool(str(semantics[state].get("read", "")).strip()), f"semantic_read:{state}")

        slots = kit.get("slots", [])
        require(isinstance(slots, list), "slots")
        require(int(kit.get("slot_count", -1)) == EXPECTED_TOTAL, "slot_count_declared")
        require(len(slots) == EXPECTED_TOTAL, f"slot_count:{len(slots)}")

        ids: set[str] = set()
        filenames: set[str] = set()
        counts = Counter()
        per_state_frames: dict[tuple[str, str], list[int]] = defaultdict(list)

        for slot in slots:
            require(isinstance(slot, dict), "slot_not_object")
            fighter = str(slot.get("fighter", ""))
            state = str(slot.get("state", ""))
            frame = int(slot.get("frame", 0))
            require(fighter in EXPECTED_FIGHTERS, f"slot_fighter:{fighter}")
            require(state in EXPECTED_STATES, f"slot_state:{state}")
            require(1 <= frame <= EXPECTED_STATES[state], f"slot_frame:{fighter}:{state}:{frame}")
            expected_id = f"{fighter}:{state}:{frame:03d}"
            expected_name = f"char_{fighter}__{state}__f{frame:03d}.png"
            require(slot.get("slot_id") == expected_id, f"slot_id:{expected_id}")
            require(slot.get("filename") == expected_name, f"filename:{expected_name}")
            require(expected_id not in ids, f"duplicate_slot:{expected_id}")
            require(expected_name not in filenames, f"duplicate_filename:{expected_name}")
            ids.add(expected_id)
            filenames.add(expected_name)
            require(slot.get("native_facing") == EXPECTED_FIGHTERS[fighter]["facing"], f"slot_facing:{expected_id}")
            require(int(slot.get("canonical_footline_y", -1)) == EXPECTED_FIGHTERS[fighter]["footline"], f"slot_footline:{expected_id}")
            require(bool(str(slot.get("phase", "")).strip()), f"slot_phase:{expected_id}")
            require(len(str(slot.get("pose_brief", "")).strip()) >= 40, f"slot_brief:{expected_id}")
            refs = slot.get("study_only_existing_states", [])
            require(isinstance(refs, list) and len(refs) >= 1, f"slot_refs:{expected_id}")
            require(slot.get("must_be_new_authored_art") is True, f"slot_authored:{expected_id}")
            require(slot.get("may_relabel_existing_frame") is False, f"slot_relabel:{expected_id}")
            require(slot.get("may_use_placeholder") is False, f"slot_placeholder:{expected_id}")
            require(slot.get("may_fake_world_translation") is False, f"slot_translation:{expected_id}")
            require(slot.get("approval_status") == "not_authored", f"slot_status:{expected_id}")
            counts[(fighter, state)] += 1
            per_state_frames[(fighter, state)].append(frame)

        for fighter in EXPECTED_FIGHTERS:
            for state, expected in EXPECTED_STATES.items():
                require(counts[(fighter, state)] == expected, f"coverage:{fighter}:{state}")
                require(sorted(per_state_frames[(fighter, state)]) == list(range(1, expected + 1)), f"frame_sequence:{fighter}:{state}")

        policy = kit.get("production_policy", {})
        require(policy.get("this_file_contains_runtime_art") is False, "policy_runtime_art")
        require(policy.get("art_generation_may_begin") is True, "policy_generation")
        require(policy.get("pack_release_allowed") is False, "policy_release")
        require(policy.get("runtime_activation_allowed") is False, "policy_activation")
        require(policy.get("playtest_02_visual_completion_allowed") is False, "policy_playtest")
        require("34 PNGs" in str(policy.get("next_gate", "")), "policy_next_gate")

    except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
        return fail(str(exc))

    print("PACK04_REFERENCE_KIT=PASS fighters=2 states=5 slots=34")
    print("PACK04_REFERENCE_LIAN=PASS identity=current_modular_main motion_lineage=study_only")
    print("PACK04_REFERENCE_RIVAL=PASS identity=canonical-production-v1 weapon=wooden_training_saber")
    print("PACK04_REFERENCE_GUARDRAILS=PASS placeholders=false relabel=false physics_translation=false")
    print("PACK04_PRODUCTION_STATUS=READY_FOR_AUTHORING art_status=NOT_AUTHORED release=false runtime_active=false playtest_02=false")
    print(f"SIGNATURE={SIGNATURE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
