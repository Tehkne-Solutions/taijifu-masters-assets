# First Playable Lot 01 — Esteira de release

## Objetivo

Transformar frames artisticamente aprovados de Lian Wu em um ZIP canônico, validado e pronto para o importador do repositório `taijifu-masters`.

## Entrada

```text
production/pack_01_lian_wu/first_playable_lot_01/
├── manifest.json
├── runtime-map.json
├── approval.json
└── animations/
```

O arquivo `approval.json` deve declarar:

```json
{
  "status": "approved",
  "signature": "Tehkné Solutions"
}
```

## Validação local

```bash
python tools/validate_first_playable_lot01.py \
  production/pack_01_lian_wu/first_playable_lot_01 \
  --report lot01-validation.json
```

O validador verifica:

- os dez estados obrigatórios;
- quantidade mínima de frames;
- nomenclatura canônica;
- sequência contínua a partir de `f001`;
- arquivos não vazios;
- aprovação explícita;
- assinatura da Tehkné Solutions;
- hashes SHA-256 dos frames.

## Artifact

O workflow gera:

```text
PACK_01_LIAN_WU_FIRST_PLAYABLE_LOT_01_v1.0.0.zip
PACK_01_LIAN_WU_FIRST_PLAYABLE_LOT_01_v1.0.0.zip.sha256
lot01-validation.json
```

O artifact ainda não deve ser tratado como release pública automaticamente. Após revisão visual final, ele pode ser publicado em GitHub Release e consumido pelo importador do jogo.

## Bloqueadores

- turnaround ainda marcado como `art_correction_required`;
- leitura de duas espadas;
- espada desembainhada em estado neutro;
- pivô ou linha dos pés inconsistente;
- frames ausentes ou fora de sequência;
- `approval.json` sem aprovação explícita.

Assinatura: Tehkné Solutions
