"""Backfill histórico — separado de propósito da ingestão diária (`daily_job.py`, que só
olha o jogo de ONTEM): cobre qualquer partida finalizada, de qualquer data, e é o único
jeito de fechar o passivo de partidas antigas sem estatística completa.

Prioriza Fila A (estatística de escanteio/cartão — o gargalo mais urgente do produto)
sobre Fila B (estatística de jogador — cresce igual, mas não bloqueia corners/cards).
Usa `fixture_detail.fixtures_with_incomplete_statistics`/`fixtures_missing_player_stats`
— a mesma definição de "completo" que a ingestão diária usa, nunca uma checagem
duplicada e mais fraca.

Nunca consome a cota reservada pra operação normal (`reserve`): pára ANTES de chegar
nesse piso, checando a cota real gasta hoje a cada tentativa (não um número pré-calculado
uma vez só, que ficaria errado se outro job rodasse no meio). `DEFAULT_RESERVE=20`
(reduzido de 50 em 27/08/2026, a pedido — ainda sem usuário real dependendo da
sincronização normal, só reserva o mínimo pra sync de fixtures do dia continuar
funcionando pro próprio desenvolvimento/teste; reavaliar pra cima quando houver
tráfego de verdade).

Rodável manual (`scripts/backfill_statistics.py`) ou automático (1x/dia, não a cada
ciclo de 4h — é catch-up lento, não dado que precisa ficar fresco; ver
`scripts/run_scheduler.py`)."""
import time

from app.core import db
from app.engine.integrations import api_football
from app.engine.jobs import fixture_detail

PACING_SECONDS = 6.5
DAILY_QUOTA = 100
DEFAULT_RESERVE = 20


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


def _run_one_queue(kind: str, fixture_ids: list[int], fetch_fn, reserve: int) -> tuple[int, int, int]:
    ok = failed = skipped_quota = 0
    for i, fixture_id in enumerate(fixture_ids, start=1):
        remaining = DAILY_QUOTA - _calls_used_today()
        if remaining <= reserve:
            skipped_quota = len(fixture_ids) - i + 1
            print(
                f"[historical_backfill:{kind}] parando — só {remaining} chamadas restantes hoje, "
                f"reserva de {reserve} pra operação normal. {skipped_quota} partida(s) ficaram de fora."
            )
            break
        try:
            saved = fetch_fn(fixture_id)
            ok += 1
            print(f"[historical_backfill:{kind}] ({i}/{len(fixture_ids)}) fixture {fixture_id}: {saved} linhas salvas")
        except api_football.ApiFootballError as exc:
            failed += 1
            print(f"[historical_backfill:{kind}] ({i}/{len(fixture_ids)}) falhou fixture {fixture_id}: {exc}")
            error_text = str(exc).lower()
            # achado real (27/08/2026): as duas mensagens de erro da API-Football
            # contêm "request limit" — "reached the request limit FOR THE DAY" (cota
            # diária, essa sim é motivo de parar) e "reached your PER-MINUTE request
            # limit" (throttling passageiro, provavelmente concorrência com o sync
            # normal do scheduler rodando ao mesmo tempo). Checar só "request limit"
            # tratava as duas como a mesma coisa e abortava o backfill inteiro por um
            # rate-limit de 1 minuto que se resolveria sozinho — 58 partidas ficaram de
            # fora sem necessidade na primeira vez que isso aconteceu.
            if "per-minute" in error_text:
                print(f"[historical_backfill:{kind}] limite por minuto (passageiro) — esperando um pouco mais antes de continuar.")
                time.sleep(PACING_SECONDS * 3)
                continue
            if "for the day" in error_text:
                skipped_quota = len(fixture_ids) - i
                print(f"[historical_backfill:{kind}] cota diária confirmada esgotada — parando, {skipped_quota} partida(s) ficaram de fora.")
                break
        time.sleep(PACING_SECONDS)
    return ok, failed, skipped_quota


def run_historical_backfill(
    kind: str = "both", league_ids: list[int] | None = None, limit: int | None = None, reserve: int = DEFAULT_RESERVE,
) -> dict:
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
        print(f"[historical_backfill] {len(stats_missing)} partidas com estatística incompleta (escanteio/cartão)")
        ok, failed, skipped = _run_one_queue("statistics", stats_missing, fixture_detail.fetch_statistics, reserve)
        total_ok += ok
        total_failed += failed
        total_skipped += skipped

    if kind in ("players", "both"):
        print(f"[historical_backfill] {len(players_missing)} partidas sem estatística de jogador")
        ok, failed, skipped = _run_one_queue("players", players_missing, fixture_detail.fetch_player_stats, reserve)
        total_ok += ok
        total_failed += failed
        total_skipped += skipped

    result = {"ok": total_ok, "failed": total_failed, "skipped_quota": total_skipped}
    print(f"[historical_backfill] concluído: {result}")
    return result
