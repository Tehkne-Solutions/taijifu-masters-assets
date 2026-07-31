# Entrada de spritesheets — First Playable

A produção artística pode entregar cada lutador como um único spritesheet RGBA, desde que a grade não possua margem nem gutter. A ferramenta recorta e nomeia os 44 frames canônicos sem aprovar o lote automaticamente.

## 1. Gerar o mapa da grade

```bash
python tools/generate_first_playable_layout.py lian_wu intake/lian-wu-layout.json
python tools/generate_first_playable_layout.py training_rival intake/rival-layout.json
```

O padrão usa células de 512×512, oito colunas, seis linhas, `gutter=0` e `margin=0`.

## 2. Validar sem escrever

```bash
python tools/import_first_playable_spritesheet.py \
  intake/lian-wu.png intake/lian-wu-layout.json --dry-run
```

## 3. Recortar o pack

```bash
python tools/import_first_playable_spritesheet.py \
  intake/lian-wu.png intake/lian-wu-layout.json
```

O resultado é gravado em:

```text
production/first_playable/lian_wu/first_playable_lot_01/animations/
```

Para o Rival, o destino equivalente usa `training_rival`.

## Regras bloqueantes

- exatamente 44 células mapeadas;
- matriz 6/8/3/2/2/6/3/5/3/6;
- nenhuma célula reutilizada;
- imagem RGBA;
- dimensões exatas da grade;
- células entre 128×128 e 1024×1024;
- `gutter=0` e `margin=0`;
- destino existente só é substituído com `--replace`.

Depois do recorte, ainda são obrigatórios o preflight técnico, a revisão na bancada visual do Godot e a aprovação artística.

Assinatura: Tehkné Solutions
