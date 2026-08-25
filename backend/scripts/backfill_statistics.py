"""Backfill pontual: estatística (escanteio/cartão) de partida finalizada que ainda
não tem `fixture_statistics` — sem isso, corners.py/cards.py ficam em cold-start
permanente (não existe fonte histórica em massa pra isso, diferente de gol).

1 chamada de API-Football por partida (fetch_statistics). Roda com o mesmo pacing
usado no resto do sistema (10 req/min = 6.5s) — mesmo aceitando estourar o
orçamento diário de 100, ainda respeita o limite por minuto, que é o que de fato
derruba a chamada na hora.

Uso: python scripts/backfill_statistics.py [league_id ...] [--limit N]
Sem argumento de liga: roda pra todas. --limit corta em N partidas (default: sem corte)."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core import db
from app.engine.jobs import fixture_detail

PACING_SECONDS = 6.5


def _fixtures_missing_statistics(league_ids: list[int] | None) -> list[int]:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            query = """SELECT f.id FROM fixtures f
                       WHERE f.status = 'FT'
                         AND NOT EXISTS (SELECT 1 FROM fixture_statistics fs WHERE fs.fixture_id = f.id)"""
            params: tuple = ()
            if league_ids:
                query += " AND f.league_id = ANY(%s)"
                params = (league_ids,)
            query += " ORDER BY f.date DESC"
            cur.execute(query, params)
            return [r[0] for r in cur.fetchall()]
    finally:
        conn.close()


if __name__ == "__main__":
    args = sys.argv[1:]
    limit = None
    if "--limit" in args:
        i = args.index("--limit")
        limit = int(args[i + 1])
        del args[i : i + 2]
    league_ids = [int(a) for a in args] if args else None

    db.bootstrap()
    fixture_ids = _fixtures_missing_statistics(league_ids)
    if limit:
        fixture_ids = fixture_ids[:limit]

    print(f"[backfill_statistics] {len(fixture_ids)} partidas sem estatística — começando")
    ok = failed = 0
    for i, fixture_id in enumerate(fixture_ids, start=1):
        try:
            saved = fixture_detail.fetch_statistics(fixture_id)
            ok += 1
            print(f"[backfill_statistics] ({i}/{len(fixture_ids)}) fixture {fixture_id}: {saved} linhas salvas")
        except Exception as exc:
            failed += 1
            print(f"[backfill_statistics] ({i}/{len(fixture_ids)}) falhou fixture {fixture_id}: {exc}")
        time.sleep(PACING_SECONDS)

    print(f"[backfill_statistics] concluído: {ok} ok, {failed} falharam")
