"""Processo separado — roda a sincronização diária sozinho, sem precisar chamar
script na mão. Deixe essa janela aberta (ou registre como tarefa do Windows)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from engine import db
from engine.ingest.daily_job import run_daily_sync

SYNC_INTERVAL_HOURS = 4

if __name__ == "__main__":
    db.bootstrap()
    print("[scheduler] rodando sincronização inicial...")
    run_daily_sync()

    scheduler = BlockingScheduler()
    scheduler.add_job(run_daily_sync, IntervalTrigger(hours=SYNC_INTERVAL_HOURS), id="daily_sync")
    print(f"[scheduler] agendado — próxima sincronização a cada {SYNC_INTERVAL_HOURS}h. Ctrl+C para parar.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("[scheduler] parado.")
