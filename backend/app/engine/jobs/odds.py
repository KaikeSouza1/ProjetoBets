"""Odds — só automática (`capture_odds_for_upcoming_fixtures`, chamada pelo scheduler).
Não existe caminho "sob demanda" hoje: nenhuma rota da API chama `fetch_and_store_odds`
quando alguém abre a análise de uma partida (achado revisando o orçamento de cota,
25/08/2026 — comentário antigo dizia o contrário, ficou desatualizado). Isso significa
que TODO o consumo de odds na API-Football é previsível/controlado pelo agendador,
nunca varia com tráfego de usuário. Cada chamada grava um snapshot novo (nunca
sobrescreve), para permitir ver o movimento da odd depois — e, com captura automática
repetida, começar a construir o par (odd pré-jogo, resultado real) que o backtest com
odds reais precisa (ver `engine/backtest/historical_eval.py`).

Fetch/normalização vêm de `providers.api_football_odds` — este módulo só orquestra
(seleciona partida, chama o provider, grava). Não importa `api_football` diretamente."""
import time

from app.core import config, db
from app.engine.integrations import api_football
from app.engine.providers import api_football_odds
from app.engine.providers.odds_storage import store_markets

DEFAULT_BOOKMAKER_ID = api_football_odds.DEFAULT_BOOKMAKER_ID

# API-Football free tier: 10 req/minuto — ver daily_job.API_FOOTBALL_PACING_SECONDS
# pro achado completo (auditoria 25/08/2026, /api/status mostrou >50% de erro 24h)
API_FOOTBALL_PACING_SECONDS = 6.5

# achado real na mesma auditoria: `_select_fixtures_for_capture` só evitava recapturar
# odd que JÁ TINHA sido capturada com sucesso (`odds_snapshots`) — uma fixture sem odd
# NENHUMA (a maioria durante uma falha de cota) nunca tinha proteção nenhuma contra
# retry repetido, e cada restart do scheduler tentava de novo na hora. O crash loop
# investigado nesta auditoria (65 restarts num dia) teria multiplicado isso por 65 se
# não tivesse sido corrigido primeiro — esta cota é a segunda camada de proteção,
# pro caso de outro crash loop diferente aparecer no futuro. Mais curto que o cooldown
# de recaptura normal (3h, `ODDS_CAPTURE_COOLDOWN_HOURS`) de propósito: não deve
# atrapalhar retry legítimo dentro do ciclo normal de 4h, só absorver restart repetido
# em sequência curta.
RETRY_COOLDOWN_MINUTES = 30


def fetch_and_store_odds(fixture_id: int, bookmaker_id: int = DEFAULT_BOOKMAKER_ID) -> int:
    markets = api_football_odds.fetch_odds(fixture_id, bookmaker_id)
    if not markets:
        return 0

    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            saved = store_markets(cur, fixture_id, markets)
        conn.commit()
    finally:
        conn.close()
    print(f"[odds] fixture {fixture_id}: {saved} mercados salvos ({markets[0].bookmaker_name})")
    return saved


def _select_fixtures_for_capture(max_fixtures: int, cooldown_hours: int) -> list[int]:
    """Partida elegível: ainda não começou E está dentro da janela em que a
    API-Football libera odd no plano gratuito (hoje ± 1 dia — mesma janela que
    `fixtures_daily.sync_fixtures_for_date` já usa). Prioriza quem NUNCA teve odd
    capturada (garante cobertura ampla primeiro); só gasta cota numa 2ª captura do
    mesmo jogo (o que building um histórico de movimento de odd pra CLV) se sobrar
    orçamento — nunca recaptura antes do cooldown, pra não estourar os 100 req/dia."""
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT f.id,
                          EXISTS(SELECT 1 FROM odds_snapshots os WHERE os.fixture_id = f.id) AS has_capture
                   FROM fixtures f
                   WHERE f.status IN ('NS', 'TBD')
                     AND f.date BETWEEN now() - interval '1 day' AND now() + interval '1 day'
                     AND NOT EXISTS (
                         SELECT 1 FROM odds_snapshots os
                         WHERE os.fixture_id = f.id AND os.captured_at > now() - (%s || ' hours')::interval
                     )
                     AND NOT EXISTS (
                         SELECT 1 FROM raw_api_payloads rap
                         WHERE rap.source = 'api-football' AND rap.endpoint = 'odds'
                           AND rap.params->>'fixture' = f.id::text
                           AND rap.fetched_at > now() - (%s || ' minutes')::interval
                     )
                   ORDER BY has_capture ASC, f.date ASC
                   LIMIT %s""",
                (cooldown_hours, RETRY_COOLDOWN_MINUTES, max_fixtures),
            )
            return [r[0] for r in cur.fetchall()]
    finally:
        conn.close()


def capture_odds_for_upcoming_fixtures(
    max_fixtures: int = config.ODDS_CAPTURE_MAX_FIXTURES_PER_RUN,
    cooldown_hours: int = config.ODDS_CAPTURE_COOLDOWN_HOURS,
) -> dict:
    """Chamada pelo scheduler (`daily_job.run_daily_sync`) — automatiza o que antes só
    acontecia quando alguém clicava manualmente na análise de uma partida. Limitada de
    propósito (`max_fixtures` por chamada): a cota da API-Football é 100 req/dia no
    plano gratuito, compartilhada com `fixtures_daily` e o backfill de estatística —
    ver `daily_job.py` pro orçamento completo."""
    fixture_ids = _select_fixtures_for_capture(max_fixtures, cooldown_hours)
    total_saved = 0
    for i, fixture_id in enumerate(fixture_ids):
        try:
            total_saved += fetch_and_store_odds(fixture_id)
        except api_football.ApiFootballError as exc:
            print(f"[odds] captura automática falhou pra fixture {fixture_id}: {exc}")
        if i < len(fixture_ids) - 1:
            time.sleep(API_FOOTBALL_PACING_SECONDS)
    return {"fixtures_attempted": len(fixture_ids), "markets_saved": total_saved}
