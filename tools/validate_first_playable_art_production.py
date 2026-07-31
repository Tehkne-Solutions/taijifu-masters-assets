#!/usr/bin/env python3
"""Valida a produção artística real dos dois lutadores do First Playable.

Não cria arquivos, não aceita placeholders e não promove aprovação.
Assinatura: Tehkné Solutions
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_ROOT = ROOT / "production" / "first_playable"
ANIMATIONS = {
    "idle": 6,
    "run": 8,
    "jump_start": 3,
    "airborne": 2,
    "fall": 2,
    "attack_light": 6,
    "guard": 3,
    "dodge": 5,
    "hit": 3,
    "ko": 6,
}
CHARACTERS = {
    "lian_wu": "char_lian_wu",
    "training_rival": "char_training_rival",
}
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@dataclass
class Finding:
    level: str
    character: str
    code: str
    message: str


def read_png_header(path: Path) -> tuple[int, int, int]:
    with path.open("rb") as handle:
        if handle.read(8) != PNG_SIGNATURE:
            raise ValueError("assinatura PNG inválida")
        length = struct.unpack(">I", handle.read(4))[0]
        chunk_type = handle.read(4)
        if chunk_type != b"IHDR" or length != 13:
            raise ValueError("IHDR inválido")
        width, height, _bit_depth, color_type, _compression, _filter, _interlace = struct.unpack(
            ">IIBBBBB", handle.read(13)
        )
        return width, height, color_type


def validate_character(character: str, prefix: str) -> tuple[list[Finding], int]:
    findings: list[Finding] = []
    lot_root = PRODUCTION_ROOT / character / "first_playable_lot_01"
    manifest_path = lot_root / "work-manifest.json"
    total_present = 0

    if not manifest_path.exists():
        findings.append(Finding("error", character, "manifest_missing", str(manifest_path)))
        return findings, 0

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        findings.append(Finding("error", character, "manifest_invalid", str(exc)))
        return findings, 0

    if manifest.get("signature") != "Tehkné Solutions":
        findings.append(Finding("error", character, "signature_invalid", "assinatura ausente ou incorreta"))

    animation_root = lot_root / "animations"
    dimensions: set[tuple[int, int]] = set()

    for animation, expected_count in ANIMATIONS.items():
        folder = animation_root / animation
        expected_names = {
            f"{prefix}__{animation}__f{index:03d}.png"
            for index in range(1, expected_count + 1)
        }
        actual_files = sorted(folder.glob("*.png")) if folder.exists() else []
        actual_names = {path.name for path in actual_files}
        total_present += len(actual_files)

        missing = sorted(expected_names - actual_names)
        unexpected = sorted(actual_names - expected_names)
        if missing:
            findings.append(Finding("error", character, "frames_missing", f"{animation}: {', '.join(missing)}"))
        if unexpected:
            findings.append(Finding("error", character, "frames_unexpected", f"{animation}: {', '.join(unexpected)}"))

        pattern = re.compile(rf"^{re.escape(prefix)}__{re.escape(animation)}__f\d{{3}}\.png$")
        for frame in actual_files:
            if not pattern.match(frame.name):
                findings.append(Finding("error", character, "filename_invalid", frame.name))
                continue
            if frame.stat().st_size < 128:
                findings.append(Finding("error", character, "file_too_small", frame.name))
                continue
            try:
                width, height, color_type = read_png_header(frame)
            except Exception as exc:
                findings.append(Finding("error", character, "png_invalid", f"{frame.name}: {exc}"))
                continue
            if width <= 0 or height <= 0:
                findings.append(Finding("error", character, "dimensions_invalid", frame.name))
            else:
                dimensions.add((width, height))
            if color_type not in (4, 6):
                findings.append(Finding("error", character, "alpha_required", f"{frame.name}: color_type={color_type}"))

    if len(dimensions) > 1:
        findings.append(Finding("error", character, "dimensions_inconsistent", str(sorted(dimensions))))

    approved = manifest.get("status") == "approved" or manifest.get("approval", {}).get("art") is True
    has_errors = any(item.level == "error" for item in findings)
    if approved and (has_errors or total_present != 44):
        findings.append(Finding("error", character, "false_approval", "lote aprovado sem 44 frames válidos"))

    if total_present == 44 and not has_errors:
        findings.append(Finding("info", character, "ready_for_visual_review", "44 frames tecnicamente válidos; revisão no Godot ainda obrigatória"))

    return findings, total_present


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="artifacts/first-playable-art-preflight.json")
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()

    all_findings: list[Finding] = []
    counts: dict[str, int] = {}
    for character, prefix in CHARACTERS.items():
        findings, count = validate_character(character, prefix)
        all_findings.extend(findings)
        counts[character] = count

    errors = [item for item in all_findings if item.level == "error"]
    complete = all(counts.get(character) == 44 for character in CHARACTERS)
    passed = not errors and (complete or args.allow_incomplete)
    report = {
        "gate_id": "taijifu-first-playable-art-preflight-v1",
        "signature": "Tehkné Solutions",
        "expected_total": 88,
        "present_total": sum(counts.values()),
        "counts": counts,
        "complete": complete,
        "passed": passed,
        "findings": [asdict(item) for item in all_findings],
    }

    report_path = ROOT / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Frames presentes: {report['present_total']}/88")
    for finding in all_findings:
        print(f"[{finding.level.upper()}] {finding.character} {finding.code}: {finding.message}")
    print(f"Relatório: {report_path.relative_to(ROOT)}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
