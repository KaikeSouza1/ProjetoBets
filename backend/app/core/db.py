from pathlib import Path

import psycopg2
import psycopg2.extensions
import psycopg2.pool

from app.core import config

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

# medido: 127 partidas / 314 conexões abertas e fechadas (uma a cada `db.get_connection()`)
# levavam ~17.5s no dashboard, dominado por handshake+auth do Postgres a cada chamada, não
# pela query em si. O pool reaproveita o socket já autenticado; `get_connection()` continua
# devolvendo algo que se comporta como uma conexão normal — todo o código existente já faz
# `conn = db.get_connection(); ...; conn.close()`, então o wrapper below faz `close()` devolver
# a conexão pro pool em vez de fechar o socket, sem precisar tocar nenhum call site.
_pool: psycopg2.pool.ThreadedConnectionPool | None = None


class _PooledConnection:
    """Encaminha tudo pra conexão real, exceto close() — que devolve pro pool.

    Um `cur.execute()` que falhar (erro de sintaxe, FK, etc.) deixa a conexão em
    transação abortada; sem o rollback abaixo, ela voltaria pro pool nesse estado e a
    PRÓXIMA requisição que a pegasse falharia com "current transaction is aborted",
    mesmo fazendo uma query perfeitamente válida. Isso não existia antes do pool — cada
    `conn.close()` fechava o socket de verdade. Com conexão reaproveitada, todo `close()`
    precisa deixá-la limpa pro próximo uso."""

    __slots__ = ("_pool", "_conn")

    def __init__(self, pool: psycopg2.pool.ThreadedConnectionPool, conn):
        self._pool = pool
        self._conn = conn

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def close(self):
        try:
            if self._conn.closed == 0:
                status = self._conn.get_transaction_status()
                if status != psycopg2.extensions.TRANSACTION_STATUS_IDLE:
                    self._conn.rollback()
            self._pool.putconn(self._conn)
        except Exception:
            try:
                self._pool.putconn(self._conn, close=True)
            except Exception:
                pass


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


def _get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=20,
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            dbname=config.DB_NAME,
        )
    return _pool


def get_connection():
    pool = _get_pool()
    return _PooledConnection(pool, pool.getconn())


def bootstrap():
    """Garante que o banco e todas as tabelas existem. Idempotente — seguro rodar a cada abertura do app."""
    _ensure_database_exists()
    _apply_schema()
