from datetime import datetime, timezone

from fastapi import APIRouter

from app.core import db

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    db_ok = True
    try:
        conn = db.get_connection()
        conn.close()
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "database": db_ok, "time": datetime.now(timezone.utc)}
