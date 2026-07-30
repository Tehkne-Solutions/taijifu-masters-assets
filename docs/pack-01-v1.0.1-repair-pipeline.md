# Pack 01 v1.0.1 — pipeline de reparo

O helper `tools/repair_pack01_v101.py` executa apenas reparos determinísticos e mensuráveis sobre uma cópia extraída da v1.0.0.

## Corrige automaticamente

- portraits neutral, happy e battle: remove espaço transparente excessivo e reenquadra a arte;
- source master: substitui a composição promocional por uma referência frontal limpa;
- preserva estrutura e nomes dos arquivos;
- produz `repair-report-v1.0.1.json`.

## Não corrige automaticamente

- continuidade de espada, bainha ou acessórios entre as quatro vistas;
- diferenças de desenho que exigem pintura ou regeneração artística;
- aprovação visual final.

Esses itens continuam sendo gates manuais e impedem a publicação da Release v1.0.1 até serem resolvidos.

## Uso

```bash
python tools/repair_pack01_v101.py extracted-v1.0.0 staging-v1.0.1
```

O resultado é um staging para revisão, não uma Release aprovada. O ZIP canônico somente deve ser montado após a correção do turnaround e a nova revisão visual.
