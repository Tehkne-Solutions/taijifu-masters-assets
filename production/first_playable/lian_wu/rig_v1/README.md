# VM01-A2 — Lian Wu Rig v1

Assinatura: Tehkné Solutions

## Objetivo

Transformar a pose neutra canônica em uma base de rig reproduzível sem geração de nova arte.

## Gate de reconstrução

- fonte: `lian_wu_neutral.png` canônico;
- método: partição determinística e disjunta dos pixels opacos;
- partes: cabeça/cabelo, torso, braço esquerdo, braço direito, cintura/faixa, perna esquerda, perna direita e arma;
- pixels opacos de origem: `245156`;
- pixels atribuídos exatamente uma vez: `PASS`;
- diferença da reconstrução: `0`;
- `RIG_V1_RECONSTRUCTION=PASS`.

## Combat stance

A primeira tentativa de mover as peças rigidamente foi reprovada por criar costuras visíveis. Ela não é asset e não pode ser promovida.

Uma candidata contínua derivada da própria arte canônica pode ser usada somente como bancada de postura. Ela permanece `candidate_pending_godot_bench` e não libera animações.

## Estado

```text
RIG_V1_RECONSTRUCTION=PASS
COMBAT_STANCE_AUTHORING_ALLOWED=TRUE
GODOT_BENCH_REQUIRED=TRUE
CHARACTER_LOCK=BLOCKED
ANIMATION_PACK_ALLOWED=FALSE
```

O próximo gate é integrar neutral + candidata de stance em bancada 1920x1080 no runtime real do Godot e validar escala, pivot, facing, flip, baseline, sombra e hitbox.
