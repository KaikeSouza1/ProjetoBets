from fastapi import APIRouter, Query

from app.api.schemas.dashboard import DashboardOut
from app.services import dashboard_service

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardOut)
def get_dashboard(
    days_ahead: int = Query(14, ge=1, le=30),
    league_id: int | None = None,
    min_edge: float | None = Query(None, description="Edge mínimo, ex.: 0.05 para 5%"),
    min_confidence: str | None = Query(None, pattern="^(baixa|média|alta)$"),
):
    return dashboard_service.build_dashboard(
        days_ahead=days_ahead, league_id=league_id, min_edge=min_edge, min_confidence=min_confidence,
    )
