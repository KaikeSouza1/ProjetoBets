"""Métricas de avaliação — puras, sem I/O. Recebem listas já resolvidas (previsão +
resultado real) e devolvem números. Nenhuma função aqui decide COMO uma previsão foi
gerada ou se ela vazou dado futuro — isso é responsabilidade de quem monta a lista
(ver backtest.py para o walk-forward, historical_eval.py para a avaliação com odds).

Todas as funções que agregam por amostra (buckets, calibração) recusam a devolver um
número "limpo" pra amostra pequena — devolvem o `n` junto com um rótulo de confiança,
pra interface nunca mostrar 'ROI +40%' como se fosse um fato sólido baseado em 5 apostas."""
from dataclasses import dataclass

# resultado de UMA aposta avaliada — nunca inferido quando o dado real não permite decidir
GREEN = "GREEN"
RED = "RED"
PUSH = "PUSH"
VOID = "VOID"
UNRESOLVED = "UNRESOLVED"
BET_RESULTS = (GREEN, RED, PUSH, VOID, UNRESOLVED)

# ver seção "amostra mínima" do relatório de estabilização de backtest: abaixo de 20,
# um intervalo de confiança binomial pra hit rate é largo o bastante (ex.: 60% com n=5
# tem IC 95% cobrindo ~15%–95%) pra tornar o número quase inútil; 100 é a regra de bolso
# comum pra estabilizar uma proporção (reduz o erro padrão à metade em relação a n=25).
# Não são "verdades estatísticas" — são limiares operacionais, por isso configuráveis.
MIN_SAMPLE_INSUFFICIENT = 20
MIN_SAMPLE_LIMITED = 100


def sample_confidence_label(n: int, insufficient: int = MIN_SAMPLE_INSUFFICIENT, limited: int = MIN_SAMPLE_LIMITED) -> str:
    if n < insufficient:
        return "insuficiente"
    if n < limited:
        return "limitada"
    return "representativa"


# ==================== Brier score ====================

def brier_score_binary(pairs: list[tuple[float, bool]]) -> float | None:
    """BS = média((p - o)²), o ∈ {0,1}. Intervalo [0,1] — 0 é calibração perfeita, 0.25
    é o que dá 'sempre chutar 50%'. Válida pra QUALQUER evento binário isolado (home_win
    sozinho, btts_yes sozinho, etc.) — inclusive quando o evento binário é 1 dos 3
    resultados de um mercado 1X2, DESDE que tratado como pergunta binária própria
    ('foi vitória da casa? sim/não'), não como parte de uma decisão de 3 classes.
    Ver `brier_score_multiclass` pra 1X2 tratado como decisão conjunta."""
    if not pairs:
        return None
    n = len(pairs)
    return sum((p - float(o)) ** 2 for p, o in pairs) / n


def brier_score_multiclass(rows: list[tuple[dict[str, float], str]]) -> float | None:
    """Brier score clássico (Brier, 1950) pra previsão de K classes MUTUAMENTE
    EXCLUSIVAS — ex.: 1X2 (home_win/draw/away_win), nunca gols over/under (que não são
    3 classes de uma mesma decisão). Cada `row` é (probs, classe_real), onde `probs` tem
    uma entrada por classe e soma ~1.

      BS = média_dos_jogos( soma_das_classes( (p_k - o_k)² ) )

    Intervalo [0,2] — NÃO é o mesmo número/escala do Brier binário acima. Nunca comparar
    os dois valores lado a lado como se fossem a mesma métrica; documentado explicitamente
    porque é o erro mais comum ao aplicar Brier em mercados multiclasse (seção 10 do
    pedido de auditoria de backtest)."""
    if not rows:
        return None
    total = 0.0
    for probs, actual_class in rows:
        total += sum((p - (1.0 if cls == actual_class else 0.0)) ** 2 for cls, p in probs.items())
    return total / len(rows)


# ==================== calibração ====================

DEFAULT_CALIBRATION_BUCKETS = [(0.0, 0.5), (0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0)]


def calibration_table(predictions: list[tuple[float, bool]], buckets=DEFAULT_CALIBRATION_BUCKETS) -> list[dict]:
    """Agrupa por faixa de probabilidade PREVISTA e compara com a frequência REAL —
    'quando o modelo diz 70%, esse evento aconteceu perto de 70% das vezes?'. Isso é a
    pergunta que importa; taxa de acerto isolada (>=50% => 'acertou') esconde
    super/sub-confiança do modelo. Faixas sem amostra suficiente aparecem com
    `confidence='insuficiente'` — nunca omitidas silenciosamente, pra não parecer que a
    calibração foi 'perfeita' numa faixa que só não tinha dado."""
    rows = []
    for low, high in buckets:
        in_bucket = [(p, o) for p, o in predictions if low <= p < high or (high == 1.0 and p == 1.0)]
        n = len(in_bucket)
        mean_predicted = sum(p for p, _ in in_bucket) / n if n else None
        realized_frequency = sum(1 for _, o in in_bucket if o) / n if n else None
        rows.append({
            "bucket_low": low, "bucket_high": high, "n": n,
            "mean_predicted": mean_predicted, "realized_frequency": realized_frequency,
            "confidence": sample_confidence_label(n),
        })
    return rows


