# Taijifu Masters — First Playable Visual Execution Plan

Status: active
Owner: Tehkné Solutions
Scope: First Playable visual milestone only

## 0. Regra de processo obrigatória

Nenhuma nova arte, código visual, animação, UI ou integração pode ser produzida imediatamente após feedback do playtest.

Todo material recebido (vídeo, screenshot, telemetry, ZIP, log, asset, referência) passa primeiro por:

1. ingestão;
2. verificação técnica;
3. comparação com contratos canônicos;
4. classificação do problema;
5. definição de hipótese;
6. plano de alteração mínimo;
7. implementação;
8. validação automática;
9. validação visual;
10. promoção.

Se um item não puder ser verificado, ele é marcado como `unverified` e não pode motivar mudança definitiva.

## 1. Evidência obrigatória por feedback

Para cada novo playtest registrar:

- build/commit testado;
- duração da sessão;
- dificuldade;
- vencedor e razão;
- distribuição de técnicas P1/P2;
- hits confirmados;
- defesa/parry/esquiva;
- pursuit events;
- climax events;
- Flow/Martial Code;
- recursos ausentes na telemetria;
- problemas visuais observados no vídeo;
- problemas de gameplay observados no vídeo;
- problemas que aparecem em ambos vídeo + telemetry;
- problemas que aparecem em apenas uma fonte.

Nenhuma conclusão deve misturar evidência visual e telemetry sem declarar qual fonte sustenta cada ponto.

## 2. Estado real do Visual Milestone 01

### Infraestrutura
- presenters reais no jogo: pronta;
- importador spritesheet: pronto;
- recorte/nomenclatura: pronto;
- Git LFS: pronto;
- preflight RGBA/transparência: pronto;
- release pipeline: pronto;
- Tehkné Assets Forge: pronto para checksum/intake/budget.

### Arte final
- Lian Wu premium: não produzido/aprovado;
- Rival premium: não produzido/aprovado;
- arena premium: não produzida/aprovada;
- VFX premium: não produzidos/aprovados;
- UI sprite-based premium: não produzida/aprovada.

Fallback procedural é somente desenvolvimento e nunca pode ser promovido como arte final.

## 3. Direção visual canônica

- comic/manga 2.5D martial fantasy;
- fighter readability próxima de arena fighters/Gunbound-like, sem copiar IP;
- personagens com silhueta forte, outline controlado, sombra de contato e rim-light discreto;
- cenário layered parallax, fighter-first;
- UI martial-fantasy ink, sprite-based, rápida e compacta;
- sem dashboard/site layout;
- sem glassmorphism;
- sem gradiente genérico como linguagem visual;
- sem glow neon/roxo tech como linguagem principal;
- sem texto embutido na arte;
- única assinatura permitida: Tehkné Solutions.

## 4. Ordem de produção bloqueante

### VM01-A — Lian Wu premium
Entregar primeiro um único personagem completo e jogável.

Estados mínimos:
- idle;
- run;
- jump_start;
- airborne;
- fall;
- land;
- air_jump;
- wall_climb;
- guard;
- parry;
- dodge;
- hit;
- posture_break;
- ko;
- tai_1 / tai_2 / tai_3;
- ji_1 / ji_2 / ji_3;
- fu_1 / fu_2 / fu_3;
- climax_charge;
- climax_cast.

Gate A: Lian Wu real deve substituir completamente o fallback procedural no jogo.

### VM01-B — Rival premium
Mesmo contrato de animação, identidade própria dark armor + ember + metal + brass.

Gate B: dois lutadores reais animados simultaneamente.

### VM01-C — Arena Ruínas do Caminho Triplo
Layers:
- sky_far;
- mountains_far;
- temple_silhouette;
- mist_mid;
- ruins_mid;
- foliage_mid;
- playfield_ground;
- platform_surfaces;
- foreground_rocks;
- foreground_foliage.

Animated:
- mist;
- leaves;
- cloth banners;
- embers;
- water/stream;
- ambient dust.

Gate C: procedural arena deixa de ser camada primária.

### VM01-D — Combat VFX
- hit_light;
- hit_heavy;
- guard_impact;
- parry_flash;
- dodge_trail;
- posture_break;
- mana_cast;
- stamina_exhaust;
- fire_climax;
- water_climax;
- earth_climax;
- air_climax.

Gate D: golpes e elementos têm leitura própria sem depender de texto HUD.

### VM01-E — Premium HUD/UI
- health_frame_p1/p2;
- posture;
- stamina;
- mana;
- combo;
- Tai/Ji/Fu;
- climax warning;
- round start;
- victory/defeat;
- pause;
- buttons;
- keycaps.

