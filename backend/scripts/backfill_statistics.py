"""CLI pro backfill histórico — lógica real em `app/engine/jobs/historical_backfill.py`,
que também roda sozinho 1x/dia via `scripts/run_scheduler.py`. Este script é só pra
rodar manual (mais controle sobre liga/limite/reserva num momento específico).

Uso: python scripts/backfill_statistics.py [league_id ...] [--limit N] [--reserve N] [--kind statistics|players|both]
Sem argumento de liga: roda pra todas. --limit corta em N partidas (default: sem corte).
--reserve (default 50): pára quando sobrar só essa quantidade de chamadas na cota do dia.
--kind (default both): que tipo de dado buscar."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core import db
from app.engine.jobs.historical_backfill import DEFAULT_RESERVE, run_historical_backfill

if __name__ == "__main__":
    args = sys.argv[1:]
    limit = None
    if "--limit" in args:
        i = args.index("--limit")
        limit = int(args[i + 1])
        del args[i : i + 2]
    reserve = DEFAULT_RESERVE
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
    run_historical_backfill(kind=kind, league_ids=league_ids, limit=limit, reserve=reserve)
