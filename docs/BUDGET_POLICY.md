# Política de budget técnico de assets

Cada pack publicado pode declarar limites em `catalog/packs.json`:

```json
{
  "budget": {
    "max_files": 64,
    "max_disk_bytes": 268435456
  }
}
```

O workflow baixa o ZIP canônico, valida checksum e intake, extrai o conteúdo em área temporária e executa:

```bash
tehkne-assets-forge check-budget extracted \
  --max-files 64 \
  --max-disk-bytes 268435456
```

Os limites são contratos de segurança e manutenção, não metas de ocupação. Um pack abaixo do limite ainda depende de revisão visual e aprovação explícita antes da importação no jogo.

O relatório `budget-report.json` é publicado junto dos relatórios de intake e checksum.
