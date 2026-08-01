#!/usr/bin/env python3
"""Monta o spritesheet canônico do First Playable a partir de packs de animação.

Cada entrada é uma tira horizontal RGBA sem margem ou gutter. A ferramenta
valida o contrato, recorta cada frame, posiciona pela layout canônica e executa
o gate final de candidato antes de liberar o spritesheet.

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
from validate_first_playable_spritesheet_candidate import validate_candidate

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ANIMATIONS = [
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


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else repo_root / path


def _alpha_ratio(image: Image.Image, threshold: int) -> float:
    alpha = image.getchannel("A")
    total = image.width * image.height
    occupied = sum(
        count
        for count, value in alpha.getcolors(maxcolors=256) or []
        if value > threshold
    )
    return occupied / max(1, total)


def _transparent_ratio(image: Image.Image, threshold: int) -> float:
    return 1.0 - _alpha_ratio(image, threshold)


def load_animation_pack_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema",
        "pack_id",
        "character_id",
        "cell",
        "final_sheet",
        "source_dir",
        "animation_packs",
    }
    missing = sorted(required - data.keys())
    if missing:
        raise ValueError(f"manifest incompleto: {', '.join(missing)}")
    if data["schema"] != "taijifu-first-playable-animation-pack-v1":
        raise ValueError(f"schema inválido: {data['schema']}")
    return data


def validate_animation_pack_manifest(data: dict[str, Any]) -> None:
    cell = data["cell"]
    final_sheet = data["final_sheet"]
    cell_width = int(cell.get("width", 0))
    cell_height = int(cell.get("height", 0))
    columns = int(final_sheet.get("columns", 0))
    rows = int(final_sheet.get("rows", 0))

    if not (128 <= cell_width <= 1024 and 128 <= cell_height <= 1024):
        raise ValueError("células devem ficar entre 128×128 e 1024×1024")
    if columns != 8 or rows != 6:
        raise ValueError("grade final deve ser exatamente 8×6")
    if int(final_sheet.get("width", 0)) != columns * cell_width:
        raise ValueError("largura final diverge da grade e da célula")
    if int(final_sheet.get("height", 0)) != rows * cell_height:
        raise ValueError("altura final diverge da grade e da célula")
    if int(cell.get("margin", 0)) != 0 or int(cell.get("gutter", 0)) != 0:
        raise ValueError("packs devem usar margin=0 e gutter=0")
    if cell.get("background") != "transparent":
        raise ValueError("background deve ser transparent")

    packs = data["animation_packs"]
    if len(packs) != len(EXPECTED_ANIMATIONS):
        raise ValueError(f"manifest deve conter {len(EXPECTED_ANIMATIONS)} packs de animação")

    sources: set[str] = set()
    total = 0
    for position, ((expected_name, expected_frames), pack) in enumerate(
        zip(EXPECTED_ANIMATIONS, packs, strict=True),
        start=1,
    ):
        if int(pack.get("order", 0)) != position:
            raise ValueError(f"ordem inválida no pack {pack.get('id', position)}")
        if pack.get("animation") != expected_name:
            raise ValueError(
                f"animação esperada {expected_name}; recebeu {pack.get('animation')}"
            )
        if int(pack.get("frames", 0)) != expected_frames:
            raise ValueError(
                f"{expected_name} deve ter {expected_frames} frames; "
                f"recebeu {pack.get('frames')}"
            )
        source = str(pack.get("source", "")).strip()
        if not source:
            raise ValueError(f"source ausente em {expected_name}")
        if source in sources:
            raise ValueError(f"source duplicado: {source}")
        sources.add(source)
        total += expected_frames

    if total != 44:
        raise ValueError(f"total deve ser 44 frames; recebeu {total}")


def assemble_animation_packs(
    manifest_path: Path,
    *,
    repo_root: Path = ROOT,
    output_path: Path | None = None,
    report_path: Path | None = None,
    alpha_threshold: int = 8,
    min_frame_alpha_ratio: float = 0.002,
    min_strip_transparent_ratio: float = 0.10,
) -> dict[str, Any]:
    manifest = load_animation_pack_manifest(manifest_path)
    validate_animation_pack_manifest(manifest)

    repo_root = repo_root.resolve()
    cell = manifest["cell"]
    final_sheet = manifest["final_sheet"]
    cell_width = int(cell["width"])
    cell_height = int(cell["height"])
    columns = int(final_sheet["columns"])
    rows = int(final_sheet["rows"])
    character = str(manifest["character_id"])

    source_dir = _resolve(repo_root, manifest["source_dir"])
    layout_path = _resolve(repo_root, final_sheet["layout"])
    destination = output_path or _resolve(repo_root, final_sheet["output"])

    layout = load_layout(layout_path)
    validate_frame_map(layout)
    if layout["character"] != character:
        raise ValueError(
            f"personagem do layout {layout['character']} diverge do manifest {character}"
        )
    if (
        int(layout["cell_width"]) != cell_width
        or int(layout["cell_height"]) != cell_height
        or int(layout["columns"]) != columns
        or int(layout["rows"]) != rows
    ):
        raise ValueError("layout diverge da grade declarada no manifest")

    target_cells = {
        (str(item["animation"]), int(item["index"])): (
            int(item["column"]),
            int(item["row"]),
        )
        for item in layout["frames"]
    }

    errors: list[str] = []
    pack_reports: list[dict[str, Any]] = []
    canvas = Image.new("RGBA", (columns * cell_width, rows * cell_height), (0, 0, 0, 0))

    for pack in manifest["animation_packs"]:
        animation = str(pack["animation"])
        frames = int(pack["frames"])
        source_path = source_dir / str(pack["source"])
        pack_report: dict[str, Any] = {
            "id": pack["id"],
            "animation": animation,
            "frames": frames,
            "source": str(source_path),
            "frame_alpha_ratios": [],
            "errors": [],
        }

        if not source_path.exists():
            message = f"pack ausente: {source_path}"
            errors.append(message)
            pack_report["errors"].append(message)
            pack_reports.append(pack_report)
            continue

        try:
            with Image.open(source_path) as strip_source:
                strip_source.load()
                if strip_source.mode != "RGBA":
                    message = f"{animation} deve ser RGBA; modo atual: {strip_source.mode}"
                    errors.append(message)
                    pack_report["errors"].append(message)
                    pack_reports.append(pack_report)
                    continue

                expected_size = (frames * cell_width, cell_height)
                if strip_source.size != expected_size:
                    message = (
                        f"{animation} dimensão esperada {expected_size}; "
                        f"recebida {strip_source.size}"
                    )
                    errors.append(message)
                    pack_report["errors"].append(message)
                    pack_reports.append(pack_report)
                    continue

                transparent_ratio = _transparent_ratio(strip_source, alpha_threshold)
                pack_report["transparent_ratio"] = round(transparent_ratio, 8)
                if transparent_ratio < min_strip_transparent_ratio:
                    message = (
                        f"{animation} fundo não é suficientemente transparente: "
                        f"{transparent_ratio:.4f} < {min_strip_transparent_ratio:.4f}"
                    )
                    errors.append(message)
                    pack_report["errors"].append(message)

                for index in range(1, frames + 1):
                    left = (index - 1) * cell_width
                    frame = strip_source.crop(
                        (left, 0, left + cell_width, cell_height)
                    )
                    ratio = _alpha_ratio(frame, alpha_threshold)
                    pack_report["frame_alpha_ratios"].append(round(ratio, 8))
                    if ratio < min_frame_alpha_ratio:
                        message = (
                            f"{animation} frame {index:03d} vazio ou quase vazio: "
                            f"alpha_ratio={ratio:.6f}"
                        )
                        errors.append(message)
                        pack_report["errors"].append(message)
                        continue

                    target = target_cells.get((animation, index))
                    if target is None:
                        message = f"layout não possui {animation} frame {index:03d}"
                        errors.append(message)
                        pack_report["errors"].append(message)
                        continue
                    column, row = target
                    canvas.alpha_composite(frame, (column * cell_width, row * cell_height))
        except OSError as exc:
            message = f"falha ao abrir {source_path}: {exc}"
            errors.append(message)
            pack_report["errors"].append(message)

        pack_report["passed"] = not pack_report["errors"]
        pack_reports.append(pack_report)

    final_report: dict[str, Any] | None = None
    if not errors:
        destination.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(destination, format="PNG", optimize=False)
        final_report = validate_candidate(destination, layout_path)
        if not final_report["passed"]:
            errors.extend(str(item) for item in final_report["errors"])
            destination.unlink(missing_ok=True)

    report = {
        "schema": "taijifu-first-playable-animation-pack-assembly-report-v1",
        "manifest": str(manifest_path),
        "character": character,
        "source_dir": str(source_dir),
        "output": str(destination),
        "pack_count": len(pack_reports),
        "frame_count": 44,
        "packs": pack_reports,
        "final_candidate": final_report,
        "errors": errors,
        "passed": not errors,
        "signature": "Tehkné Solutions",
    }

    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--alpha-threshold", type=int, default=8)
    parser.add_argument("--min-frame-alpha-ratio", type=float, default=0.002)
    parser.add_argument("--min-strip-transparent-ratio", type=float, default=0.10)
    args = parser.parse_args()

    try:
        report = assemble_animation_packs(
            args.manifest,
            output_path=args.output,
            report_path=args.report,
            alpha_threshold=args.alpha_threshold,
            min_frame_alpha_ratio=args.min_frame_alpha_ratio,
            min_strip_transparent_ratio=args.min_strip_transparent_ratio,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    if report["passed"]:
        print(
            "FIRST_PLAYABLE_ANIMATION_PACK_ASSEMBLY_OK "
            f"{report['character']} {report['frame_count']}/44"
        )
        return 0

    for error in report["errors"]:
        print(f"ERRO: {error}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
