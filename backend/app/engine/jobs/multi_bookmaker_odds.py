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
(9001) porque nunca existiu no espaço de bookmaker da API-Football."""
import re
import unicodedata

from app.core import config, db
from app.engine.integrations import odds_api_io
from app.engine.models.players import ANYTIME_SCORER_BET_TYPE_ID, ANYTIME_SCORER_BET_TYPE_NAME

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

GOAL_LINES = {0.5, 1.5, 2.5, 3.5, 4.5}
CORNER_LINES = {6.5, 7.5, 8.5, 9.5, 10.5}
CARD_LINES = {1.5, 2.5, 3.5, 4.5, 5.5}

# prefixo/sufixo de organização e estado que a odds-api.io usa e a API-Football não
# (ex.: "SE Palmeiras SP" vs nosso "Palmeiras") — removidos só pra comparação, nunca
# gravados em lugar nenhum
_IGNORED_TOKENS = {
    "fc", "ec", "cr", "ca", "se", "aa", "sc", "ac", "rb", "ge", "ar", "esporte", "clube", "de", "do",
    "sp", "rj", "mg", "rs", "pr", "pe", "go", "df", "es", "pi", "al", "ma", "pa", "am", "rn", "pb", "to", "ba", "sc",
}


def _normalize(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    tokens = [t for t in re.findall(r"[a-z0-9]+", ascii_name.lower()) if t not in _IGNORED_TOKENS]
    return " ".join(tokens)


def _names_match(a: str, b: str) -> bool:
    na, nb = _normalize(a), _normalize(b)
    if not na or not nb:
        return False
    return na == nb or na in nb or nb in na


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
        for event in pending_events:
            if _names_match(fixture["home_name"], event["home"]) and _names_match(fixture["away_name"], event["away"]):
                matched[fixture["fixture_id"]] = event["id"]
                break
    return matched


def _store_bookmaker(cur, name: str):
    cur.execute(
        "INSERT INTO bookmakers (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
        (BOOKMAKER_IDS[name], name),
    )


def _ensure_player_bet_type(cur):
    cur.execute(
        "INSERT INTO bet_types (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
        (ANYTIME_SCORER_BET_TYPE_ID, ANYTIME_SCORER_BET_TYPE_NAME),
    )


def _insert_snapshot(cur, fixture_id: int, bookmaker_name: str, bet_type_id: int) -> int:
    cur.execute(
        """INSERT INTO odds_snapshots (fixture_id, bookmaker_id, bet_type_id, source)
           VALUES (%s, %s, %s, %s) RETURNING id""",
        (fixture_id, BOOKMAKER_IDS[bookmaker_name], bet_type_id, odds_api_io.SOURCE),
    )
    return cur.fetchone()[0]


def _insert_value(cur, snapshot_id: int, label: str, odd: float):
    cur.execute("INSERT INTO odds_values (snapshot_id, label, odd) VALUES (%s, %s, %s)", (snapshot_id, label, odd))


def _store_markets(cur, fixture_id: int, bookmaker_name: str, markets: list[dict]) -> int:
    saved = 0
    for market in markets:
        name = market["name"]
        rows = market["odds"]
        if not rows:
            continue

        if name == "ML" and len(rows) == 1:
            row = rows[0]
            snap = _insert_snapshot(cur, fixture_id, bookmaker_name, 1)
            _insert_value(cur, snap, "Home", float(row["home"]))
            _insert_value(cur, snap, "Draw", float(row["draw"]))
            _insert_value(cur, snap, "Away", float(row["away"]))
            saved += 1

        elif name == "Both Teams To Score" and len(rows) == 1:
            row = rows[0]
            snap = _insert_snapshot(cur, fixture_id, bookmaker_name, 8)
            _insert_value(cur, snap, "Yes", float(row["yes"]))
            _insert_value(cur, snap, "No", float(row["no"]))
            saved += 1

        elif name == "Anytime Goalscorer" and rows:
            snap = _insert_snapshot(cur, fixture_id, bookmaker_name, ANYTIME_SCORER_BET_TYPE_ID)
            for row in rows:
                _insert_value(cur, snap, row["label"], float(row["over"]))
            saved += 1

        elif name in ("Totals", "Corners Totals", "Bookings Totals"):
            bet_type_id, valid_lines = {
                "Totals": (5, GOAL_LINES), "Corners Totals": (45, CORNER_LINES), "Bookings Totals": (80, CARD_LINES),
            }[name]
            for row in rows:
                if row["hdp"] not in valid_lines:
                    continue
                snap = _insert_snapshot(cur, fixture_id, bookmaker_name, bet_type_id)
                _insert_value(cur, snap, f"Over {row['hdp']}", float(row["over"]))
                _insert_value(cur, snap, f"Under {row['hdp']}", float(row["under"]))
                saved += 1
    return saved


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
                    for bm in BOOKMAKERS:
                        _store_bookmaker(cur, bm)
                    _ensure_player_bet_type(cur)
                    for event in results:
                        fixture_id = fixture_ids_by_event.get(event["id"])
                        if fixture_id is None:
                            continue
                        for bookmaker_name, markets in event.get("bookmakers", {}).items():
                            if bookmaker_name not in BOOKMAKER_IDS:
                                continue  # "Bet365 (no latency)" e variantes — só a casa exata
                            total_saved += _store_markets(cur, fixture_id, bookmaker_name, markets)
                conn.commit()
            finally:
                conn.close()

    result = {"fixtures_matched": total_matched, "markets_saved": total_saved}
    print(f"[multi_bookmaker_odds] {result}")
    return result
