"""Odds sob demanda — só busca quando o usuário abre a análise de uma partida específica.
Cada chamada grava um snapshot novo (nunca sobrescreve), para permitir ver o movimento da odd depois."""
from engine import db
from engine.sources import api_football

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
