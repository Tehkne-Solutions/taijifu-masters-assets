# First Playable — Generation Batch 01

Este batch produz **dois spritesheets**, não 88 imagens avulsas.

## FP_CHAR_01_LIAN_WU

- 44 frames canônicos em uma única folha 8×6;
- 512×512 por célula;
- fundo transparente;
- orientação nativa para a direita;
- pivô visual bottom-center consistente;
- identidade: lutador marcial de leitura limpa, roupa branca com acentos azuis e dourados;
- uma única katana, com continuidade rigorosa entre todos os frames;
- sem texto, logo, moldura, sombra de célula ou elementos promocionais;
- escala corporal e linha dos pés constantes entre todas as células.

## FP_CHAR_02_TRAINING_RIVAL

- 44 frames canônicos em uma única folha 8×6;
- 512×512 por célula;
- fundo transparente;
- orientação nativa para a esquerda;
- pivô visual bottom-center consistente;
- identidade: rival de treino mais pesado, armadura escura com leitura brasa/metal;
- manoplas e silhueta curta/pesada consistentes em todos os frames;
- sem texto, logo, moldura, sombra de célula ou elementos promocionais;
- escala corporal e linha dos pés constantes entre todas as células.

## Ordem exata das animações

1. `idle` — 6
2. `run` — 8
3. `jump_start` — 3
4. `airborne` — 2
5. `fall` — 2
6. `attack_light` — 6
7. `guard` — 3
8. `dodge` — 5
9. `hit` — 3
10. `ko` — 6

Total: **44 células usadas**. As quatro células restantes da grade 8×6 devem permanecer completamente transparentes.

## Esteira

```bash
python tools/prepare_first_playable_generation_batch.py

python tools/import_first_playable_spritesheet.py \
  intake/first_playable/FP_CHAR_01_LIAN_WU.png \
  intake/first_playable/FP_CHAR_01_LIAN_WU.layout.json \
  --dry-run

python tools/import_first_playable_spritesheet.py \
  intake/first_playable/FP_CHAR_02_TRAINING_RIVAL.png \
  intake/first_playable/FP_CHAR_02_TRAINING_RIVAL.layout.json \
  --dry-run

python tools/validate_first_playable_art_production.py
```

Somente após preflight estrito verde os frames podem ser promovidos para integração no jogo.

Assinatura: Tehkné Solutions
