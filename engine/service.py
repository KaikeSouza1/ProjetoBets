"""Camada de serviço: tudo que a interface (Streamlit) chama. Nunca calcula nada aqui —
só orquestra os módulos do motor (modelo, valuebet) e faz leitura do banco."""
from datetime import date as date_cls

from engine import db
from engine.models import cards, corners, players, poisson_goals
from engine.valuebet import build_opportunities

_MODEL_MODULES = {"gols": poisson_goals, "escanteios": corners, "cartões": cards}
_model_cache: dict[tuple[str, int], object] = {}


def _league_model(family: str, league_id: int):
    key = (family, league_id)
    if key not in _model_cache:
        _model_cache[key] = _MODEL_MODULES[family].build_league_model(league_id)
    return _model_cache[key]


def get_league_maturity() -> dict[int, int]:
    """Quantas partidas finalizadas cada liga já tem — usado só pra escolher um jogo
    padrão razoável (liga com temporada em curso, não uma que acabou de começar)."""
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT l.id, count(*) FROM fd_matches fm
                   JOIN leagues l ON l.football_data_code = fm.competition_code
                   WHERE fm.status = 'FINISHED' GROUP BY l.id"""
            )
            return dict(cur.fetchall())
    finally:
        conn.close()


def list_leagues() -> list[dict]:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, country FROM leagues ORDER BY country, name")
            return [{"id": r[0], "name": r[1], "country": r[2]} for r in cur.fetchall()]
    finally:
        conn.close()


def list_fixtures(day: date_cls | None = None, league_id: int | None = None) -> list[dict]:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            query = """
                SELECT f.id, f.date, f.status, l.id, l.name,
                       ht.id, ht.name, at.id, at.name, f.home_goals, f.away_goals
                FROM fixtures f
                JOIN leagues l ON l.id = f.league_id
                JOIN teams ht ON ht.id = f.home_team_id
                JOIN teams at ON at.id = f.away_team_id
                WHERE 1=1
            """
            params = []
            if day:
                query += " AND f.date::date = %s"
                params.append(day)
            if league_id:
                query += " AND l.id = %s"
                params.append(league_id)
            query += " ORDER BY f.date"
            cur.execute(query, params)
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {
            "fixture_id": r[0], "date": r[1], "status": r[2],
            "league_id": r[3], "league_name": r[4],
            "home_team_id": r[5], "home_team": r[6],
            "away_team_id": r[7], "away_team": r[8],
            "home_goals": r[9], "away_goals": r[10],
        }
        for r in rows
    ]


def list_upcoming(days_ahead: int = 14) -> list[dict]:
    """Calendário sem a trava de 3 dias da API-Football — fonte é a football-data.org,
    que dá o calendário completo da temporada de graça. Cada jogo carrega `fixture_id`
    (id da API-Football) só quando ele já existir na nossa janela de captura (~hoje ± 1
    dia); fora disso o jogo aparece igual, só que sem odds/escalação/estatística ainda —
    essas dependem da partida entrar na janela, não tem como pular essa espera."""
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT fm.fd_match_id, fm.utc_date, fm.status, l.id, l.name, l.country,
                          fm.home_team_id, ht.name, fm.away_team_id, at.name,
                          fm.home_goals, fm.away_goals, f.id
                   FROM fd_matches fm
                   JOIN leagues l ON l.football_data_code = fm.competition_code
                   JOIN teams ht ON ht.id = fm.home_team_id
                   JOIN teams at ON at.id = fm.away_team_id
                   LEFT JOIN fixtures f ON f.league_id = l.id
                                        AND f.home_team_id = fm.home_team_id
                                        AND f.away_team_id = fm.away_team_id
                                        AND f.date::date = fm.utc_date::date
                   WHERE fm.status IN ('SCHEDULED', 'TIMED', 'FINISHED')
                     AND fm.utc_date::date BETWEEN CURRENT_DATE AND CURRENT_DATE + %s
                   ORDER BY fm.utc_date""",
                (days_ahead,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {
            "fd_match_id": r[0], "fixture_id": r[12], "date": r[1], "status": r[2],
            "league_id": r[3], "league_name": r[4], "league_country": r[5],
            "league_display": f"{r[4]} ({r[5]})",
            "home_team_id": r[6], "home_team": r[7],
            "away_team_id": r[8], "away_team": r[9],
            "home_goals": r[10], "away_goals": r[11],
            "has_full_data": r[12] is not None,
        }
        for r in rows
    ]


