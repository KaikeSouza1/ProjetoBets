"""Rotina diária: tudo que o agendador chama. Cada etapa é isolada — uma falhar
não impede as outras (loga e segue). Orçamento pensado para caber nos 100 req/dia
da API-Football deixando sobra para os cliques sob demanda na interface."""
import datetime
import time

from engine import db
from engine.ingest import fixture_detail, fixtures_daily, season_form

FOOTBALL_DATA_PACING_SECONDS = 6.5  # limite da football-data.org é 10 requisições/minuto


def _target_league_ids() -> list[int]:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM leagues")
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
