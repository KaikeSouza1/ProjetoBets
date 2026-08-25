"""Rotina diária: tudo que o agendador chama. Cada etapa é isolada — uma falhar
não impede as outras (loga e segue). Orçamento pensado para caber nos 100 req/dia
da API-Football deixando sobra para os cliques sob demanda na interface."""
import datetime
import time

from app.core import db
from app.engine.jobs import fixture_detail, fixtures_daily, multi_bookmaker_odds, odds, season_form
from app.services import opportunity_notifications, result_tracking

FOOTBALL_DATA_PACING_SECONDS = 6.5  # limite da football-data.org é 10 requisições/minuto
# API-Football free tier: 10 req/minuto (confirmado em api-football.com/news/post/how-ratelimit-works,
# 25/08/2026) — achado real na auditoria: o backfill abaixo disparava statistics+player_stats+injuries
# de N partidas em sequência SEM pausa nenhuma, estourando o limite por minuto sempre que
# tinha mais de ~3 partidas pra processar (confirmado via /api/status: 130 erros em 240
# chamadas nas últimas 24h). 6.5s dá a mesma folga que já existia pro football-data.org.
API_FOOTBALL_PACING_SECONDS = 6.5


def _target_league_ids() -> list[int]:
    """Só ligas com football_data_code — usada exclusivamente pra chamar `season_form`
    (football-data.org). Liga só-API-Football (ex.: Copa do Brasil, sem essa coluna)
    não tem o que sincronizar aqui; ela entra em `fixtures_daily` e na captura de odds
    normalmente, que já cobrem todas as ligas sem filtro."""
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM leagues WHERE football_data_code IS NOT NULL")
            return [r[0] for r in cur.fetchall()]
    finally:
        conn.close()


def _yesterday_missing_statistics() -> list[int]:
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            return fixture_detail.fixtures_with_incomplete_statistics(cur, since=yesterday, until=yesterday)
    finally:
        conn.close()


def _yesterday_missing_player_stats() -> list[int]:
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            return fixture_detail.fixtures_missing_player_stats(cur, since=yesterday, until=yesterday)
    finally:
        conn.close()


def run_daily_sync():
    today = datetime.date.today()

    for day in (today - datetime.timedelta(days=1), today, today + datetime.timedelta(days=1)):
        try:
            fixtures_daily.sync_fixtures_for_date(day)
        except Exception as exc:
            print(f"[daily_job] falhou fixtures_daily {day}: {exc}")
        time.sleep(API_FOOTBALL_PACING_SECONDS)

    # captura automática de odds pré-jogo — sem isso, o backtest com odds reais
    # (engine/backtest/historical_eval.py) nunca vai ter partida elegível pra avaliar,
    # porque odd só existia quando alguém clicava manualmente na análise
    try:
        result = odds.capture_odds_for_upcoming_fixtures()
        print(f"[daily_job] captura automática de odds: {result}")
    except Exception as exc:
        print(f"[daily_job] falhou captura automática de odds: {exc}")

    # fonte adicional (Bet365 + Superbet via odds-api.io) — nunca substitui a de cima,
    # só soma bookmaker quando o jogo casa; ver multi_bookmaker_odds.py
    try:
        result = multi_bookmaker_odds.capture_multi_bookmaker_odds()
        print(f"[daily_job] captura multi-casa (Bet365/Superbet): {result}")
    except Exception as exc:
        print(f"[daily_job] falhou captura multi-casa: {exc}")

    for league_id in _target_league_ids():
        try:
            season_form.sync_standings(league_id)
        except Exception as exc:
            print(f"[daily_job] falhou sync_standings liga {league_id}: {exc}")
        time.sleep(FOOTBALL_DATA_PACING_SECONDS)
        try:
            season_form.sync_league_results(league_id)
        except Exception as exc:
            print(f"[daily_job] falhou sync_league_results liga {league_id}: {exc}")
        time.sleep(FOOTBALL_DATA_PACING_SECONDS)

    # ingestão diária (não confundir com backfill histórico — ver scripts/backfill_statistics.py
    # e scripts/backfill_api_football_league.py, que cobrem o passivo de partidas mais
    # antigas sob demanda, respeitando cota, sem entrar nesse loop automático): só as
    # partidas de ONTEM, e só o que os modelos de gols/escanteio/cartão/jogador
    # realmente usam pra treinar — estatística (escanteio/cartão) e estatística de
    # jogador (histórico agregado em engine/models/players.py).
    #
    # `injuries` foi removido daqui (achado real na auditoria de cota, 25/08/2026):
    # a única coisa que lê `injuries` é a exclusão de jogador machucado numa previsão
    # de jogo FUTURO (players.py, `_unavailable_player_ids`) — buscar lesão de um jogo
    # de ONTEM que já acabou não serve pra nada, e não existe hoje nenhum outro lugar
    # que busque `injuries` pra jogo futuro (não tem enriquecimento pré-jogo automático
    # ainda) — ou seja, essa chamada nunca teve efeito prático nenhum, só gastava cota.
    for fixture_id in _yesterday_missing_statistics():
        try:
            fixture_detail.fetch_statistics(fixture_id)
        except Exception as exc:
            print(f"[daily_job] falhou fetch_statistics fixture {fixture_id}: {exc}")
        time.sleep(API_FOOTBALL_PACING_SECONDS)

    for fixture_id in _yesterday_missing_player_stats():
        try:
            fixture_detail.fetch_player_stats(fixture_id)
        except Exception as exc:
            print(f"[daily_job] falhou fetch_player_stats fixture {fixture_id}: {exc}")
        time.sleep(API_FOOTBALL_PACING_SECONDS)

    # fecha o ciclo de auditoria: previsão que já tem resultado real disponível vira
    # WIN/LOSS agora (só mercados de gols — ver result_tracking.py)
    try:
        result_tracking.resolve_pending_snapshots()
    except Exception as exc:
        print(f"[daily_job] falhou result_tracking: {exc}")

    # Opportunity Engine -> fila: enfileira as melhores oportunidades do dia pros leads
    # cadastrados. Só enfileira — o envio real depende do WhatsAppProvider configurado
    # (console por padrão; nada sai de verdade sem EVOLUTION_API_URL/KEY real).
    try:
        opportunity_notifications.enqueue_daily_opportunities()
    except Exception as exc:
        print(f"[daily_job] falhou opportunity_notifications: {exc}")

    print(f"[daily_job] sincronização diária concluída — {today.isoformat()}")
