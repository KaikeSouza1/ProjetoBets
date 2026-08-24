from fastapi import APIRouter

from app.api.schemas.common import LeagueOut
from app.services import analysis_service as svc

router = APIRouter(prefix="/api/leagues", tags=["leagues"])


@router.get("", response_model=list[LeagueOut])
def list_leagues():
    return svc.list_leagues()
