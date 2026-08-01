from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from assemble_first_playable_animation_packs import assemble_animation_packs

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


def _write_layout(root: Path, cell: int = 128) -> Path:
    target = root / "intake/first_playable/FP_CHAR_01_LIAN_WU.layout.json"
    target.parent.mkdir(parents=True, exist_ok=True)
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
    target.write_text(
        json.dumps(
            {
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
        ),
        encoding="utf-8",
    )
    return target


def _write_manifest(root: Path, cell: int = 128) -> Path:
    target = root / "production/first_playable/lian_wu/animation-pack-01.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    packs = []
    for order, (animation, frames) in enumerate(ANIMATIONS, start=1):
        packs.append(
            {
                "order": order,
                "id": f"TEST_{animation.upper()}",
                "animation": animation,
                "frames": frames,
                "source": f"{animation}.png",
            }
        )
    target.write_text(
        json.dumps(
            {
                "schema": "taijifu-first-playable-animation-pack-v1",
                "pack_id": "TEST_LIAN_WU",
                "character_id": "lian_wu",
                "cell": {
                    "width": cell,
                    "height": cell,
                    "background": "transparent",
                    "margin": 0,
                    "gutter": 0,
                },
                "final_sheet": {
                    "columns": 8,
                    "rows": 6,
                    "width": 8 * cell,
                    "height": 6 * cell,
                    "output": "intake/first_playable/FP_CHAR_01_LIAN_WU.png",
                    "layout": "intake/first_playable/FP_CHAR_01_LIAN_WU.layout.json",
                },
                "source_dir": "intake/first_playable/FP_CHAR_01_LIAN_WU.animation-packs",
                "animation_packs": packs,
            }
        ),
        encoding="utf-8",
    )
    return target


def _write_strips(root: Path, cell: int = 128) -> Path:
    source_dir = root / "intake/first_playable/FP_CHAR_01_LIAN_WU.animation-packs"
    source_dir.mkdir(parents=True, exist_ok=True)
    for animation, frames in ANIMATIONS:
        image = Image.new("RGBA", (frames * cell, cell), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        for index in range(frames):
            left = index * cell + 24
            top = 16
            right = (index + 1) * cell - 24
            bottom = cell - 8
            draw.rectangle((left, top, right, bottom), fill=(50, 110, 190, 255))
        image.save(source_dir / f"{animation}.png")
    return source_dir


def _prepare(root: Path, cell: int = 128) -> Path:
    _write_layout(root, cell)
    manifest = _write_manifest(root, cell)
    _write_strips(root, cell)
    return manifest


def test_assembles_valid_animation_packs(tmp_path: Path) -> None:
    manifest = _prepare(tmp_path)
    output = tmp_path / "assembled.png"
    report = assemble_animation_packs(
        manifest,
        repo_root=tmp_path,
        output_path=output,
    )
    assert report["passed"] is True
    assert output.exists()
    with Image.open(output) as image:
        assert image.mode == "RGBA"
        assert image.size == (1024, 768)
        reserved = image.crop((4 * 128, 5 * 128, 8 * 128, 6 * 128))
        assert reserved.getbbox() is None


def test_rejects_missing_animation_pack(tmp_path: Path) -> None:
    manifest = _prepare(tmp_path)
    (tmp_path / "intake/first_playable/FP_CHAR_01_LIAN_WU.animation-packs/guard.png").unlink()
    report = assemble_animation_packs(manifest, repo_root=tmp_path)
    assert report["passed"] is False
    assert any("pack ausente" in error for error in report["errors"])


def test_rejects_wrong_strip_dimensions(tmp_path: Path) -> None:
    manifest = _prepare(tmp_path)
    source = tmp_path / "intake/first_playable/FP_CHAR_01_LIAN_WU.animation-packs/idle.png"
    Image.new("RGBA", (500, 128), (0, 0, 0, 0)).save(source)
    report = assemble_animation_packs(manifest, repo_root=tmp_path)
    assert report["passed"] is False
    assert any("idle dimensão esperada" in error for error in report["errors"])


def test_rejects_empty_frame_inside_strip(tmp_path: Path) -> None:
    manifest = _prepare(tmp_path)
    source = tmp_path / "intake/first_playable/FP_CHAR_01_LIAN_WU.animation-packs/hit.png"
    with Image.open(source) as original:
        editable = original.copy()
    ImageDraw.Draw(editable).rectangle((128, 0, 255, 127), fill=(0, 0, 0, 0))
    editable.save(source)
    report = assemble_animation_packs(manifest, repo_root=tmp_path)
    assert report["passed"] is False
    assert any("hit frame 002 vazio" in error for error in report["errors"])


def test_rejects_opaque_strip_background(tmp_path: Path) -> None:
    manifest = _prepare(tmp_path)
    source = tmp_path / "intake/first_playable/FP_CHAR_01_LIAN_WU.animation-packs/fall.png"
    Image.new("RGBA", (2 * 128, 128), (20, 20, 20, 255)).save(source)
    report = assemble_animation_packs(manifest, repo_root=tmp_path)
    assert report["passed"] is False
    assert any("fall fundo não é suficientemente transparente" in error for error in report["errors"])


# Tehkné Solutions
