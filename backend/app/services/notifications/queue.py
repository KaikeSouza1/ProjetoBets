"""Fila de notificação — Opportunity Engine (quando existir wiring pra WhatsApp) grava
aqui via `enqueue`, nunca chama `provider.send` direto. `process_pending` é o worker;
hoje chamado sob demanda/pelo scheduler, não um processo separado (não tem Redis nem
fila de verdade — Postgres com FOR UPDATE SKIP LOCKED é suficiente pro volume atual,
ver auditoria seção 19: não introduzir infraestrutura que o estágio atual não precisa)."""
from dataclasses import dataclass

from app.core import db
from app.services.notifications.provider import WhatsAppProvider, get_provider


def enqueue(to_phone: str, message: str, idempotency_key: str) -> bool:
    """True se enfileirou agora; False se essa `idempotency_key` já existia (nunca
    manda a mesma oportunidade 2x pro mesmo número por reprocessamento)."""
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO notification_queue (idempotency_key, to_phone, message)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (idempotency_key) DO NOTHING
                   RETURNING id""",
                (idempotency_key, to_phone, message),
            )
            row = cur.fetchone()
        conn.commit()
    finally:
        conn.close()
    return row is not None


@dataclass
class ProcessResult:
    sent: int
    retrying: int
    dead_letter: int
    provider: str


def process_pending(limit: int = 20, provider: WhatsAppProvider | None = None) -> ProcessResult:
    """`provider` normalmente vem de `get_provider()` (produção) — parâmetro existe
    pra teste conseguir injetar um provider falho sem precisar credencial real nem
    monkeypatch."""
    provider = provider or get_provider()
    sent = retrying = dead_lettered = 0

    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            # FOR UPDATE SKIP LOCKED: se um dia existir mais de 1 worker rodando junto,
            # cada um pega uma fatia diferente da fila em vez de mandar a mesma linha 2x
            cur.execute(
                """SELECT id, to_phone, message, attempts, max_attempts
                   FROM notification_queue
                   WHERE status = 'pending'
                   ORDER BY created_at
                   LIMIT %s
                   FOR UPDATE SKIP LOCKED""",
                (limit,),
            )
            rows = cur.fetchall()

            for row_id, to_phone, message, attempts, max_attempts in rows:
                result = provider.send(to_phone, message)
                new_attempts = attempts + 1

                if result.ok:
                    cur.execute(
                        """UPDATE notification_queue
                           SET status = 'sent', sent_at = now(), attempts = %s, provider = %s
                           WHERE id = %s""",
                        (new_attempts, result.provider, row_id),
                    )
                    sent += 1
                    continue

                if new_attempts >= max_attempts:
                    cur.execute(
                        """UPDATE notification_queue
                           SET status = 'dead_letter', attempts = %s, last_error = %s, provider = %s
                           WHERE id = %s""",
                        (new_attempts, result.detail, result.provider, row_id),
                    )
                    dead_lettered += 1
                else:
                    cur.execute(
                        """UPDATE notification_queue
                           SET attempts = %s, last_error = %s, provider = %s
                           WHERE id = %s""",
                        (new_attempts, result.detail, result.provider, row_id),
                    )
                    retrying += 1
        conn.commit()
    finally:
        conn.close()

    return ProcessResult(sent=sent, retrying=retrying, dead_letter=dead_lettered, provider=provider.name)
