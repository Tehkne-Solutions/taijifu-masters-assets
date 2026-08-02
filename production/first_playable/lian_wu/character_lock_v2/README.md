# VM01-A2 — Lian Wu Character Lock / Rig Base

Tehkné Solutions

## Verified in this stage

- `neutral`: canonical front from Canonical Clean v1.0.1; no redraw.
- `silhouette_25pct`: deterministic derivative of the canonical alpha.
- Native facing: right.
- Canonical pivot: normalized `(0.5, 0.92)`.
- Current game Fighter scene uses a capsule radius `16`, height `78`, collision position `(0,-16)` and sprite presentation offset `(0,-17)`.

## Deliberately not fabricated

`combat_stance` is still blocked. A distinct stance changes limb pose and cannot be obtained by cleanup/cropping while preserving the canonical character. It must be authored from Rig v1.

The 1920x1080 Godot bench remains blocked until both lock poses exist.

## Next execution block — Rig v1

Segment the canonical neutral into a reversible layered rig with at least:

- head / hair-front / hair-back / topknot / ribbon
- torso / waist / sash
- upper-arm L/R / forearm L/R / hand L/R
- thigh L/R / shin L/R / foot L/R
- sheath / katana

Rig output must reconstruct the canonical neutral with no visible identity change before it may be used to author `combat_stance`.

## Promotion rule

Animation generation remains forbidden until:

1. Rig v1 reconstruction gate passes;
2. combat stance is authored from that rig;
3. neutral + stance pass the Godot bench;
4. VM01-A2 Character Lock becomes PASS.
