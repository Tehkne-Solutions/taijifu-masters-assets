# Revisão visual — Pack 01 Lian Wu Base v1.0.0

- Resultado: **REPROVADO**
- Data: 2026-07-30
- Release: `assets-pack-01-v1.0.0`
- ZIP: `PACK_01_LIAN_WU_BASE_FINAL_v1.0.0.zip`
- SHA-256: `0aea374365b8736ae2134312e94d8128260a9c7650cc840aa2e588a4ab70872a`
- Evidência: workflow `30575810174`, artifact `8772631486`

## Itens aprovados

- identidade visual geral coerente com a direção de arte do personagem;
- paleta branca, azul profundo, preto e dourado consistente;
- silhueta principal legível;
- turnaround contém frente, costas e duas laterais;
- PNGs possuem canal alpha;
- icons individuais existem nos tamanhos declarados;
- intake, checksum e budget técnico foram aprovados.

## Bloqueios

### 1. Portraits exportados em escala incorreta

Os três portraits 1024×1024 possuem conteúdo útil aproximado de apenas 102–108 px de largura e 109–128 px de altura, ocupando uma fração muito pequena do canvas. Isso impede uso adequado em HUD, diálogo, seleção e batalha.

Arquivos afetados:

- `portrait_lian_wu__neutral_raw.png`
- `portrait_lian_wu__happy_raw.png`
- `portrait_lian_wu__battle_raw.png`

Correção exigida: recortar e reenquadrar cada portrait para preencher o canvas, mantendo margem segura uniforme, foco no rosto e transparência real.

### 2. Source master contém elementos editoriais embutidos

`char_lian_wu__master_raw.png` inclui logo, nome do personagem, textos e pinceladas de apresentação. Esse arquivo é uma prancha promocional, não um source master limpo para produção.

Correção exigida: exportar uma versão limpa do personagem, sem logo, copy, labels ou elementos gráficos externos, preservando somente o personagem em fundo transparente.

### 3. Inconsistência entre vistas laterais

As vistas laterais não apresentam o armamento com a mesma leitura visual. Uma lateral mostra uma bainha/arma azul dominante, enquanto a outra apresenta lâminas cinzas expostas com configuração diferente. Isso prejudica continuidade de modelagem, animação e sprites direcionais.

Arquivos afetados:

- `char_lian_wu__side_left_raw.png`
- `char_lian_wu__side_right_raw.png`

Correção exigida: definir configuração canônica de arma, bainha, quantidade, posição e orientação, reproduzindo-a de forma coerente em frente, costas e laterais.

## Melhorias recomendadas

- padronizar margens do turnaround;
- revisar alinhamento de pés e altura entre as quatro vistas;
- validar legibilidade dos icons em 32 px e 64 px em fundo claro e escuro;
- manter o personagem centralizado pelo pivô corporal, não apenas pelo bounding box visual;
- gerar uma prancha de comparação automática para a v1.0.1.

## Decisão

A versão v1.0.0 permanece preservada e auditável, mas não está aprovada para importação no Taijifu Masters.

Próxima versão exigida:

- tag: `assets-pack-01-v1.0.1`
- ZIP: `PACK_01_LIAN_WU_BASE_FINAL_v1.0.1.zip`
- status inicial: `published_pending_forge_validation`
