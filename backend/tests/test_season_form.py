"""Achado real (26/08/2026): football-data.org devolveu `"status":
"2026-08-26 19:00:00Z"` (o mesmo valor de utcDate) pra Real Madrid x Real Sociedad —
não é status válido nenhum, bug do lado deles, confirmado no payload arquivado. Sem
validar, essa partida sumia de `list_upcoming` em silêncio (filtra por
status IN ('SCHEDULED','TIMED','FINISHED')), mesmo com modelo+odd prontos."""
from app.engine.jobs.season_form import _normalize_status


def test_valid_status_passes_through_unchanged():
    assert _normalize_status("SCHEDULED", {"home": None, "away": None}) == "SCHEDULED"
    assert _normalize_status("FINISHED", {"home": 2, "away": 1}) == "FINISHED"


def test_garbage_status_with_score_infers_finished():
    assert _normalize_status("2026-08-26 19:00:00Z", {"home": 2, "away": 1}) == "FINISHED"


def test_garbage_status_without_score_infers_scheduled():
    assert _normalize_status("2026-08-26 19:00:00Z", {"home": None, "away": None}) == "SCHEDULED"


def test_partial_score_treated_as_not_finished():
    # nunca finge que uma partida acabou só porque metade do placar chegou
    assert _normalize_status("garbage", {"home": 2, "away": None}) == "SCHEDULED"
