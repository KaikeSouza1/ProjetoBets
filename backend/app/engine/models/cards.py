"""Modelo de cartões — independente dos modelos de gols e escanteios.
Conta cartão amarelo + vermelho como 1 cartão cada (convenção mais simples e comum
nos mercados 'total de cartões'). Mesmo cold-start real dos escanteios: só cresce
conforme fixture_detail.fetch_statistics() é chamado para partidas finalizadas.
"""
from dataclasses import dataclass, field

from scipy.stats import poisson

from app.core import db

CARD_LINES = [1.5, 2.5, 3.5, 4.5, 5.5]


def _to_int(value: str | None) -> int:
    if not value or not value.strip().isdigit():
        return 0
    return int(value)


@dataclass
class TeamStrength:
    home_attack: float
    home_defense: float
    away_attack: float
    away_defense: float
    n_matches: int


@dataclass
class LeagueModel:
    league_id: int
    league_avg_home: float
    league_avg_away: float
    strengths: dict[int, TeamStrength] = field(default_factory=dict)


def _fetch_matches(league_id: int):
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT f.id, f.home_team_id, f.away_team_id
                   FROM fixtures f
                   WHERE f.league_id = %s AND f.status = 'FT'
                     AND EXISTS (SELECT 1 FROM fixture_statistics fs WHERE fs.fixture_id = f.id)""",
                (league_id,),
            )
            fixtures = cur.fetchall()

            matches = []
            for fixture_id, home_id, away_id in fixtures:
                cur.execute(
                    """SELECT team_id, stat_type, value FROM fixture_statistics
                       WHERE fixture_id = %s AND stat_type IN ('Yellow Cards', 'Red Cards')""",
                    (fixture_id,),
                )
                by_team = {}
                for team_id, stat_type, value in cur.fetchall():
                    by_team.setdefault(team_id, 0)
                    by_team[team_id] += _to_int(value)
                if home_id in by_team and away_id in by_team:
                    matches.append((home_id, away_id, by_team[home_id], by_team[away_id]))
    finally:
        conn.close()
    return matches


def build_league_model(league_id: int) -> LeagueModel:
    matches = _fetch_matches(league_id)
    if not matches:
        raise ValueError(
            f"liga {league_id}: nenhuma partida com estatística de cartão ainda — "
            "rode fixture_detail.fetch_statistics(fixture_id) para partidas finalizadas"
        )

    league_avg_home = sum(m[2] for m in matches) / len(matches)
    league_avg_away = sum(m[3] for m in matches) / len(matches)

    team_ids = {m[0] for m in matches} | {m[1] for m in matches}
    strengths = {}
    for team_id in team_ids:
        home_m = [m for m in matches if m[0] == team_id]
        away_m = [m for m in matches if m[1] == team_id]
        n_matches = len(home_m) + len(away_m)

        home_for = [m[2] for m in home_m]
        home_against = [m[3] for m in home_m]
        away_for = [m[3] for m in away_m]
        away_against = [m[2] for m in away_m]

        home_attack = (sum(home_for) / len(home_for) / league_avg_home) if home_for else 1.0
        home_defense = (sum(home_against) / len(home_against) / league_avg_away) if home_against else 1.0
        away_attack = (sum(away_for) / len(away_for) / league_avg_away) if away_for else 1.0
        away_defense = (sum(away_against) / len(away_against) / league_avg_home) if away_against else 1.0

        strengths[team_id] = TeamStrength(home_attack, home_defense, away_attack, away_defense, n_matches)

    return LeagueModel(league_id, league_avg_home, league_avg_away, strengths)


@dataclass
class FixtureCardsPrediction:
    lambda_home: float
    lambda_away: float
    n_matches_home_team: int
    n_matches_away_team: int
    markets: dict[str, float]


def predict_fixture(model: LeagueModel, home_team_id: int, away_team_id: int) -> FixtureCardsPrediction:
    home = model.strengths.get(home_team_id)
    away = model.strengths.get(away_team_id)
    if home is None or away is None:
        raise ValueError("time sem estatística de cartão calculada — dados insuficientes")

    lambda_home = model.league_avg_home * home.home_attack * away.away_defense
    lambda_away = model.league_avg_away * away.away_attack * home.home_defense
    total_lambda = lambda_home + lambda_away

    markets = {}
    for line in CARD_LINES:
        over = 1 - poisson.cdf(int(line), total_lambda)
        key = str(line).replace(".", "_")
        markets[f"card_over_{key}"] = over
        markets[f"card_under_{key}"] = 1 - over

    return FixtureCardsPrediction(
        lambda_home=lambda_home,
        lambda_away=lambda_away,
        n_matches_home_team=home.n_matches,
        n_matches_away_team=away.n_matches,
        markets=markets,
    )
