# VM02-C33 — Mountain Dojo Night visual art handoff

The C33 branch is reserved for the three canonical arena image layers required by the existing C30 intake contract:

- `packs/stages/mountain_dojo_night/v1/background.png`
- `packs/stages/mountain_dojo_night/v1/midground.png`
- `packs/stages/mountain_dojo_night/v1/foreground.png`

Runtime metadata already lives on `main` through VM02-C32. Promotion remains blocked until the three PNGs are materialized, visually reviewed, and the game-side C30/C34 gates pass.

Expected transition after the image delivery:

```text
VM02_C30_ARENA_FILE_COUNT=6/6
VM02_C30_ARENA_FILE_CONTRACT=PASS
VM02_C30_ARENA_IMPORT=PASS
VM02_C30_ARENA_CANONICAL_READY=PASS
```

The candidate visual pack is delivered through the C33 operator bundle so binary upload can remain deterministic and hash-checked before push.

Tehkné Solutions
