from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "tools/generate_first_playable_layout.py"
IMPORTER = ROOT / "tools/import_first_playable_spritesheet.py"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *args], cwd=ROOT, text=True, capture_output=True)


def test_generates_and_imports_44_frames(tmp_path: Path) -> None:
    layout = tmp_path / "layout.json"
    generated = run(str(GENERATOR), "lian_wu", str(layout), "--cell-width", "128", "--cell-height", "128")
    assert generated.returncode == 0, generated.stderr
    payload = json.loads(layout.read_text(encoding="utf-8"))
    sheet = tmp_path / "sheet.png"
    Image.new("RGBA", (payload["columns"] * 128, payload["rows"] * 128), (0, 0, 0, 0)).save(sheet)
    output = tmp_path / "animations"
    imported = run(str(IMPORTER), str(sheet), str(layout), "--output", str(output))
    assert imported.returncode == 0, imported.stderr
    assert len(list(output.rglob("*.png"))) == 44
    assert (output / "idle/char_lian_wu__idle__f001.png").exists()
    assert (output / "ko/char_lian_wu__ko__f006.png").exists()


def test_rejects_gutter(tmp_path: Path) -> None:
    layout = tmp_path / "layout.json"
    run(str(GENERATOR), "training_rival", str(layout), "--cell-width", "128", "--cell-height", "128")
    payload = json.loads(layout.read_text(encoding="utf-8"))
    payload["gutter"] = 1
    layout.write_text(json.dumps(payload), encoding="utf-8")
    sheet = tmp_path / "sheet.png"
    Image.new("RGBA", (payload["columns"] * 128, payload["rows"] * 128), (0, 0, 0, 0)).save(sheet)
    result = run(str(IMPORTER), str(sheet), str(layout), "--dry-run")
    assert result.returncode == 2
    assert "gutter=0" in result.stderr


def test_rejects_non_rgba_sheet(tmp_path: Path) -> None:
    layout = tmp_path / "layout.json"
    run(str(GENERATOR), "lian_wu", str(layout), "--cell-width", "128", "--cell-height", "128")
    payload = json.loads(layout.read_text(encoding="utf-8"))
    sheet = tmp_path / "sheet.png"
    Image.new("RGB", (payload["columns"] * 128, payload["rows"] * 128), (255, 255, 255)).save(sheet)
    result = run(str(IMPORTER), str(sheet), str(layout), "--dry-run")
    assert result.returncode == 2
    assert "deve ser RGBA" in result.stderr
