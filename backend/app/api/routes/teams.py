from fastapi import APIRouter
from pydantic import BaseModel

from app.core.errors import NotFoundError
from app.services import analysis_service as svc

router = APIRouter(prefix="/api/teams", tags=["teams"])


class TeamOut(BaseModel):
    id: int
    name: str
    country: str | None = None
    logo_url: str | None = None


@router.get("/{team_id}", response_model=TeamOut)
def get_team(team_id: int):
    team = svc.get_team(team_id)
    if not team:
        raise NotFoundError(f"time {team_id} não encontrado")
    return team
