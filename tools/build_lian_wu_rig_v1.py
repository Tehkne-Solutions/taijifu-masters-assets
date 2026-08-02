from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageChops
import hashlib
import json

SOURCE = Path("production/first_playable/lian_wu/character_lock_v1/lian_wu_neutral.png")
OUTPUT = Path("production/first_playable/lian_wu/rig_v1/generated")
PARTS = [
    "head_hair", "torso", "arm_left", "arm_right",
    "waist_sash", "leg_left", "leg_right", "weapon"
]


def region_name(x: int, y: int) -> str:
    if 315 <= x <= 390 and 620 <= y <= 735:
        return "weapon"
    if y < 385:
        return "head_hair"
    if y < 705 and x < 425:
        return "arm_left"
    if y < 705 and x > 610:
        return "arm_right"
    if y < 555:
        return "torso"
    if y < 755:
        return "waist_sash"
    if x < 515:
        return "leg_left"
    return "leg_right"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def main() -> int:
    if not SOURCE.exists():
        print(f"RIG_V1_RECONSTRUCTION=BLOCKED missing={SOURCE}")
        return 2

    OUTPUT.mkdir(parents=True, exist_ok=True)
    source = Image.open(SOURCE).convert("RGBA")
    layers = {name: Image.new("RGBA", source.size, (0, 0, 0, 0)) for name in PARTS}
    source_px = source.load()
    layer_px = {name: image.load() for name, image in layers.items()}
    opaque = 0
    assigned = 0

    for y in range(source.height):
        for x in range(source.width):
            px = source_px[x, y]
            if px[3] == 0:
                continue
            opaque += 1
            name = region_name(x, y)
            layer_px[name][x, y] = px
            assigned += 1

    reconstructed = Image.new("RGBA", source.size, (0, 0, 0, 0))
    for name in PARTS:
        path = OUTPUT / f"{name}.png"
        layers[name].save(path)
        reconstructed = Image.alpha_composite(reconstructed, layers[name])

    reconstructed_path = OUTPUT / "lian_wu_neutral_reconstructed.png"
    reconstructed.save(reconstructed_path)
    diff = ImageChops.difference(source, reconstructed)
    exact = diff.getbbox() is None

    report = {
        "schema": "tehkne/taijifu-lian-wu-rig-build/v1",
        "signature": "Tehkné Solutions",
        "source_sha256": sha256(SOURCE),
        "opaque_source_pixels": opaque,
        "assigned_pixels": assigned,
        "assigned_exactly_once": assigned == opaque,
        "reconstruction_pixel_exact": exact,
        "parts": PARTS,
    }
    (OUTPUT / "build-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"RIG_V1_RECONSTRUCTION={'PASS' if exact and assigned == opaque else 'FAIL'}")
    return 0 if exact and assigned == opaque else 1


if __name__ == "__main__":
    raise SystemExit(main())
