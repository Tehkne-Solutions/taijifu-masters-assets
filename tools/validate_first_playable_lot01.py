#!/usr/bin/env python3
"""Valida o diretório de produção do First Playable Lot 01.

Assinatura: Tehkné Solutions
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

REQUIRED = {
    "idle": 4,
    "run": 6,
    "jump_start": 2,
    "airborne": 1,
    "fall": 2,
    "attack_light": 4,
    "guard": 2,
    "dodge": 4,
    "hit": 2,
    "ko": 4,
}
NAME_RE = re.compile(r"^char_lian_wu__([a-z_]+)__f(\d{3})\.png$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(root: Path) -> dict:
    errors: list[str] = []
    files: list[dict] = []
    for required in ("manifest.json", "runtime-map.json", "approval.json"):
        if not (root / required).is_file():
            errors.append(f"arquivo obrigatório ausente: {required}")

    approval_path = root / "approval.json"
    if approval_path.is_file():
        approval = json.loads(approval_path.read_text(encoding="utf-8"))
        if approval.get("status") != "approved":
            errors.append("approval.json deve conter status=approved")
        if approval.get("signature") != "Tehkné Solutions":
            errors.append("assinatura de aprovação inválida")

    animations_root = root / "animations"
    for animation, minimum in REQUIRED.items():
        folder = animations_root / animation
        frames = sorted(folder.glob("*.png")) if folder.is_dir() else []
        if len(frames) < minimum:
            errors.append(f"{animation}: esperado >= {minimum} frames; recebido {len(frames)}")
        expected_index = 1
        for frame in frames:
            match = NAME_RE.match(frame.name)
            if not match or match.group(1) != animation:
                errors.append(f"nome inválido: {frame.relative_to(root)}")
                continue
            index = int(match.group(2))
            if index != expected_index:
                errors.append(f"sequência inválida em {animation}: esperado f{expected_index:03d}")
            expected_index += 1
            if frame.stat().st_size == 0:
                errors.append(f"PNG vazio: {frame.relative_to(root)}")
            files.append({"path": frame.relative_to(root).as_posix(), "sha256": sha256(frame)})

    return {"schema": "tehkne/taijifu-first-playable-lot01-validation/v1", "ok": not errors, "errors": errors, "files": files, "signature": "Tehkné Solutions"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = validate(args.root)
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
