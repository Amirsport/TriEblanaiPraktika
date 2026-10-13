CREATE TABLE IF NOT EXISTS zones (
    id       INTEGER PRIMARY KEY,
    name     TEXT    NOT NULL,
    position INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS readings (
    id          BIGSERIAL PRIMARY KEY,
    zone_id     INTEGER NOT NULL REFERENCES zones(id),
    temperature DOUBLE PRECISION,
    moisture    DOUBLE PRECISION,
    light       DOUBLE PRECISION,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_readings_zone ON readings(zone_id, id DESC);

CREATE TABLE IF NOT EXISTS zone_devices (
    id         BIGSERIAL PRIMARY KEY,
    zone_id    INTEGER NOT NULL REFERENCES zones(id),
    name       TEXT    NOT NULL,
    enabled    BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(zone_id, name)
);

CREATE TABLE IF NOT EXISTS settings (
    id                    INTEGER PRIMARY KEY CHECK (id = 1),
    mode                  TEXT NOT NULL DEFAULT 'auto',
    moisture_target       DOUBLE PRECISION NOT NULL DEFAULT 55,
    moisture_threshold    DOUBLE PRECISION NOT NULL DEFAULT 35,
    temperature_threshold DOUBLE PRECISION NOT NULL DEFAULT 30,
    light_threshold       DOUBLE PRECISION NOT NULL DEFAULT 8000,
    photoperiod           DOUBLE PRECISION NOT NULL DEFAULT 14,
    watering_duration     DOUBLE PRECISION NOT NULL DEFAULT 10,
    ventilation_duration  DOUBLE PRECISION NOT NULL DEFAULT 30,
    auto_watering         BOOLEAN NOT NULL DEFAULT TRUE,
    auto_ventilation      BOOLEAN NOT NULL DEFAULT TRUE,
    auto_lighting         BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS state (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    tank        DOUBLE PRECISION NOT NULL DEFAULT 78,
    window_open DOUBLE PRECISION NOT NULL DEFAULT 0,
    source      TEXT NOT NULL DEFAULT 'simulator',
    port        TEXT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS logs (
    id      BIGSERIAL PRIMARY KEY,
    ts      TIMESTAMPTZ NOT NULL DEFAULT now(),
    level   TEXT NOT NULL DEFAULT 'info',
    zone_id INTEGER,
    message TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_logs_ts ON logs(id DESC);

CREATE TABLE IF NOT EXISTS users (
    id            BIGSERIAL PRIMARY KEY,
    username      TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_name ON users (username);

CREATE TABLE IF NOT EXISTS auth_sessions (
    token      TEXT PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON auth_sessions(user_id);

CREATE TABLE IF NOT EXISTS user_states (
    user_id    BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    payload    TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS secret_data (
    id         BIGSERIAL PRIMARY KEY,
    name       TEXT NOT NULL,
    value      TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_secret_name ON secret_data (name);

-- Игра Narutodle: набор персонажей и журнал матчей.
CREATE TABLE IF NOT EXISTS narutodle_characters (
    id         BIGSERIAL PRIMARY KEY,
    name       TEXT NOT NULL,
    gender     TEXT NOT NULL DEFAULT '',
    village    TEXT NOT NULL DEFAULT '',
    clan       TEXT NOT NULL DEFAULT '',
    nature     TEXT NOT NULL DEFAULT '[]',
    kekkei     TEXT NOT NULL DEFAULT '',
    jinchuriki TEXT NOT NULL DEFAULT '',
    debut      TEXT NOT NULL DEFAULT '',
    status     TEXT NOT NULL DEFAULT '',
    color      TEXT NOT NULL DEFAULT '',
    image      TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_narutodle_characters_name ON narutodle_characters (name);

-- Ссылок на users нет намеренно: история матчей переживает удаление аккаунта.
CREATE TABLE IF NOT EXISTS narutodle_matches (
    id              BIGSERIAL PRIMARY KEY,
    room            TEXT NOT NULL DEFAULT '',
    round_number    INTEGER NOT NULL DEFAULT 1,
    target          TEXT NOT NULL DEFAULT '',
    player1_id      BIGINT,
    player1_name    TEXT NOT NULL DEFAULT '',
    player2_id      BIGINT,
    player2_name    TEXT NOT NULL DEFAULT '',
    winner_id       BIGINT,
    winner_name     TEXT NOT NULL DEFAULT '',
    loser_name      TEXT NOT NULL DEFAULT '',
    winner_attempts INTEGER NOT NULL DEFAULT 0,
    loser_attempts  INTEGER NOT NULL DEFAULT 0,
    reason          TEXT NOT NULL DEFAULT '',
    played_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_narutodle_matches_played ON narutodle_matches (id DESC);
CREATE INDEX IF NOT EXISTS idx_narutodle_matches_players ON narutodle_matches (player1_id, player2_id);