def get_fixture(fixture_id: int) -> dict | None:
    fixtures = _fixtures_where("f.id = %s", (fixture_id,))
    return fixtures[0] if fixtures else None


def _fixtures_where(where_sql: str, params: tuple) -> list[dict]:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""SELECT f.id, f.date, f.status, f.league_id, l.name, l.country,
                           f.home_team_id, ht.name, f.away_team_id, at.name,
                           f.home_goals, f.away_goals, r.name
                    FROM fixtures f
                    JOIN leagues l ON l.id = f.league_id
                    JOIN teams ht ON ht.id = f.home_team_id
                    JOIN teams at ON at.id = f.away_team_id
                    LEFT JOIN referees r ON r.id = f.referee_id
                    WHERE {where_sql}""",
                params,
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return [
        {
            "fixture_id": r[0], "date": r[1], "status": r[2], "league_id": r[3], "league_name": r[4],
            "league_display": f"{r[4]} ({r[5]})",
            "home_team_id": r[6], "home_team": r[7], "away_team_id": r[8], "away_team": r[9],
            "home_goals": r[10], "away_goals": r[11], "referee": r[12],
        }
        for r in rows
    ]


def get_recent_form(team_id: int, limit: int = 5) -> list[dict]:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT utc_date, home_team_name_raw, away_team_name_raw, home_goals, away_goals, home_team_id
                   FROM fd_matches
                   WHERE (home_team_id = %s OR away_team_id = %s) AND status = 'FINISHED'
                   ORDER BY utc_date DESC LIMIT %s""",
                (team_id, team_id, limit),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    out = []
    for utc_date, home_name, away_name, hg, ag, home_id in rows:
        is_home = home_id == team_id
        gf, ga = (hg, ag) if is_home else (ag, hg)
        result = "V" if gf > ga else ("E" if gf == ga else "D")
        opponent = away_name if is_home else home_name
        out.append({
            "date": utc_date, "opponent": opponent, "home_away": "casa" if is_home else "fora",
            "goals_for": gf, "goals_against": ga, "result": result,
        })
    return out


