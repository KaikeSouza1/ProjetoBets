"""Modelo de escanteios — independente do modelo de gols, mesma lógica de força
ataque/defesa (Maher), mas alimentado por 'Corner Kicks' de fixture_statistics.

Cold-start real: só temos estatística de partidas que nós mesmos buscamos via
fetch_statistics(fixture_id) — diferente dos gols, não existe um bulk histórico
gratuito para escanteios. Confiança começa baixa e cresce conforme o uso.
"""
from dataclasses import dataclass, field

from scipy.stats import poisson

from engine import db

MAX_CORNERS = 20
CORNER_LINES = [6.5, 7.5, 8.5, 9.5, 10.5]


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
                """SELECT f.home_team_id, f.away_team_id, fsh.value, fsa.value
                   FROM fixtures f
                   JOIN fixture_statistics fsh ON fsh.fixture_id = f.id AND fsh.team_id = f.home_team_id
                                                AND fsh.stat_type = 'Corner Kicks'
                   JOIN fixture_statistics fsa ON fsa.fixture_id = f.id AND fsa.team_id = f.away_team_id
                                                AND fsa.stat_type = 'Corner Kicks'
                   WHERE f.league_id = %s AND f.status = 'FT'
                     AND fsh.value IS NOT NULL AND fsa.value IS NOT NULL""",
                (league_id,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return [(h, a, int(ch), int(ca)) for h, a, ch, ca in rows if ch.strip().isdigit() and ca.strip().isdigit()]


def build_league_model(league_id: int) -> LeagueModel:
    matches = _fetch_matches(league_id)
    if not matches:
        raise ValueError(
            f"liga {league_id}: nenhuma partida com estatística de escanteio ainda — "
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
class FixtureCornersPrediction:
    lambda_home: float
    lambda_away: float
    n_matches_home_team: int
    n_matches_away_team: int
    markets: dict[str, float]


def predict_fixture(model: LeagueModel, home_team_id: int, away_team_id: int) -> FixtureCornersPrediction:
    home = model.strengths.get(home_team_id)
    away = model.strengths.get(away_team_id)
    if home is None or away is None:
        raise ValueError("time sem estatística de escanteio calculada — dados insuficientes")

    lambda_home = model.league_avg_home * home.home_attack * away.away_defense
    lambda_away = model.league_avg_away * away.away_attack * home.home_defense
    total_lambda = lambda_home + lambda_away

    markets = {}
    for line in CORNER_LINES:
        over = 1 - poisson.cdf(int(line), total_lambda)  # linha sempre X.5 -> cdf(int(line)) já exclui o empate
        key = str(line).replace(".", "_")
        markets[f"corner_over_{key}"] = over
        markets[f"corner_under_{key}"] = 1 - over

    return FixtureCornersPrediction(
        lambda_home=lambda_home,
        lambda_away=lambda_away,
        n_matches_home_team=home.n_matches,
        n_matches_away_team=away.n_matches,
        markets=markets,
    )
