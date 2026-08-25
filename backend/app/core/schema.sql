-- Motor de análise de apostas de futebol — schema PostgreSQL
-- Todo o schema é idempotente (IF NOT EXISTS) para poder rodar a cada abertura do app.

-- ==================== arquivo bruto ====================

CREATE TABLE IF NOT EXISTS raw_api_payloads (
    id          BIGSERIAL PRIMARY KEY,
    source      TEXT NOT NULL,           -- 'api-football' | 'football-data-org'
    endpoint    TEXT NOT NULL,
    params      JSONB NOT NULL DEFAULT '{}',
    payload     JSONB NOT NULL,
    fetched_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_raw_payloads_endpoint ON raw_api_payloads (source, endpoint, fetched_at);

-- ==================== entidades base ====================

CREATE TABLE IF NOT EXISTS leagues (
    id                  BIGINT PRIMARY KEY,      -- id da API-Football
    football_data_code  TEXT UNIQUE,             -- código da football-data.org ('BSA', 'PL', ...), quando aplicável
    name                TEXT NOT NULL,
    country             TEXT,
    tier                TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS league_coverage (
    league_id    BIGINT NOT NULL REFERENCES leagues(id),
    season       INT NOT NULL,
    flag_name    TEXT NOT NULL,
    flag_value   BOOLEAN NOT NULL,
    checked_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (league_id, season, flag_name)
);

CREATE TABLE IF NOT EXISTS venues (
    id       BIGINT PRIMARY KEY,
    name     TEXT,
    city     TEXT,
    country  TEXT
);

CREATE TABLE IF NOT EXISTS teams (
    id                BIGSERIAL PRIMARY KEY,   -- surrogate nosso; as duas fontes têm espaços de id diferentes
    api_football_id   BIGINT UNIQUE,
    football_data_id   BIGINT UNIQUE,
    name              TEXT NOT NULL,
    country           TEXT,
    founded           INT,
    venue_id          BIGINT REFERENCES venues(id),
    logo_url          TEXT
);

CREATE TABLE IF NOT EXISTS coaches (
    id    BIGINT PRIMARY KEY,
    name  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS referees (
    id                    BIGSERIAL PRIMARY KEY,
    name                  TEXT NOT NULL UNIQUE,
    matches_seen          INT NOT NULL DEFAULT 0,
    avg_cards_per_match   NUMERIC(5,2)
);

CREATE TABLE IF NOT EXISTS players (
    id           BIGINT PRIMARY KEY,
    name         TEXT NOT NULL,
    birthdate    DATE,
    nationality  TEXT,
    position     TEXT
);

-- ==================== partidas ====================

CREATE TABLE IF NOT EXISTS fixtures (
    id              BIGINT PRIMARY KEY,     -- id da API-Football
    league_id       BIGINT REFERENCES leagues(id),
    season          INT,
    round           TEXT,
    date            TIMESTAMPTZ,
    status          TEXT,
    elapsed         INT,
    referee_id      BIGINT REFERENCES referees(id),
    venue_id        BIGINT REFERENCES venues(id),
    home_team_id    BIGINT REFERENCES teams(id),
    away_team_id    BIGINT REFERENCES teams(id),
    home_goals      INT,
    away_goals      INT,
    home_goals_ht   INT,
    away_goals_ht   INT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_fixtures_date ON fixtures (date);
CREATE INDEX IF NOT EXISTS idx_fixtures_league_season ON fixtures (league_id, season);
CREATE INDEX IF NOT EXISTS idx_fixtures_teams ON fixtures (home_team_id, away_team_id);

CREATE TABLE IF NOT EXISTS fixture_statistics (
    fixture_id  BIGINT NOT NULL REFERENCES fixtures(id),
    team_id     BIGINT NOT NULL REFERENCES teams(id),
    stat_type   TEXT NOT NULL,
    value       TEXT,
    PRIMARY KEY (fixture_id, team_id, stat_type)
);

CREATE TABLE IF NOT EXISTS fixture_events (
    id                BIGSERIAL PRIMARY KEY,
    fixture_id        BIGINT NOT NULL REFERENCES fixtures(id),
    team_id           BIGINT REFERENCES teams(id),
    player_id         BIGINT REFERENCES players(id),
    assist_player_id  BIGINT REFERENCES players(id),
    minute            INT,
    extra_minute      INT,
    type              TEXT,
    detail            TEXT,
    comment           TEXT
);
CREATE INDEX IF NOT EXISTS idx_fixture_events_fixture ON fixture_events (fixture_id);

CREATE TABLE IF NOT EXISTS fixture_lineups (
    id          BIGSERIAL PRIMARY KEY,
    fixture_id  BIGINT NOT NULL REFERENCES fixtures(id),
    team_id     BIGINT NOT NULL REFERENCES teams(id),
    formation   TEXT,
    coach_id    BIGINT REFERENCES coaches(id),
    UNIQUE (fixture_id, team_id)
);

CREATE TABLE IF NOT EXISTS fixture_lineup_players (
    lineup_id   BIGINT NOT NULL REFERENCES fixture_lineups(id),
    player_id   BIGINT NOT NULL REFERENCES players(id),
    position    TEXT,
    grid        TEXT,
    is_starter  BOOLEAN NOT NULL,
    PRIMARY KEY (lineup_id, player_id)
);

CREATE TABLE IF NOT EXISTS fixture_player_stats (
    fixture_id       BIGINT NOT NULL REFERENCES fixtures(id),
    team_id          BIGINT REFERENCES teams(id),
    player_id        BIGINT NOT NULL REFERENCES players(id),
    minutes          INT,
    position         TEXT,
    rating           NUMERIC(4,2),
    shots_total      INT,
    shots_on         INT,
    goals            INT,
    assists          INT,
    passes_total     INT,
    passes_key       INT,
    fouls_committed  INT,
    fouls_drawn      INT,
    yellow_cards     INT,
    red_cards        INT,
    PRIMARY KEY (fixture_id, player_id)
);

-- ==================== resultados de temporada (football-data.org, bootstrap do modelo) ====================

CREATE TABLE IF NOT EXISTS fd_matches (
    fd_match_id        BIGINT PRIMARY KEY,      -- id nativo da football-data.org (espaço de id separado do da API-Football)
    competition_code   TEXT NOT NULL,
    season_start_year  INT,
    matchday           INT,
    utc_date           TIMESTAMPTZ,
    status             TEXT,
    home_team_id       BIGINT REFERENCES teams(id),   -- nosso id interno, resolvido por nome
    away_team_id       BIGINT REFERENCES teams(id),
    home_team_name_raw TEXT NOT NULL,
    away_team_name_raw TEXT NOT NULL,
    home_goals         INT,
    away_goals         INT,
    fetched_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_fd_matches_competition ON fd_matches (competition_code, season_start_year);
CREATE INDEX IF NOT EXISTS idx_fd_matches_teams ON fd_matches (home_team_id, away_team_id);

CREATE TABLE IF NOT EXISTS api_request_log (
    id           BIGSERIAL PRIMARY KEY,
    source       TEXT NOT NULL,
    endpoint     TEXT NOT NULL,
    status_code  INT,
    called_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_api_request_log_source_date ON api_request_log (source, called_at);

-- ==================== forma e classificação (football-data.org) ====================

CREATE TABLE IF NOT EXISTS team_recent_form (
    id          BIGSERIAL PRIMARY KEY,
    team_id     BIGINT NOT NULL REFERENCES teams(id),
    fetched_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    source      TEXT NOT NULL DEFAULT 'football-data-org',
    results     JSONB NOT NULL,   -- lista de {date, opponent, home_away, goals_for, goals_against}
    wins        INT,
    draws       INT,
    losses      INT
);
CREATE INDEX IF NOT EXISTS idx_team_recent_form_team ON team_recent_form (team_id, fetched_at DESC);

CREATE TABLE IF NOT EXISTS standings_snapshots (
    id             BIGSERIAL PRIMARY KEY,
    league_id      BIGINT REFERENCES leagues(id),
    season         INT,
    snapshot_date  DATE NOT NULL,
    team_id        BIGINT NOT NULL REFERENCES teams(id),
    rank           INT,
    points         INT,
    played         INT,
    win            INT,
    draw           INT,
    lose           INT,
    goals_for      INT,
    goals_against  INT,
    source         TEXT NOT NULL DEFAULT 'football-data-org',
    UNIQUE (league_id, season, snapshot_date, team_id, source)
);
CREATE INDEX IF NOT EXISTS idx_standings_league_season_date ON standings_snapshots (league_id, season, snapshot_date);

-- ==================== desfalques ====================

CREATE TABLE IF NOT EXISTS injuries (
    id           BIGSERIAL PRIMARY KEY,
    player_id    BIGINT REFERENCES players(id),
    team_id      BIGINT REFERENCES teams(id),
    fixture_id   BIGINT REFERENCES fixtures(id),
    type         TEXT,     -- 'Injury' | 'Suspension'
    reason       TEXT,
    reported_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_injuries_fixture ON injuries (fixture_id);

CREATE TABLE IF NOT EXISTS sidelined (
    id          BIGSERIAL PRIMARY KEY,
    player_id   BIGINT REFERENCES players(id),
    type        TEXT,
    start_date  DATE,
    end_date    DATE
);

-- ==================== odds (append-only) ====================

CREATE TABLE IF NOT EXISTS bookmakers (
    id    INT PRIMARY KEY,
    name  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bet_types (
    id             INT PRIMARY KEY,
    name           TEXT NOT NULL,
    source_system  TEXT NOT NULL DEFAULT 'prematch'  -- 'prematch' | 'live'
);

CREATE TABLE IF NOT EXISTS odds_snapshots (
    id            BIGSERIAL PRIMARY KEY,
    fixture_id    BIGINT NOT NULL REFERENCES fixtures(id),
    bookmaker_id  INT NOT NULL REFERENCES bookmakers(id),
    bet_type_id   INT NOT NULL REFERENCES bet_types(id),
    captured_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    source        TEXT NOT NULL DEFAULT 'api-football'
);
CREATE INDEX IF NOT EXISTS idx_odds_snapshots_fixture ON odds_snapshots (fixture_id, captured_at);

CREATE TABLE IF NOT EXISTS odds_values (
    id           BIGSERIAL PRIMARY KEY,
    snapshot_id  BIGINT NOT NULL REFERENCES odds_snapshots(id),
    label        TEXT NOT NULL,
    odd          NUMERIC(7,3) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_odds_values_snapshot ON odds_values (snapshot_id);

-- ==================== saída do motor ====================

-- `feature_snapshots` -> `model_predictions` -> `value_bets` eram o desenho normalizado
-- original pra isso (previsão separada de aposta-contra-odd), mas nunca chegaram a
-- receber 1 linha sequer — `prediction_snapshots` (mais abaixo) resolveu o mesmo
-- problema de outro jeito e é o que o código usa de fato desde então. Auditado em
-- 25/08/2026 (contagem de linhas = 0 nas 3, nenhum código referenciando fora daqui):
-- lixo de schema, removido. Guarda condicional por segurança — só derruba se de fato
-- não acumulou dado em algum ambiente que não foi auditado.
-- EXECUTE (SQL dinâmico) de propósito: o Postgres tenta planejar uma subquery
-- referenciando a tabela mesmo dentro de um IF que nunca chega a executá-la, e
-- explode em "relation does not exist" numa instalação nova, onde essas tabelas
-- nunca existiram. Adiando pra string só resolve a referência em tempo de execução,
-- depois do to_regclass já ter confirmado que a tabela existe.
DO $$
DECLARE row_count INT;
BEGIN
    IF to_regclass('public.value_bets') IS NOT NULL THEN
        EXECUTE 'SELECT count(*) FROM value_bets' INTO row_count;
        IF row_count = 0 THEN
            DROP TABLE value_bets;
        END IF;
    END IF;
END $$;
DO $$
DECLARE row_count INT;
BEGIN
    IF to_regclass('public.model_predictions') IS NOT NULL THEN
        EXECUTE 'SELECT count(*) FROM model_predictions' INTO row_count;
        IF row_count = 0 THEN
            DROP TABLE model_predictions;
        END IF;
    END IF;
END $$;
DO $$
DECLARE row_count INT;
BEGIN
    IF to_regclass('public.feature_snapshots') IS NOT NULL THEN
        EXECUTE 'SELECT count(*) FROM feature_snapshots' INTO row_count;
        IF row_count = 0 THEN
            DROP TABLE feature_snapshots;
        END IF;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS model_versions (
    id             SERIAL PRIMARY KEY,
    market_family  TEXT NOT NULL,
    version        TEXT NOT NULL,
    description    TEXT,
    params         JSONB,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (market_family, version)
);

-- ==================== backtest ====================

CREATE TABLE IF NOT EXISTS backtest_runs (
    id                SERIAL PRIMARY KEY,
    model_version_id  INT REFERENCES model_versions(id),
    date_from         DATE,
    date_to           DATE,
    notes             TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS backtest_bets (
    id                     BIGSERIAL PRIMARY KEY,
    backtest_run_id        INT NOT NULL REFERENCES backtest_runs(id),
    fixture_id             BIGINT REFERENCES fixtures(id),        -- só quando a partida também existe via API-Football
    fd_match_id            BIGINT REFERENCES fd_matches(fd_match_id),  -- fonte real do backtest histórico (football-data.org)
    market_key             TEXT,
    predicted_probability  NUMERIC(6,5),
    actual_outcome         BOOLEAN,   -- o mercado realmente aconteceu? (sem odd, não dá pra falar em ganhou/perdeu em R$)
    odd_used               NUMERIC(7,3),   -- NULL quando não há odd histórica real capturada ANTES do apito inicial
    result                 TEXT,   -- GREEN | RED | PUSH | VOID | UNRESOLVED (ver engine.backtest.metrics) — nunca inferido
    profit_loss            NUMERIC(9,4),
    edge_predicted          NUMERIC(7,5)
);
CREATE INDEX IF NOT EXISTS idx_backtest_bets_run ON backtest_bets (backtest_run_id);

-- colunas da avaliação histórica com odds reais (engine.backtest.historical_eval) —
-- adicionadas depois, então ADD COLUMN IF NOT EXISTS em vez de recriar a tabela.
ALTER TABLE backtest_bets ADD COLUMN IF NOT EXISTS implied_probability NUMERIC(6,5);
ALTER TABLE backtest_bets ADD COLUMN IF NOT EXISTS opportunity_score NUMERIC(7,5);
ALTER TABLE backtest_bets ADD COLUMN IF NOT EXISTS bookmaker_name TEXT;
-- momento da odd usada pra avaliar — SEMPRE a odd em "prediction_time" (1ª captura
-- pré-jogo), nunca a mais recente antes do apito; ver historical_eval.py
ALTER TABLE backtest_bets ADD COLUMN IF NOT EXISTS odds_captured_at TIMESTAMPTZ;
-- preparo pra CLV (seção 12 da auditoria) — só populado quando existir uma 2ª captura
-- pré-jogo distinta da usada na avaliação; nunca estimado/inventado
ALTER TABLE backtest_bets ADD COLUMN IF NOT EXISTS closing_odd NUMERIC(7,3);
ALTER TABLE backtest_bets ADD COLUMN IF NOT EXISTS closing_odds_captured_at TIMESTAMPTZ;
-- trilha de auditoria anti-leakage: sempre TRUE por construção (só entra aqui partida
-- com odd pré-jogo confirmada) — guardado explicitamente pra nunca precisar confiar
-- "de olho" que a regra foi respeita da em alguma consulta futura
ALTER TABLE backtest_bets ADD COLUMN IF NOT EXISTS odds_known_before_kickoff BOOLEAN;
-- distingue COMO essa linha foi gerada — nunca misturar sem essa etiqueta (seção 3 e 16
-- da auditoria): walk-forward de calibração (sem odd) vs avaliação com odd histórica
-- real vs (futuro) snapshot ao vivo genuinamente pré-jogo
ALTER TABLE backtest_bets ADD COLUMN IF NOT EXISTS evaluation_source TEXT;
CREATE INDEX IF NOT EXISTS idx_backtest_bets_source ON backtest_bets (evaluation_source);

CREATE TABLE IF NOT EXISTS backtest_metrics (
    id               BIGSERIAL PRIMARY KEY,
    backtest_run_id  INT NOT NULL REFERENCES backtest_runs(id),
    market_key       TEXT,
    league_id        BIGINT,
    roi              NUMERIC,
    hit_rate         NUMERIC,
    brier_score      NUMERIC,
    yield_pct        NUMERIC,
    n_bets           INT,
    max_drawdown     NUMERIC,
    computed_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ==================== histórico de previsões (append-only) ====================
-- `model_predictions`/`value_bets` acima foram desenhadas pra isso mas nunca chegaram a
-- receber uma linha (nada no código grava nelas). Em vez de forçar a previsão real no
-- desenho normalizado de 2 tabelas (previsão + aposta-contra-odd separadas, exigindo
-- join por odds_snapshot pra reconstruir o estado num instante), esta tabela guarda 1
-- linha "achatada" por oportunidade capturada — exatamente o suficiente pra responder
-- "qual era a previsão do modelo às 10:00, e como a odd mudou até às 18:00" sem join.
CREATE TABLE IF NOT EXISTS prediction_snapshots (
    id                    BIGSERIAL PRIMARY KEY,
    fixture_id            BIGINT REFERENCES fixtures(id),            -- NULL: partida ainda fora da janela da API-Football
    fd_match_id           BIGINT REFERENCES fd_matches(fd_match_id),
    market_key            TEXT NOT NULL,                             -- ex.: 'btts_yes', 'over_2_5', 'corner_over_9_5'
    market_label          TEXT NOT NULL,                             -- rótulo legível no momento da captura
    model_probability      NUMERIC(6,5) NOT NULL,
    bookmaker_name        TEXT,                                      -- NULL quando não há odd capturada ainda
    odd                    NUMERIC(7,3),
    implied_probability    NUMERIC(6,5),
    edge                   NUMERIC(7,5),
    confidence             TEXT NOT NULL,                            -- 'alta' | 'média' | 'baixa'
    data_quality           NUMERIC(5,2) NOT NULL,                    -- 0-100
    opportunity_score       NUMERIC(7,5),                             -- NULL quando não há odd (ver valuebet.calculate_opportunity_score)
    score_version          TEXT NOT NULL DEFAULT 'v1',               -- valuebet.OPPORTUNITY_SCORE_VERSION no momento da captura
    -- MANUAL_VIEW: alguém abriu a análise dessa partida (viés de seleção — não é amostra
    -- representativa). PERIODIC_JOB: captura sistemática (ver services.snapshot_service.
    -- capture_snapshots_for_upcoming_matches). NUNCA tratar as duas como equivalentes
    -- num backtest — ver auditoria "snapshots e backtest".
    source                 TEXT NOT NULL DEFAULT 'MANUAL_VIEW',
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_prediction_snapshots_fixture ON prediction_snapshots (fixture_id, market_key, created_at);
CREATE INDEX IF NOT EXISTS idx_prediction_snapshots_fd_match ON prediction_snapshots (fd_match_id, market_key, created_at);
-- tabela já existia sem esta coluna em ambientes que rodaram o schema antes desta versão
ALTER TABLE prediction_snapshots ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'MANUAL_VIEW';
CREATE INDEX IF NOT EXISTS idx_prediction_snapshots_source ON prediction_snapshots (source);

-- ==================== landing / captação (produto WhatsApp) ====================

CREATE TABLE IF NOT EXISTS whatsapp_leads (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    phone       TEXT NOT NULL,              -- E.164 sem "+", ex.: 5542998119282
    plan        TEXT NOT NULL DEFAULT 'gratis',  -- 'gratis' | 'pro' — plano escolhido no cadastro, não confirma pagamento
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_whatsapp_leads_phone ON whatsapp_leads (phone);
