# Arquitetura

Visão geral do backend — como o dado entra, vira previsão, vira oportunidade, e
eventualmente chega no usuário. Documentos mais específicos (cada família de modelo,
formato de odds, runbook operacional) ficam pra depois; isto aqui é o mapa.

## As três aplicações

- **`backend/`** — tudo que segue neste documento.
- **`frontend/`** — dashboard interno (React), consome só `backend/app/api/routes/*`,
  nunca fala com o banco direto.
- **`landing/`** — site público de captação de lead pro WhatsApp, também independente,
  fala com `POST /api/leads` (`app/api/routes/leads.py`).

## Fluxo de dado, ponta a ponta

```
fonte externa (API-Football, football-data.org, odds-api.io)
    -> app/engine/integrations/*        (cliente HTTP cru de cada fonte)
    -> app/engine/providers/*           (normaliza pra um DTO comum: NormalizedFixture,
                                          NormalizedOddsMarket, etc. — a única camada que
                                          sabe o formato específico de cada fonte)
    -> storage function do provider     (grava no schema comum: fixtures, odds_snapshots,
                                          teams, ...)
    -> app/engine/jobs/*                (orquestra: quando sincronizar o quê, paginação,
                                          pacing de rate limit; chamado pelo scheduler)
    -> app/engine/models/*              (Poisson/Maher: calcula força de ataque/defesa
                                          por time a partir do histórico, gera probabilidade
                                          por mercado)
    -> app/engine/valuebet/valuebet.py  (compara probabilidade do modelo com a odd real:
                                          edge, confidence, data_quality, opportunity_score)
    -> app/services/*                   (monta a resposta pra API: dashboard, análise de
                                          partida, snapshot de previsão, notificação)
    -> app/api/routes/*                 (HTTP — o único ponto que frontend/landing tocam)
```

### Por que "integrations" e "providers" são camadas separadas

`integrations/` fala HTTP com uma API externa específica e devolve o que ela devolve.
`providers/` traduz isso pra um formato comum (`NormalizedFixture`, `NormalizedTeam`,
`NormalizedOddsMarket`/`NormalizedOddsValue`) e grava no schema. Nada fora de
`providers/` sabe o formato de resposta da API-Football ou do odds-api.io — se uma
fonte trocar de formato, ou se uma fonte nova entrar, só essa camada muda.

Duas fontes de odds hoje: `api_football_odds.py` (odds pré-jogo por partida, captura
automática — `app/engine/jobs/odds.py`) e `odds_api_io_odds.py` (Bet365 + Superbet,
casamento por nome de time via `app/engine/teammatch.py` — `app/engine/jobs/
multi_bookmaker_odds.py`). Nenhuma substitui a outra; `odds_storage.store_markets`
grava as duas no mesmo jeito, `valuebet.fetch_latest_odds` pega a melhor odd entre
bookmakers disponíveis.

**Deliberadamente não abstraído ainda:** `StatisticsProvider` (só existe uma fonte,
API-Football, pra estatística/lesão/escalação — abstrair sem uma segunda fonte real
seria inventar uma interface sem propósito). Mesma lógica pra normalização central de
jogador/competição/mercado — uma fonte cada, sem duplicação real a resolver.

### Casamento de nome de time

`app/engine/teammatch.py` — times têm um id canônico (`teams.id`) e colunas de id
externo por fonte (`api_football_id`, `football_data_id`) quando a fonte já dá um id
estável. Quando não dá (odds-api.io manda só o nome), casa por normalização de string
(remove acento, remove ruído tipo "FC"/"SAF", compara substring com guarda de tamanho
mínimo) — `names_match()`, usada tanto na captura de odds multi-casa quanto em
qualquer lugar futuro que precise casar nome de time sem id.

## Modelos estatísticos e versionamento

Cada família de modelo (`app/engine/models/poisson_goals.py`, `corners.py`,
`cards.py`, `players.py`) exporta um `MODEL_VERSION` (ex.: `"poisson-maher-v1"`).
Essa versão é gravada junto com toda previsão (`prediction_snapshots.model_version`,
via `app/services/snapshot_service.py`) e com todo backtest (`model_versions` +
`backtest_runs`, via `app/engine/backtest/backtest.py`). Isso existe pra nunca
comparar a acurácia de uma versão de modelo contra decisões tomadas por outra —
mudar a fórmula de um modelo é sempre uma versão nova, nunca uma edição silenciosa.

Gols e escanteios/cartões usam Poisson com força de ataque/defesa por time (Maher,
1982) — ver docstring de `calculate_opportunity_score` em `valuebet.py` pra como a
probabilidade vira "vale a pena olhar". Jogador usa taxa por 90 minutos jogados,
excluindo quem está de fora por lesão/escalação confirmada.

## Value betting

`app/engine/valuebet/valuebet.py`:

- `edge = model_probability - implied_probability` (`implied_probability = 1/odd`)
- `data_quality_score(n_matches, has_odds)` — 0-100, peso 80 pro tamanho de amostra
  (satura em 30 jogos), peso 20 pra ter odd capturada. Documentado em detalhe (o que
  entra, o que ainda não entra e por quê) na própria função.
- `calculate_opportunity_score(edge, confidence, quality)` — a fórmula de ranking,
  auditável numa linha, com uma seção inteira de docstring sobre o que ela NÃO mede
  (correlação entre mercados da mesma partida, estabilidade da odd no tempo, CLV).
  Ler a docstring antes de mudar o peso de qualquer fator — cada peso ali existe
  porque reflete um dado real que o sistema tem, nunca um número escolhido a dedo.

