import streamlit as st

from engine import db, service

st.set_page_config(page_title="Motor de Análise de Apostas", layout="wide", initial_sidebar_state="expanded")


@st.cache_resource
def _bootstrap():
    db.bootstrap()
    return True


_bootstrap()

# ==================== estilo ====================
st.markdown(
    """
<style>
:root {
    --accent: #1f8f5f;
    --accent-soft: #e6f4ec;
    --negative: #c0392b;
    --negative-soft: #fbeae8;
    --ink-soft: #6b7280;
    --border: #e5e7eb;
}
.block-container { padding-top: 1.6rem; max-width: 1200px; }

.hero {
    background: linear-gradient(135deg, #143d2b 0%, #1f8f5f 100%);
    color: white; border-radius: 16px; padding: 28px 32px; margin-bottom: 20px;
}
.hero h1 { margin: 0 0 4px; font-size: 1.7rem; }
.hero p { margin: 0; opacity: .88; font-size: .95rem; }

.stat-row { display: flex; gap: 12px; margin: 4px 0 22px; flex-wrap: wrap; }
.stat-card {
    background: white; border: 1px solid var(--border); border-radius: 12px;
    padding: 12px 18px; flex: 1; min-width: 140px;
}
.stat-card .num { font-size: 1.5rem; font-weight: 700; color: #111827; }
.stat-card .lbl { font-size: .78rem; color: var(--ink-soft); text-transform: uppercase; letter-spacing: .04em; }

.day-header {
    font-size: .82rem; font-weight: 700; text-transform: uppercase; letter-spacing: .05em;
    color: var(--ink-soft); margin: 22px 0 8px; padding-bottom: 6px; border-bottom: 1px solid var(--border);
}

.league-tag {
    display: inline-block; font-size: .7rem; font-weight: 700; color: var(--accent);
    background: var(--accent-soft); padding: 2px 8px; border-radius: 999px; margin-bottom: 4px;
}

.pill { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: .78rem; font-weight: 700; }
.pill-pos { background: var(--accent-soft); color: var(--accent); }
.pill-neg { background: var(--negative-soft); color: var(--negative); }
.pill-neutral { background: #f3f4f6; color: var(--ink-soft); }

table.mkt { width: 100%; border-collapse: collapse; font-size: .92rem; }
table.mkt th { text-align: left; color: var(--ink-soft); font-size: .75rem; text-transform: uppercase;
    letter-spacing: .03em; padding: 6px 10px; border-bottom: 1px solid var(--border); }
table.mkt td { padding: 7px 10px; border-bottom: 1px solid #f3f4f6; }
table.mkt tr:last-child td { border-bottom: none; }

/* botão do card selecionado: verde (marca), não o vermelho padrão do tema */
div[data-testid="stButton"] button[kind="primary"] {
    background-color: var(--accent) !important; border-color: var(--accent) !important; color: white !important;
}

.best-pick {
    border: 1px solid var(--accent); background: var(--accent-soft); border-radius: 14px;
    padding: 18px 22px; margin: 6px 0 18px;
}
.best-pick .eyebrow { font-size: .75rem; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; color: var(--accent); }
.best-pick .headline { font-size: 1.3rem; font-weight: 700; color: #111827; margin: 4px 0 6px; }
.best-pick .detail { font-size: .88rem; color: var(--ink-soft); }

.no-data-box {
    border: 1px dashed var(--border); border-radius: 12px; padding: 16px 20px;
    color: var(--ink-soft); font-size: .9rem; background: #fafafa;
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="hero">
    <h1>⚽ Motor de análise estatística de apostas</h1>
    <p>Ferramenta de análise — nenhuma probabilidade aqui é certeza. São estimativas de modelo comparadas à odd de mercado.</p>
</div>
""",
    unsafe_allow_html=True,
)

# ==================== dados base ====================
leagues = service.list_leagues()

