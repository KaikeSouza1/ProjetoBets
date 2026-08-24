"""Processo separado — roda a sincronização diária sozinho, sem precisar chamar
script na mão. Deixe essa janela aberta (ou registre como tarefa do Windows)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core import db
from app.engine.jobs.daily_job import run_daily_sync
from app.services.snapshot_service import capture_snapshots_for_upcoming_matches

SYNC_INTERVAL_HOURS = 4
SNAPSHOT_INTERVAL_HOURS = 4
# 3 dias, não os 7 do padrão da função: partida mais próxima do apito é a que tem
# chance real de já ter odd capturada (ver odds.capture_odds_for_upcoming_fixtures,
# janela hoje±1 dia) — snapshot de partida a 7 dias de distância quase certamente não
# tem odd nenhuma pra comparar ainda, só custa escrita sem construir o par que o
# backtest com odds reais precisa
SNAPSHOT_DAYS_AHEAD = 3


def _run_snapshot_capture():
    result = capture_snapshots_for_upcoming_matches(days_ahead=SNAPSHOT_DAYS_AHEAD)
    print(f"[scheduler] captura de snapshots: {result}")


if __name__ == "__main__":
    db.bootstrap()
    print("[scheduler] rodando sincronização inicial...")
    run_daily_sync()
    _run_snapshot_capture()

    scheduler = BlockingScheduler()
    scheduler.add_job(run_daily_sync, IntervalTrigger(hours=SYNC_INTERVAL_HOURS), id="daily_sync")
    scheduler.add_job(_run_snapshot_capture, IntervalTrigger(hours=SNAPSHOT_INTERVAL_HOURS), id="snapshot_capture")
    print(
        f"[scheduler] agendado — sincronização a cada {SYNC_INTERVAL_HOURS}h, "
        f"snapshots a cada {SNAPSHOT_INTERVAL_HOURS}h. Ctrl+C para parar."
    )
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("[scheduler] parado.")
