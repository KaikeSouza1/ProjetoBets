"""`_resolve_snapshot_fd_match_id` é a trava contra o bug real que derrubava o
scheduler inteiro: liga só-API-Football (Copa do Brasil) fabrica um `fd_match_id`
(reaproveita o id da fixture) só pra roteamento — gravar isso como FK em
`prediction_snapshots.fd_match_id` violava a constraint porque não existe linha
correspondente em `fd_matches`, derrubando `record_snapshot` com ForeignKeyViolation
e, em cascata, o processo do scheduler (ver match_service.py)."""
from app.services.match_service import _resolve_snapshot_fd_match_id


def test_fabricated_fd_match_id_never_reaches_the_database():
    match = {"fixture_id": 1623069, "fd_match_id": 1623069, "fd_match_id_is_real": False}
    assert _resolve_snapshot_fd_match_id(match) is None


def test_real_fd_match_id_passes_through():
    match = {"fixture_id": 555, "fd_match_id": 987654, "fd_match_id_is_real": True}
    assert _resolve_snapshot_fd_match_id(match) == 987654


def test_missing_flag_defaults_to_real_backwards_compatible():
    # fd_matches-backed matches (a maioria) nunca setam essa chave — comportamento
    # anterior ao fix precisa continuar valendo pra eles
    match = {"fixture_id": 555, "fd_match_id": 987654}
    assert _resolve_snapshot_fd_match_id(match) == 987654
