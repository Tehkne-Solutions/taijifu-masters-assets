#!/usr/bin/env python3
"""Gera o layout canônico de 44 células para spritesheets do First Playable.

Assinatura: Tehkné Solutions
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ANIMATIONS = [
    ("idle", 6),
    ("run", 8),
    ("jump_start", 3),
    ("airborne", 2),
    ("fall", 2),
    ("attack_light", 6),
    ("guard", 3),
    ("dodge", 5),
    ("hit", 3),
    ("ko", 6),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("character", choices=["lian_wu", "training_rival"])
    parser.add_argument("output", type=Path)
    parser.add_argument("--cell-width", type=int, default=512)
    parser.add_argument("--cell-height", type=int, default=512)
    parser.add_argument("--columns", type=int, default=8)
    args = parser.parse_args()
    if not 128 <= args.cell_width <= 1024 or not 128 <= args.cell_height <= 1024:
        raise SystemExit("célula deve ficar entre 128 e 1024 px")
    if args.columns < 1:
        raise SystemExit("columns deve ser maior que zero")

    frames = []
    cursor = 0
    for animation, count in ANIMATIONS:
        for index in range(1, count + 1):
            frames.append({
                "animation": animation,
                "index": index,
                "column": cursor % args.columns,
                "row": cursor // args.columns,
            })
            cursor += 1
    rows = (cursor + args.columns - 1) // args.columns
    payload = {
        "schema": "taijifu-first-playable-spritesheet-layout-v1",
        "character": args.character,
        "cell_width": args.cell_width,
        "cell_height": args.cell_height,
        "columns": args.columns,
        "rows": rows,
        "gutter": 0,
        "margin": 0,
        "frames": frames,
        "signature": "Tehkné Solutions",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Layout criado: {args.output} ({args.columns}×{rows}, 44 frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
