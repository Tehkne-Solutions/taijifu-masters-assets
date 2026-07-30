# Validação automática do Asset Vault

O workflow `Validate Asset Vault` usa uma versão fixada do **Tehkné Assets Forge** para impedir que mudanças futuras da ferramenta alterem silenciosamente a validação de um pack existente.

## Validação do catálogo

Executada em pull requests e pushes que alteram `catalog/**`:

```bash
tehkne-assets-forge validate-catalog catalog/packs.json
```

## Validação de Release

Executada quando uma Release é publicada ou manualmente por `workflow_dispatch`:

1. localiza exatamente um pack pelo `release_tag`;
2. baixa somente o ZIP cujo nome está no catálogo;
3. executa intake seguro sem extrair conteúdo fora da área temporária;
4. calcula o SHA-256;
5. compara com `sha256` quando o campo estiver registrado no catálogo;
6. publica relatórios de intake e checksum como artifact do workflow.

## Promoção de status

A publicação da Release não aprova automaticamente o pack.

Fluxo correto:

```text
published_pending_forge_validation
  -> checksum registrado no catálogo
  -> workflow verde com comparação SHA-256
  -> revisão visual e budget
  -> approved_for_game_import
```

Enquanto `sha256` estiver ausente, o workflow pode confirmar estrutura e segurança, mas o status deve continuar pendente.

## Execução manual do Pack 01

Na aba Actions, execute `Validate Asset Vault` e informe:

```text
assets-pack-01-v1.0.0
```

O SHA-256 calculado aparecerá no resumo do job e no artifact `checksum-report.json`.
