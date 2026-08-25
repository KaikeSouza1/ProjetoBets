"""Recebe eventos do CodeChat (mensagem chegando, conexão mudando, etc.) — configurado
via webhook/set na própria instância (ver scripts/codechat_manager.py). Formato do
payload confirmado direto no tráfego real recebido aqui, não em documentação externa
(mesmo princípio usado pra descobrir o CodeChatProvider — ver notifications/provider.py)."""
from fastapi import APIRouter, Request

from app.services import whatsapp_commands
from app.services.notifications.provider import get_provider

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])


def _extract_inbound_text(payload: dict) -> tuple[str, str] | None:
    """(telefone_sem_sufixo, texto) da primeira mensagem recebida (não enviada por nós)
    no evento, ou None se o payload não tiver mensagem reconhecível — nunca assume
    formato, só extrai o que consegue confirmar presente."""
    data = payload.get("data")
    messages = []
    if isinstance(data, dict) and isinstance(data.get("messages"), list):
        messages = data["messages"]
    elif isinstance(data, list):
        messages = data
    elif isinstance(data, dict):
        messages = [data]

    for msg in messages:
        if not isinstance(msg, dict):
            continue
        key = msg.get("key") or {}
        from_me = key.get("fromMe") if isinstance(key, dict) else msg.get("keyFromMe")
        if from_me:
            continue
        remote_jid = (key.get("remoteJid") if isinstance(key, dict) else None) or msg.get("keyRemoteJid")
        # só conversa 1:1 de verdade — grupo (@g.us), status (status@broadcast) e canal
        # (@newsletter) nunca viram comando. Achado real testando contra o WhatsApp
        # pessoal do usuário já pareado: sem esse filtro, "/odds" digitado por QUALQUER
        # pessoa num grupo em comum faria o bot responder ali, público, pro grupo todo.
        if not remote_jid or not remote_jid.endswith("@s.whatsapp.net"):
            continue
        phone = remote_jid.split("@", 1)[0]

        text = None
        message_obj = msg.get("message")
        if isinstance(message_obj, dict):
            text = message_obj.get("conversation") or (message_obj.get("extendedTextMessage") or {}).get("text")
        if text is None:
            content = msg.get("content")
            if isinstance(content, dict):
                text = content.get("text")
        if isinstance(text, str) and text.strip():
            return phone, text
    return None


@router.post("/webhook")
async def receive_webhook(request: Request):
    payload = await request.json()
    print(f"[whatsapp:webhook] {payload}")

    extracted = _extract_inbound_text(payload)
    if extracted is None:
        return {"handled": False}

    phone, text = extracted
    reply = whatsapp_commands.handle_command(phone, text)
    if reply is None:
        return {"handled": False}

    result = get_provider().send(phone, reply)
    return {"handled": True, "sent": result.ok}
