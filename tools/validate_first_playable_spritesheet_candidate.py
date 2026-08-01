#!/usr/bin/env python3
"""Valida spritesheets candidatos antes do recorte do First Playable.

Este gate não aprova direção artística. Ele bloqueia arquivos estruturalmente
incompatíveis com o batch canônico: dimensão, RGBA, transparência, células
usadas vazias e células reservadas contaminadas.

Assinatura: Tehkné Solutions
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Pillow é obrigatório: python -m pip install Pillow") from exc

from import_first_playable_spritesheet import load_layout, validate_frame_map


def _alpha_stats(image: Image.Image, threshold: int) -> tuple[int, int, float]:
    alpha = image.getchannel("A")
    total = image.width * image.height
    occupied = sum(count for value, count in alpha.getcolors(maxcolors=256) or [] if value > threshold)
    transparent = total - occupied
    return occupied, transparent, occupied / max(1, total)


def validate_candidate(
    sheet_path: Path,
    layout_path: Path,
    *,
    alpha_threshold: int = 8,
    min_used_alpha_ratio: float = 0.002,
    min_sheet_transparent_ratio: float = 0.10,
) -> dict[str, Any]:
    layout = load_layout(layout_path)
    validate_frame_map(layout)

    columns = int(layout["columns"])
    rows = int(layout["rows"])
    cell_width = int(layout["cell_width"])
    cell_height = int(layout["cell_height"])
    expected_size = (columns * cell_width, rows * cell_height)
    used_cells = {(int(item["column"]), int(item["row"])) for item in layout["frames"]}
    all_cells = {(column, row) for row in range(rows) for column in range(columns)}
    unused_cells = sorted(all_cells - used_cells, key=lambda item: (item[1], item[0]))

    errors: list[str] = []
    cells: list[dict[str, Any]] = []

    with Image.open(sheet_path) as source:
        source.load()
        if source.mode != "RGBA":
            errors.append(f"spritesheet deve ser RGBA; modo atual: {source.mode}")
        if source.size != expected_size:
            errors.append(f"dimensão esperada {expected_size}; recebida {source.size}")

        if source.mode == "RGBA" and source.size == expected_size:
            _, transparent_pixels, sheet_alpha_ratio = _alpha_stats(source, alpha_threshold)
            transparent_ratio = transparent_pixels / max(1, source.width * source.height)
            if transparent_ratio < min_sheet_transparent_ratio:
                errors.append(
                    "fundo global não é suficientemente transparente: "
                    f"{transparent_ratio:.4f} < {min_sheet_transparent_ratio:.4f}"
                )

            for row in range(rows):
                for column in range(columns):
                    box = (
                        column * cell_width,
                        row * cell_height,
                        (column + 1) * cell_width,
                        (row + 1) * cell_height,
                    )
                    cell = source.crop(box)
                    occupied, _, ratio = _alpha_stats(cell, alpha_threshold)
                    is_used = (column, row) in used_cells
                    cells.append(
                        {
                            "column": column,
                            "row": row,
                            "used": is_used,
                            "occupied_pixels": occupied,
                            "alpha_ratio": round(ratio, 8),
                        }
                    )
                    if is_used and ratio < min_used_alpha_ratio:
                        errors.append(
                            f"célula usada vazia ou quase vazia: ({column}, {row}) "
                            f"alpha_ratio={ratio:.6f}"
                        )
                    if not is_used and occupied > 0:
                        errors.append(
                            f"célula reservada deve ser totalmente transparente: "
                            f"({column}, {row}) possui {occupied} pixels"
                        )
        else:
            sheet_alpha_ratio = 0.0
            transparent_ratio = 0.0

    report = {
        "schema": "taijifu-first-playable-spritesheet-candidate-report-v1",
        "sheet": str(sheet_path),
        "layout": str(layout_path),
        "character": layout["character"],
        "expected_size": list(expected_size),
        "grid": {"columns": columns, "rows": rows},
        "used_cells": len(used_cells),
        "unused_cells": [list(cell) for cell in unused_cells],
        "sheet_alpha_ratio": round(sheet_alpha_ratio, 8),
        "sheet_transparent_ratio": round(transparent_ratio, 8),
        "thresholds": {
            "alpha": alpha_threshold,
            "min_used_alpha_ratio": min_used_alpha_ratio,
            "min_sheet_transparent_ratio": min_sheet_transparent_ratio,
        },
        "cells": cells,
        "errors": errors,
        "passed": not errors,
        "signature": "Tehkné Solutions",
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sheet", type=Path)
    parser.add_argument("layout", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--alpha-threshold", type=int, default=8)
    parser.add_argument("--min-used-alpha-ratio", type=float, default=0.002)
    parser.add_argument("--min-sheet-transparent-ratio", type=float, default=0.10)
    args = parser.parse_args()

    try:
        report = validate_candidate(
            args.sheet,
            args.layout,
            alpha_threshold=args.alpha_threshold,
            min_used_alpha_ratio=args.min_used_alpha_ratio,
            min_sheet_transparent_ratio=args.min_sheet_transparent_ratio,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if report["passed"]:
        print(
            "FIRST_PLAYABLE_SPRITESHEET_CANDIDATE_OK "
            f"{report['character']} {report['used_cells']}/44"
        )
        return 0

    for error in report["errors"]:
        print(f"ERRO: {error}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
