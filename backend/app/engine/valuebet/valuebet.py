"""Edge e valor esperado: compara a probabilidade do nosso modelo com a probabilidade
implícita da odd do mercado. Nunca afirma certeza — só estima edge e confiança."""
from dataclasses import dataclass

from app.core import db

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
    confidence: str          # rótulo qualitativo ('alta'/'média'/'baixa') — calibração do modelo, não certeza do resultado
    data_quality: int        # 0-100 — quanto dado real sustenta esta estimativa (amostra + odd disponível)
    opportunity_score: float | None  # ranking de valor; None quando não há odd para comparar


def implied_probability(odd: float) -> float:
    return 1.0 / odd


def edge(model_prob: float, implied_prob: float) -> float:
    return model_prob - implied_prob


def expected_value(model_prob: float, odd: float) -> float:
    return model_prob * odd - 1.0


def confidence_label(n_matches_min: int) -> str:
    """Confiança do MODELO (calibração), não confiança de que a aposta vai ganhar.
    'Alta' significa 'amostra grande o bastante pra essa estimativa ser estável' —
    nunca 'alta chance de acertar'."""
    if n_matches_min >= 15:
        return "alta"
    if n_matches_min >= 6:
        return "média"
    return "baixa"


def _confidence_weight(label: str) -> float:
    return {"alta": 1.0, "média": 0.6, "baixa": 0.3}[label]


def data_quality_score(n_matches_min: int, has_odds: bool) -> int:
    """0-100: quanto dado real sustenta a estimativa.

    FATORES USADOS (só os que o sistema efetivamente tem disponível hoje):
    - tamanho da amostra (peso 80): jogos finalizados usados pra calcular a força do
      time, saturando perto de 30 partidas — dobrar de 30 para 60 não muda muito a
      força calculada, então não deveria valer mais qualidade.
    - odd capturada (peso 20): sem odd não existe "valor" pra comparar, só a
      probabilidade crua do modelo — falta metade do dado que sustenta uma oportunidade.

    FATORES QUE O SISTEMA AINDA NÃO TEM (por isso NÃO estão aqui — nenhum peso foi
    inventado pra eles):
    - recência dos jogos usados: o modelo de gols usa TODOS os jogos finalizados da
      competição sem filtrar por data/temporada; não há hoje um sinal de "essa força
      foi calculada com jogos de que época" pra pesar.
    - escalação/lesão: já existem tabelas (`fixture_lineups`, `injuries`) e já entram
      no cálculo de jogador (`players.py` exclui quem está fora), mas não entram no
      cálculo de força de time — não tem como usar um dado que o cálculo não consome.
    - estatística por partida (posse, finalizações): capturada em `fixture_statistics`
      mas hoje só alimenta escanteios/cartões, não gols.

    Quando qualquer um desses passar a alimentar o cálculo de força, ele entra aqui
    como um componente novo — não como peso arbitrário, como reflexo de um dado que
    o modelo passou a usar de fato."""
    sample_component = min(n_matches_min / 30, 1.0) * 80
    odds_component = 20 if has_odds else 0
    return round(sample_component + odds_component)


OPPORTUNITY_SCORE_VERSION = "v1"  # sobe quando a fórmula abaixo mudar — grava junto no snapshot (snapshot_service.py)


