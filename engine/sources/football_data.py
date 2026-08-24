"""Cliente para a football-data.org (v4). Fonte de tabela/forma/resultados da temporada atual."""
import requests

from engine import config, db
from engine.sources.api_football import psycopg_json

BASE_URL = "https://api.football-data.org/v4"
SOURCE = "football-data-org"


class FootballDataError(Exception):
    pass


def get(endpoint: str, params: dict | None = None) -> dict:
    params = params or {}
    resp = requests.get(
        f"{BASE_URL}/{endpoint}",
        headers={"X-Auth-Token": config.FOOTBALL_DATA_ORG_KEY},
        params=params,
        timeout=20,
    )
    payload = resp.json()

    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO api_request_log (source, endpoint, status_code) VALUES (%s, %s, %s)",
                (SOURCE, endpoint, resp.status_code),
            )
            cur.execute(
                """INSERT INTO raw_api_payloads (source, endpoint, params, payload)
                   VALUES (%s, %s, %s, %s)""",
                (SOURCE, endpoint, psycopg_json(params), psycopg_json(payload)),
            )
        conn.commit()
    finally:
        conn.close()

    if resp.status_code >= 400:
        raise FootballDataError(f"{endpoint} {params}: HTTP {resp.status_code} - {payload}")

    return payload
