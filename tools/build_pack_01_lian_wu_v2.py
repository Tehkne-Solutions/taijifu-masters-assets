#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

PACK_ID = "pack_01_lian_wu_first_playable"
PACK_VERSION = "2.0.0"
ZIP_NAME = "PACK_01_LIAN_WU_FIRST_PLAYABLE_FINAL_v2.0.0.zip"
PINNED_GAME_COMMIT = "7cb383f438b005fe0024870e426f52f95c644950"
LOT_REL = Path("assets/tgap/pack_01_lian_wu/first_playable_lot_01")
PROMOTION_REL = Path("config/c64_lot01_promotion.json")
FAMILIES_REL = Path("assets/pack_01_characters/lian_wu/metadata/c64_first_playable_families.json")
EXPECTED = {
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
}
FIXED_ZIP_TIME = (2026, 8, 14, 12, 0, 0)


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def require(value: bool, reason: str) -> None:
    if not value:
        raise SystemExit(f"PACK01_V2=BLOCKED reason={reason}")


def add_bytes(zf: ZipFile, name: str, data: bytes) -> None:
    info = ZipInfo(name, FIXED_ZIP_TIME)
    info.compress_type = ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    zf.writestr(info, data)


def parse_checksums(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        sha, rel = line.split(None, 1)
        result[rel.strip()] = sha.strip().lower()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-root", required=True)
    parser.add_argument("--output-dir", default="artifacts/pack01-v2")
    parser.add_argument("--game-commit", default=PINNED_GAME_COMMIT)
    args = parser.parse_args()

    game = Path(args.game_root).resolve()
    out = Path(args.output_dir).resolve()
    lot = game / LOT_REL
    promotion_path = game / PROMOTION_REL
    families_path = game / FAMILIES_REL
    require(args.game_commit == PINNED_GAME_COMMIT, f"unpinned_game_commit_{args.game_commit}")
    require(lot.is_dir(), "lot_missing")

    approval_path = lot / "approval.json"
    manifest_path = lot / "manifest.json"
    checksums_path = lot / "checksums.sha256"
    runtime_map_path = lot / "runtime-map.json"
    spriteframes_path = lot / "lian_wu_first_playable_frames.tres"
    for path in (approval_path, manifest_path, checksums_path, runtime_map_path, spriteframes_path, promotion_path, families_path):
        require(path.is_file(), f"missing_{path.name}")

    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    promotion = json.loads(promotion_path.read_text(encoding="utf-8"))

    require(approval.get("signature") == "Tehkné Solutions", "approval_signature")
    require(approval.get("status") == "approved", "approval_status")
    require(approval.get("technical_generation") == "pass", "technical_generation")
    require(approval.get("visual_review") == "pass", "visual_review")
    require(approval.get("binary_promotion_allowed") is True, "binary_promotion")
    require(approval.get("approved_scope") == "first_playable_runtime", "approval_scope")
    require(approval.get("final_authored_animation_claimed") is False, "authored_claim_must_be_false")

    require(manifest.get("signature") == "Tehkné Solutions", "manifest_signature")
    require(manifest.get("status") == "approved_first_playable_runtime", "manifest_status")
    require(manifest.get("character_id") == "lian_wu", "character_id")
    require(manifest.get("visual_method") == "whole_sprite_continuous_affine_v1", "visual_method")
    require(manifest.get("frame_count") == 45, "frame_count_contract")
    require(manifest.get("animation_count") == 10, "animation_count_contract")

    require(promotion.get("signature") == "Tehkné Solutions", "promotion_signature")
    require(promotion.get("status") == "approved_for_first_playable_promotion", "promotion_status")
    technical = promotion.get("technical_review", {})
    require(technical.get("animations") == 10 and technical.get("frames") == 45, "promotion_matrix")
    require(technical.get("godot_import") == "pass", "godot_import")
    require(technical.get("real_battle_presenter") == "pass", "real_battle_presenter")
    policy = promotion.get("policy", {})
    require(policy.get("scope") == "first_playable_runtime", "promotion_scope")
    require(policy.get("final_authored_animation_claimed") is False, "promotion_authored_claim")

    expected_checksums = parse_checksums(checksums_path)
    frames: list[Path] = []
    matrix: dict[str, int] = {}
    for anim, count in EXPECTED.items():
        folder = lot / "animations" / anim
        current = sorted(folder.glob("*.png"))
        require(len(current) == count, f"{anim}_count_{len(current)}_of_{count}")
        matrix[anim] = len(current)
        for index, path in enumerate(current, 1):
            expected_name = f"char_lian_wu__{anim}__f{index:02d}.png"
            require(path.name == expected_name, f"naming_{path.name}")
            rel = path.relative_to(lot).as_posix()
            require(rel in expected_checksums, f"checksum_record_missing_{rel}")
            require(digest(path) == expected_checksums[rel], f"checksum_mismatch_{rel}")
        frames.extend(current)
    require(len(frames) == 45, f"global_frame_count_{len(frames)}")
    frame_checksum_records = {k: v for k, v in expected_checksums.items() if k.startswith("animations/") and k.endswith(".png")}
    require(len(frame_checksum_records) == 45, f"checksum_frame_records_{len(frame_checksum_records)}")

    support = [approval_path, manifest_path, checksums_path, runtime_map_path, spriteframes_path, promotion_path, families_path]
    source_files = sorted(frames + support, key=lambda p: p.as_posix())
    records = []
    for path in source_files:
        if path.is_relative_to(lot):
            rel = Path("first_playable_lot_01") / path.relative_to(lot)
        else:
            rel = Path("evidence") / path.name
        records.append({"file": rel.as_posix(), "bytes": path.stat().st_size, "sha256": digest(path)})

    pack_manifest = {
        "schema": "taijifu/global-pack/v1",
        "signature": "Tehkné Solutions",
        "pack_id": PACK_ID,
        "display_name": "PACK 01 — Lian Wu First Playable",
        "version": PACK_VERSION,
        "character_id": "lian_wu",
        "source_repository": "Tehkne-Solutions/taijifu-masters",
        "source_commit": PINNED_GAME_COMMIT,
        "source_stage": "C64",
        "runtime_scope": "first_playable_runtime",
        "final_authored_animation_claimed": False,
        "future_authored_animation_replacement_allowed": True,
        "visual_method": manifest["visual_method"],
        "frame_count": 45,
        "animation_matrix": matrix,
        "source_character_lock_sha256": manifest.get("source_character_lock_sha256"),
        "source_character_lock_rgba_sha256": manifest.get("source_character_lock_rgba_sha256"),
        "review_artifact": promotion.get("review_artifact", {}),
        "files": records,
    }
    manifest_bytes = (json.dumps(pack_manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    out.mkdir(parents=True, exist_ok=True)
    zip_path = out / ZIP_NAME
    with ZipFile(zip_path, "w") as zf:
        add_bytes(zf, "PACK_MANIFEST.json", manifest_bytes)
        for path in source_files:
            if path.is_relative_to(lot):
                arc = (Path("first_playable_lot_01") / path.relative_to(lot)).as_posix()
            else:
                arc = (Path("evidence") / path.name).as_posix()
            add_bytes(zf, arc, path.read_bytes())

    zip_sha = digest(zip_path)
    (out / f"{ZIP_NAME}.sha256").write_text(f"{zip_sha}  {ZIP_NAME}\n", encoding="utf-8")
    release_manifest = {
        "schema": "taijifu/global-pack-release/v1",
        "signature": "Tehkné Solutions",
        "pack_id": PACK_ID,
        "version": PACK_VERSION,
        "filename": ZIP_NAME,
        "sha256": zip_sha,
        "archive_files": len(source_files) + 1,
        "runtime_frames": 45,
        "source_commit": PINNED_GAME_COMMIT,
        "status": "release_candidate_built_from_c64_approved_runtime_assets",
    }
    (out / "PACK_01_V2_RELEASE_MANIFEST.json").write_text(
        json.dumps(release_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print("PACK01_V2_SOURCE=PASS stage=C64 pinned=true")
    print("PACK01_V2_APPROVAL=PASS visual_review=pass binary_promotion_allowed=true")
    print("PACK01_V2_MATRIX=PASS animations=10 frames=45")
    print(f"PACK01_V2_ARCHIVE=PASS files={len(source_files) + 1}")
    print(f"PACK01_V2_ZIP={zip_path}")
    print(f"PACK01_V2_SHA256={zip_sha}")
    print("PACK01_V2_AUTHORED_CLAIM=false")
    print("PACK01_V2=PASS")
    print("SIGNATURE=Tehkné Solutions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
