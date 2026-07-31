# First Playable — produção artística

Este diretório concentra apenas os lotes artísticos reais necessários para remover os fallbacks procedurais do First Playable.

## Lotes obrigatórios

- `lian_wu/first_playable_lot_01/`
- `training_rival/first_playable_lot_01/`

Cada lote deve conter 44 PNGs individuais distribuídos entre: `idle`, `run`, `jump_start`, `airborne`, `fall`, `attack_light`, `guard`, `dodge`, `hit` e `ko`.

## Regra de verdade

- nenhum arquivo placeholder pode ser aprovado;
- `approval.json` permanece em `art_required` ou `review_required` até revisão visual no Godot;
- checksums são gerados apenas depois dos PNGs finais;
- o ZIP de release só pode ser produzido após validação automática e revisão visual.

## Ordem de produção

1. Lote A: idle, run, guard, hit e ko.
2. Lote B: attack_light e dodge.
3. Lote C: jump_start, airborne e fall.
4. Revisão em movimento no First Playable.
5. Aprovação, checksums e empacotamento.

Assinatura: Tehkné Solutions
