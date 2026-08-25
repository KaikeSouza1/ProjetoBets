"""Fecha o ciclo de auditoria: toda previsão registrada em `prediction_snapshots`
precisa eventualmente virar WIN/LOSS (resultado real conhecido), não ficar pra sempre
como só uma probabilidade que ninguém checou depois.

Escopo de hoje: só mercados de gols (mesma família que `backtest.actual_outcomes_from_score`
já resolve) — escanteio/cartão/jogador não têm resolução de resultado real implementada
ainda (precisaria comparar contra `fixture_statistics`, que é outro pedaço de trabalho,
não este). Nunca inventa resultado pra mercado que não sabe resolver: fica NULL, não
GREEN nem RED."""
from app.core import db
from app.engine.backtest.backtest import actual_outcomes_from_score, resolve_actual


def resolve_pending_snapshots() -> dict:
    conn = db.get_connection()
    resolved = skipped_unresolvable_market = 0
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT ps.id, ps.market_key, f.home_goals, f.away_goals
                   FROM prediction_snapshots ps
                   JOIN fixtures f ON f.id = ps.fixture_id
                   WHERE ps.actual_outcome IS NULL
                     AND f.status = 'FT' AND f.home_goals IS NOT NULL AND f.away_goals IS NOT NULL"""
            )
            rows = cur.fetchall()

            for snapshot_id, market_key, home_goals, away_goals in rows:
                actuals = actual_outcomes_from_score(home_goals, away_goals)
                outcome = resolve_actual(market_key, actuals)
                if outcome is None:
                    skipped_unresolvable_market += 1
                    continue
                cur.execute(
                    "UPDATE prediction_snapshots SET actual_outcome = %s, resolved_at = now() WHERE id = %s",
                    (outcome, snapshot_id),
                )
                resolved += 1
        conn.commit()
    finally:
        conn.close()

    result = {"resolved": resolved, "skipped_unresolvable_market": skipped_unresolvable_market}
    print(f"[result_tracking] {result}")
    return result
