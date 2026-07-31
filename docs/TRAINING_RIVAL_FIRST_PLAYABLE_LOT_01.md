# Rival de Treino — First Playable Lot 01

## Objetivo

Substituir o segundo fallback procedural do First Playable por um oponente visualmente coerente, legível e tecnicamente compatível com o runtime existente.

## Escopo mínimo

O lote exige 44 PNGs individuais distribuídos entre idle, run, jump_start, airborne, fall, attack_light, guard, dodge, hit e ko.

## Direção visual

- fantasia marcial comic-mangá 2.5D;
- silhueta compacta e defensiva;
- roupa carvão, osso, brasa e dourado dessaturado;
- uma única espada de treino em madeira;
- sem glow tecnológico roxo;
- sem leitura de personagem principal ou campeão;
- orientação nativa para a esquerda, com espelhamento no runtime;
- fundo transparente;
- pivô bottom-center e linha dos pés estável.

## Estrutura canônica

```text
PACK_TRAINING_RIVAL_FIRST_PLAYABLE_LOT_01_v1.0.0/
├── manifest.json
├── approval.json
├── checksums.sha256
├── runtime-map.json
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

## Nomenclatura

```text
char_training_rival__<animation>__f<frame-3-digits>.png
```

## Regra de aprovação

O lote só pode ser marcado como `approved` após validação lado a lado de escala, pivô, arma única, transparência, coerência de roupa e leitura de silhueta.

Assinatura: Tehkné Solutions