def calculate_opportunity_score(edge_val: float | None, confidence: str, quality: int) -> float | None:
    """Rankeia oportunidades por valor estimado, não pela maior probabilidade crua —
    uma aposta a 95% com odd 1.05 (edge quase zero) não deve superar uma a 61% com odd
    1.90 (edge real). Isolada nesta função de propósito: é o ranking mais provável de
    mudar conforme o produto evolui, e nada fora daqui deveria depender da fórmula exata.

      opportunity_score = edge * confidence_weight * (0.5 + 0.5 * quality / 100)

    - confidence_weight (0.3 a 1.0, de confidence_label/tamanho de amostra): pune edge
      sustentado por amostra pequena — um edge grande calculado com 3 partidas pesa
      menos que o mesmo edge com 30.
    - quality/100 (contribui só a segunda metade do fator — nunca zera o edge sozinho):
      pune quando falta dado além da amostra (hoje, principalmente a odd em si).

    O QUE MEDE: uma estimativa relativa de "vale mais a pena olhar essa oportunidade
    do que aquela outra", combinando o tamanho do edge com o quão sólido é o dado por
    trás dele. É um RANKING, não uma métrica absoluta — comparar o score de duas
    partidas de ligas diferentes é razoável; comparar o valor absoluto contra um
    threshold fixo sem contexto não é o uso pretendido.

    O QUE NÃO MEDE:
    - não é probabilidade de lucro nem valor esperado em R$ (isso é `expected_value`,
      um campo separado);
    - não considera CORRELAÇÃO entre mercados da mesma partida — duas oportunidades
      "fortes" no mesmo jogo (ex.: over 1.5 E btts sim) não são independentes, e o
      score atual não sabe disso;
    - não considera quão líquido/estável é o mercado daquela odd (não temos histórico
      de variação de odd ainda — ver seção de snapshots);
    - não decai com o tempo: uma odd capturada há 3 dias pesa igual a uma capturada
      agora, porque não guardamos a idade da captura no score.

    DISTORÇÕES POSSÍVEIS:
    - times/ligas com pouquíssimos jogos mas 1 edge grande isolado podem ainda
      aparecer no topo se a odd for muito favorável — confidence_weight reduz isso,
      não elimina;
    - a nota de qualidade satura em 30 jogos; uma liga com 30 jogos e outra com 300
      recebem o mesmo peso de amostra, mesmo a segunda sendo estatisticamente mais
      sólida.

    POR QUE É ADEQUADA PRA V1: usa só os 3 números que o sistema já calcula com
    confiança (edge, confidence, data_quality), é auditável numa linha, e não introduz
    peso nenhum que não venha de um dado real observado.

    MÉTRICAS FUTURAS QUE PODERIAM MELHORAR O RANKING (nenhuma implementada ainda):
    calibração histórica por faixa de edge/mercado (do backtest), estabilidade da odd
    entre capturas (precisa dos snapshots), CLV (closing line value), e penalização
    por correlação entre mercados da mesma partida.

    Sem odd real não há o que rankear — devolve None, e a oportunidade fica de fora do
    ranking de valor (aparece só como estimativa de probabilidade na interface). Nunca
    inventa uma odd pra poder calcular um score."""
    if edge_val is None:
        return None
    return edge_val * _confidence_weight(confidence) * (0.5 + 0.5 * quality / 100)


