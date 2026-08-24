"""Edge e valor esperado: compara a probabilidade do nosso modelo com a probabilidade
implícita da odd do mercado. Nunca afirma certeza — só estima edge e confiança."""
from dataclasses import dataclass

from engine import db

# market_key do nosso modelo -> (bet_type_id da API-Football, rótulo exato do value)
GOALS_ODDS_MAP = {
    "home_win": (1, "Home"),
    "draw": (1, "Draw"),
    "away_win": (1, "Away"),
    "double_chance_1x": (12, "Home/Draw"),
    "double_chance_12": (12, "Home/Away"),
    "double_chance_x2": (12, "Draw/Away"),
    "btts_yes": (8, "Yes"),
    "btts_no": (8, "No"),
    "over_0_5": (5, "Over 0.5"), "under_0_5": (5, "Under 0.5"),
    "over_1_5": (5, "Over 1.5"), "under_1_5": (5, "Under 1.5"),
    "over_2_5": (5, "Over 2.5"), "under_2_5": (5, "Under 2.5"),
    "over_3_5": (5, "Over 3.5"), "under_3_5": (5, "Under 3.5"),
    "over_4_5": (5, "Over 4.5"), "under_4_5": (5, "Under 4.5"),
}

# mercados de escanteio/cartão têm bet_type_id próprio na API-Football (45 e 80);
# chaves prefixadas (corner_/card_) para não colidir com as linhas de gols acima
CORNER_ODDS_MAP = {
    f"corner_over_{str(line).replace('.', '_')}": (45, f"Over {line}")
    for line in [6.5, 7.5, 8.5, 9.5, 10.5]
} | {
    f"corner_under_{str(line).replace('.', '_')}": (45, f"Under {line}")
    for line in [6.5, 7.5, 8.5, 9.5, 10.5]
}
CARD_ODDS_MAP = {
    f"card_over_{str(line).replace('.', '_')}": (80, f"Over {line}")
    for line in [1.5, 2.5, 3.5, 4.5, 5.5]
} | {
    f"card_under_{str(line).replace('.', '_')}": (80, f"Under {line}")
    for line in [1.5, 2.5, 3.5, 4.5, 5.5]
}

MARKET_ODDS_MAP = GOALS_ODDS_MAP | CORNER_ODDS_MAP | CARD_ODDS_MAP

MARKET_LABELS_PT = {
    "home_win": "Vitória do time da casa",
    "draw": "Empate",
    "away_win": "Vitória do time visitante",
    "double_chance_1x": "Dupla chance (casa ou empate)",
    "double_chance_12": "Dupla chance (casa ou fora)",
    "double_chance_x2": "Dupla chance (empate ou fora)",
    "draw_no_bet_home": "Empate anula (casa)",
    "draw_no_bet_away": "Empate anula (fora)",
    "btts_yes": "Ambas marcam — sim",
    "btts_no": "Ambas marcam — não",
    "over_0_5": "Mais de 0.5 gols", "under_0_5": "Menos de 0.5 gols",
    "over_1_5": "Mais de 1.5 gols", "under_1_5": "Menos de 1.5 gols",
    "over_2_5": "Mais de 2.5 gols", "under_2_5": "Menos de 2.5 gols",
    "over_3_5": "Mais de 3.5 gols", "under_3_5": "Menos de 3.5 gols",
    "over_4_5": "Mais de 4.5 gols", "under_4_5": "Menos de 4.5 gols",
}
MARKET_LABELS_PT |= {
    f"corner_over_{str(line).replace('.', '_')}": f"Mais de {line} escanteios"
    for line in [6.5, 7.5, 8.5, 9.5, 10.5]
} | {
    f"corner_under_{str(line).replace('.', '_')}": f"Menos de {line} escanteios"
    for line in [6.5, 7.5, 8.5, 9.5, 10.5]
} | {
    f"card_over_{str(line).replace('.', '_')}": f"Mais de {line} cartões"
    for line in [1.5, 2.5, 3.5, 4.5, 5.5]
} | {
    f"card_under_{str(line).replace('.', '_')}": f"Menos de {line} cartões"
    for line in [1.5, 2.5, 3.5, 4.5, 5.5]
}


@dataclass
class MarketOpportunity:
    market_key: str
    label: str
    probability: float
    odd: float | None
    bookmaker_name: str | None
    implied_probability: float | None
    edge: float | None
    expected_value: float | None
    confidence: str
    data_quality: str
    rank_score: float


def implied_probability(odd: float) -> float:
    return 1.0 / odd


def edge(model_prob: float, implied_prob: float) -> float:
    return model_prob - implied_prob


def expected_value(model_prob: float, odd: float) -> float:
    return model_prob * odd - 1.0


def confidence_label(n_matches_min: int) -> str:
    if n_matches_min >= 15:
        return "alta"
    if n_matches_min >= 6:
        return "média"
    return "baixa"


def _confidence_weight(label: str) -> float:
    return {"alta": 1.0, "média": 0.6, "baixa": 0.3}[label]


def _latest_odds(cur, fixture_id: int) -> dict[tuple[int, str], tuple[float, str]]:
    """Última odd por (bet_type_id, label) para a partida — snapshot mais recente de cada bet_type."""
    cur.execute(
        """SELECT DISTINCT ON (os.bet_type_id, ov.label)
               os.bet_type_id, ov.label, ov.odd, bm.name
           FROM odds_snapshots os
           JOIN odds_values ov ON ov.snapshot_id = os.id
           JOIN bookmakers bm ON bm.id = os.bookmaker_id
           WHERE os.fixture_id = %s
           ORDER BY os.bet_type_id, ov.label, os.captured_at DESC""",
        (fixture_id,),
    )
    out = {}
    for bet_type_id, label, odd, bm_name in cur.fetchall():
        out[(bet_type_id, label)] = (float(odd), bm_name)
    return out


def build_opportunities(fixture_id: int, prediction, min_matches_for_market: int) -> list[MarketOpportunity]:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            odds_lookup = _latest_odds(cur, fixture_id)
    finally:
        conn.close()

    confidence = confidence_label(min_matches_for_market)
    data_quality = confidence  # v1: mesma base (jogos históricos); evolui quando entrarem escalação/lesão

    opportunities = []
    for market_key, probability in prediction.markets.items():
        label = MARKET_LABELS_PT.get(market_key, market_key)
        odds_key = MARKET_ODDS_MAP.get(market_key)
        odd = bm_name = implied = edge_val = ev_val = None

        if odds_key and odds_key in odds_lookup:
            odd, bm_name = odds_lookup[odds_key]
            implied = implied_probability(odd)
            edge_val = edge(probability, implied)
            ev_val = expected_value(probability, odd)
            rank_score = edge_val * _confidence_weight(confidence)
        else:
            rank_score = -1.0  # sem odd -> não entra no ranking de valor, só aparece como estimativa

        opportunities.append(
            MarketOpportunity(
                market_key=market_key,
                label=label,
                probability=probability,
                odd=odd,
                bookmaker_name=bm_name,
                implied_probability=implied,
                edge=edge_val,
                expected_value=ev_val,
                confidence=confidence,
                data_quality=data_quality,
                rank_score=rank_score,
            )
        )

    opportunities.sort(key=lambda o: o.rank_score, reverse=True)
    return opportunities
