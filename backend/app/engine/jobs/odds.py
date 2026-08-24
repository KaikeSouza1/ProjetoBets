"""Odds — sob demanda (usuário abre a análise) e automática (`capture_odds_for_upcoming_fixtures`,
chamada pelo scheduler). Cada chamada grava um snapshot novo (nunca sobrescreve), para
permitir ver o movimento da odd depois — e, com captura automática repetida, começar a
construir o par (odd pré-jogo, resultado real) que o backtest com odds reais precisa
(ver `engine/backtest/historical_eval.py` — hoje zero pares existem no banco)."""
from app.core import config, db
from app.engine.integrations import api_football

DEFAULT_BOOKMAKER_ID = 8  # Bet365 — confirmado como o mais completo nos testes


def fetch_and_store_odds(fixture_id: int, bookmaker_id: int = DEFAULT_BOOKMAKER_ID) -> int:
    results = api_football.get("odds", {"fixture": fixture_id})
    if not results:
        return 0

    bookmakers = results[0].get("bookmakers", [])
    bm = next((b for b in bookmakers if b["id"] == bookmaker_id), None)
    if bm is None and bookmakers:
        bm = bookmakers[0]
    if bm is None:
        return 0

    conn = db.get_connection()
    saved = 0
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO bookmakers (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
                (bm["id"], bm["name"]),
            )
            for bet in bm["bets"]:
                cur.execute(
                    "INSERT INTO bet_types (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
                    (bet["id"], bet["name"] or f"(sem nome #{bet['id']})"),
                )
                cur.execute(
                    """INSERT INTO odds_snapshots (fixture_id, bookmaker_id, bet_type_id)
                       VALUES (%s, %s, %s) RETURNING id""",
                    (fixture_id, bm["id"], bet["id"]),
                )
                snapshot_id = cur.fetchone()[0]
                for v in bet["values"]:
                    cur.execute(
                        "INSERT INTO odds_values (snapshot_id, label, odd) VALUES (%s, %s, %s)",
                        (snapshot_id, v["value"], float(v["odd"])),
                    )
                saved += 1
        conn.commit()
    finally:
        conn.close()
    print(f"[odds] fixture {fixture_id}: {saved} mercados salvos ({bm['name']})")
    return saved


def _select_fixtures_for_capture(max_fixtures: int, cooldown_hours: int) -> list[int]:
    """Partida elegível: ainda não começou E está dentro da janela em que a
    API-Football libera odd no plano gratuito (hoje ± 1 dia — mesma janela que
    `fixtures_daily.sync_fixtures_for_date` já usa). Prioriza quem NUNCA teve odd
    capturada (garante cobertura ampla primeiro); só gasta cota numa 2ª captura do
    mesmo jogo (o que building um histórico de movimento de odd pra CLV) se sobrar
    orçamento — nunca recaptura antes do cooldown, pra não estourar os 100 req/dia."""
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT f.id,
                          EXISTS(SELECT 1 FROM odds_snapshots os WHERE os.fixture_id = f.id) AS has_capture
                   FROM fixtures f
                   WHERE f.status IN ('NS', 'TBD')
                     AND f.date BETWEEN now() - interval '1 day' AND now() + interval '1 day'
                     AND NOT EXISTS (
                         SELECT 1 FROM odds_snapshots os
                         WHERE os.fixture_id = f.id AND os.captured_at > now() - (%s || ' hours')::interval
                     )
                   ORDER BY has_capture ASC, f.date ASC
                   LIMIT %s""",
                (cooldown_hours, max_fixtures),
            )
            return [r[0] for r in cur.fetchall()]
    finally:
        conn.close()


def capture_odds_for_upcoming_fixtures(
    max_fixtures: int = config.ODDS_CAPTURE_MAX_FIXTURES_PER_RUN,
    cooldown_hours: int = config.ODDS_CAPTURE_COOLDOWN_HOURS,
) -> dict:
    """Chamada pelo scheduler (`daily_job.run_daily_sync`) — automatiza o que antes só
    acontecia quando alguém clicava manualmente na análise de uma partida. Limitada de
    propósito (`max_fixtures` por chamada): a cota da API-Football é 100 req/dia no
    plano gratuito, compartilhada com `fixtures_daily` e o backfill de estatística —
    ver `daily_job.py` pro orçamento completo."""
    fixture_ids = _select_fixtures_for_capture(max_fixtures, cooldown_hours)
    total_saved = 0
    for fixture_id in fixture_ids:
        try:
            total_saved += fetch_and_store_odds(fixture_id)
        except api_football.ApiFootballError as exc:
            print(f"[odds] captura automática falhou pra fixture {fixture_id}: {exc}")
    return {"fixtures_attempted": len(fixture_ids), "markets_saved": total_saved}
