#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

EXPECTED_FRONT_CLEAN_SHA = "0e435757b5c8a114f3ba91653f79bc86db51ee9cf3bfb74c529efed5d4ff7ab5"
EXPECTED_COMBAT_SHA = "c8e6cd1feece7c2a54cf2279085c2a4bb33338dd6a3dcb3e4d5a2402b537631c"
SLOTS = (
    "torso_underpaint_complete",
    "arm_left_complete",
    "arm_right_complete",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_rgba(path: Path) -> np.ndarray:
    img = Image.open(path).convert("RGBA")
    if img.size != (1024, 1024):
        raise SystemExit(f"invalid canvas for {path}: {img.size}")
    return np.array(img)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kit", type=Path, required=True)
    parser.add_argument("--neutral", type=Path, required=True)
    parser.add_argument("--combat", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)

    neutral_sha = sha256(args.neutral)
    combat_sha = sha256(args.combat)
    if neutral_sha != EXPECTED_FRONT_CLEAN_SHA:
        raise SystemExit(f"neutral/front-clean hash mismatch: {neutral_sha}")
    if combat_sha != EXPECTED_COMBAT_SHA:
        raise SystemExit(f"combat hash mismatch: {combat_sha}")

    canonical_path = args.kit / "canonical-source.png"
    canonical = load_rgba(canonical_path)
    neutral = load_rgba(args.neutral)
    combat = load_rgba(args.combat)

    if not np.array_equal(combat, canonical):
        raise SystemExit("combat stance is not pixel-exact to authoring-kit canonical source")

    report = {
        "schema": "tehkne/taijifu-lian-wu-layered-master-source-recovery/v1",
        "signature": "Tehkné Solutions",
        "status": "PARTIAL_SOURCE_RECOVERY_ONLY",
        "provenance": {
            "neutral_is_canonical_front_clean": True,
            "neutral_sha256": neutral_sha,
            "combat_is_authoring_kit_canonical": True,
            "combat_sha256": combat_sha,
            "automatic_inpainting_used": False,
            "generative_model_used": False,
        },
        "slots": {},
        "totals": {},
        "gates": {
            "visible_canonical_pixels_locked": True,
            "authored_layers_complete": False,
            "contact_absorb_allowed": False,
            "pack04_promotion_allowed": False,
            "counts_toward_pack04": False,
        },
    }

    total_hidden = 0
    total_recovered = 0
    total_remaining = 0

    for slot in SLOTS:
        authoring_mask = np.array(Image.open(args.kit / f"{slot}_authoring_mask.png").convert("L")) > 0
        locked_mask = np.array(Image.open(args.kit / f"{slot}_locked_visible_mask.png").convert("L")) > 0

        hidden_target = authoring_mask & (canonical[:, :, 3] == 0)
        recovered = hidden_target & (neutral[:, :, 3] > 0)
        remaining = hidden_target & ~recovered

        partial = np.zeros_like(canonical)
        partial[recovered] = neutral[recovered]
        preview = canonical.copy()
        preview[recovered] = neutral[recovered]

        partial_path = args.out / f"{slot}__recovered_partial.png"
        preview_path = args.out / f"{slot}__recovered_preview.png"
        Image.fromarray(partial, "RGBA").save(partial_path, optimize=True)
        Image.fromarray(preview, "RGBA").save(preview_path, optimize=True)

        hidden_px = int(hidden_target.sum())
        recovered_px = int(recovered.sum())
        remaining_px = int(remaining.sum())
        locked_overlap = int((recovered & locked_mask).sum())
        if locked_overlap != 0:
            raise SystemExit(f"locked pixel overlap detected for {slot}: {locked_overlap}")

        total_hidden += hidden_px
        total_recovered += recovered_px
        total_remaining += remaining_px

        report["slots"][slot] = {
            "hidden_target_px": hidden_px,
            "recovered_from_front_clean_px": recovered_px,
            "remaining_hidden_px": remaining_px,
            "recovery_pct": round((recovered_px / hidden_px * 100.0) if hidden_px else 0.0, 3),
            "locked_overlap_px": locked_overlap,
            "partial_sha256": sha256(partial_path),
        }

    report["totals"] = {
        "hidden_target_px": total_hidden,
        "recovered_real_hidden_px": total_recovered,
        "remaining_hidden_px": total_remaining,
        "recovery_pct": round(total_recovered / total_hidden * 100.0, 3),
    }

    (args.out / "source-recovery-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("LIAN_WU_LAYERED_MASTER_SOURCE_RECOVERY=PASS")
    print(f"CANONICAL_FRONT_CLEAN_SHA={neutral_sha}")
    print(f"RECOVERED_REAL_HIDDEN_PIXELS={total_recovered}")
    print(f"REMAINING_HIDDEN_PIXELS={total_remaining}")
    print("AUTHORED_LAYERS_COMPLETE=false")
    print("PACK04_PROMOTION_ALLOWED=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
