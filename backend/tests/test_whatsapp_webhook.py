"""_extract_inbound_text não assume 1 formato só — testa contra os 2 formatos vistos:
o dos exemplos de sendText no swagger do CodeChat (key/message aninhados, estilo
Baileys) e um formato mais achatado (keyRemoteJid/content), pra não quebrar se o
payload real do webhook vier num formato e a doc mostrar outro."""
from app.api.routes.whatsapp import _extract_inbound_text


def test_extracts_from_nested_baileys_style_payload():
    payload = {
        "event": "messages.upsert",
        "instance": "projetobets",
        "data": {
            "messages": [
                {
                    "key": {"remoteJid": "554298119282@s.whatsapp.net", "fromMe": False, "id": "ABC"},
                    "message": {"conversation": "/odds"},
                }
            ]
        },
    }
    assert _extract_inbound_text(payload) == ("554298119282", "/odds")


def test_extracts_from_flat_content_style_payload():
    payload = {
        "event": "messages.upsert",
        "data": {"keyRemoteJid": "554298119282@s.whatsapp.net", "keyFromMe": False, "content": {"text": "/odds"}},
    }
    assert _extract_inbound_text(payload) == ("554298119282", "/odds")


def test_ignores_messages_sent_by_us():
    payload = {
        "data": {
            "messages": [
                {"key": {"remoteJid": "554298119282@s.whatsapp.net", "fromMe": True}, "message": {"conversation": "/odds"}}
            ]
        }
    }
    assert _extract_inbound_text(payload) is None


def test_ignores_events_without_recognizable_message():
    assert _extract_inbound_text({"event": "connection.update", "data": {"state": "open"}}) is None


def test_ignores_group_messages():
    payload = {
        "data": {"keyRemoteJid": "120363424686223779@g.us", "keyFromMe": False, "content": {"text": "/odds"}}
    }
    assert _extract_inbound_text(payload) is None


def test_ignores_status_and_newsletter():
    for jid in ("status@broadcast", "120363336020038705@newsletter"):
        payload = {"data": {"keyRemoteJid": jid, "keyFromMe": False, "content": {"text": "/odds"}}}
        assert _extract_inbound_text(payload) is None
