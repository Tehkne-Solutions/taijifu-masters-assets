#!/usr/bin/env python3
"""Block Lian Wu Candidate 02 until the canonical binary references exist and are hashed."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTAKE_PATH = ROOT / "production/first_playable/lian_wu/character_lock_v1/candidate-02-intake.json"
REFERENCE_ROOT = ROOT / "production/first_playable/lian_wu/canonical_reference_v1"
REQUIRED = [
    Path("source/char_lian_wu__master_raw.png"),
    Path("turnaround/char_lian_wu__front_raw.png"),
    Path("turnaround/char_lian_wu__side_left_raw.png"),
    Path("turnaround/char_lian_wu__back_raw.png"),
    Path("turnaround/char_lian_wu__side_right_raw.png"),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_png(path: Path) -> bool:
    try:
        return path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    except OSError:
        return False


def main() -> int:
    if not INTAKE_PATH.is_file():
        print("VM01_A1_CANDIDATE_02_INPUTS=FAIL missing intake manifest")
        return 2

    intake = json.loads(INTAKE_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []
    hashes: dict[str, str] = {}

    for relative in REQUIRED:
        path = REFERENCE_ROOT / relative
        if not path.is_file():
            errors.append(f"missing {relative.as_posix()}")
            continue
        if not is_png(path):
            errors.append(f"not a PNG {relative.as_posix()}")
            continue
        hashes[relative.as_posix()] = sha256(path)

    generation = intake.get("generation_policy", {})
    if generation.get("text_only_regeneration_allowed") is not False:
        errors.append("text-only regeneration must remain forbidden")
    if generation.get("canonical_images_required_before_generation") is not True:
        errors.append("canonical images must be required before generation")

    if errors:
        print("VM01_A1_CANDIDATE_02_INPUTS=BLOCKED")
        for error in errors:
            print(f"- {error}")
        return 1

    print("VM01_A1_CANDIDATE_02_INPUTS=PASS")
    for path, digest in sorted(hashes.items()):
        print(f"{path} sha256={digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
