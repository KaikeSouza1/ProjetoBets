"""Roda manualmente 1 ciclo de captura periódica de snapshots (source=PERIODIC_JOB).
Não é chamado por nenhum scheduler ainda — ver app/services/snapshot_service.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core import db
from app.services.snapshot_service import capture_snapshots_for_upcoming_matches

if __name__ == "__main__":
    db.bootstrap()
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    result = capture_snapshots_for_upcoming_matches(days_ahead=days)
    print(f"[capture_snapshots] janela de {days} dias: {result}")
