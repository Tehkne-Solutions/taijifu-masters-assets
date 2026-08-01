# Intake oficial — spritesheets do First Playable

Este fluxo começa somente depois que um pack artístico produzir um spritesheet candidato.
Ele não substitui a revisão visual e não promove arte automaticamente.

## Arquivos esperados

```text
intake/first_playable/
├── FP_CHAR_01_LIAN_WU.png
├── FP_CHAR_01_LIAN_WU.layout.json
├── FP_CHAR_02_TRAINING_RIVAL.png
└── FP_CHAR_02_TRAINING_RIVAL.layout.json
```

Os layouts são gerados por:

```bash
python tools/prepare_first_playable_generation_batch.py
```

## Preflight obrigatório

Lian Wu:

```bash
python tools/validate_first_playable_spritesheet_candidate.py \
  intake/first_playable/FP_CHAR_01_LIAN_WU.png \
  intake/first_playable/FP_CHAR_01_LIAN_WU.layout.json \
  --report artifacts/candidate-intake/FP_CHAR_01_LIAN_WU.json
```

Rival de Treino:

```bash
python tools/validate_first_playable_spritesheet_candidate.py \
  intake/first_playable/FP_CHAR_02_TRAINING_RIVAL.png \
  intake/first_playable/FP_CHAR_02_TRAINING_RIVAL.layout.json \
  --report artifacts/candidate-intake/FP_CHAR_02_TRAINING_RIVAL.json
```

## O que o gate bloqueia

- dimensão diferente da declarada no layout;
- imagem sem canal RGBA;
- fundo global opaco;
- uma das 44 células usadas vazia ou quase vazia;
- conteúdo nas quatro células reservadas;
- layout inválido, duplicado ou divergente do contrato de 44 frames.

A saída válida é:

```text
FIRST_PLAYABLE_SPRITESHEET_CANDIDATE_OK <character> 44/44
```

Somente depois disso o importador pode recortar e nomear os frames:

```bash
python tools/import_first_playable_spritesheet.py \
  intake/first_playable/FP_CHAR_01_LIAN_WU.png \
  intake/first_playable/FP_CHAR_01_LIAN_WU.layout.json \
  --dry-run
```

A revisão artística no Godot e o preflight estrito dos 88 frames continuam obrigatórios.

Assinatura: Tehkné Solutions
