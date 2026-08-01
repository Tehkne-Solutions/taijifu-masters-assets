# VM01-A1 — Lian Wu Character Lock — Candidate 01 Review

Status: `REJECTED_DO_NOT_PROMOTE`

Signature: Tehkné Solutions

## Scope

Review only the two generated character-lock candidates before silhouette generation, Godot bench, animation production or fallback replacement.

## Evidence

### Neutral

- file: `lian_wu_neutral.png`
- SHA256: `d29ed9fc2e443d35fb11e9c4028cb8fa13cd1741d527d3b9bc997ca773b9fc9f`
- PNG: RGBA
- canvas: 768x768
- alpha bounds: x=144..622, y=48..719
- feet baseline: y=720

### Combat stance

- file: `lian_wu_combat_stance.png`
- SHA256: `6a8d04f3796bfc9b788147ca3433a94bcf63a3ce0a2612fc09bf7951f0c71cc6`
- PNG: RGBA
- canvas: 768x768
- alpha bounds: x=69..698, y=265..719
- feet baseline: y=720

## Technical checks

- truecolor RGBA: PASS
- transparent canvas: PASS
- one character per file: PASS
- identical canvas dimensions: PASS
- common feet baseline within 3 px: PASS (0 px delta)
- native facing right: PASS

## Blocking visual findings

### Identity mismatch

The current canonical source and front turnaround define Lian Wu as a boyish chibi martial fighter with:

- high blue-tied topknot;
- strong brows and compact fighter face;
- asymmetric white/water-blue/black/gold garment construction;
- broad blue front sash;
- black trousers and dark armored forearms/boots;
- one katana tied to the left hip.

Candidate 01 instead reads as a different feminine character with:

- long loose hair and different facial construction;
- white head ribbon plus secondary blue bow;
- purple sash and purple structural accents;
- different shoulder, sleeve, trouser, boot and waist construction;
- weapon/sheath design not continuous with the current canonical source.

This is not a small styling variation. It is a different character identity and cannot be corrected by pivot, scaling, silhouette extraction or runtime integration.

### Weapon gate remains blocked

The repository turnaround is still `art_correction_required`. Candidate 01 does not solve that correction and cannot establish approved katana/sheath continuity.

## Decision

```text
VM01_A1_CHARACTER_LOCK=REJECTED

neutral_pose=FAIL_IDENTITY
combat_stance=FAIL_IDENTITY
identity_continuity=FAIL
weapon_continuity=BLOCKED
transparent_background=PASS
feet_baseline=PASS
silhouette_25pct=NOT_RUN
godot_scale_bench=NOT_RUN
fallback_replacement_ready=FAIL
```

Silhouette and Godot bench were intentionally not produced. The process forbids generating downstream evidence from rejected upstream art.

## Required next action

Regenerate only:

- `lian_wu_neutral.png`
- `lian_wu_combat_stance.png`

using `source/char_lian_wu__master_raw.png` and `turnaround/char_lian_wu__front_raw.png` as strict identity references. The next pair must preserve the canonical boyish fighter identity and outfit construction before any runtime work resumes.
