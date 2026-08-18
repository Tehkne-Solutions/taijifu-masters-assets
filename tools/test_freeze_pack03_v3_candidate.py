#!/usr/bin/env python3
"""Synthetic contract tests for PACK 03 v3 candidate freezing."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

MODULE_PATH = Path(__file__).with_name("freeze_pack03_v3_candidate.py")
spec = importlib.util.spec_from_file_location("pack03_freezer", MODULE_PATH)
assert spec and spec.loader
freezer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(freezer)


def write_status(root: Path) -> None:
    payload = {
        "schema": "tehkne/taijifu-pack03-art-review/v3",
        "signature": "Tehkné Solutions",
        "arena_id": "mountain_dojo_night",
        "candidate_id": "pack03_mountain_dojo_night_art_pass_v3",
        "status": "art_pending",
        "layers": {
            "background.png": {"state": "missing", "sha256": None},
            "midground.png": {"state": "missing", "sha256": None},
            "foreground.png": {"state": "missing", "sha256": None},
        },
        "automated_validation": "pending",
        "foreground_transparency": "pending",
        "safe_zone": "pending",
        "manual_visual_review": "pending",
        "godot_runtime_capture": "pending",
        "c30_materialization": "pending",
        "stage_premium_runtime_review": "pending",
        "vertical_slice_asset_truth": "pending",
        "promotion": False,
        "canonical_replacement_authorized": False,
    }
    (root / "review-status.json").write_text(json.dumps(payload), encoding="utf-8")


def bind(root: Path) -> None:
    freezer.ROOT = root
    freezer.STATUS_PATH = root / "review-status.json"


def make_valid_layers(root: Path) -> None:
    Image.new("RGB", (1920, 1080), (20, 30, 40)).save(root / "background.png")
    Image.new("RGB", (1920, 1080), (50, 60, 70)).save(root / "midground.png")
    fg = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    draw = ImageDraw.Draw(fg)
    draw.rectangle((0, 120, 120, 760), fill=(50, 70, 45, 255))
    draw.rectangle((1800, 160, 1919, 800), fill=(60, 55, 40, 255))
    fg.save(root / "foreground.png")


def assert_valid_freeze() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_status(root)
        make_valid_layers(root)
        bind(root)
        assert freezer.main() == 0
        status = json.loads((root / "review-status.json").read_text(encoding="utf-8"))
        assert status["status"] == "technical_frozen"
        assert status["automated_validation"] == "pass"
        assert status["foreground_transparency"] == "pass"
        assert status["safe_zone"] == "pass"
        assert status["manual_visual_review"] == "pending"
        assert status["godot_runtime_capture"] == "pending"
        assert status["promotion"] is False
        assert status["canonical_replacement_authorized"] is False
        for name in freezer.LAYERS:
            assert status["layers"][name]["state"] == "frozen"
            assert len(status["layers"][name]["sha256"]) == 64


def assert_safe_zone_blocks() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_status(root)
        make_valid_layers(root)
        fg = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
        draw = ImageDraw.Draw(fg)
        draw.rectangle((400, 150, 1500, 760), fill=(255, 255, 255, 255))
        fg.save(root / "foreground.png")
        bind(root)
        assert freezer.main() == 2


def assert_missing_waits() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_status(root)
        bind(root)
        assert freezer.main() == 0
        status = json.loads((root / "review-status.json").read_text(encoding="utf-8"))
        assert status["status"] == "art_pending"
        assert status["promotion"] is False


def main() -> int:
    assert_valid_freeze()
    assert_safe_zone_blocks()
    assert_missing_waits()
    print("PACK03_V3_FREEZER_TEST=PASS valid_freeze=true safe_zone_fail_closed=true missing_waits=true")
    print("SIGNATURE=Tehkné Solutions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
