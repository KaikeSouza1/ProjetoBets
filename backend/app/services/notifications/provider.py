"""WhatsAppProvider — a Oportunidade nunca chama CodeChat (ou qualquer outro provedor)
direto. Sempre por aqui, pra poder trocar de provedor sem tocar em fila, worker ou
opportunity engine.

`ConsoleWhatsAppProvider` é o padrão de segurança: sem credencial nenhuma configurada,
o sistema nunca tenta mandar mensagem de verdade, só loga — arquitetura pronta pra
plugar CodeChat (ou WhatsApp Cloud API oficial) assim que a credencial existir, sem
precisar reescrever fila/worker."""
from dataclasses import dataclass
from typing import Protocol

import requests

from app.core import config


@dataclass(frozen=True)
class SendResult:
    ok: bool
    provider: str
    detail: str | None = None


class WhatsAppProvider(Protocol):
    name: str

    def send(self, to_phone: str, message: str) -> SendResult: ...


class ConsoleWhatsAppProvider:
    """Provider padrão — nunca faz chamada de rede nenhuma. Usado sempre que nenhuma
    credencial de provedor real está configurada (ver `get_provider`)."""

    name = "console"

    def send(self, to_phone: str, message: str) -> SendResult:
        print(f"[whatsapp:console] pra {to_phone}: {message}")
        return SendResult(ok=True, provider=self.name)


class CodeChatProvider:
    """CodeChat (self-hosted, não-oficial, WPPConnect por baixo) — container real já
    rodando na VM (`api_codechat`, porta 28080). Só é escolhido por `get_provider`
    quando CODECHAT_BASE_URL/GLOBAL_API_KEY/INSTANCE_NAME estiverem configurados no
    ambiente. Formato de corpo/rota confirmado direto no swagger da instância rodando
    (/docs), não documentação externa — ver scripts/codechat_manager.py."""

    name = "codechat"

    def __init__(self, base_url: str, api_key: str, instance: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.instance = instance

    def send(self, to_phone: str, message: str) -> SendResult:
        try:
            resp = requests.post(
                f"{self.base_url}/message/sendText/{self.instance}",
                headers={"apikey": self.api_key},
                json={
                    "number": to_phone,
                    "options": {"delay": 1200, "presence": "composing"},
                    "textMessage": {"text": message},
                },
                timeout=15,
            )
        except requests.RequestException as exc:
            return SendResult(ok=False, provider=self.name, detail=str(exc)[:300])
        if resp.status_code >= 300:
            return SendResult(ok=False, provider=self.name, detail=resp.text[:300])
        return SendResult(ok=True, provider=self.name)


def get_provider() -> WhatsAppProvider:
    if config.CODECHAT_BASE_URL and config.CODECHAT_GLOBAL_API_KEY and config.CODECHAT_INSTANCE_NAME:
        return CodeChatProvider(config.CODECHAT_BASE_URL, config.CODECHAT_GLOBAL_API_KEY, config.CODECHAT_INSTANCE_NAME)
    return ConsoleWhatsAppProvider()
