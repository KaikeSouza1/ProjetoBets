import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

API_FOOTBALL_KEY = os.environ["API_FOOTBALL_KEY"]
FOOTBALL_DATA_ORG_KEY = os.environ["FOOTBALL_DATA_ORG_KEY"]
ODDS_API_IO_KEY = os.environ.get("ODDS_API_IO_KEY")

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", "5432"))
DB_NAME = os.environ.get("DB_NAME", "projetobets")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres")

# Configuração OPERACIONAL, não uma verdade estatística: acima disso, uma partida é
# marcada STALE (dado desatualizado). 48h é um chute razoável pro scheduler atual (roda
# a cada 4h — 48h dá margem folgada pra falha temporária sem gerar alarme falso), não
# um número derivado de nenhuma análise. Ajuste livremente por ambiente via .env.
DATA_STALE_THRESHOLD_HOURS = int(os.environ.get("DATA_STALE_THRESHOLD_HOURS", "48"))

# captura automática de odds (engine/jobs/odds.py::capture_odds_for_upcoming_fixtures) —
# orçamento pensado pra não estourar os 100 req/dia da API-Football, compartilhados com
# fixtures_daily (~3/run) e o backfill de estatística (~3/partida finalizada ontem).
# Com scheduler a cada 4h (6 runs/dia), o padrão abaixo soma até 30 req/dia extras.
ODDS_CAPTURE_MAX_FIXTURES_PER_RUN = int(os.environ.get("ODDS_CAPTURE_MAX_FIXTURES_PER_RUN", "5"))
ODDS_CAPTURE_COOLDOWN_HOURS = int(os.environ.get("ODDS_CAPTURE_COOLDOWN_HOURS", "3"))

# Evolution API (WhatsApp não-oficial, self-hosted) — opcional de propósito. Sem os 3
# configurados, `notifications.provider.get_provider()` cai pro ConsoleWhatsAppProvider
# (só loga, nunca manda mensagem de verdade) — nunca falha por falta de credencial,
# só não envia nada real até você configurar isso.
EVOLUTION_API_URL = os.environ.get("EVOLUTION_API_URL")
EVOLUTION_API_KEY = os.environ.get("EVOLUTION_API_KEY")
EVOLUTION_API_INSTANCE = os.environ.get("EVOLUTION_API_INSTANCE")
