"""Adapter: API-Football -> NormalizedFixture. Só busca e normaliza — filtro de
liga-alvo e gravação continuam em `jobs/fixtures_daily.py` (isso é orquestração do
job, não contrato de fonte de dado)."""
from datetime import date as date_cls

from app.engine.integrations import api_football
from app.engine.providers.fixtures import NormalizedFixture, NormalizedTeam, NormalizedVenue

SOURCE = "api-football"


def fetch_fixtures_for_date(day: date_cls) -> list[NormalizedFixture]:
    results = api_football.get("fixtures", {"date": day.isoformat()})
    return [_normalize(item) for item in results]


def fetch_fixtures_for_league_season(league_external_id: int, season: int) -> list[NormalizedFixture]:
    """1 chamada devolve a temporada inteira da liga (API-Football não pagina isso) —
    usado pra backfill de liga sem football_data_code (ver jobs/backfill_api_football_league.py),
    já que `fetch_fixtures_for_date` só alcança o que o job diário sincroniza (janela de
    poucos dias), nunca o histórico passado."""
    results = api_football.get("fixtures", {"league": league_external_id, "season": season})
    return [_normalize(item) for item in results]


def _normalize(item: dict) -> NormalizedFixture:
    fx = item["fixture"]
    goals = item["goals"]
    score_ht = item["score"]["halftime"]

    venue_raw = fx.get("venue")
    venue = (
        NormalizedVenue(venue_raw["id"], venue_raw.get("name"), venue_raw.get("city"))
        if venue_raw and venue_raw.get("id")
        else None
    )

    home = item["teams"]["home"]
    away = item["teams"]["away"]

    return NormalizedFixture(
        external_id=fx["id"],
        league_external_id=item["league"]["id"],
        season=item["league"]["season"],
        round=item["league"].get("round"),
        date=fx["date"],
        status=fx["status"]["short"],
        elapsed=fx["status"].get("elapsed"),
        referee_name=fx.get("referee"),
        venue=venue,
        home_team=NormalizedTeam(home["id"], home["name"], home.get("logo")),
        away_team=NormalizedTeam(away["id"], away["name"], away.get("logo")),
        home_goals=goals.get("home"),
        away_goals=goals.get("away"),
        home_goals_ht=score_ht.get("home"),
        away_goals_ht=score_ht.get("away"),
        source=SOURCE,
    )
