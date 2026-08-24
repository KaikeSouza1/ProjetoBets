from datetime import date

from fastapi import APIRouter, Query

from app.api.schemas.match import MatchAnalysisOut, MatchFormOut, MatchHeaderOut, MatchMarketsOut, MatchPlayersOut, MatchSummaryOut
from app.core.errors import NotFoundError
from app.services import analysis_service as svc
from app.services import match_service

router = APIRouter(prefix="/api/matches", tags=["matches"])


def _get_match_or_404(match_id: int) -> dict:
    match = svc.get_upcoming_match(match_id)
    if not match:
        raise NotFoundError(f"partida {match_id} não encontrada")
    return match


@router.get("", response_model=list[MatchSummaryOut])
def list_matches(
    from_: date | None = Query(None, alias="from"),
    to: date | None = None,
    league_id: int | None = None,
    sort_by: str = Query("valor", pattern="^(valor|probabilidade)$"),
):
    days_ahead = 14
    if to:
        days_ahead = max((to - date.today()).days, 1)
    matches = svc.list_upcoming(days_ahead=days_ahead)
    if league_id is not None:
        matches = [m for m in matches if m["league_id"] == league_id]
    if from_:
        matches = [m for m in matches if m["date"].date() >= from_]
    if to:
        matches = [m for m in matches if m["date"].date() <= to]
    last_updated = svc.get_last_updated()  # 1x pra toda a lista, não por partida
    return [match_service.get_summary(m, last_updated=last_updated, sort_by=sort_by) for m in matches]


@router.get("/{match_id}", response_model=MatchHeaderOut)
def get_match(match_id: int):
    return match_service.get_header(_get_match_or_404(match_id))


@router.get("/{match_id}/analysis", response_model=MatchAnalysisOut)
def get_match_analysis(match_id: int, sort_by: str = Query("valor", pattern="^(valor|probabilidade)$")):
    return match_service.get_analysis(_get_match_or_404(match_id), sort_by=sort_by)


@router.get("/{match_id}/markets", response_model=MatchMarketsOut)
def get_match_markets(match_id: int):
    return match_service.get_markets(_get_match_or_404(match_id))


@router.get("/{match_id}/form", response_model=MatchFormOut)
def get_match_form(match_id: int):
    return match_service.get_form(_get_match_or_404(match_id))


@router.get("/{match_id}/players", response_model=MatchPlayersOut)
def get_match_players(match_id: int):
    return match_service.get_players(_get_match_or_404(match_id))
