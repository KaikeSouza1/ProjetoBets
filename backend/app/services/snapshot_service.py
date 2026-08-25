"""Histórico append-only de previsões. Nunca sobrescreve: cada chamada grava novas
linhas, então dá pra reconstruir "qual era a previsão do modelo nesse instante" mais
tarde.

DUAS FONTES, NUNCA misturadas sem rótulo (`source`):
  MANUAL_VIEW  — alguém abriu a análise de UMA partida (`match_service.get_analysis`).
                 Isso é uma OBSERVAÇÃO PARCIAL: existe porque alguém clicou, não porque
                 o sistema amostra sistematicamente. Não é histórico representativo.
  PERIODIC_JOB — `capture_snapshots_for_upcoming_matches`, pensada pra rodar em ciclo
                 (não ligada a nenhum scheduler ainda — ver docstring da função).

Nenhuma das duas é chamada no caminho do dashboard (127 partidas por request escrevendo
aqui multiplicaria a carga que a fase de performance acabou de reduzir)."""
from app.core import db
from app.engine.valuebet.valuebet import MarketOpportunity, OPPORTUNITY_SCORE_VERSION

MANUAL_VIEW = "MANUAL_VIEW"
PERIODIC_JOB = "PERIODIC_JOB"


def record_snapshot(
    fixture_id: int | None, fd_match_id: int | None, opportunities: list[MarketOpportunity], source: str = MANUAL_VIEW,
) -> int:
    if not opportunities:
        return 0
    conn = db.get_connection()
    saved = 0
    try:
        with conn.cursor() as cur:
            for o in opportunities:
                cur.execute(
                    """INSERT INTO prediction_snapshots (
                           fixture_id, fd_match_id, market_key, market_label, model_probability,
                           bookmaker_name, odd, implied_probability, edge, confidence, data_quality,
                           opportunity_score, score_version, source, model_version
                       ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        fixture_id, fd_match_id, o.market_key, o.label, o.probability,
                        o.bookmaker_name, o.odd, o.implied_probability, o.edge, o.confidence, o.data_quality,
                        o.opportunity_score, OPPORTUNITY_SCORE_VERSION, source, o.model_version,
                    ),
                )
                saved += 1
        conn.commit()
    finally:
        conn.close()
    return saved


def get_snapshot_history(fd_match_id: int, market_key: str) -> list[dict]:
    """Reconstrói o estado da previsão de um mercado ao longo do tempo — a pergunta
    'qual era a previsão 7 dias antes do jogo, e como a odd mudou' que os snapshots existem
    para responder. Sem página dedicada ainda; usado pra validar a persistência.
    `source` vem junto de propósito — nunca assuma que uma sequência de linhas é uma
    amostragem regular sem checar se são todas MANUAL_VIEW (podem ser 5 cliques na mesma
    tarde, não 5 momentos espaçados de verdade)."""
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT model_probability, bookmaker_name, odd, implied_probability, edge,
                          confidence, data_quality, opportunity_score, source, created_at
                   FROM prediction_snapshots
                   WHERE fd_match_id = %s AND market_key = %s
                   ORDER BY created_at""",
                (fd_match_id, market_key),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return [
        {
            "model_probability": r[0], "bookmaker_name": r[1], "odd": r[2], "implied_probability": r[3],
            "edge": r[4], "confidence": r[5], "data_quality": r[6], "opportunity_score": r[7],
            "source": r[8], "created_at": r[9],
        }
        for r in rows
    ]


def capture_snapshots_for_upcoming_matches(days_ahead: int = 7) -> dict:
    """Arquitetura pro histórico automático — o que falta pra `prediction_snapshots`
    deixar de ser 'só quando alguém abriu a análise' e virar uma amostragem periódica
    de verdade. NÃO está registrada em nenhum scheduler ainda (ver
    `backend/scripts/capture_snapshots.py` pra rodar manualmente) — decisão de
    cadência/custo é operacional, não de arquitetura, e ligar isso automaticamente
    multiplica o volume de escrita por N execuções/dia × M partidas na janela.

    Reaproveita `match_service.get_analysis` inteiro, só troca o `source` do snapshot —
    então o que é gravado aqui é EXATAMENTE o que a API mostraria se alguém abrisse a
    partida naquele instante, nunca um cálculo paralelo."""
    from app.services import analysis_service as svc
    from app.services import match_service

    matches = svc.list_upcoming(days_ahead=days_ahead)
    matches_with_data = 0
    total_opportunities = 0

    for match in matches:
        analysis = match_service.get_analysis(match, source=PERIODIC_JOB)
        n_opps = (1 if analysis.best_opportunity else 0) + len(analysis.other_opportunities)
        if n_opps:
            matches_with_data += 1
            total_opportunities += n_opps

    return {
        "matches_scanned": len(matches),
        "matches_with_opportunities": matches_with_data,
        "snapshots_written": total_opportunities,
    }
