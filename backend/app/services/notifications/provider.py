"""WhatsAppProvider — a Oportunidade nunca chama Evolution API (ou qualquer outro
provedor) direto. Sempre por aqui, pra poder trocar de provedor sem tocar em fila,
worker ou opportunity engine.

`ConsoleWhatsAppProvider` é o padrão de segurança: sem credencial nenhuma configurada,
o sistema nunca tenta mandar mensagem de verdade, só loga — arquitetura pronta pra
plugar Evolution API (ou WhatsApp Cloud API oficial) assim que a credencial existir,
sem precisar reescrever fila/worker."""
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


class EvolutionApiProvider:
    """Evolution API (self-hosted, não-oficial) — só é escolhido por `get_provider`
    quando EVOLUTION_API_URL/KEY/INSTANCE estiverem configurados no .env."""

    name = "evolution-api"

    def __init__(self, base_url: str, api_key: str, instance: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.instance = instance

    def send(self, to_phone: str, message: str) -> SendResult:
        try:
            resp = requests.post(
                f"{self.base_url}/message/sendText/{self.instance}",
                headers={"apikey": self.api_key},
                json={"number": to_phone, "text": message},
                timeout=15,
            )
        except requests.RequestException as exc:
            return SendResult(ok=False, provider=self.name, detail=str(exc)[:300])
        if resp.status_code >= 300:
            return SendResult(ok=False, provider=self.name, detail=resp.text[:300])
        return SendResult(ok=True, provider=self.name)


def get_provider() -> WhatsAppProvider:
    if config.EVOLUTION_API_URL and config.EVOLUTION_API_KEY and config.EVOLUTION_API_INSTANCE:
        return EvolutionApiProvider(config.EVOLUTION_API_URL, config.EVOLUTION_API_KEY, config.EVOLUTION_API_INSTANCE)
    return ConsoleWhatsAppProvider()
