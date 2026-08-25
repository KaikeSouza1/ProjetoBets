"""Pull diário de fixtures via API-Football. Uma chamada cobre todas as ligas do mundo para a data
pedida; aqui filtramos para as ligas-alvo (as 6 semeadas em `leagues`) antes de gravar.

Fetch/normalização vêm de `providers.api_football_fixtures` — este módulo só orquestra
(filtra liga-alvo, faz upsert de venue/time/árbitro/partida)."""
from datetime import date as date_cls

from app.core import db
from app.engine import teammatch
from app.engine.providers import api_football_fixtures
from app.engine.providers.fixtures import NormalizedFixture


def _target_league_ids(cur) -> set[int]:
    cur.execute("SELECT id FROM leagues")
    return {row[0] for row in cur.fetchall()}


def _upsert_venue(cur, venue) -> int | None:
    if not venue:
        return None
    cur.execute(
        """INSERT INTO venues (id, name, city) VALUES (%s, %s, %s)
           ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, city = EXCLUDED.city""",
        (venue.external_id, venue.name, venue.city),
    )
    return venue.external_id


def _upsert_team(cur, team) -> int:
    return teammatch.upsert_team(cur, "api-football", team.external_id, team.name, team.logo_url)


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


def _store_fixture(cur, fixture: NormalizedFixture):
    venue_id = _upsert_venue(cur, fixture.venue)
    home_team_id = _upsert_team(cur, fixture.home_team)
    away_team_id = _upsert_team(cur, fixture.away_team)
    referee_id = _upsert_referee(cur, fixture.referee_name)

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
            fixture.external_id, fixture.league_external_id, fixture.season, fixture.round,
            fixture.date, fixture.status, fixture.elapsed,
            referee_id, venue_id, home_team_id, away_team_id,
            fixture.home_goals, fixture.away_goals, fixture.home_goals_ht, fixture.away_goals_ht,
        ),
    )


def sync_fixtures_for_date(day: date_cls) -> int:
    fixtures = api_football_fixtures.fetch_fixtures_for_date(day)

    conn = db.get_connection()
    saved = 0
    try:
        with conn.cursor() as cur:
            target_ids = _target_league_ids(cur)
            for fixture in fixtures:
                if fixture.league_external_id not in target_ids:
                    continue
                _store_fixture(cur, fixture)
                saved += 1
        conn.commit()
    finally:
        conn.close()

    print(f"[fixtures_daily] {day.isoformat()}: {len(fixtures)} jogos no mundo, {saved} salvos (ligas-alvo)")
    return saved
