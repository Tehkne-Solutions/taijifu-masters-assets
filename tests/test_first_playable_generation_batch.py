import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / "production" / "first_playable" / "generation-batch-01.json"


def test_generation_batch_contract():
    payload = json.loads(BATCH.read_text(encoding="utf-8"))
    assert payload["strategy"] == "spritesheet_per_character"
    assert payload["sheet"] == {
        "columns": 8,
        "rows": 6,
        "cell_width": 512,
        "cell_height": 512,
        "sheet_width": 4096,
        "sheet_height": 3072,
        "margin": 0,
        "gutter": 0,
        "background": "transparent",
        "borders": False,
    }
    assert len(payload["packs"]) == 2
    assert {pack["character_id"] for pack in payload["packs"]} == {"lian_wu", "training_rival"}
    assert all(pack["required_frames"] == 44 for pack in payload["packs"])
    assert sum(item["frames"] for item in payload["animations"]) == 44
    assert payload["acceptance"]["no_cell_borders"] is True
    assert payload["acceptance"]["exactly_44_used_cells"] is True
    assert payload["acceptance"]["unused_cells_transparent"] is True
    assert payload["signature"] == "Tehkné Solutions"
