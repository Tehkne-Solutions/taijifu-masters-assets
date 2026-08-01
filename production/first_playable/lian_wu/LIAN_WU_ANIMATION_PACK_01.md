# FP_CHAR_01_LIAN_WU — Animation Pack 01

Este estágio substitui a tentativa de gerar uma spritesheet monolítica por uma produção controlada em **dez packs de animação**. A entrega final continua sendo um único `FP_CHAR_01_LIAN_WU.png` 8×6.

## Estrutura de entrada

```text
intake/first_playable/
└── FP_CHAR_01_LIAN_WU.animation-packs/
    ├── idle.png
    ├── run.png
    ├── jump_start.png
    ├── airborne.png
    ├── fall.png
    ├── attack_light.png
    ├── guard.png
    ├── dodge.png
    ├── hit.png
    └── ko.png
```

Cada arquivo é uma tira horizontal RGBA, sem margem e sem gutter. Cada célula mede `512×512`.

| Pack | Arquivo | Frames | Dimensão |
|---|---|---:|---:|
| LNW_IDLE_01 | `idle.png` | 6 | 3072×512 |
| LNW_RUN_01 | `run.png` | 8 | 4096×512 |
| LNW_JUMP_START_01 | `jump_start.png` | 3 | 1536×512 |
| LNW_AIRBORNE_01 | `airborne.png` | 2 | 1024×512 |
| LNW_FALL_01 | `fall.png` | 2 | 1024×512 |
| LNW_ATTACK_LIGHT_01 | `attack_light.png` | 6 | 3072×512 |
| LNW_GUARD_01 | `guard.png` | 3 | 1536×512 |
| LNW_DODGE_01 | `dodge.png` | 5 | 2560×512 |
| LNW_HIT_01 | `hit.png` | 3 | 1536×512 |
| LNW_KO_01 | `ko.png` | 6 | 3072×512 |

## Trava visual

Todos os packs devem preservar:

- o mesmo Lian Wu;
- orientação nativa para a direita;
- jaqueta marcial branca com acentos azuis e dourados;
- calça escura;
- uma única katana;
- cabelo escuro preso;
- escala corporal e linha dos pés consistentes;
- contorno comic-mangá 2.5D;
- fundo transparente;
- corpo inteiro sem cortes.

Não são permitidos texto, logos, molduras, fundos opacos, troca de roupa, armas extras ou mudança de câmera.

## Montagem oficial

```bash
python tools/prepare_first_playable_generation_batch.py

python tools/assemble_first_playable_animation_packs.py \
  production/first_playable/lian_wu/animation-pack-01.json \
  --report artifacts/animation-pack-assembly/FP_CHAR_01_LIAN_WU.json
```

A ferramenta valida cada tira, recorta os 44 frames, posiciona cada frame pela layout canônica e executa novamente o gate do spritesheet final.

A saída obrigatória é:

```text
FIRST_PLAYABLE_ANIMATION_PACK_ASSEMBLY_OK lian_wu 44/44
```

Somente depois dessa saída o `FP_CHAR_01_LIAN_WU.png` pode seguir para o importador e para a revisão artística no Godot.

## Estado

```text
Contrato dos dez packs      pronto
Montador determinístico     pronto
Testes automatizados        pronto
Arte real produzida         0/44
Integração no jogo          aguardando arte aprovada
```

Assinatura: Tehkné Solutions
