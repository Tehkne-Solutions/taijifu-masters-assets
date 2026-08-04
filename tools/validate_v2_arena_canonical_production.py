from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "production" / "v2" / "arena" / "mountain_dojo_night"
MANIFEST = PACK / "production-manifest.json"
REQUIRED = [
    "background.png",
    "midground.png",
    "foreground.png",
    "collision.json",
    "lighting.json",
    "manifest.json",
]

if not MANIFEST.exists():
    raise SystemExit("VM02_C31_PRODUCTION_MANIFEST=BLOCKED")

meta = json.loads(MANIFEST.read_text(encoding="utf-8"))
if meta.get("signature") != "Tehkné Solutions" or meta.get("arena_id") != "mountain_dojo_night":
    raise SystemExit("VM02_C31_PRODUCTION_MANIFEST_SCHEMA=BLOCKED")

print("VM02_C31_PRODUCTION_MANIFEST=PASS")
print("VM02_C31_PRODUCTION_MANIFEST_SCHEMA=PASS")

present = [name for name in REQUIRED if (PACK / name).exists()]
missing = [name for name in REQUIRED if name not in present]
print(f"VM02_C31_ARENA_FILE_COUNT={len(present)}/{len(REQUIRED)}")

if missing:
    print("VM02_C31_CANONICAL_FILE_CONTRACT=BLOCKED")
    print(f"VM02_C31_MISSING_FILE_COUNT={len(missing)}")
    for name in missing:
        print(f"VM02_C31_MISSING_FILE={name}")
else:
    print("VM02_C31_CANONICAL_FILE_CONTRACT=PASS")

print("VM02_C31_PRODUCTION_PIPELINE=PASS")
print("VM02_C31_C30_HANDOFF_READY=" + ("PASS" if not missing else "BLOCKED"))
