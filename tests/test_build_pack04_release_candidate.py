#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "production/pack04/production-reference-kit-v1.json"
BUILDER = ROOT / "tools/build_pack04_release_candidate.py"


def main() -> int:
    kit = json.loads(KIT.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        temp = Path(tmp)
        frames = temp / "frames"
        output = temp / "candidate"
        for slot in kit["slots"]:
            fighter = slot["fighter"]
            state = slot["state"]
            filename = slot["filename"]
            footline = int(slot["canonical_footline_y"])
            target = frames / fighter / state / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            image = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            draw.rectangle((390, 240, 634, footline - 1), fill=(80, 120, 160, 255))
            image.save(target)

        result = subprocess.run(
            [sys.executable, str(BUILDER), "--frames-root", str(frames), "--output", str(output)],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        print(result.stdout, end="")
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
            return result.returncode

        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        runtime_map = json.loads((output / "runtime-map.json").read_text(encoding="utf-8"))
        approval = json.loads((output / "approval.json").read_text(encoding="utf-8"))
        checksums = [line for line in (output / "checksums.sha256").read_text(encoding="utf-8").splitlines() if line.strip()]

        assert manifest["asset_count"] == 34
        assert len(manifest["assets"]) == 34
        assert set(runtime_map["mappings"]) == {"lian_wu", "training_rival"}
        assert approval["approved"] is False
        assert approval["human_review"] == "PENDING"
        assert approval["status"] == "pending"
        assert approval["reviewer"] == ""
        assert approval["evidence"] == []
        assert len(checksums) == 37
        assert not (output / "checksums.json").exists()

        print("PACK04_RC_BUILDER_TEST=PASS assets=34 checksum_entries=37")
        print("PACK04_RC_SYNTHETIC_FIXTURE=PASS packaging_only=true art_claim=false")
        print("PACK04_RC_HUMAN_GATE=PASS pending_cannot_promote=true")
        print("SIGNATURE=Tehkné Solutions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
