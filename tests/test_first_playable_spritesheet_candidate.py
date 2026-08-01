from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from validate_first_playable_spritesheet_candidate import validate_candidate

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


def _write_layout(path: Path, cell: int = 128) -> Path:
    frames = []
    cursor = 0
    for animation, count in ANIMATIONS:
        for index in range(1, count + 1):
            frames.append(
                {
                    "animation": animation,
                    "index": index,
                    "column": cursor % 8,
                    "row": cursor // 8,
                }
            )
            cursor += 1
    payload = {
        "schema": "taijifu-first-playable-spritesheet-layout-v1",
        "character": "lian_wu",
        "cell_width": cell,
        "cell_height": cell,
        "columns": 8,
        "rows": 6,
        "gutter": 0,
        "margin": 0,
        "frames": frames,
        "signature": "Tehkné Solutions",
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_valid_sheet(path: Path, cell: int = 128) -> Path:
    image = Image.new("RGBA", (8 * cell, 6 * cell), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    for cursor in range(44):
        column = cursor % 8
        row = cursor // 8
        left = column * cell + 24
        top = row * cell + 16
        right = (column + 1) * cell - 24
        bottom = (row + 1) * cell - 8
        draw.rectangle((left, top, right, bottom), fill=(40, 90, 160, 255))
    image.save(path)
    return path


def test_accepts_valid_candidate(tmp_path: Path) -> None:
    layout = _write_layout(tmp_path / "layout.json")
    sheet = _write_valid_sheet(tmp_path / "sheet.png")
    report = validate_candidate(sheet, layout)
    assert report["passed"] is True
    assert report["used_cells"] == 44
    assert report["unused_cells"] == [[4, 5], [5, 5], [6, 5], [7, 5]]


def test_rejects_wrong_dimensions(tmp_path: Path) -> None:
    layout = _write_layout(tmp_path / "layout.json")
    sheet = tmp_path / "sheet.png"
    Image.new("RGBA", (900, 700), (0, 0, 0, 0)).save(sheet)
    report = validate_candidate(sheet, layout)
    assert report["passed"] is False
    assert any("dimensão esperada" in error for error in report["errors"])


def test_rejects_opaque_background(tmp_path: Path) -> None:
    layout = _write_layout(tmp_path / "layout.json")
    sheet = tmp_path / "sheet.png"
    Image.new("RGBA", (1024, 768), (40, 40, 40, 255)).save(sheet)
    report = validate_candidate(sheet, layout)
    assert report["passed"] is False
    assert any("fundo global" in error for error in report["errors"])


def test_rejects_empty_used_cell(tmp_path: Path) -> None:
    layout = _write_layout(tmp_path / "layout.json")
    sheet = _write_valid_sheet(tmp_path / "sheet.png")
    with Image.open(sheet) as image:
        editable = image.copy()
    ImageDraw.Draw(editable).rectangle((0, 0, 127, 127), fill=(0, 0, 0, 0))
    editable.save(sheet)
    report = validate_candidate(sheet, layout)
    assert report["passed"] is False
    assert any("célula usada vazia" in error for error in report["errors"])


def test_rejects_content_in_reserved_cell(tmp_path: Path) -> None:
    layout = _write_layout(tmp_path / "layout.json")
    sheet = _write_valid_sheet(tmp_path / "sheet.png")
    with Image.open(sheet) as image:
        editable = image.copy()
    draw = ImageDraw.Draw(editable)
    draw.rectangle((4 * 128 + 20, 5 * 128 + 20, 4 * 128 + 80, 5 * 128 + 100), fill=(255, 0, 0, 255))
    editable.save(sheet)
    report = validate_candidate(sheet, layout)
    assert report["passed"] is False
    assert any("célula reservada" in error for error in report["errors"])


# Tehkné Solutions
