"""Dados de referência: ligas que acompanhamos, tipos de aposta, bookmakers.
Chamado uma vez (ou raramente) — não muda com frequência.
"""
from engine import db
from engine.sources import api_football

TARGET_LEAGUES = [
    ("BSA", "Serie A", "Brazil"),
    ("PL", "Premier League", "England"),
    ("PD", "La Liga", "Spain"),
    ("BL1", "Bundesliga", "Germany"),
    ("SA", "Serie A", "Italy"),
    ("FL1", "Ligue 1", "France"),
]


def sync_target_leagues():
    """Resolve o id de cada liga-alvo na API-Football e grava o código correspondente da football-data.org."""
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            for fd_code, search_term, country in TARGET_LEAGUES:
                results = api_football.get("leagues", {"search": search_term})
                match = next(
                    (r for r in results if r["league"]["type"] == "League" and r["country"]["name"] == country),
                    None,
                )
                if not match:
                    print(f"[reference] liga não encontrada: {search_term} ({country})")
                    continue
                league = match["league"]
                cur.execute(
                    """INSERT INTO leagues (id, football_data_code, name, country)
                       VALUES (%s, %s, %s, %s)
                       ON CONFLICT (id) DO UPDATE SET football_data_code = EXCLUDED.football_data_code""",
                    (league["id"], fd_code, league["name"], country),
                )
        conn.commit()
    finally:
        conn.close()


def sync_bet_types():
    results = api_football.get("odds/bets")
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            for bet in results:
                name = bet["name"] or f"(sem nome #{bet['id']})"
                cur.execute(
                    """INSERT INTO bet_types (id, name) VALUES (%s, %s)
                       ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name""",
                    (bet["id"], name),
                )
        conn.commit()
    finally:
        conn.close()
    print(f"[reference] {len(results)} bet_types sincronizados")


def sync_bookmakers():
    results = api_football.get("odds/bookmakers")
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            for bm in results:
                name = bm["name"] or f"(sem nome #{bm['id']})"
                cur.execute(
                    """INSERT INTO bookmakers (id, name) VALUES (%s, %s)
                       ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name""",
                    (bm["id"], name),
                )
        conn.commit()
    finally:
        conn.close()
    print(f"[reference] {len(results)} bookmakers sincronizados")
