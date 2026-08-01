#!/usr/bin/env python3
"""Prepara os dois layouts canônicos do batch artístico do First Playable.

Assinatura: Tehkné Solutions
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "tools" / "generate_first_playable_layout.py"
INTAKE = ROOT / "intake" / "first_playable"

PACKS = [
    ("lian_wu", "FP_CHAR_01_LIAN_WU.layout.json"),
    ("training_rival", "FP_CHAR_02_TRAINING_RIVAL.layout.json"),
]


def main() -> int:
    INTAKE.mkdir(parents=True, exist_ok=True)
    for character, filename in PACKS:
        command = [
            sys.executable,
            str(GENERATOR),
            character,
            str(INTAKE / filename),
            "--cell-width",
            "512",
            "--cell-height",
            "512",
            "--columns",
            "8",
        ]
        subprocess.run(command, cwd=ROOT, check=True)
    print("FIRST_PLAYABLE_GENERATION_BATCH_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