with st.sidebar:
    st.header("Filtros")
    league_options = {"Todas as ligas": None} | {f"{l['name']} ({l['country']})": l["id"] for l in leagues}
    league_label = st.selectbox("Liga", list(league_options.keys()))
    selected_league_id = league_options[league_label]

    days_ahead = st.slider("Ver quantos dias à frente", min_value=3, max_value=30, value=14) or 14

    with st.expander("ℹ️ Sobre odds/escalação em jogos mais distantes"):
        st.caption(
            "O calendário (esses próximos dias) vem da football-data.org, sem trava de data. "
            "Só odds, escalação, lesão e estatística por partida dependem da API-Football, "
            "que no plano gratuito só libera isso numa janela de hoje ± 1 dia — jogos mais "
            "distantes mostram a probabilidade do modelo mesmo assim, só sem odd pra comparar ainda."
        )

    st.divider()
    with st.expander("📐 Avaliação do modelo (backtest)"):
        st.caption(
            "Só valida calibração (Brier score / taxa de acerto) contra o resultado real, "
            "sem ROI — não temos odd histórica salva ainda para calcular lucro."
        )
        backtest_league_options = {f"{l['name']} ({l['country']})": l["id"] for l in leagues}
        bt_label = st.selectbox("Liga para o backtest", list(backtest_league_options.keys()), key="bt_league")
        bt_league_id = backtest_league_options[bt_label]

        if st.button("Rodar backtest desta liga"):
            from engine.backtest import run_goals_backtest
            with st.spinner("Rodando validação walk-forward..."):
                try:
                    summary = run_goals_backtest(bt_league_id)
                    st.success(f"{summary.n_matches_evaluated} partidas avaliadas.")
                except ValueError as exc:
                    st.warning(str(exc))

        metrics = service.get_latest_backtest_metrics(bt_league_id)
        if metrics:
            st.dataframe(
                [
                    {
                        "Mercado": m["market_key"], "Taxa de acerto": f"{m['hit_rate']*100:.1f}%",
                        "Brier score": f"{m['brier_score']:.3f}", "N": m["n_bets"],
                    }
                    for m in metrics
                ],
                hide_index=True, width="stretch",
            )
            st.caption("Brier score: quanto menor, melhor calibrado. 0.25 é o que dá 'sempre chutar 50%'.")

all_matches = service.list_upcoming(days_ahead=days_ahead)
fixtures = [f for f in all_matches if selected_league_id is None or f["league_id"] == selected_league_id]

n_leagues_present = len({f["league_id"] for f in all_matches})
n_with_odds_window = sum(1 for f in all_matches if f["has_full_data"])
st.markdown(
    f"""
<div class="stat-row">
    <div class="stat-card"><div class="num">{len(all_matches)}</div><div class="lbl">jogos nos próximos {days_ahead} dias</div></div>
    <div class="stat-card"><div class="num">{n_leagues_present}</div><div class="lbl">ligas com jogo no período</div></div>
    <div class="stat-card"><div class="num">{n_with_odds_window}</div><div class="lbl">já na janela de odds (API-Football)</div></div>
    <div class="stat-card"><div class="num">{len(fixtures)}</div><div class="lbl">exibidos com o filtro atual</div></div>
</div>
""",
    unsafe_allow_html=True,
)

if not fixtures:
    st.info("Nenhum jogo com esse filtro. Tente 'Todas as ligas' ou aumente o período no slider.")
    st.stop()

if "selected_match" not in st.session_state or st.session_state.selected_match not in {f["fd_match_id"] for f in fixtures}:
    # prioriza um jogo de liga com temporada madura (mais partidas finalizadas) e já na
    # janela de odds — senão o primeiro clique caía numa liga recém-começada sem dado
    # nenhum, e parecia que a aplicação não funcionava
    maturity = service.get_league_maturity()
    default_match = max(
        fixtures,
        key=lambda f: (maturity.get(f["league_id"], 0), f["has_full_data"]),
    )
    st.session_state.selected_match = default_match["fd_match_id"]

