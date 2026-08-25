"""Processo separado — roda a sincronização diária sozinho, sem precisar chamar
script na mão. Deixe essa janela aberta (ou registre como tarefa do Windows)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core import db
from app.engine.jobs.daily_job import run_daily_sync
from app.engine.jobs.historical_backfill import run_historical_backfill
from app.services.snapshot_service import capture_snapshots_for_upcoming_matches

SYNC_INTERVAL_HOURS = 4
SNAPSHOT_INTERVAL_HOURS = 4
# 1x/dia, não a cada 4h como os outros — é catch-up de partida antiga (lento de
# propósito, respeitando --reserve), não dado que precisa ficar fresco. Não roda na
# sincronização inicial do processo (só no intervalo) — restart repetido (deploy) não
# deve disparar isso de novo a cada vez, só a ingestão diária normal tem essa proteção
# própria (fixtures_daily.SYNC_FRESHNESS_COOLDOWN_MINUTES); aqui é mais simples só não
# rodar no startup.
BACKFILL_INTERVAL_HOURS = 24
# 3 dias, não os 7 do padrão da função: partida mais próxima do apito é a que tem
# chance real de já ter odd capturada (ver odds.capture_odds_for_upcoming_fixtures,
# janela hoje±1 dia) — snapshot de partida a 7 dias de distância quase certamente não
# tem odd nenhuma pra comparar ainda, só custa escrita sem construir o par que o
# backtest com odds reais precisa
SNAPSHOT_DAYS_AHEAD = 3


def _run_snapshot_capture():
    result = capture_snapshots_for_upcoming_matches(days_ahead=SNAPSHOT_DAYS_AHEAD)
    print(f"[scheduler] captura de snapshots: {result}")


def _run_historical_backfill():
    result = run_historical_backfill()
    print(f"[scheduler] backfill histórico: {result}")


if __name__ == "__main__":
    db.bootstrap()
    print("[scheduler] rodando sincronização inicial...")
    run_daily_sync()
    _run_snapshot_capture()

    scheduler = BlockingScheduler()
    scheduler.add_job(run_daily_sync, IntervalTrigger(hours=SYNC_INTERVAL_HOURS), id="daily_sync")
    scheduler.add_job(_run_snapshot_capture, IntervalTrigger(hours=SNAPSHOT_INTERVAL_HOURS), id="snapshot_capture")
    scheduler.add_job(_run_historical_backfill, IntervalTrigger(hours=BACKFILL_INTERVAL_HOURS), id="historical_backfill")
    print(
        f"[scheduler] agendado — sincronização a cada {SYNC_INTERVAL_HOURS}h, "
        f"snapshots a cada {SNAPSHOT_INTERVAL_HOURS}h, backfill histórico a cada "
        f"{BACKFILL_INTERVAL_HOURS}h. Ctrl+C para parar."
    )
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("[scheduler] parado.")
