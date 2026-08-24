from pathlib import Path

import psycopg2
import psycopg2.extensions

from engine import config

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def _connect(dbname: str):
    return psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        dbname=dbname,
    )


def _ensure_database_exists():
    conn = _connect("postgres")
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (config.DB_NAME,))
            if cur.fetchone() is None:
                cur.execute(f'CREATE DATABASE "{config.DB_NAME}"')
    finally:
        conn.close()


def _apply_schema():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()


def get_connection():
    return _connect(config.DB_NAME)


def bootstrap():
    """Garante que o banco e todas as tabelas existem. Idempotente — seguro rodar a cada abertura do app."""
    _ensure_database_exists()
    _apply_schema()
