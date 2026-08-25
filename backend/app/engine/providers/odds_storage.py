"""Domain -> Database pra qualquer `NormalizedOddsMarket`, seja qual for a fonte.
Antes desta camada, `odds.py` e `multi_bookmaker_odds.py` tinham cada um sua própria
cópia quase idêntica de "insere bookmaker, insere snapshot, insere values" — a mesma
lógica de storage duplicada por fonte é exatamente o tipo de coisa que a abstração de
provider existe pra eliminar."""
from app.engine.providers.odds import NormalizedOddsMarket


def store_markets(cur, fixture_id: int, markets: list[NormalizedOddsMarket]) -> int:
    saved = 0
    seen_bookmakers: set[int] = set()
    for market in markets:
        if market.bookmaker_id not in seen_bookmakers:
            cur.execute(
                "INSERT INTO bookmakers (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
                (market.bookmaker_id, market.bookmaker_name),
            )
            seen_bookmakers.add(market.bookmaker_id)

        cur.execute(
            """INSERT INTO odds_snapshots (fixture_id, bookmaker_id, bet_type_id, source)
               VALUES (%s, %s, %s, %s) RETURNING id""",
            (fixture_id, market.bookmaker_id, market.bet_type_id, market.source),
        )
        snapshot_id = cur.fetchone()[0]
        for v in market.values:
            cur.execute(
                "INSERT INTO odds_values (snapshot_id, label, odd) VALUES (%s, %s, %s)",
                (snapshot_id, v.label, v.odd),
            )
        saved += 1
    return saved
