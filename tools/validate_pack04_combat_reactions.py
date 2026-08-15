#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "packs/characters/combat_reactions/v1/pack-manifest.json"
BASE = MANIFEST.parent
STATES = {
    "block_recoil": 3,
    "parry": 3,
    "posture_break": 4,
    "knockback": 4,
    "neutral_recovery": 3,
}
CHARACTERS = {
    "lian_wu": 969,
    "training_rival": 970,
}


def block(reason: str) -> int:
    print(f"PACK04_COMBAT_REACTIONS=BLOCKED {reason}")
    return 2


def expected_paths() -> list[tuple[str, str, int, Path]]:
    rows: list[tuple[str, str, int, Path]] = []
    for character in CHARACTERS:
        for state, count in STATES.items():
            for frame in range(1, count + 1):
                name = f"char_{character}__{state}__f{frame:02d}.png"
                rows.append((character, state, frame, BASE / character / state / name))
    return rows


def main() -> int:
    if not MANIFEST.is_file():
        return block("manifest_missing")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("pack_id") != "PACK_04_COMBAT_REACTIONS_AND_MOTION":
        return block("pack_id")
    if manifest.get("signature") != "Tehkné Solutions":
        return block("signature")
    if int(manifest.get("frame_budget", {}).get("total_new_frames", 0)) != 34:
        return block("frame_budget")
    if manifest.get("promotion", {}).get("canonical_ready") is not False:
        return block("premature_canonical_ready")
    if manifest.get("promotion", {}).get("release_allowed") is not False:
        return block("premature_release_allowed")

    rows = expected_paths()
    missing = [path.relative_to(ROOT).as_posix() for _, _, _, path in rows if not path.is_file()]
    if missing:
        print(f"PACK04_REQUIRED_FILES=BLOCKED present={34-len(missing)}/34 missing={len(missing)}")
        for item in missing[:10]:
            print(f"PACK04_MISSING={item}")
        if len(missing) > 10:
            print(f"PACK04_MISSING_MORE={len(missing)-10}")
        return block("authored_pngs_missing")

    state_bounds: dict[tuple[str, str], list[tuple[int, int]]] = {}
    for character, state, frame, path in rows:
        try:
            with Image.open(path) as image:
                image.load()
                if image.size != (1024, 1024):
                    return block(f"dimensions={path.relative_to(ROOT)}:{image.size}")
                if image.mode != "RGBA":
                    return block(f"mode={path.relative_to(ROOT)}:{image.mode}")
                alpha = image.getchannel("A")
                lo, hi = alpha.getextrema()
                if lo != 0:
                    return block(f"alpha_background_not_transparent={path.relative_to(ROOT)} min={lo}")
                if hi == 0:
                    return block(f"empty_frame={path.relative_to(ROOT)}")
                bbox = alpha.getbbox()
                if bbox is None:
                    return block(f"empty_bbox={path.relative_to(ROOT)}")
                left, top, right, bottom = bbox
                expected_footline = CHARACTERS[character]
                if abs(bottom - expected_footline) > 3:
                    return block(
                        f"footline={path.relative_to(ROOT)} actual={bottom} expected={expected_footline}"
                    )
                state_bounds.setdefault((character, state), []).append((right - left, bottom - top))
        except Exception as exc:
            return block(f"png_read={path.relative_to(ROOT)}:{exc}")

    # Bounds consistency is evaluated within a single reaction state. Across states,
    # posture break and knockback are intentionally allowed to change silhouette height.
    for (character, state), bounds in state_bounds.items():
        widths = [w for w, _ in bounds]
        heights = [h for _, h in bounds]
        for values, axis in ((widths, "width"), (heights, "height")):
            smallest = max(1, min(values))
            largest = max(values)
            variation = (largest - smallest) / smallest
            if variation > 0.08:
                return block(
                    f"bounds_variation={character}/{state}/{axis}:{variation:.4f}>0.08"
                )

    print("PACK04_REQUIRED_FILES=PASS 34/34")
    print("PACK04_RGBA=PASS")
    print("PACK04_ALPHA=PASS")
    print("PACK04_FOOTLINE=PASS tolerance=3px")
    print("PACK04_STATE_BOUNDS=PASS max_variation=8pct")
    print("PACK04_ART_INTAKE=PASS")
    print("PACK04_PROMOTION=BLOCKED runtime_integration_and_human_review_pending")
    print("SIGNATURE=Tehkné Solutions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
