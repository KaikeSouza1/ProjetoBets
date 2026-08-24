"""Pull diário de fixtures via API-Football. Uma chamada cobre todas as ligas do mundo para a data
pedida; aqui filtramos para as ligas-alvo (as 6 semeadas em `leagues`) antes de gravar."""
from datetime import date as date_cls

from engine import db, teammatch
from engine.sources import api_football


def _target_league_ids(cur) -> set[int]:
    cur.execute("SELECT id FROM leagues")
    return {row[0] for row in cur.fetchall()}


def _upsert_venue(cur, venue: dict | None):
    if not venue or not venue.get("id"):
        return None
    cur.execute(
        """INSERT INTO venues (id, name, city) VALUES (%s, %s, %s)
           ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, city = EXCLUDED.city""",
        (venue["id"], venue.get("name"), venue.get("city")),
    )
    return venue["id"]


def _upsert_team(cur, team: dict) -> int:
    return teammatch.upsert_team(cur, "api-football", team["id"], team["name"], team.get("logo"))


def _upsert_referee(cur, referee_name: str | None) -> int | None:
    if not referee_name:
        return None
    name = referee_name.split(",")[0].strip()
    cur.execute(
        """INSERT INTO referees (name) VALUES (%s)
           ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
           RETURNING id""",
        (name,),
    )
    return cur.fetchone()[0]


def sync_fixtures_for_date(day: date_cls) -> int:
    date_str = day.isoformat()
    results = api_football.get("fixtures", {"date": date_str})

    conn = db.get_connection()
    saved = 0
    try:
        with conn.cursor() as cur:
            target_ids = _target_league_ids(cur)
            for item in results:
                league_id = item["league"]["id"]
                if league_id not in target_ids:
                    continue

                venue_id = _upsert_venue(cur, item["fixture"].get("venue"))
                home_team_id = _upsert_team(cur, item["teams"]["home"])
                away_team_id = _upsert_team(cur, item["teams"]["away"])
                referee_id = _upsert_referee(cur, item["fixture"].get("referee"))

                fx = item["fixture"]
                goals = item["goals"]
                score_ht = item["score"]["halftime"]

                cur.execute(
                    """INSERT INTO fixtures (
                           id, league_id, season, round, date, status, elapsed,
                           referee_id, venue_id, home_team_id, away_team_id,
                           home_goals, away_goals, home_goals_ht, away_goals_ht, updated_at
                       ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, now())
                       ON CONFLICT (id) DO UPDATE SET
                           status = EXCLUDED.status, elapsed = EXCLUDED.elapsed,
                           home_goals = EXCLUDED.home_goals, away_goals = EXCLUDED.away_goals,
                           home_goals_ht = EXCLUDED.home_goals_ht, away_goals_ht = EXCLUDED.away_goals_ht,
                           referee_id = EXCLUDED.referee_id, updated_at = now()""",
                    (
                        fx["id"], league_id, item["league"]["season"], item["league"].get("round"),
                        fx["date"], fx["status"]["short"], fx["status"].get("elapsed"),
                        referee_id, venue_id, home_team_id, away_team_id,
                        goals.get("home"), goals.get("away"), score_ht.get("home"), score_ht.get("away"),
                    ),
                )
                saved += 1
        conn.commit()
    finally:
        conn.close()

    print(f"[fixtures_daily] {date_str}: {len(results)} jogos no mundo, {saved} salvos (ligas-alvo)")
    return saved
