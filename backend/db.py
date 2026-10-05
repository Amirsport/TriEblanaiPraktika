# -*- coding: utf-8 -*-
"""Слой доступа к данным (SQLite) для теплицы из 12 участков.

Схема:
    zones        — 12 участков (секций парника);
    readings     — показания датчиков по каждому участку (история);
    zone_devices — исполнители (полив/проветривание/досветка) по участкам;
    settings     — глобальные настройки и пороги (одна строка id=1);
    state        — глобальное состояние: бак, форточка, источник данных;
    logs         — журнал событий.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

ZONE_COUNT = 12
ZONE_NAMES = [f"Участок {i}" for i in range(1, ZONE_COUNT + 1)]
DEVICES = ("watering", "ventilation", "lighting")

DEFAULT_SETTINGS: Dict[str, Any] = {
    "mode": "auto",
    "moisture_target": 55.0,
    "moisture_threshold": 35.0,
    "temperature_threshold": 30.0,
    "light_threshold": 8000.0,
    "photoperiod": 14.0,
    "watering_duration": 10.0,
    "ventilation_duration": 30.0,
    "auto_watering": 1,
    "auto_ventilation": 1,
    "auto_lighting": 0,
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS zones (
    id       INTEGER PRIMARY KEY,
    name     TEXT    NOT NULL,
    position INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS readings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    zone_id     INTEGER NOT NULL REFERENCES zones(id),
    temperature REAL,
    moisture    REAL,
    light       REAL,
    recorded_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_readings_zone ON readings(zone_id, id DESC);

CREATE TABLE IF NOT EXISTS zone_devices (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    zone_id    INTEGER NOT NULL REFERENCES zones(id),
    name       TEXT    NOT NULL,
    enabled    INTEGER NOT NULL DEFAULT 0 CHECK(enabled IN (0,1)),
    updated_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE(zone_id, name)
);

CREATE TABLE IF NOT EXISTS settings (
    id                    INTEGER PRIMARY KEY CHECK(id = 1),
    mode                  TEXT    NOT NULL DEFAULT 'auto',
    moisture_target       REAL    NOT NULL DEFAULT 55,
    moisture_threshold    REAL    NOT NULL DEFAULT 35,
    temperature_threshold REAL    NOT NULL DEFAULT 30,
    light_threshold       REAL    NOT NULL DEFAULT 8000,
    photoperiod           REAL    NOT NULL DEFAULT 14,
    watering_duration     REAL    NOT NULL DEFAULT 10,
    ventilation_duration  REAL    NOT NULL DEFAULT 30,
    auto_watering         INTEGER NOT NULL DEFAULT 1,
    auto_ventilation      INTEGER NOT NULL DEFAULT 1,
    auto_lighting         INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS state (
    id          INTEGER PRIMARY KEY CHECK(id = 1),
    tank        REAL    NOT NULL DEFAULT 78,
    window_open REAL    NOT NULL DEFAULT 0,
    source      TEXT    NOT NULL DEFAULT 'simulator',
    port        TEXT,
    updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS logs (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ts      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    level   TEXT    NOT NULL DEFAULT 'info',
    zone_id INTEGER,
    message TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_logs_ts ON logs(id DESC);
"""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class Database:
    """Тонкая обёртка над SQLite. Соединение открывается на каждую операцию."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(str(self.path), timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    # ------------------------------------------------------------------ setup
    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript(SCHEMA)
            db.executemany(
                "INSERT OR IGNORE INTO zones (id, name, position) VALUES (?, ?, ?)",
                [(i, name, i) for i, name in enumerate(ZONE_NAMES, start=1)],
            )
            cols = ", ".join(DEFAULT_SETTINGS)
            marks = ", ".join("?" for _ in DEFAULT_SETTINGS)
            db.execute(
                f"INSERT OR IGNORE INTO settings (id, {cols}) VALUES (1, {marks})",
                tuple(DEFAULT_SETTINGS.values()),
            )
            db.execute("INSERT OR IGNORE INTO state (id) VALUES (1)")
            db.executemany(
                "INSERT OR IGNORE INTO zone_devices (zone_id, name, enabled) VALUES (?, ?, 0)",
                [(z, d) for z in range(1, ZONE_COUNT + 1) for d in DEVICES],
            )

    # ------------------------------------------------------------------ zones
    def zones(self) -> List[Dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute("SELECT id, name, position FROM zones ORDER BY position").fetchall()
        return [dict(row) for row in rows]

    # --------------------------------------------------------------- readable
    def state(self) -> Dict[str, Any]:
        with self.connect() as db:
            row = db.execute("SELECT tank, window_open, source, port, updated_at FROM state WHERE id = 1").fetchone()
        return dict(row) if row else {"tank": 78, "window_open": 0, "source": "simulator", "port": None, "updated_at": _now()}

    def set_state(self, **fields) -> None:
        if not fields:
            return
        fields["updated_at"] = _now()
        assignments = ", ".join(f"{key} = ?" for key in fields)
        with self.connect() as db:
            db.execute(f"UPDATE state SET {assignments} WHERE id = 1", tuple(fields.values()))

    def settings(self) -> Dict[str, Any]:
        with self.connect() as db:
            row = db.execute("SELECT * FROM settings WHERE id = 1").fetchone()
        data = dict(row) if row else dict(DEFAULT_SETTINGS)
        data.pop("id", None)
        return data

    def update_settings(self, values: Dict[str, Any]) -> Dict[str, Any]:
        allowed = set(DEFAULT_SETTINGS)
        clean = {k: v for k, v in values.items() if k in allowed}
        if clean:
            assignments = ", ".join(f"{key} = ?" for key in clean)
            with self.connect() as db:
                db.execute(f"UPDATE settings SET {assignments} WHERE id = 1", tuple(clean.values()))
        return self.settings()

    # --------------------------------------------------------------- readings
    def add_reading(self, zone_id: int, temperature: Optional[float], moisture: Optional[float], light: Optional[float]) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO readings (zone_id, temperature, moisture, light) VALUES (?, ?, ?, ?)",
                (zone_id, temperature, moisture, light),
            )

    def latest_readings(self) -> Dict[int, Dict[str, Any]]:
        result: Dict[int, Dict[str, Any]] = {}
        with self.connect() as db:
            for zone_id in range(1, ZONE_COUNT + 1):
                row = db.execute(
                    "SELECT temperature, moisture, light, recorded_at FROM readings "
                    "WHERE zone_id = ? ORDER BY id DESC LIMIT 1",
                    (zone_id,),
                ).fetchone()
                result[zone_id] = dict(row) if row else {
                    "temperature": None, "moisture": None, "light": None, "recorded_at": None,
                }
        return result

    def history(self, zone_id: Optional[int] = None, limit: int = 60) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 500))
        with self.connect() as db:
            if zone_id is None:
                rows = db.execute(
                    "SELECT zone_id, temperature, moisture, light, recorded_at FROM readings "
                    "ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT zone_id, temperature, moisture, light, recorded_at FROM readings "
                    "WHERE zone_id = ? ORDER BY id DESC LIMIT ?",
                    (zone_id, limit),
                ).fetchall()
        return [dict(row) for row in reversed(rows)]

    # ---------------------------------------------------------------- devices
    def devices(self) -> Dict[int, Dict[str, bool]]:
        with self.connect() as db:
            rows = db.execute("SELECT zone_id, name, enabled FROM zone_devices").fetchall()
        result: Dict[int, Dict[str, bool]] = {z: {d: False for d in DEVICES} for z in range(1, ZONE_COUNT + 1)}
        for row in rows:
            result[row["zone_id"]][row["name"]] = bool(row["enabled"])
        return result

    def set_device(self, zone_id: int, name: str, enabled: bool) -> None:
        if name not in DEVICES:
            raise ValueError(f"Неизвестный исполнитель: {name}")
        with self.connect() as db:
            db.execute(
                "INSERT INTO zone_devices (zone_id, name, enabled, updated_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(zone_id, name) DO UPDATE SET enabled = excluded.enabled, updated_at = excluded.updated_at",
                (zone_id, name, 1 if enabled else 0, _now()),
            )

    # ------------------------------------------------------------------- logs
    def add_log(self, message: str, level: str = "info", zone_id: Optional[int] = None) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO logs (level, zone_id, message) VALUES (?, ?, ?)",
                (level, zone_id, message),
            )

    def logs(self, limit: int = 100, level: Optional[str] = None) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 500))
        with self.connect() as db:
            if level and level != "all":
                rows = db.execute(
                    "SELECT id, ts, level, zone_id, message FROM logs WHERE level = ? ORDER BY id DESC LIMIT ?",
                    (level, limit),
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT id, ts, level, zone_id, message FROM logs ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [dict(row) for row in rows]

    def clear_logs(self) -> None:
        with self.connect() as db:
            db.execute("DELETE FROM logs")

    def has_recent_log(self, message: str, seconds: int = 120) -> bool:
        with self.connect() as db:
            row = db.execute(
                "SELECT 1 FROM logs WHERE message = ? "
                "AND ts >= strftime('%Y-%m-%dT%H:%M:%fZ','now', ?) LIMIT 1",
                (message, f"-{int(seconds)} seconds"),
            ).fetchone()
        return row is not None

    def purge_history(self, keep_per_zone: int = 500) -> None:
        with self.connect() as db:
            db.execute(
                "DELETE FROM readings WHERE id NOT IN ("
                "  SELECT id FROM (SELECT id, ROW_NUMBER() OVER (PARTITION BY zone_id ORDER BY id DESC) AS rn "
                "  FROM readings) WHERE rn <= ?)",
                (keep_per_zone,),
            )
