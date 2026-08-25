"""Backfill pontual: estatística (escanteio/cartão) e estatística de jogador de
partida finalizada que ainda não tem o dado completo — sem isso, corners.py/cards.py/
players.py ficam em cold-start permanente (não existe fonte histórica em massa pra
isso, diferente de gol). Usa `fixture_detail.fixtures_with_incomplete_statistics` /
`fixtures_missing_player_stats` — a mesma definição de "completo" que o job diário usa,
não uma checagem duplicada e mais fraca (achado real da auditoria de cota, 25/08/2026:
"tem linha" não é o mesmo que "tem Corner Kicks/Cards pros dois times").

Isso é o BACKFILL HISTÓRICO — deliberadamente separado da ingestão diária
(`daily_job.py`, que só olha o jogo de ONTEM): esse aqui cobre qualquer partida
finalizada, de qualquer data, e é sempre manual/sob controle de quem roda.

1 chamada de API-Football por partida por tipo de dado. Roda com o mesmo pacing usado
no resto do sistema (10 req/min = 6.5s). Reserva de cota (`--reserve`) pra nunca
consumir o orçamento que a operação normal (sync diário, captura de odds) precisa no
resto do dia — pára ANTES de chegar nesse piso, não depois.

Uso: python scripts/backfill_statistics.py [league_id ...] [--limit N] [--reserve N] [--kind statistics|players|both]
Sem argumento de liga: roda pra todas. --limit corta em N partidas (default: sem corte).
--reserve (default 20): pára quando sobrar só essa quantidade de chamadas na cota do dia.
--kind (default both): que tipo de dado buscar."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core import db
from app.engine.integrations import api_football
from app.engine.jobs import fixture_detail

PACING_SECONDS = 6.5
DAILY_QUOTA = 100


def _calls_used_today() -> int:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM api_request_log WHERE source='api-football' AND called_at::date = CURRENT_DATE"
            )
            return cur.fetchone()[0]
    finally:
        conn.close()


def _run_backfill(kind: str, fixture_ids: list[int], fetch_fn, reserve: int) -> tuple[int, int, int]:
    ok = failed = skipped_quota = 0
    for i, fixture_id in enumerate(fixture_ids, start=1):
        remaining = DAILY_QUOTA - _calls_used_today()
        if remaining <= reserve:
            skipped_quota = len(fixture_ids) - i + 1
            print(
                f"[backfill_statistics:{kind}] parando — só {remaining} chamadas restantes hoje, "
                f"reserva de {reserve} pra operação normal. {skipped_quota} partida(s) ficaram de fora."
            )
            break
        try:
            saved = fetch_fn(fixture_id)
            ok += 1
            print(f"[backfill_statistics:{kind}] ({i}/{len(fixture_ids)}) fixture {fixture_id}: {saved} linhas salvas")
        except api_football.ApiFootballError as exc:
            failed += 1
            print(f"[backfill_statistics:{kind}] ({i}/{len(fixture_ids)}) falhou fixture {fixture_id}: {exc}")
            if "request limit" in str(exc).lower():
                skipped_quota = len(fixture_ids) - i
                print(f"[backfill_statistics:{kind}] cota confirmada esgotada — parando, {skipped_quota} partida(s) ficaram de fora.")
                break
        time.sleep(PACING_SECONDS)
    return ok, failed, skipped_quota


if __name__ == "__main__":
    args = sys.argv[1:]
    limit = None
    if "--limit" in args:
        i = args.index("--limit")
        limit = int(args[i + 1])
        del args[i : i + 2]
    reserve = 20
    if "--reserve" in args:
        i = args.index("--reserve")
        reserve = int(args[i + 1])
        del args[i : i + 2]
    kind = "both"
    if "--kind" in args:
        i = args.index("--kind")
        kind = args[i + 1]
        del args[i : i + 2]
    league_ids = [int(a) for a in args] if args else None

    db.bootstrap()
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            stats_missing = fixture_detail.fixtures_with_incomplete_statistics(cur, league_ids=league_ids)
            players_missing = fixture_detail.fixtures_missing_player_stats(cur, league_ids=league_ids)
    finally:
        conn.close()

    if limit:
        stats_missing = stats_missing[:limit]
        players_missing = players_missing[:limit]

    total_ok = total_failed = total_skipped = 0

    if kind in ("statistics", "both"):
        print(f"[backfill_statistics] {len(stats_missing)} partidas com estatística incompleta (escanteio/cartão)")
        ok, failed, skipped = _run_backfill("statistics", stats_missing, fixture_detail.fetch_statistics, reserve)
        total_ok += ok
        total_failed += failed
        total_skipped += skipped

    if kind in ("players", "both"):
        print(f"[backfill_statistics] {len(players_missing)} partidas sem estatística de jogador")
        ok, failed, skipped = _run_backfill("players", players_missing, fixture_detail.fetch_player_stats, reserve)
        total_ok += ok
        total_failed += failed
        total_skipped += skipped

    print(f"[backfill_statistics] concluído: {total_ok} ok, {total_failed} falharam, {total_skipped} não tentadas (reserva de cota)")