def fetch_latest_odds(fixture_id: int) -> dict[tuple[int, str], tuple[float, str]]:
    """Melhor odd disponível por (bet_type_id, label) para a partida — a mais recente de
    CADA bookmaker, e entre elas a maior (odd mais alta = melhor pro apostador). Hoje só
    existe 1 bookmaker capturado, então o resultado é idêntico a 'a mais recente'; a query
    já fica pronta pra quando existir mais de uma casa (ver ingest/odds.py) sem precisar
    trocar nada aqui — só a query mudaria de comportamento sozinha.

    Chamada UMA VEZ por partida (não por família de mercado) — reaproveitada por
    `build_opportunities` para gols/escanteios/cartões, que antes repetiam essa mesma
    consulta 3x por partida sem motivo."""
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """WITH latest_per_bookmaker AS (
                       SELECT DISTINCT ON (os.bookmaker_id, os.bet_type_id)
                              os.bookmaker_id, os.bet_type_id, os.id AS snapshot_id
                       FROM odds_snapshots os
                       WHERE os.fixture_id = %s
                       ORDER BY os.bookmaker_id, os.bet_type_id, os.captured_at DESC
                   )
                   SELECT DISTINCT ON (lpb.bet_type_id, ov.label)
                          lpb.bet_type_id, ov.label, ov.odd, bm.name
                   FROM latest_per_bookmaker lpb
                   JOIN odds_values ov ON ov.snapshot_id = lpb.snapshot_id
                   JOIN bookmakers bm ON bm.id = lpb.bookmaker_id
                   ORDER BY lpb.bet_type_id, ov.label, ov.odd DESC""",
                (fixture_id,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return {(bet_type_id, label): (float(odd), bm_name) for bet_type_id, label, odd, bm_name in rows}


def fetch_odds_before(fixture_id: int, cutoff) -> dict[tuple[int, str], tuple[float, str]]:
    """Igual a `fetch_latest_odds`, mas só considera snapshots com `captured_at < cutoff`.

    Existe pra um motivo específico: NUNCA use `fetch_latest_odds` pra avaliar uma
    partida histórica — 'mais recente' significa 'mais recente AGORA', que pode ter sido
    capturado bem depois da partida já ter acontecido. Isso seria o produto se
    autoenganando: usar uma odd que só existiu depois do resultado como se already fosse
    conhecida antes. `fetch_odds_before` é o único jeito seguro de reconstruir 'qual odd
    dava pra saber até este instante' — usado por `historical_eval.py` pro backtest
    com odds reais (ver seção de auditoria de data leakage)."""
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """WITH eligible_per_bookmaker AS (
                       SELECT DISTINCT ON (os.bookmaker_id, os.bet_type_id)
                              os.bookmaker_id, os.bet_type_id, os.id AS snapshot_id
                       FROM odds_snapshots os
                       WHERE os.fixture_id = %s AND os.captured_at < %s
                       ORDER BY os.bookmaker_id, os.bet_type_id, os.captured_at DESC
                   )
                   SELECT DISTINCT ON (epb.bet_type_id, ov.label)
                          epb.bet_type_id, ov.label, ov.odd, bm.name
                   FROM eligible_per_bookmaker epb
                   JOIN odds_values ov ON ov.snapshot_id = epb.snapshot_id
                   JOIN bookmakers bm ON bm.id = epb.bookmaker_id
                   ORDER BY epb.bet_type_id, ov.label, ov.odd DESC""",
                (fixture_id, cutoff),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return {(bet_type_id, label): (float(odd), bm_name) for bet_type_id, label, odd, bm_name in rows}


def odds_capture_window(fixture_id: int, cutoff) -> tuple[object | None, object | None]:
    """(primeira, última) captured_at entre os snapshots pré-corte desta partida —
    'primeira' é a odd no momento em que a previsão teria sido feita; 'última' (quando
    diferente da primeira) é o candidato a odd de fechamento pra CLV. Se só existir 1
    captura, devolve (ts, None) — nunca inventa uma 2ª odd pra simular fechamento."""
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT MIN(captured_at), MAX(captured_at) FROM odds_snapshots
                   WHERE fixture_id = %s AND captured_at < %s""",
                (fixture_id, cutoff),
            )
            first, last = cur.fetchone()
    finally:
        conn.close()
    if first is None:
        return None, None
    return first, (last if last != first else None)


def build_opportunities(
    odds_lookup: dict[tuple[int, str], tuple[float, str]], prediction, min_matches_for_market: int,
) -> list[MarketOpportunity]:
    """Puro — sem I/O. `odds_lookup` vem de `fetch_latest_odds`, buscado uma vez por
    partida pelo chamador (ver analysis_service._compute_market_families) e reutilizado
    para as 3 famílias de mercado. Passe `{}` para uma partida sem odd capturada ainda."""
    confidence = confidence_label(min_matches_for_market)

    opportunities = []
    for market_key, probability in prediction.markets.items():
        # os modelos usam scipy/numpy por dentro (Poisson) — probability chega aqui como
        # np.float64. Não é erro de cálculo, é tipo: psycopg2 não sabe adaptar np.float64
        # pra SQL. Convertido pra float nativo já na entrada, sem tocar no valor numérico
        # nem em nenhuma fórmula — só no tipo Python, no limite entre motor e persistência.
        probability = float(probability)
        label = MARKET_LABELS_PT.get(market_key, market_key)
        odds_key = MARKET_ODDS_MAP.get(market_key)
        odd = bm_name = implied = edge_val = ev_val = None

        has_odds = bool(odds_key and odds_key in odds_lookup)
        if has_odds:
            odd, bm_name = odds_lookup[odds_key]
            implied = implied_probability(odd)
            edge_val = edge(probability, implied)
            ev_val = expected_value(probability, odd)

        quality = data_quality_score(min_matches_for_market, has_odds)
        score = calculate_opportunity_score(edge_val, confidence, quality)

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
                data_quality=quality,
                opportunity_score=score,
            )
        )

    # oportunidades sem score (sem odd) vão para o fim, ordenadas por probabilidade só
    # pra não ficarem em ordem arbitrária — nunca competem por ranking de valor com as que têm odd
    opportunities.sort(key=lambda o: (o.opportunity_score is not None, o.opportunity_score or o.probability), reverse=True)
    return opportunities
