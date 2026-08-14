#!/usr/bin/env python3
"""Build the canonical PACK 03 Mountain Dojo Night release deterministically."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

SIGNATURE = "Tehkné Solutions"
PACK_ID = "pack_03_mountain_dojo_night"
VERSION = "1.0.0"
STAGE_ROOT = Path("packs/stages/mountain_dojo_night/v1")
ZIP_NAME = "PACK_03_MOUNTAIN_DOJO_NIGHT_FINAL_v1.0.0.zip"
MANIFEST_NAME = "PACK_03_RELEASE_MANIFEST.json"
FIXED_DT = (1980, 1, 1, 0, 0, 0)

REQUIRED = [
    "background.png",
    "midground.png",
    "foreground.png",
    "collision.json",
    "lighting.json",
    "manifest.json",
    "ENV01_FINAL_ART_CONTRACT.json",
    "ENV01_LAYER_PRODUCTION_SPEC.json",
    "ENV01_CANDIDATE_EVIDENCE.json",
    "ENV01_FINAL_ART_EVIDENCE.json",
    "ENV01_ACCEPTANCE.txt",
    "ENV01_REVIEW_STATES.txt",
    "C33_RECOVERY_EVIDENCE.json",
    "C33_ART_SOURCE.md",
]

EXPECTED_LAYER_SHA256 = {
    "background.png": "dea8326025e65dcfd12bfa7073f0c666b37f267580b946649a6e6010b71269d9",
    "midground.png": "000b550881f334ac6cf60d8f567ca051c85ccb61f4fd1e788bf3fcccef6ba907",
    "foreground.png": "d7741b66dc15a16ad5c58d5f6b3fb9344b502f05bdac97d871dbde495de9430d",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_contract() -> None:
    manifest = json.loads((STAGE_ROOT / "manifest.json").read_text(encoding="utf-8-sig"))
    evidence = json.loads((STAGE_ROOT / "ENV01_FINAL_ART_EVIDENCE.json").read_text(encoding="utf-8-sig"))
    candidate = json.loads((STAGE_ROOT / "ENV01_CANDIDATE_EVIDENCE.json").read_text(encoding="utf-8-sig"))

    if manifest.get("signature") != SIGNATURE or manifest.get("arena_id") != "mountain_dojo_night":
        raise SystemExit("PACK03_RELEASE=BLOCKED reason=manifest_identity")
    if manifest.get("version") != VERSION or manifest.get("status") != "art_final":
        raise SystemExit("PACK03_RELEASE=BLOCKED reason=manifest_not_final")
    if manifest.get("promotion", {}).get("canonical_ready") is not True:
        raise SystemExit("PACK03_RELEASE=BLOCKED reason=canonical_not_ready")
    if evidence.get("signature") != SIGNATURE or evidence.get("promotion_decision") != "PASS":
        raise SystemExit("PACK03_RELEASE=BLOCKED reason=final_evidence")
    if evidence.get("godot_runtime_capture") != "PASS" or evidence.get("manual_visual_review") != "PASS":
        raise SystemExit("PACK03_RELEASE=BLOCKED reason=review_not_pass")
    required_states = {"neutral_duo", "physical_hit", "critical_posture_break", "elemental_state"}
    if not required_states.issubset(set(evidence.get("reviewed_states", []))):
        raise SystemExit("PACK03_RELEASE=BLOCKED reason=review_states")
    if candidate.get("art_pass", {}).get("version") != "v2.1":
        raise SystemExit("PACK03_RELEASE=BLOCKED reason=art_pass")

    for name in REQUIRED:
        if not (STAGE_ROOT / name).is_file():
            raise SystemExit(f"PACK03_RELEASE=BLOCKED reason=missing file={name}")

    for name, expected in EXPECTED_LAYER_SHA256.items():
        actual = sha256((STAGE_ROOT / name).read_bytes())
        if actual != expected:
            raise SystemExit(
                f"PACK03_RELEASE=BLOCKED reason=layer_hash file={name} actual={actual} expected={expected}"
            )
        frozen = candidate.get("layers", {}).get(name, {}).get("sha256")
        if frozen != expected:
            raise SystemExit(f"PACK03_RELEASE=BLOCKED reason=candidate_hash file={name}")


def write_deterministic_zip(output: Path) -> list[dict]:
    records: list[dict] = []
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for name in sorted(REQUIRED):
            source = STAGE_ROOT / name
            data = source.read_bytes()
            arcname = f"PACK_03_MOUNTAIN_DOJO_NIGHT_FINAL_v1.0.0/{name}"
            info = zipfile.ZipInfo(arcname, FIXED_DT)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            zf.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
            records.append({"file": name, "bytes": len(data), "sha256": sha256(data)})
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="artifacts/pack03")
    args = parser.parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    validate_contract()
    zip_path = out_dir / ZIP_NAME
    records = write_deterministic_zip(zip_path)
    digest = sha256(zip_path.read_bytes())
    checksum_path = out_dir / f"{ZIP_NAME}.sha256"
    checksum_path.write_text(f"{digest}  {ZIP_NAME}\n", encoding="utf-8")

    release_manifest = {
        "schema": "tehkne/taijifu-pack-release/v1",
        "signature": SIGNATURE,
        "pack_id": PACK_ID,
        "arena_id": "mountain_dojo_night",
        "version": VERSION,
        "tag": "assets-pack-03-v1.0.0",
        "artifact": ZIP_NAME,
        "artifact_sha256": digest,
        "file_count": len(records),
        "files": records,
        "source": {
            "asset_art_pass": "v2.1",
            "final_manifest_status": "art_final",
            "canonical_ready": True,
            "evidence": "ENV01_FINAL_ART_EVIDENCE.json",
        },
    }
    (out_dir / MANIFEST_NAME).write_text(
        json.dumps(release_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"PACK03_RELEASE_FILE_COUNT=PASS files={len(records)}")
    print(f"PACK03_RELEASE_SHA256={digest}")
    print(f"PACK03_RELEASE_ARTIFACT={zip_path.as_posix()}")
    print("PACK03=PASS")
    print(f"SIGNATURE={SIGNATURE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
