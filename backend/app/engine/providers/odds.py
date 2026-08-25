"""Contrato normalizado pra qualquer fonte de odd. O resto do sistema (storage,
opportunity engine) nunca importa `api_football`/`odds_api_io` diretamente pra pegar
odd — sempre recebe isto daqui, pra trocar/adicionar fonte sem tocar em mais nada.

Os dois adapters de hoje (`api_football_odds.py`, `odds_api_io_odds.py`) têm forma de
chamada DIFERENTE de propósito: API-Football é naturalmente por partida (1 request =
1 jogo), odds-api.io é naturalmente em lote por liga (1 request = até 10 jogos, porque
o casamento de evento é feito por nome de time, não por id nosso). Forçar os dois numa
mesma assinatura `fetch(fixture_id)` seria abstração falsa — o que os dois REALMENTE
têm em comum, e é o que importa pro resto do sistema, é a SAÍDA: sempre uma lista de
`NormalizedOddsMarket`, nunca o formato bruto de nenhuma API."""
from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedOddsValue:
    label: str
    odd: float


@dataclass(frozen=True)
class NormalizedOddsMarket:
    bet_type_id: int
    bookmaker_id: int
    bookmaker_name: str
    source: str  # 'api-football' | 'odds-api.io' — rastreabilidade, nunca escondida
    values: list[NormalizedOddsValue]