def get_standings(league_id: int) -> list[dict]:
    """Só a tabela mais recente — no início da temporada é comum vários times aparecerem
    empatados na mesma posição (todo mundo com 0 jogos), então não dá pra deduplicar por
    posição; cada time tem sua própria linha, sempre."""
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(snapshot_date) FROM standings_snapshots WHERE league_id = %s", (league_id,))
            latest_date = cur.fetchone()[0]
            if latest_date is None:
                return []
            cur.execute(
                """SELECT s.rank, t.name, s.points, s.played, s.win, s.draw, s.lose, s.goals_for, s.goals_against
                   FROM standings_snapshots s
                   JOIN teams t ON t.id = s.team_id
                   WHERE s.league_id = %s AND s.snapshot_date = %s
                   ORDER BY s.rank ASC, t.name ASC""",
                (league_id, latest_date),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return [
        {
            "rank": rank, "team": name, "points": points, "played": played,
            "win": win, "draw": draw, "lose": lose, "goals_for": gf, "goals_against": ga,
        }
        for rank, name, points, played, win, draw, lose, gf, ga in rows
    ]


def _compute_market_families(league_id: int, home_team_id: int, away_team_id: int, odds_lookup_id: int) -> dict:
    """Núcleo reaproveitado por partidas já na janela (com odds reais) e por prévias
    (fora da janela — mesma probabilidade de modelo, só que sem odd/edge pra comparar
    ainda, porque `odds_lookup_id` nunca vai ter snapshot salvo nesse caso)."""
    families = {}
    for family, module in _MODEL_MODULES.items():
        try:
            model = _league_model(family, league_id)
            prediction = module.predict_fixture(model, home_team_id, away_team_id)
            min_matches = min(prediction.n_matches_home_team, prediction.n_matches_away_team)
            opportunities = build_opportunities(odds_lookup_id, prediction, min_matches)
            families[family] = {"prediction": prediction, "opportunities": opportunities, "error": None}
        except ValueError as exc:
            families[family] = {"prediction": None, "opportunities": [], "error": str(exc)}
    return families


def get_fixture_markets(fixture_id: int) -> dict:
    """Roda os três modelos independentes (gols, escanteios, cartões) para uma partida
    já capturada pela API-Football. Cada família pode falhar isoladamente por falta de
    dado — não derruba as outras."""
    fixture = get_fixture(fixture_id)
    if not fixture:
        raise ValueError(f"fixture {fixture_id} não encontrada")

    families = _compute_market_families(fixture["league_id"], fixture["home_team_id"], fixture["away_team_id"], fixture_id)
    return {"fixture": fixture, "families": families}


def get_match_preview(league_id: int, home_team_id: int, away_team_id: int) -> dict:
    """Mesma coisa, mas para um jogo que a football-data.org já conhece e a API-Football
    ainda não capturou (fora da janela de ~3 dias). Probabilidade de modelo funciona
    igual; odds/edge ficam None porque não existe odd salva para comparar ainda."""
    families = _compute_market_families(league_id, home_team_id, away_team_id, odds_lookup_id=-1)
    return {"families": families}


def get_player_predictions(fixture_id: int) -> dict:
    """Probabilidades de jogador (marcar/assistir/cartão) para os dois times.
    Retorna erro por time se o modelo de gols não tiver dados suficientes para calcular
    o fator de força defensiva do adversário."""
    fixture = get_fixture(fixture_id)
    if not fixture:
        raise ValueError(f"fixture {fixture_id} não encontrada")

    try:
        goals_model = _league_model("gols", fixture["league_id"])
    except ValueError as exc:
        return {"home": {"players": [], "error": str(exc)}, "away": {"players": [], "error": str(exc)}}

    home_strength = goals_model.strengths.get(fixture["home_team_id"])
    away_strength = goals_model.strengths.get(fixture["away_team_id"])

    result = {}
    if away_strength is None:
        result["home"] = {"players": [], "error": "time visitante sem força defensiva calculada"}
    else:
        preds = players.predict_team_players(fixture_id, fixture["home_team_id"], away_strength.away_defense)
        result["home"] = {"players": preds, "error": None if preds else "sem jogadores com dado suficiente ainda"}

    if home_strength is None:
        result["away"] = {"players": [], "error": "time da casa sem força defensiva calculada"}
    else:
        preds = players.predict_team_players(fixture_id, fixture["away_team_id"], home_strength.home_defense)
        result["away"] = {"players": preds, "error": None if preds else "sem jogadores com dado suficiente ainda"}

    return result


def get_latest_backtest_metrics(league_id: int) -> list[dict]:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT bm.market_key, bm.hit_rate, bm.brier_score, bm.n_bets, br.date_from, br.date_to
                   FROM backtest_metrics bm
                   JOIN backtest_runs br ON br.id = bm.backtest_run_id
                   WHERE bm.league_id = %s AND bm.backtest_run_id = (
                       SELECT MAX(backtest_run_id) FROM backtest_metrics WHERE league_id = %s
                   )
                   ORDER BY bm.market_key""",
                (league_id, league_id),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return [
        {"market_key": r[0], "hit_rate": r[1], "brier_score": r[2], "n_bets": r[3], "date_from": r[4], "date_to": r[5]}
        for r in rows
    ]
