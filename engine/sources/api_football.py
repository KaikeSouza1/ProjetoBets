"""Cliente para a API-Football (v3.football.api-sports.io).

Toda chamada é logada em api_request_log e o payload bruto é arquivado em
raw_api_payloads antes de qualquer parsing — para poder reprocessar sem gastar cota de novo.
"""
import requests

from engine import config, db

BASE_URL = "https://v3.football.api-sports.io"
SOURCE = "api-football"


class ApiFootballError(Exception):
    pass


def get(endpoint: str, params: dict | None = None) -> list:
    """Faz a chamada, arquiva o payload bruto, loga a requisição e devolve response['response']."""
    params = params or {}
    resp = requests.get(
        f"{BASE_URL}/{endpoint}",
        headers={"x-apisports-key": config.API_FOOTBALL_KEY},
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

    if payload.get("errors"):
        raise ApiFootballError(f"{endpoint} {params}: {payload['errors']}")

    return payload.get("response", [])


def psycopg_json(obj):
    from psycopg2.extras import Json

    return Json(obj)
