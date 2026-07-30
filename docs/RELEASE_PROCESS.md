# Processo oficial de releases de assets

## Regra central

O histórico Git armazena somente catálogo, manifests, checksums e documentação. ZIPs, PNGs e outros binários de produção são anexados às GitHub Releases.

## Publicação

1. validar o ZIP e o manifest localmente;
2. calcular SHA-256;
3. criar a tag `assets-pack-XX-vMAJOR.MINOR.PATCH`;
4. anexar ZIP, checksum e manifest à Release;
5. atualizar `catalog/packs.json`;
6. executar o Tehkné Assets Forge;
7. revisar os artifacts visuais;
8. registrar aprovação;
9. integrar o bundle no jogo.

## Pack 01

```powershell
gh release view "assets-pack-01-v1.0.0" --repo "Tehkne-Solutions/taijifu-masters-assets"
```

O status `published_pending_forge_validation` significa que a existência da Release não equivale à aprovação visual ou integração no jogo.