# ==================== grading de aposta (stake fixa) ====================

@dataclass
class GradedBet:
    bet_result: str        # GREEN | RED | PUSH | VOID | UNRESOLVED
    profit: float | None    # None quando UNRESOLVED — nunca 0 fingindo neutralidade


def grade_bet(odd: float, actual_outcome: bool | None, stake: float = 1.0) -> GradedBet:
    """Stake fixa (padrão 1 unidade) — sem stake variável por Opportunity Score nesta
    primeira versão; o objetivo agora é medir a qualidade do sinal, não simular gestão
    de banca. GREEN: profit = stake*(odd-1). RED: profit = -stake. UNRESOLVED quando o
    resultado real não pôde ser determinado com segurança — NUNCA inferido."""
    if actual_outcome is None:
        return GradedBet(UNRESOLVED, None)
    if actual_outcome:
        return GradedBet(GREEN, stake * (odd - 1))
    return GradedBet(RED, -stake)


# ==================== ROI / Yield / Hit Rate ====================
# hit rate e ROI respondem perguntas DIFERENTES — uma estratégia pode acertar menos e
# ainda lucrar mais dependendo da odd média das apostas que ganhou. Nunca reportar só
# uma achando que ela implica a outra.

def hit_rate(bet_results: list[str]) -> dict:
    """Só considera GREEN/RED no denominador — PUSH/VOID/UNRESOLVED não são 'acerto' nem
    'erro', são apostas que não resolveram como aposta binária."""
    settled = [r for r in bet_results if r in (GREEN, RED)]
    n = len(settled)
    rate = (sum(1 for r in settled if r == GREEN) / n) if n else None
    return {"n": n, "hit_rate": rate, "confidence": sample_confidence_label(n)}


def roi_and_yield(bet_results: list[str], profits: list[float | None], stake: float = 1.0) -> dict:
    """ROI e Yield são o MESMO número aqui (stake fixa) — profit total / total apostado,
    considerando só apostas GREEN/RED no total apostado (PUSH devolve a stake sem lucro
    nem perda, então não teria efeito no ROI mesmo se entrasse; VOID/UNRESOLVED nunca
    entram — não sabemos o que teria acontecido)."""
    settled_profits = [p for r, p in zip(bet_results, profits) if r in (GREEN, RED) and p is not None]
    n = len(settled_profits)
    if n == 0:
        return {"n": 0, "roi": None, "yield_pct": None, "total_profit": None, "confidence": "insuficiente"}
    total_profit = sum(settled_profits)
    total_staked = n * stake
    roi = total_profit / total_staked
    return {
        "n": n, "roi": roi, "yield_pct": roi * 100, "total_profit": total_profit,
        "confidence": sample_confidence_label(n),
    }


# ==================== buckets (edge / opportunity score) ====================

DEFAULT_EDGE_BUCKETS = [(0.0, 0.03), (0.03, 0.05), (0.05, 0.10), (0.10, 0.15), (0.15, 999.0)]
DEFAULT_SCORE_BUCKETS = [(0.0, 0.20), (0.20, 0.40), (0.40, 0.60), (0.60, 0.80), (0.80, 1.01)]


def bucket_performance(values: list[float], bet_results: list[str], profits: list[float | None], buckets: list[tuple[float, float]]) -> list[dict]:
    """Agrupa apostas por faixa de uma métrica (edge, opportunity_score, ...) e mede
    hit rate + ROI DENTRO de cada faixa — pra responder 'quanto maior o valor previsto,
    melhor o desempenho real', sem assumir a resposta. Faixas usadas são as pedidas
    explicitamente (nunca ajustadas pra fazer o resultado parecer melhor)."""
    rows = []
    for low, high in buckets:
        idx = [i for i, v in enumerate(values) if low <= v < high]
        bucket_results = [bet_results[i] for i in idx]
        bucket_profits = [profits[i] for i in idx]
        hr = hit_rate(bucket_results)
        roi = roi_and_yield(bucket_results, bucket_profits)
        rows.append({
            "bucket_low": low, "bucket_high": high,
            "n_bets": hr["n"], "hit_rate": hr["hit_rate"], "roi": roi["roi"], "yield_pct": roi["yield_pct"],
            "confidence": sample_confidence_label(hr["n"]),
        })
    return rows
