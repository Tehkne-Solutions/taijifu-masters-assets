#!/usr/bin/env python3
"""Strict First Playable art validator for the released 45+44 frame baseline."""

from __future__ import annotations

import validate_first_playable_art_production as base

base.EXPECTED = {
    "lian_wu": {
        "frames": 45,
        "animations": {
            "idle": 4,
            "walk": 6,
            "jump_start": 2,
            "jump_loop": 4,
            "land": 3,
            "light_attack": 6,
            "heavy_attack": 6,
            "guard": 1,
            "hit": 4,
            "ko": 9,
        },
    },
    "training_rival": {
        "frames": 44,
        "animations": {
            "idle": 4,
            "walk": 6,
            "jump_start": 2,
            "jump_loop": 4,
            "land": 3,
            "light_attack": 6,
            "heavy_attack": 6,
            "hit": 4,
            "ko": 9,
        },
    },
}

if __name__ == "__main__":
    raise SystemExit(base.main())

# Tehkné Solutions
