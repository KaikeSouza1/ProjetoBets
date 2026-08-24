"""Detalhe por partida, sob demanda: estatísticas, eventos, escalação, lesões.
Cada chamada custa 1 requisição à API-Football — só busca quando alguém pede
(abrir a análise de uma partida, ou o backfill lento do agendador)."""
from engine import db, teammatch
from engine.sources import api_football


def _team_internal_id(cur, api_football_team_id: int, name_hint: str) -> int:
    return teammatch.upsert_team(cur, "api-football", api_football_team_id, name_hint)


def fetch_statistics(fixture_id: int) -> int:
    results = api_football.get("fixtures/statistics", {"fixture": fixture_id})
    conn = db.get_connection()
    saved = 0
    try:
        with conn.cursor() as cur:
            for team_block in results:
                team_id = _team_internal_id(cur, team_block["team"]["id"], team_block["team"]["name"])
                for stat in team_block["statistics"]:
                    cur.execute(
                        """INSERT INTO fixture_statistics (fixture_id, team_id, stat_type, value)
                           VALUES (%s, %s, %s, %s)
                           ON CONFLICT (fixture_id, team_id, stat_type) DO UPDATE SET value = EXCLUDED.value""",
                        (fixture_id, team_id, stat["type"], str(stat["value"]) if stat["value"] is not None else None),
                    )
                    saved += 1
        conn.commit()
    finally:
        conn.close()
    print(f"[fixture_detail] statistics fixture {fixture_id}: {saved} linhas")
    return saved


