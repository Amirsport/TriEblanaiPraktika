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
