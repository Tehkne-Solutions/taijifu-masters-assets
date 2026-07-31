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
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_ROOT = ROOT / "production" / "first_playable"
CHARACTERS = {
    "lian_wu": "char_lian_wu",
    "training_rival": "char_training_rival",
}
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
NON_BLOCKING_INCOMPLETE_CODES = {"frames_missing"}


@dataclass
class Finding:
    level: str
    character: str
    code: str
    message: str


def read_png(path: Path) -> tuple[int, int, int]:
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("assinatura PNG inválida")

    offset = len(PNG_SIGNATURE)
    width = height = color_type = None
    seen_ihdr = seen_idat = seen_iend = False

    while offset < len(data):
        if offset + 12 > len(data):
            raise ValueError("chunk PNG truncado")
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        chunk_type = data[offset + 4:offset + 8]
        chunk_end = offset + 12 + length
        if chunk_end > len(data):
            raise ValueError("payload PNG truncado")
        payload = data[offset + 8:offset + 8 + length]
        expected_crc = struct.unpack(">I", data[offset + 8 + length:chunk_end])[0]
        actual_crc = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise ValueError(f"CRC inválido em {chunk_type.decode('ascii', 'replace')}")

        if chunk_type == b"IHDR":
            if seen_ihdr or offset != len(PNG_SIGNATURE) or length != 13:
                raise ValueError("IHDR inválido")
            width, height, _depth, color_type, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
            if compression != 0 or filtering != 0 or interlace not in (0, 1):
                raise ValueError("parâmetros IHDR inválidos")
            seen_ihdr = True
        elif chunk_type == b"IDAT":
            if not seen_ihdr:
                raise ValueError("IDAT antes de IHDR")
            seen_idat = True
        elif chunk_type == b"IEND":
            if length != 0:
                raise ValueError("IEND inválido")
            seen_iend = True
            if chunk_end != len(data):
                raise ValueError("dados após IEND")
            break
        offset = chunk_end

    if not (seen_ihdr and seen_idat and seen_iend):
        raise ValueError("estrutura PNG incompleta")
    assert width is not None and height is not None and color_type is not None
    return width, height, color_type


def validate_character(character: str, prefix: str) -> tuple[list[Finding], int]:
    findings: list[Finding] = []
    lot_root = PRODUCTION_ROOT / character / "first_playable_lot_01"
    manifest_path = lot_root / "work-manifest.json"
    total_present = 0

    if not manifest_path.exists():
        return [Finding("error", character, "manifest_missing", str(manifest_path))], 0

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [Finding("error", character, "manifest_invalid", str(exc))], 0

    if manifest.get("signature") != "Tehkné Solutions":
        findings.append(Finding("error", character, "signature_invalid", "assinatura ausente ou incorreta"))

    animations = manifest.get("animations")
    if not isinstance(animations, dict) or sum(animations.values()) != manifest.get("required_frames") or manifest.get("required_frames") != 44:
        findings.append(Finding("error", character, "frame_contract_invalid", "manifesto deve exigir exatamente 44 frames"))
        return findings, 0

    canvas = manifest.get("canvas", {"min": 128, "max": 1024})
    minimum = int(canvas.get("min", 128))
    maximum = int(canvas.get("max", 1024))
    dimensions: set[tuple[int, int]] = set()
    animation_root = lot_root / "animations"

    for animation, expected_count in animations.items():
        folder = animation_root / animation
        expected_names = {
            f"{prefix}__{animation}__f{index:03d}.png"
            for index in range(1, int(expected_count) + 1)
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
            try:
                width, height, color_type = read_png(frame)
            except Exception as exc:
                findings.append(Finding("error", character, "png_invalid", f"{frame.name}: {exc}"))
                continue
            if not (minimum <= width <= maximum and minimum <= height <= maximum):
                findings.append(Finding("error", character, "dimensions_out_of_bounds", f"{frame.name}: {width}x{height}"))
            else:
                dimensions.add((width, height))
            if color_type not in (4, 6):
                findings.append(Finding("error", character, "alpha_required", f"{frame.name}: color_type={color_type}"))

    if len(dimensions) > 1:
        findings.append(Finding("error", character, "dimensions_inconsistent", str(sorted(dimensions))))

    approved = manifest.get("status") == "approved" or manifest.get("approval", {}).get("art") is True
    blocking = [item for item in findings if item.level == "error"]
    if approved and (blocking or total_present != 44):
        findings.append(Finding("error", character, "false_approval", "lote aprovado sem 44 frames válidos"))
    if total_present == 44 and not blocking:
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

    blocking_errors = [
        item for item in all_findings
        if item.level == "error" and not (args.allow_incomplete and item.code in NON_BLOCKING_INCOMPLETE_CODES)
    ]
    complete = all(counts.get(character) == 44 for character in CHARACTERS)
    passed = not blocking_errors and (complete or args.allow_incomplete)
    report = {
        "gate_id": "taijifu-first-playable-art-preflight-v2",
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
