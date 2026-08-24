"""Smoke tests dos endpoints principais contra o Postgres real do projeto — não há
banco de teste separado (mesma convenção do resto do código). Confirma que a API sobe,
responde 200 nas rotas centrais e nunca deixa uma exceção crua vazar como 500."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["database"] is True


def test_leagues():
    r = client.get("/api/leagues")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_dashboard_smoke():
    r = client.get("/api/dashboard?days_ahead=14")
    assert r.status_code == 200
    body = r.json()
    assert "summary" in body
    assert "days" in body
    assert body["summary"]["matches_analyzed"] >= 0


def test_dashboard_rejects_bad_confidence_filter():
    r = client.get("/api/dashboard?min_confidence=inventado")
    assert r.status_code == 422  # validação do Pydantic, nunca um 500 cru


def test_matches_list_smoke():
    r = client.get("/api/matches")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_match_not_found_is_404_not_500():
    r = client.get("/api/matches/999999999")
    assert r.status_code == 404


def test_match_states_are_one_of_known_values():
    r = client.get("/api/matches?to=2026-09-07")
    assert r.status_code == 200
    known_states = {"READY", "PARTIAL", "NO_ODDS", "INSUFFICIENT_DATA", "STALE"}
    for match in r.json():
        assert match["state"] in known_states


def test_calibration_backtest_run_bsa_has_real_sample():
    r = client.post("/api/backtests/run?league_id=71")
    assert r.status_code == 200
    body = r.json()
    assert body["n_matches_evaluated"] > 30
    for m in body["metrics"]:
        assert m["confidence"] in ("insuficiente", "limitada", "representativa")


def test_calibration_backtest_unknown_league_is_422_not_500():
    # liga inexistente nunca vai ter football_data_code — estável independente de
    # quantos dados as ligas reais acumularem (diferente de testar por contagem de
    # partidas, que muda conforme a temporada avança e backfills são rodados)
    r = client.post("/api/backtests/run?league_id=999999")
    assert r.status_code == 422
    assert "detail" in r.json()


def test_historical_odds_summary_reports_insufficient_data_honestly():
    r = client.get("/api/backtests/historical")
    assert r.status_code == 200
    body = r.json()
    # nenhuma partida no banco real tem odd pré-jogo + resultado ao mesmo tempo hoje —
    # a API precisa dizer isso, nunca inventar um ROI
    assert body["insufficient_data"] is True
    assert body["n_bets"] == 0
    assert body["message"] is not None
