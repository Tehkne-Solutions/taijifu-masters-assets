from __future__ import annotations

import hashlib
from pathlib import Path

import cairosvg
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "packs/stages/mountain_dojo_night/v1"
SOURCE = STAGE / "source"
LAYERS = ("background", "midground", "foreground")
W, H = 1920, 1080
SAFE_X0, SAFE_X1 = 280, 1640


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_layer(name: str) -> Path:
    src = SOURCE / f"{name}.svg"
    dst = STAGE / f"{name}.png"
    if not src.is_file():
        raise SystemExit(f"PACK03_RENDER=BLOCKED missing={src}")

    raw = cairosvg.svg2png(url=str(src), output_width=W, output_height=H)
    tmp = STAGE / f".{name}.render.png"
    tmp.write_bytes(raw)
    with Image.open(tmp) as im:
        if im.size != (W, H):
            raise SystemExit(f"PACK03_RENDER=BLOCKED layer={name} size={im.size}")
        rgba = im.convert("RGBA")
        rgba.save(dst, format="PNG", optimize=True)
    tmp.unlink(missing_ok=True)
    return dst


def validate(path: Path, name: str) -> None:
    with Image.open(path) as im:
        if im.size != (W, H):
            raise SystemExit(f"PACK03_VALIDATE=BLOCKED layer={name} reason=dimensions")
        if im.mode != "RGBA":
            raise SystemExit(f"PACK03_VALIDATE=BLOCKED layer={name} reason=rgba")

        if name == "foreground":
            alpha = im.getchannel("A")
            extrema = alpha.getextrema()
            if extrema[0] >= 255:
                raise SystemExit("PACK03_FOREGROUND_ALPHA=BLOCKED reason=no_transparency")
            safe = alpha.crop((SAFE_X0, 200, SAFE_X1, 840))
            if safe.getextrema()[1] != 0:
                raise SystemExit("PACK03_FOREGROUND_SAFE_ZONE=BLOCKED reason=foreground_intrusion")
            transparent = sum(1 for v in alpha.getdata() if v == 0)
            if transparent < int(W * H * 0.45):
                raise SystemExit("PACK03_FOREGROUND_ALPHA=BLOCKED reason=insufficient_transparency")
            print(f"PACK03_FOREGROUND_ALPHA=PASS transparent_pixels={transparent}")
            print("PACK03_FOREGROUND_SAFE_ZONE=PASS")

    print(f"PACK03_LAYER=PASS layer={name} bytes={path.stat().st_size} sha256={sha256(path)}")


def main() -> int:
    outputs = [render_layer(name) for name in LAYERS]
    for name, path in zip(LAYERS, outputs):
        validate(path, name)
    print("PACK03_RENDER_SET=PASS layers=3 dimensions=1920x1080")
    print("PACK03=PASS")
    print("SIGNATURE=Tehkné Solutions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
