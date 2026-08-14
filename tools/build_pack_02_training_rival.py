#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
RIVAL = ROOT / "production/first_playable/training_rival"
LOT = RIVAL / "first_playable_lot_01"
SOURCE = RIVAL / "source"
CANONICAL = RIVAL / "canonical-production-v1.json"
PACK_ID = "pack_02_training_rival_first_playable"
PACK_VERSION = "1.0.0"
ZIP_NAME = "PACK_02_TRAINING_RIVAL_FIRST_PLAYABLE_FINAL_v1.0.0.zip"
EXPECTED_ANIMS = {
    "idle": 6,
    "run": 8,
    "jump_start": 3,
    "airborne": 2,
    "fall": 2,
    "attack_light": 6,
    "guard": 3,
    "dodge": 5,
    "hit": 3,
    "ko": 6,
}
REVIEW_FILES = [
    "PRESET02_P01_V3_REVIEW.json",
    "PRESET02_P02_REVIEW.json",
    "PRESET02_P03_REVIEW.json",
    "PRESET02_P04_REVIEW.json",
    "PRESET02_P05_REVIEW.json",
]
MANIFEST_FILES = [f"p{i:02d}-manifest.json" for i in range(1, 6)]
FIXED_ZIP_TIME = (2026, 8, 14, 12, 0, 0)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise SystemExit(f"PACK02=BLOCKED reason={reason}")


def add_bytes(zf: ZipFile, arcname: str, data: bytes) -> None:
    info = ZipInfo(arcname, FIXED_ZIP_TIME)
    info.compress_type = ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    zf.writestr(info, data)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default="artifacts/pack02")
    args = ap.parse_args()
    out = ROOT / args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    require(CANONICAL.is_file(), "canonical_contract_missing")
    canonical = json.loads(CANONICAL.read_text(encoding="utf-8"))
    require(canonical.get("signature") == "Tehkné Solutions", "canonical_signature")
    require(canonical.get("status") == "canonical_complete_44_of_44_runtime_active", "canonical_status")
    require(canonical.get("required_total_frames") == 44, "canonical_frame_contract")
    promotion = canonical.get("promotion", {})
    for key in ("asset_matrix_complete", "game_c28_import_complete", "godot_runtime_bench_complete", "runtime_ready", "real_assets_active"):
        require(promotion.get(key) is True, f"promotion_{key}")

    frames: list[Path] = []
    for anim, count in EXPECTED_ANIMS.items():
        folder = LOT / "animations" / anim
        current = sorted(folder.glob("*.png"))
        require(len(current) == count, f"{anim}_count_{len(current)}_of_{count}")
        for index, path in enumerate(current, 1):
            expected = f"char_training_rival__{anim}__f{index:03d}.png"
            require(path.name == expected, f"naming_{path.name}")
        frames.extend(current)
    require(len(frames) == 44, f"global_frame_count_{len(frames)}")

    required_text = [CANONICAL]
    for name in MANIFEST_FILES:
        p = LOT / name
        require(p.is_file(), f"missing_{name}")
        required_text.append(p)
    for name in REVIEW_FILES:
        p = SOURCE / name
        require(p.is_file(), f"missing_{name}")
        required_text.append(p)
    master = SOURCE / "training_rival_master.png"
    require(master.is_file(), "master_missing")

    file_records = []
    all_files = sorted(frames + required_text + [master], key=lambda p: p.as_posix())
    for path in all_files:
        rel = path.relative_to(RIVAL).as_posix()
        file_records.append({"file": rel, "bytes": path.stat().st_size, "sha256": sha256(path)})

    manifest = {
        "schema": "taijifu/global-pack/v1",
        "signature": "Tehkné Solutions",
        "pack_id": PACK_ID,
        "display_name": "PACK 02 — Training Rival First Playable",
        "version": PACK_VERSION,
        "character_id": "training_rival",
        "runtime_status": canonical["status"],
        "frame_count": 44,
        "animation_matrix": EXPECTED_ANIMS,
        "source_pixel_sha256": canonical.get("completion", {}).get("source_pixel_sha256"),
        "game_runtime_evidence": canonical.get("game_runtime_evidence", {}),
        "files": file_records,
    }
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    zip_path = out / ZIP_NAME
    with ZipFile(zip_path, "w") as zf:
        add_bytes(zf, "PACK_MANIFEST.json", manifest_bytes)
        for path in all_files:
            arcname = path.relative_to(RIVAL).as_posix()
            add_bytes(zf, arcname, path.read_bytes())

    digest = sha256(zip_path)
    (out / f"{ZIP_NAME}.sha256").write_text(f"{digest}  {ZIP_NAME}\n", encoding="utf-8")
    (out / "PACK_02_RELEASE_MANIFEST.json").write_text(
        json.dumps({
            "schema": "taijifu/global-pack-release/v1",
            "signature": "Tehkné Solutions",
            "pack_id": PACK_ID,
            "version": PACK_VERSION,
            "filename": ZIP_NAME,
            "sha256": digest,
            "archive_files": len(all_files) + 1,
            "runtime_frames": 44,
            "status": "release_candidate_built_from_frozen_canonical_assets",
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("PACK02_CANONICAL=PASS frames=44/44 runtime_active=true")
    print(f"PACK02_ARCHIVE=PASS files={len(all_files) + 1}")
    print(f"PACK02_ZIP={zip_path.relative_to(ROOT).as_posix()}")
    print(f"PACK02_SHA256={digest}")
    print("PACK02=PASS")
    print("SIGNATURE=Tehkné Solutions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
