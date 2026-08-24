"""Rotina diária: tudo que o agendador chama. Cada etapa é isolada — uma falhar
não impede as outras (loga e segue). Orçamento pensado para caber nos 100 req/dia
da API-Football deixando sobra para os cliques sob demanda na interface."""
import datetime
import time

from app.core import db
from app.engine.jobs import fixture_detail, fixtures_daily, multi_bookmaker_odds, odds, season_form

FOOTBALL_DATA_PACING_SECONDS = 6.5  # limite da football-data.org é 10 requisições/minuto


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


def _yesterday_finished_target_fixtures() -> list[int]:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT f.id FROM fixtures f
                   WHERE f.status = 'FT' AND f.date::date = %s
                     AND NOT EXISTS (SELECT 1 FROM fixture_statistics fs WHERE fs.fixture_id = f.id)""",
                (datetime.date.today() - datetime.timedelta(days=1),),
            )
            return [r[0] for r in cur.fetchall()]
    finally:
        conn.close()


def run_daily_sync():
    today = datetime.date.today()

    for day in (today - datetime.timedelta(days=1), today, today + datetime.timedelta(days=1)):
        try:
            fixtures_daily.sync_fixtures_for_date(day)
        except Exception as exc:
            print(f"[daily_job] falhou fixtures_daily {day}: {exc}")

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

    # backfill lento: estatística/jogador/lesão das partidas de ontem que já terminaram e
    # ainda não têm detalhe salvo — é assim que os modelos de escanteio/cartão/jogador crescem
    for fixture_id in _yesterday_finished_target_fixtures():
        for fetch in (fixture_detail.fetch_statistics, fixture_detail.fetch_player_stats, fixture_detail.fetch_injuries):
            try:
                fetch(fixture_id)
            except Exception as exc:
                print(f"[daily_job] falhou {fetch.__name__} fixture {fixture_id}: {exc}")

    print(f"[daily_job] sincronização diária concluída — {today.isoformat()}")
