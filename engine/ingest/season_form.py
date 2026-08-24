"""Resultados da temporada e classificação via football-data.org — cobre exatamente o
buraco que a API-Football deixa (temporada atual bloqueada no plano Free)."""
from datetime import date as date_cls

from engine import db, teammatch
from engine.sources import football_data


def _league_fd_code(cur, league_id: int) -> str | None:
    cur.execute("SELECT football_data_code FROM leagues WHERE id = %s", (league_id,))
    row = cur.fetchone()
    return row[0] if row else None


def sync_league_results(league_id: int) -> int:
    conn = db.get_connection()
    saved = 0
    try:
        with conn.cursor() as cur:
            code = _league_fd_code(cur, league_id)
            if not code:
                raise ValueError(f"liga {league_id} sem football_data_code — rode reference.sync_target_leagues()")

            payload = football_data.get(f"competitions/{code}/matches")  # sem filtro de status: finalizados + agendados de uma vez
            for m in payload.get("matches", []):
                home_id = teammatch.upsert_team(cur, "football-data-org", m["homeTeam"]["id"], m["homeTeam"]["name"])
                away_id = teammatch.upsert_team(cur, "football-data-org", m["awayTeam"]["id"], m["awayTeam"]["name"])
                season_year = int(m["season"]["startDate"][:4]) if m.get("season") else None
                score = m["score"]["fullTime"]

                cur.execute(
                    """INSERT INTO fd_matches (
                           fd_match_id, competition_code, season_start_year, matchday, utc_date, status,
                           home_team_id, away_team_id, home_team_name_raw, away_team_name_raw,
                           home_goals, away_goals, fetched_at
                       ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, now())
                       ON CONFLICT (fd_match_id) DO UPDATE SET
                           status = EXCLUDED.status, home_goals = EXCLUDED.home_goals,
                           away_goals = EXCLUDED.away_goals, fetched_at = now()""",
                    (
                        m["id"], code, season_year, m.get("matchday"), m["utcDate"], m["status"],
                        home_id, away_id, m["homeTeam"]["name"], m["awayTeam"]["name"],
                        score.get("home"), score.get("away"),
                    ),
                )
                saved += 1
        conn.commit()
    finally:
        conn.close()
    print(f"[season_form] liga {league_id} ({code}): {saved} resultados sincronizados")
    return saved


def sync_standings(league_id: int, snapshot_date: date_cls | None = None) -> int:
    snapshot_date = snapshot_date or date_cls.today()
    conn = db.get_connection()
    saved = 0
    try:
        with conn.cursor() as cur:
            code = _league_fd_code(cur, league_id)
            if not code:
                raise ValueError(f"liga {league_id} sem football_data_code — rode reference.sync_target_leagues()")

            payload = football_data.get(f"competitions/{code}/standings")
            total_table = next((s["table"] for s in payload["standings"] if s["type"] == "TOTAL"), [])

            for row in total_table:
                team_id = teammatch.upsert_team(cur, "football-data-org", row["team"]["id"], row["team"]["name"])
                cur.execute(
                    """INSERT INTO standings_snapshots (
                           league_id, season, snapshot_date, team_id, rank, points,
                           played, win, draw, lose, goals_for, goals_against, source
                       ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'football-data-org')
                       ON CONFLICT (league_id, season, snapshot_date, team_id, source) DO UPDATE SET
                           rank = EXCLUDED.rank, points = EXCLUDED.points, played = EXCLUDED.played,
                           win = EXCLUDED.win, draw = EXCLUDED.draw, lose = EXCLUDED.lose,
                           goals_for = EXCLUDED.goals_for, goals_against = EXCLUDED.goals_against""",
                    (
                        league_id, snapshot_date.year, snapshot_date, team_id, row["position"], row["points"],
                        row["playedGames"], row["won"], row["draw"], row["lost"],
                        row["goalsFor"], row["goalsAgainst"],
                    ),
                )
                saved += 1
        conn.commit()
    finally:
        conn.close()
    print(f"[season_form] liga {league_id} ({code}): tabela de {saved} times salva ({snapshot_date})")
    return saved
