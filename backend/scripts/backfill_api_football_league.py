"""Backfill pontual: temporada atual completa de toda liga SEM football_data_code
(hoje só Copa do Brasil) via API-Football — 1 chamada por liga cobre a temporada
inteira (API-Football não pagina fixtures por liga+temporada).

Sem isso, essas ligas nunca saem do cold-start: o sync diário (`fixtures_daily.
sync_fixtures_for_date`) só alcança ontem/hoje/amanhã, e o backfill de temporada
anterior (`backfill_previous_season.py`) só cobre ligas com football_data_code
(football-data.org). Idempotente (fixtures.id é a chave, ON CONFLICT já trata
reexecução).

Uso: python scripts/backfill_api_football_league.py [season]
season default: ano corrente (competições domésticas brasileiras seguem ano civil)."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core import db
from app.engine.jobs import fixtures_daily

PACING_SECONDS = 6.5  # limite API-Football: 10 req/min


def _leagues_without_football_data_code() -> list[tuple[int, str]]:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM leagues WHERE football_data_code IS NULL")
            return cur.fetchall()
    finally:
        conn.close()


if __name__ == "__main__":
    import datetime

    season = int(sys.argv[1]) if len(sys.argv) > 1 else datetime.date.today().year
    db.bootstrap()
    leagues = _leagues_without_football_data_code()
    if not leagues:
        print("[backfill] nenhuma liga sem football_data_code — nada a fazer")
    for league_id, name in leagues:
        try:
            saved = fixtures_daily.sync_fixtures_for_league_season(league_id, season)
            print(f"[backfill] {name} (id={league_id}), temporada {season}: {saved} partidas salvas")
        except Exception as exc:
            print(f"[backfill] falhou {name} (id={league_id}): {exc}")
        time.sleep(PACING_SECONDS)
