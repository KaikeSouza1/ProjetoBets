"""Integração real com Postgres — fila de notificação (idempotência, retry, dead-letter).
Nunca chama Evolution API de verdade: provider padrão em teste é sempre ConsoleWhatsAppProvider
(sem credencial configurada) ou um fake injetado explicitamente."""
from dataclasses import dataclass

from app.core import db
from app.services.notifications.provider import ConsoleWhatsAppProvider, SendResult
from app.services.notifications.queue import enqueue, process_pending


@dataclass
class _AlwaysFailsProvider:
    name: str = "fake-fail"

    def send(self, to_phone: str, message: str) -> SendResult:
        return SendResult(ok=False, provider=self.name, detail="erro simulado")


def _cleanup(keys: list[str]):
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM notification_queue WHERE idempotency_key = ANY(%s)", (keys,))
        conn.commit()
    finally:
        conn.close()


def test_enqueue_is_idempotent():
    key = "test:idempotent:1"
    try:
        first = enqueue("5542999998888", "oi", key)
        second = enqueue("5542999998888", "oi de novo", key)
        assert first is True
        assert second is False  # já existia — nunca duplica

        conn = db.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*), message FROM notification_queue WHERE idempotency_key = %s GROUP BY message", (key,))
                rows = cur.fetchall()
        finally:
            conn.close()
        assert len(rows) == 1
        assert rows[0][0] == 1
        assert rows[0][1] == "oi"  # a 2ª tentativa não sobrescreveu a mensagem da 1ª
    finally:
        _cleanup([key])


def test_process_pending_sends_via_console_provider_by_default():
    key = "test:console-send:1"
    try:
        enqueue("5542999998888", "mensagem de teste", key)
        result = process_pending(limit=50, provider=ConsoleWhatsAppProvider())
        assert result.sent >= 1
        assert result.provider == "console"

        conn = db.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT status, provider, sent_at FROM notification_queue WHERE idempotency_key = %s", (key,))
                status, provider_name, sent_at = cur.fetchone()
        finally:
            conn.close()
        assert status == "sent"
        assert provider_name == "console"
        assert sent_at is not None
    finally:
        _cleanup([key])


def test_process_pending_retries_before_dead_lettering():
    key = "test:retry:1"
    try:
        enqueue("5542999998888", "vai falhar", key)

        # 3 tentativas, max_attempts default = 3 — as 2 primeiras ficam pending (retry),
        # a 3ª vira dead_letter
        for expected_status in ("pending", "pending", "dead_letter"):
            process_pending(limit=50, provider=_AlwaysFailsProvider())
            conn = db.get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT status, attempts, last_error FROM notification_queue WHERE idempotency_key = %s", (key,))
                    status, attempts, last_error = cur.fetchone()
            finally:
                conn.close()
            assert status == expected_status
            assert last_error == "erro simulado"

        # depois de dead_letter, não entra mais no processamento (não fica tentando pra sempre)
        result = process_pending(limit=50, provider=_AlwaysFailsProvider())
        assert result.sent == 0 and result.retrying == 0 and result.dead_letter == 0
    finally:
        _cleanup([key])
