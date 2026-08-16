#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
KIT_PATH = ROOT / "production/pack04/production-reference-kit-v1.json"
SIGNATURE = "Tehkné Solutions"
PACK_ID = "PACK_04_COMBAT_REACTIONS_AND_MOTION"
TGAP_PACK_ID = "pack_04_combat_reactions_and_motion"
VERSION = "1.0.0"
RELEASE_TAG = "assets-pack-04-v1.0.0"


def fail(reason: str) -> int:
    print(f"PACK04_RC_BUILDER=BLOCKED reason={reason}")
    print(f"SIGNATURE={SIGNATURE}")
    return 2


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"json_root:{path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_png(path: Path, footline: int) -> None:
    with Image.open(path) as image:
        image.load()
        if image.size != (1024, 1024):
            raise ValueError(f"dimensions:{path}:{image.size}")
        if image.mode != "RGBA":
            raise ValueError(f"mode:{path}:{image.mode}")
        alpha = image.getchannel("A")
        lo, hi = alpha.getextrema()
        if lo != 0 or hi == 0:
            raise ValueError(f"alpha:{path}:min={lo}:max={hi}")
        bbox = alpha.getbbox()
        if bbox is None:
            raise ValueError(f"empty:{path}")
        if abs(int(bbox[3]) - footline) > 3:
            raise ValueError(f"footline:{path}:actual={bbox[3]}:expected={footline}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    try:
        kit = read_json(KIT_PATH)
        if kit.get("pack_id") != PACK_ID or int(kit.get("slot_count", 0)) != 34:
            raise ValueError("reference_kit_identity")
        if kit.get("production_policy", {}).get("art_generation_may_begin") is not True:
            raise ValueError("authoring_not_ready")

        frames_root = args.frames_root.resolve()
        output = args.output.resolve()
        if not frames_root.is_dir():
            raise ValueError("frames_root_missing")
        if output.exists():
            if not args.force:
                raise ValueError("output_exists_use_force")
            shutil.rmtree(output)
        output.mkdir(parents=True)

        assets: list[dict[str, str]] = []
        mappings: dict[str, dict[str, list[str]]] = {}
        copied: list[Path] = []
        for slot in kit["slots"]:
            fighter = str(slot["fighter"])
            state = str(slot["state"])
            filename = str(slot["filename"])
            source = frames_root / fighter / state / filename
            if not source.is_file():
                raise ValueError(f"frame_missing:{fighter}/{state}/{filename}")
            validate_png(source, int(slot["canonical_footline_y"]))
            relative = Path(fighter) / state / filename
            target = output / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            digest = sha256(target)
            rel = relative.as_posix()
            assets.append({"path": rel, "fighter": fighter, "state": state, "sha256": digest})
            mappings.setdefault(fighter, {}).setdefault(state, []).append(rel)
            copied.append(relative)

        extra_pngs = sorted(p.relative_to(frames_root).as_posix() for p in frames_root.rglob("*.png") if p.is_file())
        expected_pngs = sorted(p.as_posix() for p in copied)
        if extra_pngs != expected_pngs:
            raise ValueError(f"png_inventory_mismatch:actual={len(extra_pngs)}:expected=34")

        identity = {
            "pack_id": PACK_ID,
            "tgap_pack_id": TGAP_PACK_ID,
            "version": VERSION,
            "release_tag": RELEASE_TAG,
        }
        manifest = dict(identity)
        manifest.update({
            "schema": "tehkne/taijifu-pack04-materialization/v1",
            "asset_count": 34,
            "assets": assets,
            "signature": SIGNATURE,
        })
        runtime_map = dict(identity)
        runtime_map.update({
            "schema": "tehkne/taijifu-pack04-runtime-map/v1",
            "characters": ["lian_wu", "training_rival"],
            "states": ["block_recoil", "parry", "posture_break", "knockback", "neutral_recovery"],
            "mappings": mappings,
            "signature": SIGNATURE,
        })
        approval = dict(identity)
        approval.update({
            "schema": "tehkne/taijifu-pack04-approval/v1",
            "status": "pending",
            "human_visual_review": "pending",
            "identity_continuity": "pending",
            "weapon_continuity": "pending",
            "approved": False,
            "human_review": "PENDING",
            "reviewer": "",
            "evidence": [],
            "signature": SIGNATURE,
        })
        write_json(output / "manifest.json", manifest)
        write_json(output / "runtime-map.json", runtime_map)
        write_json(output / "approval.json", approval)

        checksum_targets = copied + [Path("manifest.json"), Path("runtime-map.json"), Path("approval.json")]
        lines = [f"{sha256(output / relative)}  {relative.as_posix()}" for relative in checksum_targets]
        (output / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")

    except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
        return fail(str(exc))

    print("PACK04_RC_BUILDER=PASS assets=34 support=4 checksums=37")
    print("PACK04_RC_APPROVAL=PASS approved=false human_review=PENDING")
    print("PACK04_RC_PROMOTION=BLOCKED human_visual_review_required=true")
    print("PACK04_RC_RUNTIME_ACTIVATION=BLOCKED")
    print(f"SIGNATURE={SIGNATURE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
