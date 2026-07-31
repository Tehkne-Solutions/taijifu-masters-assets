#!/usr/bin/env python3
"""Recorta spritesheets aprovados nos 44 frames canônicos do First Playable.

Exige grade sem gutter, canvas RGBA e layout explícito. Não aprova arte.
Assinatura: Tehkné Solutions
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Pillow é obrigatório: python -m pip install Pillow") from exc

ROOT = Path(__file__).resolve().parents[1]
CHARACTERS = {
    "lian_wu": {
        "prefix": "char_lian_wu",
        "output": ROOT / "production/first_playable/lian_wu/first_playable_lot_01/animations",
    },
    "training_rival": {
        "prefix": "char_training_rival",
        "output": ROOT / "production/first_playable/training_rival/first_playable_lot_01/animations",
    },
}
EXPECTED = {
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


def load_layout(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {"character", "cell_width", "cell_height", "columns", "rows", "frames"}
    missing = sorted(required - data.keys())
    if missing:
        raise ValueError(f"layout incompleto: {', '.join(missing)}")
    if data["character"] not in CHARACTERS:
        raise ValueError(f"personagem inválido: {data['character']}")
    if data.get("gutter", 0) != 0 or data.get("margin", 0) != 0:
        raise ValueError("spritesheet deve usar gutter=0 e margin=0")
    return data


def validate_frame_map(layout: dict) -> None:
    frames = layout["frames"]
    if len(frames) != 44:
        raise ValueError(f"layout deve mapear 44 frames; recebeu {len(frames)}")
    seen: set[tuple[str, int]] = set()
    cells: set[tuple[int, int]] = set()
    counts = {name: 0 for name in EXPECTED}
    for item in frames:
        animation = item.get("animation")
        index = int(item.get("index", 0))
        col = int(item.get("column", -1))
        row = int(item.get("row", -1))
        if animation not in EXPECTED:
            raise ValueError(f"animação inválida: {animation}")
        if not (1 <= index <= EXPECTED[animation]):
            raise ValueError(f"índice inválido: {animation} f{index:03d}")
        if not (0 <= col < int(layout["columns"])) or not (0 <= row < int(layout["rows"])):
            raise ValueError(f"célula fora da grade: ({col}, {row})")
        key = (animation, index)
        cell = (col, row)
        if key in seen:
            raise ValueError(f"frame duplicado: {animation} f{index:03d}")
        if cell in cells:
            raise ValueError(f"célula reutilizada: ({col}, {row})")
        seen.add(key)
        cells.add(cell)
        counts[animation] += 1
    if counts != EXPECTED:
        raise ValueError(f"matriz divergente: {counts}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sheet", type=Path)
    parser.add_argument("layout", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    layout = load_layout(args.layout)
    validate_frame_map(layout)
    character = layout["character"]
    config = CHARACTERS[character]
    output = args.output or config["output"]
    cell_w = int(layout["cell_width"])
    cell_h = int(layout["cell_height"])
    columns = int(layout["columns"])
    rows = int(layout["rows"])
    if not (128 <= cell_w <= 1024 and 128 <= cell_h <= 1024):
        raise ValueError("células devem ficar entre 128×128 e 1024×1024")

    with Image.open(args.sheet) as source:
        source.load()
        if source.mode != "RGBA":
            raise ValueError(f"spritesheet deve ser RGBA; modo atual: {source.mode}")
        expected_size = (columns * cell_w, rows * cell_h)
        if source.size != expected_size:
            raise ValueError(f"dimensão esperada {expected_size}; recebida {source.size}")
        if args.dry_run:
            print(f"OK: {character}, 44 frames, grade {columns}×{rows}, célula {cell_w}×{cell_h}")
            return 0

        if output.exists() and any(output.rglob("*.png")):
            if not args.replace:
                raise ValueError("destino já contém PNGs; use --replace explicitamente")
            shutil.rmtree(output)

        for item in layout["frames"]:
            animation = item["animation"]
            index = int(item["index"])
            col = int(item["column"])
            row = int(item["row"])
            frame = source.crop((col * cell_w, row * cell_h, (col + 1) * cell_w, (row + 1) * cell_h))
            folder = output / animation
            folder.mkdir(parents=True, exist_ok=True)
            filename = f"{config['prefix']}__{animation}__f{index:03d}.png"
            frame.save(folder / filename, format="PNG", optimize=False)

    print(f"Importados 44 frames para {output}")
    print("Status artístico permanece pendente de revisão no Godot.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        raise SystemExit(2)
