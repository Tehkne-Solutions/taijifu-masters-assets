# Pack 01 — First Playable Lot 01

## Objetivo

Este lote é o menor conjunto de produção capaz de substituir o desenho procedural de Lian Wu no First Playable.

Ele não conclui nem promove o Pack 01 completo. Seu único objetivo é liberar a integração visual real do personagem no combate P1 versus CPU.

## Escopo obrigatório

O lote deve conter dez estados de animação:

1. idle;
2. corrida;
3. início do salto;
4. subida no ar;
5. queda;
6. ataque leve;
7. defesa;
8. esquiva;
9. dano;
10. KO.

Cada frame deve ser PNG transparente, sem fundo incorporado, com pivô e linha dos pés consistentes.

## Identidade visual

- uma única espada;
- espada embainhada nos estados neutros;
- bainha fixada no quadril esquerdo;
- nenhuma leitura de segunda arma;
- roupa branca, azul-água e dourada;
- proporções e silhueta coerentes com o turnaround aprovado;
- visual comic-mangá 2.5D com contorno e separação clara do cenário.

## Estrutura do ZIP

```text
PACK_01_LIAN_WU_FIRST_PLAYABLE_LOT_01_v1.0.0/
├── manifest.json
├── checksums.sha256
├── runtime-map.json
├── approval.json
└── animations/
    ├── idle/
    ├── run/
    ├── jump_start/
    ├── airborne/
    ├── fall/
    ├── attack_light/
    ├── guard/
    ├── dodge/
    ├── hit/
    └── ko/
```

## Nomenclatura dos frames

```text
char_lian_wu__<animation>__f<frame-3-digits>.png
```

Exemplo:

```text
char_lian_wu__idle__f001.png
char_lian_wu__idle__f002.png
```

## Aprovação

O arquivo `approval.json` deve registrar:

- estado `approved`;
- versão do lote;
- checksum do manifesto;
- revisão visual do turnaround;
- confirmação de uma única arma;
- confirmação Web;
- confirmação Windows;
- assinatura `Tehkné Solutions`.

## Política de integração

O jogo pode importar este lote e remover o fallback procedural de Lian Wu somente quando todos os gates do contrato estiverem aprovados.

O Rival de Treino pode permanecer procedural temporariamente, mas o build não pode ser classificado como visualmente final enquanto isso ocorrer.

O lote deve preservar as hitboxes, hurtboxes, escala física e tempos de ataque definidos pelo gameplay. A animação visual não pode alterar as regras de combate.

## Estado atual

`art_required`

O candidato v1.0.1 existente não pode ser usado como release porque a continuidade da espada e da bainha ainda exige correção artística.

---

**Tehkné Solutions**
