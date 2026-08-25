"""Observabilidade — responde 'o sistema tá vivo de verdade, ou só o /health básico
tá respondendo?'. Nunca mede sucesso pela ausência de erro só; mede pela presença de
atividade recente por fonte, e mostra erro quando ele existe (nunca escondido)."""
from app.core import db

# acima disso sem log de nenhuma chamada, uma fonte é considerada "parada" — folga
# generosa sobre o ciclo real do scheduler (4h) pra não alarmar por atraso normal
STALE_SOURCE_HOURS = 8


def source_sync_status() -> list[dict]:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT now()")
            now = cur.fetchone()[0]
            cur.execute(
                """SELECT
                       source,
                       MAX(called_at) AS last_called_at,
                       COUNT(*) FILTER (WHERE called_at > now() - interval '24 hours') AS calls_24h,
                       COUNT(*) FILTER (
                           WHERE called_at > now() - interval '24 hours' AND status_code >= 400
                       ) AS errors_24h,
                       (SELECT status_code FROM api_request_log l2
                        WHERE l2.source = l1.source ORDER BY called_at DESC LIMIT 1) AS last_status_code
                   FROM api_request_log l1
                   GROUP BY source
                   ORDER BY source""",
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return [
        {
            "source": source,
            "last_called_at": last_called_at,
            "calls_24h": calls_24h,
            "errors_24h": errors_24h,
            "last_status_code": last_status_code,
            "stale": ((now - last_called_at).total_seconds() / 3600 > STALE_SOURCE_HOURS) if last_called_at else True,
        }
        for source, last_called_at, calls_24h, errors_24h, last_status_code in rows
    ]


def data_counts() -> dict:
    tables = [
        "fixtures", "fd_matches", "teams", "players", "leagues",
        "odds_snapshots", "prediction_snapshots", "backtest_bets", "whatsapp_leads",
    ]
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            counts = {}
            for t in tables:
                cur.execute(f"SELECT count(*) FROM {t}")
                counts[t] = cur.fetchone()[0]
    finally:
        conn.close()
    return counts


def last_scheduler_activity() -> dict:
    """Última vez que o job periódico (não clique manual) de fato gravou alguma
    previsão — proxy honesto de 'o scheduler rodou de verdade recentemente',
    melhor que só checar se o processo está de pé."""
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT MAX(created_at) FROM prediction_snapshots WHERE source = 'PERIODIC_JOB'"
            )
            last_periodic = cur.fetchone()[0]
            cur.execute("SELECT MAX(captured_at) FROM odds_snapshots")
            last_odds = cur.fetchone()[0]
    finally:
        conn.close()
    return {"last_periodic_snapshot": last_periodic, "last_odds_capture": last_odds}


def build_status_report() -> dict:
    return {
        "sources": source_sync_status(),
        "data_counts": data_counts(),
        "scheduler": last_scheduler_activity(),
    }
