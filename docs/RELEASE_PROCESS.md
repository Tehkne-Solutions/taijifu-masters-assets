# Processo oficial de releases de assets

## Regra central

O histórico Git armazena somente catálogo, manifests, checksums e documentação. ZIPs, PNGs e outros binários de produção são anexados às GitHub Releases.

## Publicação

1. validar o ZIP e o manifest localmente;
2. calcular SHA-256;
3. criar ou atualizar a entrada em `catalog/packs.json` com tag, nome canônico e status pendente;
4. integrar a alteração do catálogo no ramo `main`;
5. criar a tag `assets-pack-XX-vMAJOR.MINOR.PATCH`;
6. publicar a Release anexando ZIP, checksum e manifest;
7. executar ou confirmar o workflow `Validate Asset Vault`;
8. registrar o SHA-256 calculado no catálogo quando ainda estiver ausente;
9. executar novamente a validação criptográfica;
10. revisar os artifacts visuais e o orçamento técnico;
11. registrar aprovação;
12. integrar o bundle no jogo.

A entrada do catálogo deve existir em `main` antes do evento `release.published`. O workflow de Release sempre lê o catálogo atual do ramo principal, não o commit apontado pela tag binária.

## Pack 01

```powershell
gh release view "assets-pack-01-v1.0.0" --repo "Tehkne-Solutions/taijifu-masters-assets"
```

O status `published_pending_forge_validation` significa que a existência da Release não equivale à aprovação visual ou integração no jogo.