match = next(f for f in fixtures if f["fd_match_id"] == st.session_state.selected_match)
selected_fixture_id = match["fixture_id"]  # None quando ainda é só prévia (fora da janela da API-Football)

# ==================== partida selecionada — sempre no topo, antes da lista ====================
if selected_fixture_id:
    fixture = service.get_fixture(selected_fixture_id)
else:
    fixture = {**match, "referee": None}

st.markdown("### Partida selecionada")
col1, col2, col3 = st.columns([2, 1, 2])
with col1:
    st.markdown(f"#### {fixture['home_team']}")
with col2:
    st.markdown("<div style='text-align:center; padding-top:8px;'>×</div>", unsafe_allow_html=True)
    st.caption(fixture["date"].strftime("%d/%m/%Y %H:%M"))
with col3:
    st.markdown(f"#### {fixture['away_team']}")

st.caption(
    f"{fixture.get('league_display', fixture['league_name'])} · "
    f"árbitro: {fixture.get('referee') or 'não informado'} · status: {fixture['status']}"
)

# ---- melhor aposta: calculado uma vez, mostrado antes de qualquer aba ----
if selected_fixture_id:
    markets_result = service.get_fixture_markets(selected_fixture_id)
else:
    markets_result = service.get_match_preview(match["league_id"], match["home_team_id"], match["away_team_id"])
families = markets_result["families"]

all_opportunities = [o for data in families.values() if not data["error"] for o in data["opportunities"]]
with_odds = [o for o in all_opportunities if o.edge is not None]

if with_odds:
    best = max(with_odds, key=lambda o: o.rank_score)
    st.markdown(
        f"""<div class="best-pick">
            <div class="eyebrow">Melhor valor estimado nesta partida</div>
            <div class="headline">{best.label} — {best.probability*100:.1f}% de probabilidade</div>
            <div class="detail">Odd {best.odd:.2f} (implícita {best.implied_probability*100:.1f}%) ·
                edge estimado {best.edge*100:+.1f}% · confiança {best.confidence}.
                Estimativa de modelo, não é garantia.</div>
        </div>""",
        unsafe_allow_html=True,
    )
elif all_opportunities:
    # evita destacar "mais de 0.5 gols: 96%" como se fosse uma dica útil — isso é quase
    # sempre verdade e não ajuda ninguém a decidir nada
    interesting = [o for o in all_opportunities if 0.15 <= o.probability <= 0.85]
    best = max(interesting or all_opportunities, key=lambda o: o.probability)
    note = (
        "ainda sem odd salva pra essa partida — busque no botão dentro da aba Mercados"
        if selected_fixture_id else
        "essa partida ainda não entrou na janela de odds da API-Football"
    )
    st.markdown(
        f"""<div class="best-pick">
            <div class="eyebrow">Estimativa do modelo (sem odd pra comparar ainda)</div>
            <div class="headline">{best.label} — {best.probability*100:.1f}% de probabilidade estimada</div>
            <div class="detail">{note.capitalize()}. Sem edge calculado, então isto não é uma indicação de valor — só a chance que o modelo vê.</div>
        </div>""",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """<div class="no-data-box">
            Essa liga ainda não tem histórico suficiente pra estimar nada (temporada muito recente ou
            time sem jogo capturado ainda). Tente um jogo do Brasileirão — é a liga com mais dado acumulado hoje.
        </div>""",
        unsafe_allow_html=True,
    )

tab_overview, tab_markets, tab_players = st.tabs(["Visão geral", "Mercados", "Jogadores"])