Gate E: UI visualmente identificável como jogo de luta/martial fantasy, não site.

## 5. Pipeline por asset pack

Cada pack passa por:

`brief -> geração -> candidate -> visual review -> technical validation -> import -> in-engine bench -> approval -> LFS/release -> game integration`

Nunca gerar e promover no mesmo passo.

Cada candidate deve ter:
- ID canônico;
- versão;
- resolução;
- pivot;
- facing;
- frame count;
- alpha;
- no borders/gutter quando aplicável;
- screenshot/evidence in-engine;
- review status.

## 6. Gate visual por personagem

Antes de produzir a animação inteira:

1. neutral pose;
2. combat stance;
3. silhouette test 25%;
4. palette test;
5. weapon/accessory continuity;
6. scale/pivot bench no Godot;
7. apenas depois gerar animation packs.

Se neutral/stance falhar, não gerar dezenas de frames.

## 7. Gate de animação

Para cada animação verificar:
- silhouette readable;
- anticipation;
- contact/key pose;
- follow-through;
- recovery;
- feet/ground consistency;
- weapon continuity;
- no limb duplication;
- no costume mutation;
- no camera/background embedded;
- playback legível na velocidade real do golpe.

Animação deve acompanhar frame data do jogo, não obrigar gameplay a se ajustar a arte inconsistente.

## 8. Gate de cenário

Verificar em 16:9:
- P1/P2 sempre destacam do background;
- plataforma jogável é inequívoca;
- foreground nunca mascara lutador;
- parallax não prejudica leitura;
- contraste não depende de glow;
- camera zoom mínimo/máximo continua seguro;
- tiles/surfaces conectam sem bordas.

## 9. Gate de UI

Prioridades:
1. vida;
2. postura;
3. stamina/mana;
4. timer/round;
5. combo/martial code;
6. warning de climax.

Informação secundária fica contextual, recolhida ou em menu.

Proibido:
- cards de dashboard;
- grandes caixas de texto durante combate;
- sobreposição persistente no centro da arena;
- linguagem visual de SaaS/website;
- excesso de bordas, sombras e glow.

## 10. Regra de resposta a novos uploads

Sempre que novo material for enviado:

### A. primeiro responder internamente
- o que é;
- qual versão;
- o que ele prova;
- o que ele não prova;
- quais regressões aparecem;
- qual mudança anterior ele valida/invalida.

### B. depois escolher ação
- `no_change`: evidência insuficiente;
- `tune`: parâmetro existente;
- `fix`: bug objetivo;
- `design`: mudança de regra;
- `art`: produção visual;
- `pipeline`: problema de esteira.

### C. depois implementar
Uma causa por PR sempre que possível.

## 11. Último playtest analisado — Sprint 2.1

Vídeo: ~74.7 s.
Telemetry: schema v4, MESTRE, duração registrada 67.722 s.

Dados objetivos:
- P1 perdeu por KO;
- feedback `balanced`;
- P1: 60 técnicas, 5 hits confirmados;
- P2: 25 técnicas, 9 hits confirmados;
- P2: 119.75 dano;
- P2: 48 pattern reads;
- P2: 45 pattern guards;
- P2: 49 pursuit jumps;
- P2: 3 climax started, 2 resolved;
- P2: max Flow 100;
- P1: 0 climax;
- P1 usou Fu/Ji de forma altamente repetitiva.

Leitura conjunta vídeo + telemetry:
- perseguição vertical existe, mas `49 pursuit_jump` em uma luta é excesso e visualmente vira comportamento saltitante/repetitivo;
- IA ainda usa guarda em excesso: 45 guards para 25 técnicas ofensivas;
- luta está mais longa e mais equilibrada que as primeiras builds;
- spam do jogador ainda existe: 60 técnicas para somente 5 hits;
- visual continua quase totalmente procedural e é agora o maior limitador de percepção de qualidade.

Lacuna de observabilidade:
- telemetry v4 não exporta Mana, portanto o playtest não comprova pelo JSON consumo/regeneração de Mana da Sprint 2.1; isso precisa ser instrumentado antes de balancear Mana por dados.

## 12. Próximas tarefas congeladas

P0 Visual:
- produzir e aprovar neutral + combat stance do Lian Wu;
- validar silhouette/pivot/scale no Godot;
- gerar animation packs de Lian Wu somente após aprovação.

P0 Gameplay observability:
- adicionar Mana à telemetry;
- medir air_jump/wall_climb;
- medir pursuit loop/unstuck.

P1 Gameplay após arte inicial:
- reduzir pursuit jump spam;
- reduzir pattern guard spam;
- manter dificuldade por decisão, não por atributos.

Assinatura: Tehkné Solutions
