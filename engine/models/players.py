"""Probabilidade de jogador: marcar, assistir, receber cartão.
minutos + finalizações/participação ofensiva + força defensiva do adversário (reaproveitada
do modelo de gols) — nunca gera número para jogador lesionado/suspenso/fora da lista quando
essa informação está disponível.
"""
import math
from dataclasses import dataclass

from engine import db

MIN_APPEARANCES = 2  # abaixo disso não há amostra suficiente para uma taxa por jogo


@dataclass
class PlayerPrediction:
    player_id: int
    name: str
    n_matches: int
    avg_minutes: float
    prob_score: float
    prob_assist: float
    prob_card: float
    confidence: str


def _unavailable_player_ids(cur, fixture_id: int, team_id: int) -> set[int]:
    cur.execute(
        "SELECT player_id FROM injuries WHERE fixture_id = %s AND team_id = %s",
        (fixture_id, team_id),
    )
    injured = {r[0] for r in cur.fetchall()}

    cur.execute(
        """SELECT lp.player_id FROM fixture_lineups l
           JOIN fixture_lineup_players lp ON lp.lineup_id = l.id
           WHERE l.fixture_id = %s AND l.team_id = %s""",
        (fixture_id, team_id),
    )
    announced = {r[0] for r in cur.fetchall()}
    # se a escalação já foi anunciada, quem não está nela (titular ou banco) também fica de fora
    return injured, announced


def _referee_card_factor(cur, fixture_id: int) -> float:
    """Compara a média de cartões dos jogos apitados por este árbitro com a média geral —
    1.0 se não houver dado suficiente do árbitro (neutro, não inventa tendência)."""
    cur.execute("SELECT referee_id FROM fixtures WHERE id = %s", (fixture_id,))
    row = cur.fetchone()
    if not row or not row[0]:
        return 1.0
    referee_id = row[0]

    cur.execute(
        """SELECT AVG(cards_per_match) FROM (
               SELECT f.id, SUM(CASE WHEN fs.stat_type IN ('Yellow Cards','Red Cards')
                                      AND fs.value ~ '^[0-9]+$' THEN fs.value::int ELSE 0 END) AS cards_per_match
               FROM fixtures f JOIN fixture_statistics fs ON fs.fixture_id = f.id
               WHERE f.referee_id = %s GROUP BY f.id
           ) t""",
        (referee_id,),
    )
    referee_avg = cur.fetchone()[0]

    cur.execute(
        """SELECT AVG(cards_per_match) FROM (
               SELECT f.id, SUM(CASE WHEN fs.stat_type IN ('Yellow Cards','Red Cards')
                                      AND fs.value ~ '^[0-9]+$' THEN fs.value::int ELSE 0 END) AS cards_per_match
               FROM fixtures f JOIN fixture_statistics fs ON fs.fixture_id = f.id
               GROUP BY f.id
           ) t""",
    )
    league_avg = cur.fetchone()[0]

    if not referee_avg or not league_avg:
        return 1.0
    return float(referee_avg) / float(league_avg)


def predict_team_players(fixture_id: int, team_id: int, opponent_defense_factor: float) -> list[PlayerPrediction]:
    """opponent_defense_factor: fator de defesa do adversário vindo do modelo de gols
    (away_defense ou home_defense, conforme o mando) — reaproveitado, não recalculado aqui."""
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            injured, announced = _unavailable_player_ids(cur, fixture_id, team_id)
            referee_factor = _referee_card_factor(cur, fixture_id)

            cur.execute(
                """SELECT p.id, p.name,
                          COUNT(*) AS n, AVG(fps.minutes) AS avg_min,
                          SUM(fps.goals) AS goals, SUM(fps.assists) AS assists,
                          SUM(fps.yellow_cards) AS yellow, SUM(fps.red_cards) AS red,
                          SUM(fps.minutes) AS total_minutes
                   FROM fixture_player_stats fps
                   JOIN players p ON p.id = fps.player_id
                   WHERE fps.team_id = %s AND fps.minutes IS NOT NULL AND fps.minutes > 0
                   GROUP BY p.id, p.name""",
                (team_id,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    predictions = []
    for player_id, name, n, avg_min, goals, assists, yellow, red, total_minutes in rows:
        if player_id in injured:
            continue
        if announced and player_id not in announced:
            continue
        if n < MIN_APPEARANCES or not total_minutes:
            continue

        goals_per90 = (goals or 0) / total_minutes * 90
        assists_per90 = (assists or 0) / total_minutes * 90
        cards_per90 = ((yellow or 0) + (red or 0)) / total_minutes * 90

        expected_minutes = min(float(avg_min), 90.0)
        exp_goals = goals_per90 * (expected_minutes / 90) * opponent_defense_factor
        exp_assists = assists_per90 * (expected_minutes / 90) * opponent_defense_factor
        exp_cards = cards_per90 * (expected_minutes / 90) * referee_factor

        confidence = "média" if n >= 8 else "baixa"

        predictions.append(
            PlayerPrediction(
                player_id=player_id,
                name=name,
                n_matches=n,
                avg_minutes=float(avg_min),
                prob_score=1 - math.exp(-exp_goals),
                prob_assist=1 - math.exp(-exp_assists),
                prob_card=1 - math.exp(-exp_cards),
                confidence=confidence,
            )
        )

    predictions.sort(key=lambda p: p.prob_score, reverse=True)
    return predictions
