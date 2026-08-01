# VM01-A1 — Lian Wu Character Lock v1

Status: `blocked_missing_art_and_godot_evidence`

Este diretório define a primeira entrega visual válida do Visual Milestone 01. Nenhum PNG conceitual, contact sheet, mockup ou imagem com cenário/texto pode ser promovido aqui.

## Arquivos obrigatórios

```text
lian_wu_neutral.png
lian_wu_combat_stance.png
lian_wu_silhouette_25pct.png
character-lock.manifest.json
visual-review.json
godot-bench-1920x1080.png
README.md
```

## Regras canônicas

- PNG RGBA com fundo transparente;
- um único personagem por arquivo;
- sem texto, logo, moldura, cenário ou sombra de cenário embutidos;
- facing nativo à direita;
- pivô de runtime `x=0.5`, `y=0.92`;
- linha dos pés com tolerância máxima de 3 px;
- variação máxima de bounds entre poses: 8%;
- mesma escala corporal entre neutral e combat stance;
- visual comic-mangá 2.5D;
- topknot com laço azul;
- roupa branca, azul-água, preta e dourada;
- uma única katana;
- bainha azul no quadril esquerdo;
- katana embainhada na pose neutra;
- nenhuma leitura de segunda arma.

## Fontes canônicas

- `contracts/pack_01_lian_wu/first-playable-lot-01.json`;
- `reviews/pack_01_lian_wu_base/v1.0.1-turnaround-art-brief.md`;
- `production/first_playable/visual-milestone-01.json`;
- `production/first_playable/VISUAL_EXECUTION_PLAN.md`.

## Fluxo obrigatório

1. inserir `lian_wu_neutral.png` e `lian_wu_combat_stance.png`;
2. gerar `lian_wu_silhouette_25pct.png` a partir do candidato real;
3. executar `python tools/validate_lian_wu_character_lock.py`;
4. importar os dois candidatos no Godot;
5. usar o mesmo `FighterController` do First Playable;
6. capturar `godot-bench-1920x1080.png` em resolução real;
7. preencher `visual-review.json` com `pass`/`fail` e evidências;
8. executar novamente o validador;
9. somente após `VM01_A1_CHARACTER_LOCK=PASS` iniciar os packs de animação.

## Estado atual

Os quatro PNGs obrigatórios ainda não existem. A etapa está bloqueada e não pode ser declarada aprovada.

**Tehkné Solutions**
