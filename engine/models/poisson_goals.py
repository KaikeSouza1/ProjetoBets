"""Modelo de gols: Poisson com força ofensiva/defensiva por equipe (casa/fora separados).

Referência clássica (Maher, 1982): cada time tem uma força de ataque e de defesa,
calibradas contra a média da liga; o número esperado de gols de uma partida é o
produto dessas forças pela média da liga. É explicável: cada número do resultado
final rastreia até uma média real dos jogos capturados.
"""
from dataclasses import dataclass, field

from scipy.stats import poisson

from engine import db

MAX_GOALS = 9  # teto da matriz de placar; probabilidade acima disso é desprezível

GOAL_LINES = [0.5, 1.5, 2.5, 3.5, 4.5]


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
    league_avg_home_goals: float
    league_avg_away_goals: float
    strengths: dict[int, TeamStrength] = field(default_factory=dict)


def _fetch_matches(league_id: int) -> list[tuple]:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT football_data_code FROM leagues WHERE id = %s", (league_id,))
            row = cur.fetchone()
            if not row or not row[0]:
                raise ValueError(f"liga {league_id} sem football_data_code")
            code = row[0]

            cur.execute(
                """SELECT home_team_id, away_team_id, home_goals, away_goals
                   FROM fd_matches
                   WHERE competition_code = %s AND status = 'FINISHED'
                     AND home_team_id IS NOT NULL AND away_team_id IS NOT NULL
                     AND home_goals IS NOT NULL AND away_goals IS NOT NULL
                   ORDER BY utc_date""",
                (code,),
            )
            return cur.fetchall()
    finally:
        conn.close()


def build_league_model(league_id: int) -> LeagueModel:
    matches = _fetch_matches(league_id)
    if not matches:
        raise ValueError(f"liga {league_id}: nenhum resultado disponível — rode season_form.sync_league_results()")
    return compute_strengths_from_matches(league_id, matches)


def compute_strengths_from_matches(league_id: int, matches: list[tuple]) -> LeagueModel:
    """Núcleo puro do modelo — recebe a lista de partidas (home_id, away_id, gols_casa, gols_fora)
    já pronta. Usado tanto pela ingestão em tempo real quanto pelo backtest (que passa só as
    partidas anteriores à data prevista, para não vazar dado futuro)."""
    if not matches:
        raise ValueError(f"liga {league_id}: lista de partidas vazia")

    league_avg_home_goals = sum(m[2] for m in matches) / len(matches)
    league_avg_away_goals = sum(m[3] for m in matches) / len(matches)

    team_ids = {m[0] for m in matches} | {m[1] for m in matches}
    strengths = {}
    for team_id in team_ids:
        home_matches = [m for m in matches if m[0] == team_id]
        away_matches = [m for m in matches if m[1] == team_id]
        n_matches = len(home_matches) + len(away_matches)

        home_goals_scored = [m[2] for m in home_matches]
        home_goals_conceded = [m[3] for m in home_matches]
        away_goals_scored = [m[3] for m in away_matches]
        away_goals_conceded = [m[2] for m in away_matches]

        home_attack = (sum(home_goals_scored) / len(home_goals_scored) / league_avg_home_goals) if home_goals_scored else 1.0
        home_defense = (sum(home_goals_conceded) / len(home_goals_conceded) / league_avg_away_goals) if home_goals_conceded else 1.0
        away_attack = (sum(away_goals_scored) / len(away_goals_scored) / league_avg_away_goals) if away_goals_scored else 1.0
        away_defense = (sum(away_goals_conceded) / len(away_goals_conceded) / league_avg_home_goals) if away_goals_conceded else 1.0

        strengths[team_id] = TeamStrength(home_attack, home_defense, away_attack, away_defense, n_matches)

    return LeagueModel(league_id, league_avg_home_goals, league_avg_away_goals, strengths)


@dataclass
class FixtureGoalsPrediction:
    lambda_home: float
    lambda_away: float
    n_matches_home_team: int
    n_matches_away_team: int
    markets: dict[str, float]
    score_matrix: list  # list[list[float]] — score_matrix[h][a]


def predict_fixture(model: LeagueModel, home_team_id: int, away_team_id: int) -> FixtureGoalsPrediction:
    home = model.strengths.get(home_team_id)
    away = model.strengths.get(away_team_id)
    if home is None or away is None:
        raise ValueError("time sem força calculada nesta liga — dados insuficientes")

    lambda_home = model.league_avg_home_goals * home.home_attack * away.away_defense
    lambda_away = model.league_avg_away_goals * away.away_attack * home.home_defense

    score_matrix = [
        [poisson.pmf(h, lambda_home) * poisson.pmf(a, lambda_away) for a in range(MAX_GOALS + 1)]
        for h in range(MAX_GOALS + 1)
    ]
    total_mass = sum(sum(row) for row in score_matrix)
    score_matrix = [[p / total_mass for p in row] for row in score_matrix]

    p_home = sum(score_matrix[h][a] for h in range(MAX_GOALS + 1) for a in range(MAX_GOALS + 1) if h > a)
    p_draw = sum(score_matrix[h][a] for h in range(MAX_GOALS + 1) for a in range(MAX_GOALS + 1) if h == a)
    p_away = sum(score_matrix[h][a] for h in range(MAX_GOALS + 1) for a in range(MAX_GOALS + 1) if h < a)
    p_btts = sum(score_matrix[h][a] for h in range(1, MAX_GOALS + 1) for a in range(1, MAX_GOALS + 1))

    markets = {
        "home_win": p_home,
        "draw": p_draw,
        "away_win": p_away,
        "double_chance_1x": p_home + p_draw,
        "double_chance_x2": p_draw + p_away,
        "double_chance_12": p_home + p_away,
        "draw_no_bet_home": p_home / (p_home + p_away) if (p_home + p_away) > 0 else 0.0,
        "draw_no_bet_away": p_away / (p_home + p_away) if (p_home + p_away) > 0 else 0.0,
        "btts_yes": p_btts,
        "btts_no": 1 - p_btts,
    }
    for line in GOAL_LINES:
        over = sum(
            score_matrix[h][a]
            for h in range(MAX_GOALS + 1)
            for a in range(MAX_GOALS + 1)
            if (h + a) > line
        )
        key = str(line).replace(".", "_")
        markets[f"over_{key}"] = over
        markets[f"under_{key}"] = 1 - over

    return FixtureGoalsPrediction(
        lambda_home=lambda_home,
        lambda_away=lambda_away,
        n_matches_home_team=home.n_matches,
        n_matches_away_team=away.n_matches,
        markets=markets,
        score_matrix=score_matrix,
    )
