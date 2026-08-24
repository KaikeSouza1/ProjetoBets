"""Backfill pontual: temporada anterior das ligas europeias, pra sair do cold-start
(temporada 2026-27 mal começou — PL/SA/BL1/FL1 tinham 0 partida finalizada, PD só 7).
O modelo de gols usa TODO o histórico de fd_matches sem filtrar por temporada — isto só
adiciona dado real na mesma tabela, nenhuma fórmula muda.

Idempotente (fd_match_id é a chave, ON CONFLICT já trata reexecução)."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core import db
from app.engine.jobs import season_form

# BSA (Brasil) não entra — calendário é o ano civil, já tem 225/380 partidas da
# temporada atual, não precisa de temporada anterior pra sair do cold-start
LEAGUES_TO_BACKFILL = [
    (39, "Premier League"), (140, "La Liga"), (135, "Serie A (Italy)"),
    (78, "Bundesliga"), (61, "Ligue 1"),
]
PREVIOUS_SEASON_START_YEAR = 2025
PACING_SECONDS = 6.5  # limite football-data.org: 10 req/min

if __name__ == "__main__":
    db.bootstrap()
    for league_id, name in LEAGUES_TO_BACKFILL:
        try:
            saved = season_form.sync_league_results(league_id, season=PREVIOUS_SEASON_START_YEAR)
            print(f"[backfill] {name}: {saved} partidas da temporada {PREVIOUS_SEASON_START_YEAR}-{PREVIOUS_SEASON_START_YEAR + 1}")
        except Exception as exc:
            print(f"[backfill] falhou {name}: {exc}")
        time.sleep(PACING_SECONDS)
