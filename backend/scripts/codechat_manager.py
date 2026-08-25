"""CLI de administração da instância CodeChat (WhatsApp self-hosted, container
`api_codechat` rodando na VM, porta 28080) — criar/parear/desconectar/checar instância
sem precisar decorar rota nem token. Rotas confirmadas direto no swagger da instância
rodando (GET /docs), não documentação externa.

Nunca lê nem grava a API key em lugar nenhum do repo — sempre via variável de
ambiente. Uso:

    CODECHAT_GLOBAL_API_KEY=... python scripts/codechat_manager.py list
    CODECHAT_GLOBAL_API_KEY=... python scripts/codechat_manager.py create projetobets
    CODECHAT_GLOBAL_API_KEY=... python scripts/codechat_manager.py connect projetobets
    CODECHAT_GLOBAL_API_KEY=... python scripts/codechat_manager.py status projetobets
    CODECHAT_GLOBAL_API_KEY=... python scripts/codechat_manager.py logout projetobets
    CODECHAT_GLOBAL_API_KEY=... python scripts/codechat_manager.py delete projetobets
    CODECHAT_GLOBAL_API_KEY=... python scripts/codechat_manager.py send projetobets 5542999999999 "teste"
"""
import argparse
import base64
import os
import sys

import requests

BASE_URL = os.environ.get("CODECHAT_BASE_URL", "http://192.168.155.134:28080")
API_KEY = os.environ.get("CODECHAT_GLOBAL_API_KEY")


def _headers() -> dict:
    if not API_KEY:
        print("faltou CODECHAT_GLOBAL_API_KEY no ambiente — não sigo sem credencial.", file=sys.stderr)
        sys.exit(1)
    return {"apikey": API_KEY}


def cmd_list(args):
    resp = requests.get(f"{BASE_URL}/instance/fetchInstances", headers=_headers(), timeout=15)
    resp.raise_for_status()
    for inst in resp.json():
        print(f"{inst['name']:30s} {inst['connectionStatus']:10s} owner={inst.get('ownerJid') or '-'}")


def cmd_create(args):
    resp = requests.post(
        f"{BASE_URL}/instance/create",
        headers=_headers(),
        json={"instanceName": args.name, "description": args.description or f"ProjetoBets — {args.name}"},
        timeout=15,
    )
    if resp.status_code >= 300:
        print(f"falhou ({resp.status_code}): {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    print(f"instância criada: {data['name']} (id={data['id']})")
    print("agora rode: connect", args.name)


def cmd_connect(args):
    resp = requests.get(f"{BASE_URL}/instance/connect/{args.name}", headers=_headers(), timeout=15)
    if resp.status_code >= 300:
        print(f"falhou ({resp.status_code}): {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    b64 = data.get("base64", "")
    if "," in b64:
        b64 = b64.split(",", 1)[1]
    if not b64:
        print("sem QR novo — instância já deve estar conectada. Rode: status", args.name)
        return
    out_path = args.out or f"{args.name}_qr.png"
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(b64))
    print(f"QR salvo em: {os.path.abspath(out_path)}")
    print("escaneie no WhatsApp (Aparelhos conectados) em até ~1 minuto antes de expirar.")


def cmd_status(args):
    resp = requests.get(
        f"{BASE_URL}/instance/fetchInstances", headers=_headers(),
        params={"instanceName": args.name} if args.name else {}, timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    instances = data if isinstance(data, list) else [data]
    for inst in instances:
        print(f"nome:   {inst['name']}")
        print(f"status: {inst['connectionStatus']}")
        print(f"owner:  {inst.get('ownerJid') or '(não pareado ainda)'}")
        print(f"atualizado: {inst.get('updatedAt')}")


def cmd_logout(args):
    resp = requests.delete(f"{BASE_URL}/instance/logout/{args.name}", headers=_headers(), timeout=15)
    print(f"logout {args.name}: {resp.status_code}")


def cmd_delete(args):
    resp = requests.delete(f"{BASE_URL}/instance/delete/{args.name}", headers=_headers(), timeout=15)
    print(f"delete {args.name}: {resp.status_code}")


def cmd_webhook_set(args):
    resp = requests.put(
        f"{BASE_URL}/webhook/set/{args.name}",
        headers=_headers(),
        json={"enabled": True, "url": args.url, "events": {"messagesUpsert": True}},
        timeout=15,
    )
    if resp.status_code >= 300:
        print(f"falhou ({resp.status_code}): {resp.text}", file=sys.stderr)
        sys.exit(1)
    print(f"webhook configurado: {resp.json()}")


def cmd_send(args):
    resp = requests.post(
        f"{BASE_URL}/message/sendText/{args.name}",
        headers=_headers(),
        json={
            "number": args.phone,
            "options": {"delay": 1200, "presence": "composing"},
            "textMessage": {"text": args.text},
        },
        timeout=15,
    )
    if resp.status_code >= 300:
        print(f"falhou ({resp.status_code}): {resp.text}", file=sys.stderr)
        sys.exit(1)
    print("enviado.")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list").set_defaults(func=cmd_list)

    p = sub.add_parser("create")
    p.add_argument("name")
    p.add_argument("--description")
    p.set_defaults(func=cmd_create)

    p = sub.add_parser("connect")
    p.add_argument("name")
    p.add_argument("--out", help="caminho do PNG do QR (padrão: <name>_qr.png)")
    p.set_defaults(func=cmd_connect)

    p = sub.add_parser("status")
    p.add_argument("name", nargs="?")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("logout")
    p.add_argument("name")
    p.set_defaults(func=cmd_logout)

    p = sub.add_parser("delete")
    p.add_argument("name")
    p.set_defaults(func=cmd_delete)

    p = sub.add_parser("webhook-set")
    p.add_argument("name")
    p.add_argument("url")
    p.set_defaults(func=cmd_webhook_set)

    p = sub.add_parser("send")
    p.add_argument("name")
    p.add_argument("phone")
    p.add_argument("text")
    p.set_defaults(func=cmd_send)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
