"""Adapter: odds-api.io -> NormalizedOddsMarket. Só normaliza o payload de 1 evento —
quem chama (`multi_bookmaker_odds.py`) resolve casamento de fixture/evento e fetch em
lote, porque isso é específico de como essa fonte funciona (matching por nome de time),
não algo que pertence a este contrato normalizado."""
from app.engine.models.players import ANYTIME_SCORER_BET_TYPE_ID
from app.engine.providers.odds import NormalizedOddsMarket, NormalizedOddsValue

SOURCE = "odds-api.io"

GOAL_LINES = {0.5, 1.5, 2.5, 3.5, 4.5}
CORNER_LINES = {6.5, 7.5, 8.5, 9.5, 10.5}
CARD_LINES = {1.5, 2.5, 3.5, 4.5, 5.5}

# label (nome que a odds-api.io usa pro mercado) -> (bet_type_id, linhas válidas ou None)
_TOTALS_MARKETS = {
    "Totals": (5, GOAL_LINES),
    "Corners Totals": (45, CORNER_LINES),
    "Bookings Totals": (80, CARD_LINES),
}


def parse_bookmaker_markets(bookmaker_id: int, bookmaker_name: str, markets: list[dict]) -> list[NormalizedOddsMarket]:
    normalized = []
    for market in markets:
        name = market["name"]
        rows = market["odds"]
        if not rows:
            continue

        if name == "ML" and len(rows) == 1:
            row = rows[0]
            normalized.append(NormalizedOddsMarket(
                bet_type_id=1, bookmaker_id=bookmaker_id, bookmaker_name=bookmaker_name, source=SOURCE,
                values=[
                    NormalizedOddsValue("Home", float(row["home"])),
                    NormalizedOddsValue("Draw", float(row["draw"])),
                    NormalizedOddsValue("Away", float(row["away"])),
                ],
            ))

        elif name == "Both Teams To Score" and len(rows) == 1:
            row = rows[0]
            normalized.append(NormalizedOddsMarket(
                bet_type_id=8, bookmaker_id=bookmaker_id, bookmaker_name=bookmaker_name, source=SOURCE,
                values=[
                    NormalizedOddsValue("Yes", float(row["yes"])),
                    NormalizedOddsValue("No", float(row["no"])),
                ],
            ))

        elif name in _TOTALS_MARKETS:
            bet_type_id, valid_lines = _TOTALS_MARKETS[name]
            for row in rows:
                if row["hdp"] not in valid_lines:
                    continue
                normalized.append(NormalizedOddsMarket(
                    bet_type_id=bet_type_id, bookmaker_id=bookmaker_id, bookmaker_name=bookmaker_name, source=SOURCE,
                    values=[
                        NormalizedOddsValue(f"Over {row['hdp']}", float(row["over"])),
                        NormalizedOddsValue(f"Under {row['hdp']}", float(row["under"])),
                    ],
                ))

        elif name == "Anytime Goalscorer" and rows:
            normalized.append(NormalizedOddsMarket(
                bet_type_id=ANYTIME_SCORER_BET_TYPE_ID, bookmaker_id=bookmaker_id, bookmaker_name=bookmaker_name,
                source=SOURCE,
                values=[NormalizedOddsValue(row["label"], float(row["over"])) for row in rows],
            ))

    return normalized
