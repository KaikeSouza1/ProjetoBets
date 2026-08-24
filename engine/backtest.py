"""Backtest do modelo de gols: para cada partida já jogada, calcula a probabilidade
que o modelo TERIA dado usando só as partidas anteriores àquela data (janela expansiva,
sem olhar o futuro) e compara com o resultado real.

IMPORTANTE — o que este backtest NÃO faz: não calcula ROI, yield ou lucro/prejuízo.
Isso exigiria a odd real de mercado no momento de cada partida histórica, e não temos
esse dado — só começamos a guardar snapshots de odds a partir de agora. O que este
backtest prova é calibração: quando o modelo diz 70%, esse evento realmente acontece
perto de 70% das vezes? Isso é medido por Brier score e taxa de acerto.
"""
from dataclasses import dataclass

from engine import db
from engine.models.poisson_goals import compute_strengths_from_matches, predict_fixture

MARKETS_TO_SCORE = ["home_win", "draw", "away_win", "btts_yes", "over_2_5"]


def _actual_outcomes(home_goals: int, away_goals: int) -> dict[str, bool]:
    total = home_goals + away_goals
    return {
        "home_win": home_goals > away_goals,
        "draw": home_goals == away_goals,
        "away_win": home_goals < away_goals,
        "btts_yes": home_goals >= 1 and away_goals >= 1,
        "over_2_5": total > 2.5,
    }


def _fetch_ordered_matches(league_id: int) -> tuple[str, list[tuple]]:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT football_data_code FROM leagues WHERE id = %s", (league_id,))
            row = cur.fetchone()
            if not row or not row[0]:
                raise ValueError(f"liga {league_id} sem football_data_code")
            code = row[0]
            cur.execute(
                """SELECT fd_match_id, home_team_id, away_team_id, home_goals, away_goals, utc_date
                   FROM fd_matches
                   WHERE competition_code = %s AND status = 'FINISHED'
                     AND home_team_id IS NOT NULL AND away_team_id IS NOT NULL
                     AND home_goals IS NOT NULL AND away_goals IS NOT NULL
                   ORDER BY utc_date""",
                (code,),
            )
            return code, cur.fetchall()
    finally:
        conn.close()


def _get_or_create_model_version(cur) -> int:
    cur.execute(
        """INSERT INTO model_versions (market_family, version, description)
           VALUES ('gols', 'poisson-maher-v1', 'Poisson casa/fora com força ofensiva/defensiva (Maher, 1982)')
           ON CONFLICT (market_family, version) DO UPDATE SET description = EXCLUDED.description
           RETURNING id""",
    )
    return cur.fetchone()[0]


@dataclass
class BacktestSummary:
    backtest_run_id: int
    n_matches_evaluated: int
    metrics: dict[str, dict]  # market_key -> {brier_score, hit_rate, n_bets}


def run_goals_backtest(league_id: int, min_training_matches: int = 30) -> BacktestSummary:
    code, matches = _fetch_ordered_matches(league_id)
    if len(matches) <= min_training_matches:
        raise ValueError(
            f"liga {league_id} ({code}): só {len(matches)} partidas — precisa de mais de "
            f"{min_training_matches} para reservar um período de treino antes de avaliar"
        )

    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            model_version_id = _get_or_create_model_version(cur)
            cur.execute(
                """INSERT INTO backtest_runs (model_version_id, date_from, date_to, notes)
                   VALUES (%s, %s, %s, %s) RETURNING id""",
                (
                    model_version_id, matches[min_training_matches][5].date(), matches[-1][5].date(),
                    f"walk-forward, liga {league_id} ({code}), janela expansiva a partir de {min_training_matches} jogos; "
                    "sem odd histórica — só calibração (Brier/acerto), não ROI",
                ),
            )
            run_id = cur.fetchone()[0]

            per_market_predictions: dict[str, list[tuple[float, bool]]] = {m: [] for m in MARKETS_TO_SCORE}

            for i in range(min_training_matches, len(matches)):
                fd_match_id, home_id, away_id, home_goals, away_goals, _ = matches[i]
                training_matches = [(m[1], m[2], m[3], m[4]) for m in matches[:i]]

                try:
                    model = compute_strengths_from_matches(league_id, training_matches)
                    prediction = predict_fixture(model, home_id, away_id)
                except ValueError:
                    continue  # time sem jogo no período de treino ainda — pula, não inventa número

                actuals = _actual_outcomes(home_goals, away_goals)
                for market_key in MARKETS_TO_SCORE:
                    prob = float(prediction.markets[market_key])
                    actual = bool(actuals[market_key])
                    per_market_predictions[market_key].append((prob, actual))
                    cur.execute(
                        """INSERT INTO backtest_bets (backtest_run_id, fd_match_id, market_key, predicted_probability, actual_outcome)
                           VALUES (%s, %s, %s, %s, %s)""",
                        (run_id, fd_match_id, market_key, prob, actual),
                    )

            metrics = {}
            for market_key, preds in per_market_predictions.items():
                if not preds:
                    continue
                n = len(preds)
                brier = float(sum((p - float(a)) ** 2 for p, a in preds) / n)
                hit_rate = float(sum((p >= 0.5) == a for p, a in preds) / n)
                metrics[market_key] = {"brier_score": brier, "hit_rate": hit_rate, "n_bets": n}
                cur.execute(
                    """INSERT INTO backtest_metrics (backtest_run_id, market_key, league_id, roi, hit_rate, brier_score, n_bets)
                       VALUES (%s, %s, %s, NULL, %s, %s, %s)""",
                    (run_id, market_key, league_id, hit_rate, brier, n),
                )
        conn.commit()
    finally:
        conn.close()

    total_evaluated = max((len(v) for v in per_market_predictions.values()), default=0)
    return BacktestSummary(backtest_run_id=run_id, n_matches_evaluated=total_evaluated, metrics=metrics)
