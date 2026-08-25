# ProjetoBets

Motor de análise de apostas esportivas (futebol): modelos estatísticos (Poisson/Maher
para gols, escanteios, cartões, e taxa por 90 min para jogadores), comparação contra
odds reais de múltiplas casas, backtest com validação walk-forward (sem vazamento de
dado futuro), e um canal de distribuição via WhatsApp.

## Estrutura

Três aplicações independentes neste monorepo:

- **`backend/`** — API FastAPI + motor de análise + jobs de sincronização + fila de
  notificação WhatsApp. Ver [`backend/README.md`](backend/README.md) (se existir) ou
  [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) pro detalhe.
- **`frontend/`** — dashboard interno (React/Vite): lista de partidas, análise por
  jogo, simulador de bilhete, backtests.
- **`landing/`** — site público de captação de leads pro produto WhatsApp (React/Vite,
  independente do frontend interno — design e propósito diferentes).

## Rodando localmente

**Backend** (`backend/`):
```
python -m venv venv && venv\Scripts\activate   # ou source venv/bin/activate no Linux/Mac
pip install -r requirements.txt
# preencher .env na raiz do repo (não do backend/) com DB_HOST/PORT/NAME/USER/PASSWORD,
# API_FOOTBALL_KEY, FOOTBALL_DATA_ORG_KEY — ver app/core/config.py pra lista completa
python scripts/bootstrap_db.py    # cria o schema (core/schema.sql), idempotente
uvicorn app.main:app --reload --port 8010
```

**Scheduler** (sincronização automática — fixtures, odds, estatísticas, resolução de
previsões, fila de notificação):
```
python scripts/run_scheduler.py
```

**Frontend** / **Landing**:
```
npm install && npm run dev
```

## Testes

```
cd backend
python -m pytest tests/ -q
```

Testes de integração real contra Postgres (não mockado) — precisa do `.env`
configurado com um banco acessível. Ver [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md#testes)
pra convenção usada (fixture cria dado sintético com id alto, limpa no teardown).

## Documentação

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — visão geral do sistema: fluxo de
  dado ponta a ponta, camadas do backend, arquitetura de provider, versionamento de
  modelo, backtest, fila de notificação, integração WhatsApp.

Documentos mais específicos (fontes de dado, modelo de dado, cada família de modelo
estatístico, formato de odds, metodologia de backtest, runbook operacional) ainda não
escritos — pedir sob demanda.