def fetch_events(fixture_id: int) -> int:
    results = api_football.get("fixtures/events", {"fixture": fixture_id})
    conn = db.get_connection()
    saved = 0
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM fixture_events WHERE fixture_id = %s", (fixture_id,))
            for ev in results:
                team_id = None
                if ev.get("team") and ev["team"].get("id"):
                    team_id = _team_internal_id(cur, ev["team"]["id"], ev["team"]["name"])
                for role in ("player", "assist"):
                    person = ev.get(role)
                    if person and person.get("id"):
                        cur.execute(
                            "INSERT INTO players (id, name) VALUES (%s, %s) ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name",
                            (person["id"], person.get("name") or f"(sem nome #{person['id']})"),
                        )
                cur.execute(
                    """INSERT INTO fixture_events
                           (fixture_id, team_id, player_id, assist_player_id, minute, extra_minute, type, detail, comment)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        fixture_id, team_id,
                        ev["player"].get("id") if ev.get("player") else None,
                        ev["assist"].get("id") if ev.get("assist") else None,
                        ev["time"].get("elapsed"), ev["time"].get("extra"),
                        ev.get("type"), ev.get("detail"), ev.get("comments"),
                    ),
                )
                saved += 1
        conn.commit()
    finally:
        conn.close()
    print(f"[fixture_detail] events fixture {fixture_id}: {saved} eventos")
    return saved


def fetch_lineups(fixture_id: int) -> int:
    results = api_football.get("fixtures/lineups", {"fixture": fixture_id})
    conn = db.get_connection()
    saved = 0
    try:
        with conn.cursor() as cur:
            for block in results:
                team_id = _team_internal_id(cur, block["team"]["id"], block["team"]["name"])
                coach_id = None
                if block.get("coach") and block["coach"].get("id"):
                    coach = block["coach"]
                    cur.execute(
                        "INSERT INTO coaches (id, name) VALUES (%s, %s) ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name",
                        (coach["id"], coach["name"]),
                    )
                    coach_id = coach["id"]

                cur.execute(
                    """INSERT INTO fixture_lineups (fixture_id, team_id, formation, coach_id)
                       VALUES (%s, %s, %s, %s)
                       ON CONFLICT (fixture_id, team_id) DO UPDATE SET formation = EXCLUDED.formation, coach_id = EXCLUDED.coach_id
                       RETURNING id""",
                    (fixture_id, team_id, block.get("formation"), coach_id),
                )
                lineup_id = cur.fetchone()[0]

                for is_starter, players in ((True, block.get("startXI", [])), (False, block.get("substitutes", []))):
                    for p in players:
                        player = p["player"]
                        cur.execute(
                            "INSERT INTO players (id, name) VALUES (%s, %s) ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name",
                            (player["id"], player["name"]),
                        )
                        cur.execute(
                            """INSERT INTO fixture_lineup_players (lineup_id, player_id, position, grid, is_starter)
                               VALUES (%s, %s, %s, %s, %s)
                               ON CONFLICT (lineup_id, player_id) DO UPDATE SET
                                   position = EXCLUDED.position, grid = EXCLUDED.grid, is_starter = EXCLUDED.is_starter""",
                            (lineup_id, player["id"], player.get("pos"), player.get("grid"), is_starter),
                        )
                        saved += 1
        conn.commit()
    finally:
        conn.close()
    print(f"[fixture_detail] lineups fixture {fixture_id}: {saved} jogadores")
    return saved


def fetch_player_stats(fixture_id: int) -> int:
    results = api_football.get("fixtures/players", {"fixture": fixture_id})
    conn = db.get_connection()
    saved = 0
    try:
        with conn.cursor() as cur:
            for team_block in results:
                team_id = _team_internal_id(cur, team_block["team"]["id"], team_block["team"]["name"])
                for p in team_block["players"]:
                    player = p["player"]
                    stats = p["statistics"][0] if p["statistics"] else {}
                    cur.execute(
                        "INSERT INTO players (id, name) VALUES (%s, %s) ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name",
                        (player["id"], player["name"]),
                    )
                    games = stats.get("games", {}) or {}
                    shots = stats.get("shots", {}) or {}
                    goals = stats.get("goals", {}) or {}
                    passes = stats.get("passes", {}) or {}
                    fouls = stats.get("fouls", {}) or {}
                    cards = stats.get("cards", {}) or {}
                    cur.execute(
                        """INSERT INTO fixture_player_stats (
                               fixture_id, team_id, player_id, minutes, position, rating,
                               shots_total, shots_on, goals, assists, passes_total, passes_key,
                               fouls_committed, fouls_drawn, yellow_cards, red_cards
                           ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                           ON CONFLICT (fixture_id, player_id) DO UPDATE SET
                               minutes = EXCLUDED.minutes, rating = EXCLUDED.rating,
                               shots_total = EXCLUDED.shots_total, shots_on = EXCLUDED.shots_on,
                               goals = EXCLUDED.goals, assists = EXCLUDED.assists""",
                        (
                            fixture_id, team_id, player["id"], games.get("minutes"), games.get("position"),
                            float(games["rating"]) if games.get("rating") else None,
                            shots.get("total"), shots.get("on"), goals.get("total"), goals.get("assists"),
                            passes.get("total"), passes.get("key"),
                            fouls.get("committed"), fouls.get("drawn"),
                            cards.get("yellow"), cards.get("red"),
                        ),
                    )
                    saved += 1
        conn.commit()
    finally:
        conn.close()
    print(f"[fixture_detail] player_stats fixture {fixture_id}: {saved} jogadores")
    return saved


def fetch_injuries(fixture_id: int) -> int:
    results = api_football.get("injuries", {"fixture": fixture_id})
    conn = db.get_connection()
    saved = 0
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM injuries WHERE fixture_id = %s", (fixture_id,))
            for item in results:
                player = item["player"]
                team = item["team"]
                cur.execute(
                    "INSERT INTO players (id, name) VALUES (%s, %s) ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name",
                    (player["id"], player["name"]),
                )
                team_id = _team_internal_id(cur, team["id"], team["name"])
                cur.execute(
                    """INSERT INTO injuries (player_id, team_id, fixture_id, type, reason)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (player["id"], team_id, fixture_id, player.get("type"), player.get("reason")),
                )
                saved += 1
        conn.commit()
    finally:
        conn.close()
    print(f"[fixture_detail] injuries fixture {fixture_id}: {saved} desfalques")
    return saved