with tab_overview:
    c1, c2 = st.columns(2)
    for col, team_id, team_name in ((c1, fixture["home_team_id"], fixture["home_team"]),
                                     (c2, fixture["away_team_id"], fixture["away_team"])):
        with col:
            st.markdown(f"**Forma recente — {team_name}**")
            form = service.get_recent_form(team_id, limit=5)
            if not form:
                st.caption("Sem jogos capturados ainda para este time.")
            for m in form:
                st.write(f"{m['result']}  {m['goals_for']}-{m['goals_against']}  vs {m['opponent']} ({m['home_away']})")

    st.markdown("**Classificação**")
    standings = service.get_standings(fixture["league_id"])
    if standings:
        st.dataframe(
            [
                {
                    "Pos": s["rank"], "Time": s["team"], "Pts": s["points"], "J": s["played"],
                    "V": s["win"], "E": s["draw"], "D": s["lose"], "GP": s["goals_for"], "GC": s["goals_against"],
                }
                for s in standings
            ],
            hide_index=True, width="stretch",
        )
    else:
        st.caption("Classificação ainda não sincronizada para esta liga.")

with tab_markets:
    if not selected_fixture_id:
        st.caption("Essa partida ainda está fora da janela de odds da API-Football — mostrando só a probabilidade do modelo.")
    else:
        with st.expander("🔧 Atualizar dados desta partida"):
            st.caption("Cada busca soma requisições à cota diária da API-Football (100/dia no plano gratuito).")
            bcol1, bcol2 = st.columns(2)
            with bcol1:
                if st.button("🔄 Buscar odds atuais"):
                    from engine.ingest import odds as odds_ingest
                    with st.spinner("Consultando API-Football..."):
                        n = odds_ingest.fetch_and_store_odds(selected_fixture_id)
                    st.success(f"{n} mercados de odds salvos.")
                    st.rerun()
            with bcol2:
                if st.button("📊 Buscar estatística (só após o jogo acabar)"):
                    from engine.ingest import fixture_detail
                    with st.spinner("Consultando API-Football..."):
                        n = fixture_detail.fetch_statistics(selected_fixture_id)
                    st.success(f"{n} linhas de estatística salvas — alimenta escanteios/cartões.")
                    st.rerun()

    FRIENDLY_NO_DATA = {
        "gols": "Ainda não há histórico suficiente dessa liga/times para estimar gols.",
        "escanteios": "Ainda não capturamos estatística de escanteio pra essa liga — normal, essa parte cresce com o tempo.",
        "cartões": "Ainda não capturamos estatística de cartão pra essa liga — normal, essa parte cresce com o tempo.",
    }
    for family_name, data in families.items():
        st.markdown(f"#### {family_name.capitalize()}")
        if data["error"]:
            st.markdown(f'<div class="no-data-box">{FRIENDLY_NO_DATA.get(family_name, "Dados insuficientes ainda.")}</div>', unsafe_allow_html=True)
            continue

        prediction = data["prediction"]
        st.caption(
            f"λ esperado — {fixture['home_team']}: {prediction.lambda_home:.2f} · "
            f"{fixture['away_team']}: {prediction.lambda_away:.2f} · "
            f"jogos usados no cálculo: {prediction.n_matches_home_team} / {prediction.n_matches_away_team}"
        )

        rows_html = ["<table class='mkt'><tr><th>Mercado</th><th>Prob.</th><th>Odd</th><th>Implícita</th><th>Edge</th><th>Confiança</th></tr>"]
        for o in data["opportunities"]:
            odd_s = f"{o.odd:.2f}" if o.odd else "—"
            impl_s = f"{o.implied_probability * 100:.1f}%" if o.implied_probability else "—"
            if o.edge is None:
                edge_html = "<span class='pill pill-neutral'>—</span>"
            elif o.edge >= 0:
                edge_html = f"<span class='pill pill-pos'>+{o.edge*100:.1f}%</span>"
            else:
                edge_html = f"<span class='pill pill-neg'>{o.edge*100:.1f}%</span>"
            rows_html.append(
                f"<tr><td>{o.label}</td><td>{o.probability*100:.1f}%</td><td>{odd_s}</td>"
                f"<td>{impl_s}</td><td>{edge_html}</td><td>{o.confidence}</td></tr>"
            )
        rows_html.append("</table>")
        st.markdown("".join(rows_html), unsafe_allow_html=True)

