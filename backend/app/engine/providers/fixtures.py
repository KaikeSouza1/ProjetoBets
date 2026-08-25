"""Contrato normalizado pra qualquer fonte de partida/jogo. Job/engine nunca lê o JSON
bruto de uma API de fixtures diretamente — sempre recebe isto daqui."""
from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedTeam:
    external_id: int
    name: str
    logo_url: str | None


@dataclass(frozen=True)
class NormalizedVenue:
    external_id: int
    name: str | None
    city: str | None


@dataclass(frozen=True)
class NormalizedFixture:
    external_id: int
    league_external_id: int
    season: int
    round: str | None
    date: str  # ISO datetime — quem grava decide o parsing, aqui é só transporte
    status: str
    elapsed: int | None
    referee_name: str | None
    venue: NormalizedVenue | None
    home_team: NormalizedTeam
    away_team: NormalizedTeam
    home_goals: int | None
    away_goals: int | None
    home_goals_ht: int | None
    away_goals_ht: int | None
    source: str
