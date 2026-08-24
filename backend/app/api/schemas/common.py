"""Schemas compartilhados entre rotas — nenhuma rota devolve tupla/dict crú do banco."""
from pydantic import BaseModel


class ErrorOut(BaseModel):
    detail: str


class LeagueOut(BaseModel):
    id: int
    name: str
    country: str | None = None
