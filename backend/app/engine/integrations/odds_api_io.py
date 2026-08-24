"""Cliente para odds-api.io — agregador de odds públicas (NÃO é parceria oficial com
as casas; Bet365 e Superbet não licenciam dado pra terceiro, isso aqui é o mesmo dado
que aparece no site delas, coletado por um serviço independente — ver
app/engine/jobs/multi_bookmaker_odds.py pro porquê disso ser aceitável como fonte
ADICIONAL, nunca única). Pode quebrar ou ficar defasado se o layout da casa mudar."""
import requests

from app.core import config, db
from app.engine.integrations.api_football import psycopg_json

BASE_URL = "https://api.odds-api.io/v3"
SOURCE = "odds-api.io"


class OddsApiIoError(Exception):
    pass


def _get(path: str, params: dict) -> object:
    params = {**params, "apiKey": config.ODDS_API_IO_KEY}
    resp = requests.get(f"{BASE_URL}{path}", params=params, timeout=20)

    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO api_request_log (source, endpoint, status_code) VALUES (%s, %s, %s)",
                (SOURCE, path, resp.status_code),
            )
            logged_params = {k: v for k, v in params.items() if k != "apiKey"}
            cur.execute(
                """INSERT INTO raw_api_payloads (source, endpoint, params, payload)
                   VALUES (%s, %s, %s, %s)""",
                (SOURCE, path, psycopg_json(logged_params), psycopg_json(resp.json() if resp.ok else {"error": resp.text[:500]})),
            )
        conn.commit()
    finally:
        conn.close()

    if not resp.ok:
        raise OddsApiIoError(f"{path} {params}: HTTP {resp.status_code} {resp.text[:300]}")
    return resp.json()


def list_events(league_slug: str) -> list[dict]:
    return _get("/events", {"sport": "football", "league": league_slug})


def fetch_odds_multi(event_ids: list[int], bookmakers: list[str]) -> list[dict]:
    """Até 10 eventos por chamada (limite da API) — quem chama já garante isso."""
    return _get("/odds/multi", {"eventIds": ",".join(str(e) for e in event_ids), "bookmakers": ",".join(bookmakers)})