## Backtest — duas ferramentas, dois propósitos

- **`app/engine/backtest/backtest.py`** (walk-forward, `run_goals_backtest`): pra cada
  partida já jogada, recalcula a previsão usando SÓ o histórico anterior a ela (janela
  expansiva), e mede calibração — Brier score e taxa de acerto. Não mede ROI: não
  existe odd histórica de anos atrás no banco, só a partir de quando começamos a
  capturar (`odds_snapshots`).
- **`app/engine/backtest/historical_eval.py`**: mede ROI real contra as odds que JÁ
  temos capturadas e cujo jogo já terminou — universo menor (só o que foi capturado
  desde que o sistema existe), mas com odd de mercado de verdade.

As duas compartilham `resolve_actual(market_key, actuals)` (`backtest.py`) — a mesma
regra decide o que é WIN/LOSS pra qualquer mercado de gols, num lugar só. Mercados com
estado PUSH/VOID (ex.: `draw_no_bet_home/away` numa partida empatada) devolvem `None`
de propósito — a coluna `actual_outcome` é `BOOLEAN`, não tem onde guardar um terceiro
estado ainda, e o sistema prefere ficar `NULL` a inventar WIN ou LOSS errado.

## Fechando o ciclo: resultado real

`app/services/result_tracking.py` (`resolve_pending_snapshots`, chamado no fim de
`daily_job.run_daily_sync`) — toda previsão em `prediction_snapshots` com jogo já
terminado e mercado resolvível vira WIN/LOSS de verdade. Sem isso, uma previsão
salva nunca era conferida contra o resultado — o produto dizia "70% de chance" e
ninguém nunca sabia se aconteceu.

## Fila de notificação e WhatsApp

Duas coisas bem separadas:

- **Broadcast diário** (`app/services/opportunity_notifications.py`,
  `enqueue_daily_opportunities`, chamado no fim de `daily_job.run_daily_sync`): pega
  as melhores oportunidades do dia (mesmo ranking do dashboard, mas com um corte de
  confiança mínima — `média`/`alta`, não `baixa` — que o dashboard não tem porque lá
  tem aviso visual de contexto pro usuário julgar; numa notificação isolada não tem
  esse contexto) e enfileira uma mensagem por lead, limitada por plano
  (`PLAN_LIMITS = {"gratis": 1, "pro": 3}`) em `app/services/notifications/queue.py`
  (`enqueue`, idempotente por `idempotency_key`, formato `lead:{id}:{data}:
  {fixture}:{mercado}` — nunca manda a mesma oportunidade 2x no mesmo dia).
- **Comando sob demanda** (`app/services/whatsapp_commands.py` +
  `app/api/routes/whatsapp.py`): usuário manda `/odds` em conversa direta, o CodeChat
  chama nosso webhook (`POST /api/whatsapp/webhook`), a gente responde na hora — não
  passa pela fila, é pergunta/resposta síncrona, não broadcast.

`app/services/notifications/queue.py` (`process_pending`) é quem de fato manda —
pega da fila com `FOR UPDATE SKIP LOCKED`, chama o `WhatsAppProvider` configurado,
tenta de novo até `max_attempts`, marca `dead_letter` se esgotar. **Ainda não está
ligado no scheduler automaticamente** — isso é uma decisão deliberada (ver
`app/services/notifications/provider.py`): a fila só registra até alguém decidir
ligar o envio automático de verdade.

### CodeChat

`app/services/notifications/provider.py` — `WhatsAppProvider` é um Protocol;
`ConsoleWhatsAppProvider` (só loga, nunca manda de verdade) é o padrão sempre que
`CODECHAT_BASE_URL`/`CODECHAT_GLOBAL_API_KEY`/`CODECHAT_INSTANCE_NAME` não estão
configurados. Com os três configurados, usa `CodeChatProvider` — CodeChat é um
WhatsApp self-hosted (container `api_codechat` já rodando na VM, porta 28080) com
formato de rota/corpo confirmado direto no swagger da própria instância (`GET /docs`),
não em documentação externa. `backend/scripts/codechat_manager.py` é o CLI de gestão
(criar instância, parear via QR, checar status, configurar webhook, mandar teste
manual) — nunca lê a API key de lugar nenhum do repo, só de variável de ambiente.

**Isolamento de instância:** o servidor CodeChat hospeda várias instâncias de vários
projetos diferentes. `CODECHAT_INSTANCE_NAME` é fixo em `"projetobets"` — o provider
nunca resolve pra nenhuma outra instância do servidor.

## Testes

`backend/tests/` — integração real contra Postgres, não mockado (decisão deliberada:
ver histórico de por que — dado real pegou bug que mock não pegaria, ex.: o achado de
`data_quality=3` virando "100% de probabilidade" só apareceu rodando contra dado de
produção de verdade). Convenção: dado sintético usa id alto (900000+) pra nunca colidir
com dado real, fixture do pytest limpa no teardown. Onde popular fixture+odds+modelo
completo seria caro só pra testar uma camada de cima (ex.: fila de notificação,
comando de WhatsApp), a função aceita um parâmetro opcional pra injetar dado real (não
mock) pré-construído — mesmo padrão usado em `queue.process_pending(provider=...)`.

`python -m pytest tests/ -q` — 93 testes nesta escrita deste documento.
