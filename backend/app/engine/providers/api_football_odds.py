"""Adapter: API-Football -> NormalizedOddsMarket. Só busca e normaliza — quem chama
decide o que fazer com o resultado (gravar, comparar, o que for)."""
from app.engine.integrations import api_football
from app.engine.providers.odds import NormalizedOddsMarket, NormalizedOddsValue

SOURCE = "api-football"
DEFAULT_BOOKMAKER_ID = 8  # Bet365 — confirmado como o mais completo nos testes


def fetch_odds(fixture_id: int, bookmaker_id: int = DEFAULT_BOOKMAKER_ID) -> list[NormalizedOddsMarket]:
    results = api_football.get("odds", {"fixture": fixture_id})
    if not results:
        return []

    bookmakers = results[0].get("bookmakers", [])
    bm = next((b for b in bookmakers if b["id"] == bookmaker_id), None)
    if bm is None and bookmakers:
        bm = bookmakers[0]
    if bm is None:
        return []

    return [
        NormalizedOddsMarket(
            bet_type_id=bet["id"],
            bookmaker_id=bm["id"],
            bookmaker_name=bm["name"],
            source=SOURCE,
            values=[NormalizedOddsValue(label=v["value"], odd=float(v["odd"])) for v in bet["values"]],
        )
        for bet in bm["bets"]
    ]
