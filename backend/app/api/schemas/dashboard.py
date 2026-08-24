from datetime import datetime

from pydantic import BaseModel

from app.api.schemas.match import MatchSummaryOut


class DashboardSummaryOut(BaseModel):
    matches_analyzed: int
    opportunities_found: int
    strong_opportunities: int
    last_updated: datetime | None = None


class DayBucketOut(BaseModel):
    label: str          # 'Hoje', 'Amanhã', '+2 dias', ...
    date: str            # ISO date
    matches: list[MatchSummaryOut]


class DashboardOut(BaseModel):
    summary: DashboardSummaryOut
    best_opportunity: MatchSummaryOut | None = None
    opportunities: list[MatchSummaryOut] = []
    days: list[DayBucketOut] = []
    empty_message: str | None = None
