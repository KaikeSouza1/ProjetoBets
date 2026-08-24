"""Dados de referência: ligas que acompanhamos, tipos de aposta, bookmakers.
Chamado uma vez (ou raramente) — não muda com frequência.
"""
from app.core import db
from app.engine.integrations import api_football

TARGET_LEAGUES = [
    ("BSA", "Serie A", "Brazil"),
    ("PL", "Premier League", "England"),
    ("PD", "La Liga", "Spain"),
    ("BL1", "Bundesliga", "Germany"),
    ("SA", "Serie A", "Italy"),
    ("FL1", "Ligue 1", "France"),
]

# ligas só na API-Football — football-data.org não cobre nenhuma copa nacional (só as
# 13 competições confirmadas em GET /competitions, nenhuma é Copa do Brasil). Sem
# football_data_code de propósito: o modelo de gols detecta isso e usa `fixtures`
# (nossa própria captura via fixtures_daily) como fonte, em vez de fd_matches — ver
# poisson_goals.build_league_model.
API_FOOTBALL_ONLY_LEAGUES = [
    (73, "Copa do Brasil", "Brazil"),
]


def sync_api_football_only_leagues():
    """Registra ligas que só existem na API-Football (id já conhecido, sem busca por
    nome) — sem football_data_code, o modelo passa a usar `fixtures` como fonte de
    histórico (cresce a partir de agora; sem bulk histórico de temporada disponível pra
    copa no plano gratuito da API-Football, confirmado por teste real)."""
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            for league_id, name, country in API_FOOTBALL_ONLY_LEAGUES:
                cur.execute(
                    """INSERT INTO leagues (id, football_data_code, name, country)
                       VALUES (%s, NULL, %s, %s)
                       ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, country = EXCLUDED.country""",
                    (league_id, name, country),
                )
        conn.commit()
    finally:
        conn.close()
    print(f"[reference] {len(API_FOOTBALL_ONLY_LEAGUES)} ligas (API-Football only) registradas")


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
