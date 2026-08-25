"""Captura odds de Bet365 + Superbet via odds-api.io e grava no MESMO espaço de
bet_type_id/label que `valuebet.MARKET_ODDS_MAP` já usa pra odds vindas da API-Football
(1=1x2, 5=totals gol, 8=ambas marcam, 45=escanteio totals, 80=cartão totals) — assim
`fetch_latest_odds` (que já pega a MAIOR odd entre bookmakers pra cada mercado) passa a
comparar Bet365/Superbet contra o que a API-Football captura, sem mudar nada em
`valuebet.py` ou `analysis_service.py`.

Fonte NÃO-oficial (ver docstring de `odds_api_io.py`) — por isso é aditiva: se falhar
ou vier vazia, `fixtures_daily`/`odds.capture_odds_for_upcoming_fixtures` continuam
sendo a fonte principal, essa aqui só soma bookmaker quando dá.

Reaproveita o id 8 (Bet365) já usado pela captura via API-Football — é literalmente a
mesma casa, só chegando por uma fonte diferente; Superbet ganha um id sintético novo
(9001) porque nunca existiu no espaço de bookmaker da API-Football.

Casamento de fixture <-> evento e o fetch em lote (até 10 jogos/chamada) são
específicos de como esta fonte funciona — a normalização em si (nome de mercado bruto
-> `NormalizedOddsMarket`) e o storage vêm de `providers.odds_api_io_odds` e
`providers.odds_storage`, compartilhados com qualquer futura fonte de odd. O match de
NOME de time usa `teammatch.py` (normalização central) — nunca uma cópia local."""
from app.core import config, db
from app.engine import teammatch
from app.engine.integrations import odds_api_io
from app.engine.models.players import ANYTIME_SCORER_BET_TYPE_ID, ANYTIME_SCORER_BET_TYPE_NAME
from app.engine.providers import odds_api_io_odds
from app.engine.providers.odds_storage import store_markets

BOOKMAKER_IDS = {"Bet365": 8, "Superbet": 9001}
BOOKMAKERS = list(BOOKMAKER_IDS)

# liga nossa -> slug da odds-api.io (mesmas 6 ligas-alvo de reference.TARGET_LEAGUES)
LEAGUE_SLUGS = {
    71: "brazil-brasileiro-serie-a",
    39: "england-premier-league",
    140: "spain-laliga",
    78: "germany-bundesliga",
    135: "italy-serie-a",
    61: "france-ligue-1",
}


def _fixtures_awaiting_odds(league_id: int) -> list[dict]:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT f.id, ht.name, at.name
                   FROM fixtures f
                   JOIN teams ht ON ht.id = f.home_team_id
                   JOIN teams at ON at.id = f.away_team_id
                   WHERE f.league_id = %s AND f.status IN ('NS', 'TBD')
                     AND f.date BETWEEN now() - interval '1 day' AND now() + interval '3 day'""",
                (league_id,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return [{"fixture_id": r[0], "home_name": r[1], "away_name": r[2]} for r in rows]


def _match_fixtures_to_events(fixtures: list[dict], events: list[dict]) -> dict[int, int]:
    """fixture_id -> event id da odds-api.io — só quando casa E visitante batem;
    nunca casa por data sozinha (times diferentes jogando no mesmo horário existem)."""
    matched = {}
    pending_events = [e for e in events if e.get("status") != "settled"]
    for fixture in fixtures:
        home_norm = teammatch.normalize(fixture["home_name"])
        away_norm = teammatch.normalize(fixture["away_name"])
        for event in pending_events:
            if teammatch.names_match(home_norm, teammatch.normalize(event["home"])) and teammatch.names_match(
                away_norm, teammatch.normalize(event["away"])
            ):
                matched[fixture["fixture_id"]] = event["id"]
                break
    return matched


def _ensure_player_bet_type(cur):
    cur.execute(
        "INSERT INTO bet_types (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
        (ANYTIME_SCORER_BET_TYPE_ID, ANYTIME_SCORER_BET_TYPE_NAME),
    )


def capture_multi_bookmaker_odds() -> dict:
    if not config.ODDS_API_IO_KEY:
        return {"skipped": "ODDS_API_IO_KEY não configurada"}

    total_matched = 0
    total_saved = 0

    for league_id, slug in LEAGUE_SLUGS.items():
        fixtures = _fixtures_awaiting_odds(league_id)
        if not fixtures:
            continue

        try:
            events = odds_api_io.list_events(slug)
        except odds_api_io.OddsApiIoError as exc:
            print(f"[multi_bookmaker_odds] falhou listar eventos {slug}: {exc}")
            continue

        matches = _match_fixtures_to_events(fixtures, events)
        if not matches:
            continue
        total_matched += len(matches)

        fixture_ids_by_event = {event_id: fixture_id for fixture_id, event_id in matches.items()}
        event_ids = list(fixture_ids_by_event.keys())

        for i in range(0, len(event_ids), 10):
            chunk = event_ids[i : i + 10]
            try:
                results = odds_api_io.fetch_odds_multi(chunk, BOOKMAKERS)
            except odds_api_io.OddsApiIoError as exc:
                print(f"[multi_bookmaker_odds] falhou buscar odds {slug} {chunk}: {exc}")
                continue

            conn = db.get_connection()
            try:
                with conn.cursor() as cur:
                    _ensure_player_bet_type(cur)
                    for event in results:
                        fixture_id = fixture_ids_by_event.get(event["id"])
                        if fixture_id is None:
                            continue
                        for bookmaker_name, raw_markets in event.get("bookmakers", {}).items():
                            if bookmaker_name not in BOOKMAKER_IDS:
                                continue  # "Bet365 (no latency)" e variantes — só a casa exata
                            markets = odds_api_io_odds.parse_bookmaker_markets(
                                BOOKMAKER_IDS[bookmaker_name], bookmaker_name, raw_markets,
                            )
                            total_saved += store_markets(cur, fixture_id, markets)
                conn.commit()
            finally:
                conn.close()

    result = {"fixtures_matched": total_matched, "markets_saved": total_saved}
    print(f"[multi_bookmaker_odds] {result}")
    return result