with tab_players:
    if not selected_fixture_id:
        st.info(
            "Probabilidade de jogador depende de estatística por partida da API-Football — "
            "só fica disponível quando esta partida entrar na janela de ~3 dias antes do jogo."
        )
    else:
        st.caption(
            "Jogador lesionado/suspenso (quando informado) ou fora da escalação anunciada é excluído — "
            "não aparece probabilidade nenhuma para ele, em vez de um número especulativo."
        )
        pbcol1, pbcol2 = st.columns(2)
        with pbcol1:
            if st.button("🩹 Buscar lesões/suspensões desta partida"):
                from engine.ingest import fixture_detail
                with st.spinner("Consultando API-Football..."):
                    n = fixture_detail.fetch_injuries(selected_fixture_id)
                st.success(f"{n} desfalques registrados.")
                st.rerun()
        with pbcol2:
            if st.button("👥 Buscar estatística de jogador (só se já tiver acabado)"):
                from engine.ingest import fixture_detail
                with st.spinner("Consultando API-Football..."):
                    n = fixture_detail.fetch_player_stats(selected_fixture_id)
                st.success(f"{n} jogadores salvos.")
                st.rerun()

        player_result = service.get_player_predictions(selected_fixture_id)
        pcol1, pcol2 = st.columns(2)
        for col, side, team_name in ((pcol1, "home", fixture["home_team"]), (pcol2, "away", fixture["away_team"])):
            with col:
                st.markdown(f"**{team_name}**")
                side_data = player_result[side]
                if side_data["error"]:
                    st.caption(f"Dados insuficientes: {side_data['error']}")
                    continue
                st.dataframe(
                    [
                        {
                            "Jogador": p.name, "Jogos": p.n_matches, "Min. médios": f"{p.avg_minutes:.0f}",
                            "Marcar": f"{p.prob_score*100:.1f}%", "Assistir": f"{p.prob_assist*100:.1f}%",
                            "Cartão": f"{p.prob_card*100:.1f}%", "Confiança": p.confidence,
                        }
                        for p in side_data["players"]
                    ],
                    hide_index=True, width="stretch",
                )

st.divider()

# ==================== escolher outro jogo (a lista fica abaixo do detalhe, não antes) ====================
st.subheader("Escolher outro jogo")
current_day = None
cols = None
for i, f in enumerate(fixtures):
    day = f["date"].date()
    if day != current_day:
        current_day = day
        st.markdown(f'<div class="day-header">{day.strftime("%A, %d/%m/%Y")}</div>', unsafe_allow_html=True)
        cols = st.columns(3)
    col = cols[i % 3] if cols else st.container()
    with col:
        is_selected = f["fd_match_id"] == st.session_state.selected_match
        score = f" · {f['home_goals']}-{f['away_goals']}" if f["home_goals"] is not None else ""
        window_flag = "" if f["has_full_data"] else " 🔭"
        label = f"{f['date'].strftime('%H:%M')}  {f['home_team']} x {f['away_team']}{score}{window_flag}"
        st.markdown(f'<span class="league-tag">{f["league_display"]}</span>', unsafe_allow_html=True)
        if st.button(label, key=f"fx_{f['fd_match_id']}", type=("primary" if is_selected else "secondary"), width="stretch"):
            st.session_state.selected_match = f["fd_match_id"]
            st.rerun()
st.caption("🔭 = fora da janela de odds da API-Football ainda (mostra só a probabilidade do modelo)")

st.divider()
st.caption(
    "Ferramenta de análise estatística — não constitui recomendação de aposta garantida. "
    "Toda probabilidade é uma estimativa sujeita a incerteza do modelo e qualidade dos dados disponíveis."
)
