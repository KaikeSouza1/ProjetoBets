"""Achado real (27/08/2026): a checagem antiga (`"request limit" in erro`) tratava o
limite por MINUTO (passageiro, 10 req/min) igual ao limite do DIA (cota esgotada,
motivo real de parar) — as duas mensagens de erro da API-Football contêm a mesma
substring. Isso abortou um backfill de 85 partidas depois de só 26, sem necessidade
(o limite por minuto se resolve sozinho esperando um pouco)."""
from app.engine.integrations.api_football import ApiFootballError
from app.engine.jobs.historical_backfill import _run_one_queue


def test_per_minute_limit_does_not_abort_the_run(monkeypatch):
    monkeypatch.setattr("app.engine.jobs.historical_backfill.time.sleep", lambda _: None)
    calls = []

    def fake_fetch(fixture_id):
        calls.append(fixture_id)
        if fixture_id == 2:
            raise ApiFootballError(
                "fixtures/statistics {'fixture': 2}: {'rateLimit': 'Too many requests. "
                "You have reached your per-minute request limit. Please wait a few seconds.'}"
            )
        return 10

    ok, failed, skipped_quota = _run_one_queue("test", [1, 2, 3], fake_fetch, reserve=0)

    assert calls == [1, 2, 3]  # continuou pro 3 depois do erro de minuto no 2
    assert ok == 2
    assert failed == 1
    assert skipped_quota == 0


def test_daily_limit_aborts_the_remaining_run(monkeypatch):
    monkeypatch.setattr("app.engine.jobs.historical_backfill.time.sleep", lambda _: None)
    calls = []

    def fake_fetch(fixture_id):
        calls.append(fixture_id)
        if fixture_id == 2:
            raise ApiFootballError(
                "fixtures/statistics {'fixture': 2}: {'requests': 'You have reached the "
                "request limit for the day, Go to https://dashboard.api-football.com'}"
            )
        return 10

    ok, failed, skipped_quota = _run_one_queue("test", [1, 2, 3], fake_fetch, reserve=0)

    assert calls == [1, 2]  # nunca tentou o 3 — cota do dia é motivo real de parar
    assert ok == 1
    assert failed == 1
    assert skipped_quota == 1
