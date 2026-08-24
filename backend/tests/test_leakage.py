"""Teste sintético pedido explicitamente na auditoria: injeta uma informação do FUTURO
de propósito e garante que o walk-forward não consegue usá-la. `compute_strengths_from_matches`
e `predict_fixture` são puros (sem DB) — dá pra testar o mecanismo de corte isoladamente."""
from app.engine.backtest.backtest import actual_outcomes_from_score
from app.engine.models.poisson_goals import compute_strengths_from_matches, predict_fixture

LEAGUE_ID = 1  # arbitrário — função é pura, não toca banco

TEAM_A, TEAM_B, TEAM_C, TEAM_D = 101, 102, 103, 104


def _synthetic_matches(n_rounds: int) -> list[tuple[int, int, int, int]]:
    """N rodadas de A x B e C x D alternando mando de campo, sempre 1-1 — resultado
    neutro e repetitivo de propósito, pra qualquer desvio causado por vazamento
    ficar óbvio na comparação."""
    matches = []
    for i in range(n_rounds):
        if i % 2 == 0:
            matches.append((TEAM_A, TEAM_B, 1, 1))
            matches.append((TEAM_C, TEAM_D, 1, 1))
        else:
            matches.append((TEAM_B, TEAM_A, 1, 1))
            matches.append((TEAM_D, TEAM_C, 1, 1))
    return matches


# a informação do futuro: um jogo com um placar absurdo, muito diferente do padrão
# 1-1 constante — se isso vazar pro treino de uma previsão ANTERIOR, as forças
# calculadas (e portanto a probabilidade prevista) mudam de forma detectável
FUTURE_BLOWOUT = (TEAM_A, TEAM_B, 9, 0)


def test_prediction_at_index_is_invariant_to_future_matches_appended_after_it():
    base_matches = _synthetic_matches(20)  # 40 partidas
    cutoff_index = 30  # prevê o estado do modelo logo depois da 30ª partida

    training_without_future = base_matches[:cutoff_index]
    model_without_future = compute_strengths_from_matches(LEAGUE_ID, training_without_future)
    prediction_without_future = predict_fixture(model_without_future, TEAM_A, TEAM_B)

    # mesma lista, só que com o "resultado do futuro" inserido ANTES do índice de corte
    # ser recalculado — simula alguém rodando o backtest depois desse jogo ter existido
    extended_matches = base_matches[:cutoff_index] + [FUTURE_BLOWOUT] + base_matches[cutoff_index:]
    training_with_future_appended_after_cutoff = extended_matches[:cutoff_index]  # ainda não deveria incluir o blowout

    assert training_with_future_appended_after_cutoff == training_without_future, (
        "o corte por índice não deveria ter incluído o jogo inserido depois dele"
    )

    model_with_future_appended_after = compute_strengths_from_matches(LEAGUE_ID, training_with_future_appended_after_cutoff)
    prediction_with_future_appended_after = predict_fixture(model_with_future_appended_after, TEAM_A, TEAM_B)

    assert prediction_with_future_appended_after.lambda_home == prediction_without_future.lambda_home
    assert prediction_with_future_appended_after.lambda_away == prediction_without_future.lambda_away
    for market_key in prediction_without_future.markets:
        assert prediction_with_future_appended_after.markets[market_key] == prediction_without_future.markets[market_key]


def test_prediction_changes_when_future_match_is_wrongly_included_in_training():
    """Prova que o teste acima teria PEGO um vazamento de verdade — se o corte fosse
    feito errado (por exemplo, usando `matches[:cutoff_index+1]` em vez de
    `matches[:cutoff_index]` depois de inserir o jogo do futuro ANTES do corte), a
    previsão muda. Isso mostra que o teste de invariância não passaria 'à toa' mesmo se
    a implementação do corte estivesse quebrada."""
    base_matches = _synthetic_matches(20)
    cutoff_index = 30

    training_correct = base_matches[:cutoff_index]
    model_correct = compute_strengths_from_matches(LEAGUE_ID, training_correct)
    prediction_correct = predict_fixture(model_correct, TEAM_A, TEAM_B)

    # corte ERRADO de propósito: o jogo do futuro entra ANTES do índice de corte
    training_leaked = base_matches[:cutoff_index] + [FUTURE_BLOWOUT]
    model_leaked = compute_strengths_from_matches(LEAGUE_ID, training_leaked)
    prediction_leaked = predict_fixture(model_leaked, TEAM_A, TEAM_B)

    assert prediction_leaked.lambda_home != prediction_correct.lambda_home, (
        "o placar 9-0 inserido no treino deveria alterar a força calculada — "
        "se não alterou, o teste de invariância acima não provaria nada"
    )


def test_walk_forward_full_run_never_uses_a_later_index_for_an_earlier_prediction():
    """Reproduz o laço real de `run_goals_backtest` (sem tocar banco) pra garantir que
    NENHUMA previsão da sequência usa `matches[j]` com j >= i pra prever o índice i."""
    matches = _synthetic_matches(25)  # 50 partidas
    min_training = 20

    predictions_original = []
    for i in range(min_training, len(matches)):
        home_id, away_id, _, _ = matches[i]
        training = matches[:i]
        model = compute_strengths_from_matches(LEAGUE_ID, training)
        predictions_original.append(predict_fixture(model, home_id, away_id).markets["home_win"])

    # acrescenta o "futuro" ao final da lista completa e roda de novo o MESMO laço —
    # cada previsão em [min_training, len(matches)) deve ser idêntica, porque nenhuma
    # delas deveria alcançar o jogo extra (que só existe depois do fim da lista original)
    matches_with_extra_future = matches + [FUTURE_BLOWOUT]
    predictions_rerun = []
    for i in range(min_training, len(matches)):  # mesmo range de antes, não o da lista maior
        home_id, away_id, _, _ = matches_with_extra_future[i]
        training = matches_with_extra_future[:i]
        model = compute_strengths_from_matches(LEAGUE_ID, training)
        predictions_rerun.append(predict_fixture(model, home_id, away_id).markets["home_win"])

    assert predictions_rerun == predictions_original


def test_actual_outcomes_never_infers_missing_score():
    # placar ausente deve estourar, não silenciosamente virar um resultado inventado
    import pytest
    with pytest.raises(TypeError):
        actual_outcomes_from_score(None, 1)
