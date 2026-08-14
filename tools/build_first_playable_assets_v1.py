#!/usr/bin/env python3
"""Build the immutable Taijifu First Playable asset snapshot v1.0.0.

Composition only: no artwork is generated or transformed.
Signature: Tehkné Solutions
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
SIGNATURE = "Tehkné Solutions"
VERSION = "1.0.0"
ZIP_NAME = "TAIJIFU_FIRST_PLAYABLE_ASSETS_v1.0.0.zip"
FIXED_ZIP_TIME = (2026, 8, 14, 22, 0, 0)

LIAN_ROOT = Path("production/first_playable/lian_wu/first_playable_lot_01")
RIVAL_ROOT = Path("production/first_playable/training_rival/first_playable_lot_01")
STAGE_ROOT = Path("packs/stages/mountain_dojo_night/v1")
STAGE_RUNTIME_FILES = (
    "manifest.json",
    "background.png",
    "midground.png",
    "foreground.png",
    "collision.json",
    "lighting.json",
    "ENV01_FINAL_ART_EVIDENCE.json",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise SystemExit(f"FIRST_PLAYABLE_SNAPSHOT=BLOCKED reason={reason}")


def add_bytes(zf: ZipFile, name: str, data: bytes) -> None:
    info = ZipInfo(name, FIXED_ZIP_TIME)
    info.compress_type = ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    zf.writestr(info, data)


def component_files(root: Path) -> list[Path]:
    absolute = ROOT / root
    require(absolute.is_dir(), f"missing_component_{root.as_posix()}")
    return sorted((path for path in absolute.rglob("*") if path.is_file()), key=lambda p: p.as_posix())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="artifacts/first-playable-assets-v1")
    args = parser.parse_args()
    out = (ROOT / args.output_dir).resolve()

    lian_manifest = json.loads((ROOT / LIAN_ROOT / "work-manifest.json").read_text(encoding="utf-8"))
    rival_manifest = json.loads((ROOT / RIVAL_ROOT / "work-manifest.json").read_text(encoding="utf-8"))
    stage_manifest = json.loads((ROOT / STAGE_ROOT / "manifest.json").read_text(encoding="utf-8"))

    require(lian_manifest.get("signature") == SIGNATURE, "lian_signature")
    require(lian_manifest.get("required_frames") == 45, "lian_frame_contract")
    require(sum(lian_manifest.get("animations", {}).values()) == 45, "lian_animation_matrix")
    require(lian_manifest.get("release_tag") == "assets-pack-01-v2.0.0", "lian_release_tag")
    require(lian_manifest.get("release_sha256") == "f000de1d3a0ca452bcae88f628264a16fcb57ca5c31791dc46525e175a0cb34c", "lian_release_sha")

    require(rival_manifest.get("signature") == SIGNATURE, "rival_signature")
    require(rival_manifest.get("required_frames") == 44, "rival_frame_contract")
    require(sum(rival_manifest.get("animations", {}).values()) == 44, "rival_animation_matrix")

    require(stage_manifest.get("signature") == SIGNATURE, "stage_signature")
    require(stage_manifest.get("arena_id") == "mountain_dojo_night", "stage_id")
    require(stage_manifest.get("version") == "1.0.0", "stage_version")
    require(stage_manifest.get("status") == "art_final", "stage_status")
    require(stage_manifest.get("promotion", {}).get("canonical_ready") is True, "stage_canonical_ready")
    require(stage_manifest.get("runtime_contract", {}).get("no_procedural_placeholder") is True, "stage_no_placeholder")

    lian_files = component_files(LIAN_ROOT)
    rival_files = component_files(RIVAL_ROOT)
    stage_files = []
    for name in STAGE_RUNTIME_FILES:
        path = ROOT / STAGE_ROOT / name
        require(path.is_file(), f"stage_file_missing_{name}")
        stage_files.append(path)

    lian_png = [p for p in lian_files if p.suffix.lower() == ".png"]
    rival_png = [p for p in rival_files if p.suffix.lower() == ".png"]
    require(len(lian_png) == 45, f"lian_png_count_{len(lian_png)}")
    require(len(rival_png) == 44, f"rival_png_count_{len(rival_png)}")
    for path in lian_png + rival_png + [ROOT / STAGE_ROOT / name for name in ("background.png", "midground.png", "foreground.png")]:
        require(path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"), f"png_not_materialized_{path.relative_to(ROOT).as_posix()}")

    source_files = sorted(set(lian_files + rival_files + stage_files), key=lambda p: p.as_posix())
    records = []
    root_material = bytearray()
    for path in source_files:
        rel = path.relative_to(ROOT).as_posix()
        digest = sha256_file(path)
        size = path.stat().st_size
        records.append({"file": rel, "bytes": size, "sha256": digest})
        root_material.extend(rel.encode("utf-8"))
        root_material.extend(b"\0")
        root_material.extend(digest.encode("ascii"))
        root_material.extend(b"\n")

    content_sha256 = sha256_bytes(bytes(root_material))
    snapshot_manifest = {
        "schema": "tehkne/taijifu-first-playable-snapshot/v1",
        "signature": SIGNATURE,
        "snapshot_id": "taijifu_first_playable_assets",
        "version": VERSION,
        "status": "release_candidate",
        "composition": {
            "lian_wu": {
                "release_tag": "assets-pack-01-v2.0.0",
                "release_sha256": "f000de1d3a0ca452bcae88f628264a16fcb57ca5c31791dc46525e175a0cb34c",
                "frames": 45,
                "animations": 10,
            },
            "training_rival": {
                "release_tag": "assets-pack-02-v1.0.0",
                "frames": 44,
                "animations": 10,
            },
            "mountain_dojo_night": {
                "release_tag": "assets-pack-03-v1.0.0",
                "version": "1.0.0",
                "status": "art_final",
                "canonical_ready": True,
                "layers": 3,
            },
        },
        "fighter_frames": 89,
        "fighter_animations": 20,
        "stage_layers": 3,
        "content_sha256": content_sha256,
        "files": records,
    }
    manifest_bytes = (json.dumps(snapshot_manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    out.mkdir(parents=True, exist_ok=True)
    zip_path = out / ZIP_NAME
    with ZipFile(zip_path, "w") as archive:
        add_bytes(archive, "FIRST_PLAYABLE_SNAPSHOT_MANIFEST.json", manifest_bytes)
        for path in source_files:
            add_bytes(archive, path.relative_to(ROOT).as_posix(), path.read_bytes())

    zip_sha256 = sha256_file(zip_path)
    (out / f"{ZIP_NAME}.sha256").write_text(f"{zip_sha256}  {ZIP_NAME}\n", encoding="utf-8")
    release_manifest = {
        "schema": "tehkne/taijifu-first-playable-snapshot-release/v1",
        "signature": SIGNATURE,
        "snapshot_id": "taijifu_first_playable_assets",
        "version": VERSION,
        "filename": ZIP_NAME,
        "sha256": zip_sha256,
        "content_sha256": content_sha256,
        "archive_files": len(source_files) + 1,
        "fighter_frames": 89,
        "fighter_animations": 20,
        "stage_layers": 3,
        "status": "release_candidate_built_from_released_canonical_components",
    }
    (out / "FIRST_PLAYABLE_RELEASE_MANIFEST.json").write_text(
        json.dumps(release_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("FIRST_PLAYABLE_SNAPSHOT_COMPONENTS=PASS lian=45 rival=44 stage_layers=3")
    print("FIRST_PLAYABLE_SNAPSHOT_ART=PASS frames=89 animations=20")
    print("FIRST_PLAYABLE_SNAPSHOT_STAGE=PASS arena=mountain_dojo_night art_final=true canonical_ready=true")
    print(f"FIRST_PLAYABLE_SNAPSHOT_CONTENT_SHA256={content_sha256}")
    print(f"FIRST_PLAYABLE_SNAPSHOT_SHA256={zip_sha256}")
    print(f"FIRST_PLAYABLE_SNAPSHOT_FILES={len(source_files) + 1}")
    print("FIRST_PLAYABLE_SNAPSHOT=PASS")
    print(f"SIGNATURE={SIGNATURE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
