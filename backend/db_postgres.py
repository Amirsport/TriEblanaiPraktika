# -*- coding: utf-8 -*-
"""Слой доступа к данным для PostgreSQL (psycopg 3).

Реализует тот же интерфейс, что и backend.db.Database (SQLite), поэтому сервер
и канал Arduino работают с обоими бэкендами без изменений. DDL лежит в
backend/schema_postgres.sql — этот же файл можно выполнить в pgAdmin.
Вместо TEXT, как в SQLite, время хранится в TIMESTAMPTZ, а флаги — в BOOLEAN;
наружу (в JSON и в код автоматики) значения отдаются в том же виде, что и у SQLite:
ISO-8601 строки с 'Z' и булевы флаги.
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import json

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        'Для работы с PostgreSQL установите драйвер: pip install "psycopg[binary]"'
    ) from exc

try:  # запуск как модуль: python -m backend.server
    from .db import DEFAULT_CLIP_LENGTH, DEFAULT_SETTINGS, DEVICES, ZONE_COUNT, ZONE_NAMES
except ImportError:  # запуск как файл: python backend/server.py
    from db import (  # type: ignore
        DEFAULT_CLIP_LENGTH,
        DEFAULT_SETTINGS,
        DEVICES,
        ZONE_COUNT,
        ZONE_NAMES,
    )

SCHEMA_FILE = Path(__file__).resolve().with_name("schema_postgres.sql")

BOOL_SETTINGS = ("auto_watering", "auto_ventilation", "auto_lighting")


def schema_statements() -> List[str]:
    """Операторы DDL из schema_postgres.sql (по одному на элемент)."""
    sql = SCHEMA_FILE.read_text(encoding="utf-8")
    return [chunk.strip() for chunk in sql.split(";") if chunk.strip()]


def to_iso(value: Any) -> Optional[str]:
    """Приводит момент времени к формату SQLite-версии: 2026-10-12T12:34:56.789Z."""
    if value is None:
        return None
    if isinstance(value, datetime):
        moment = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    return str(value)


def parse_iso(value: Any) -> Optional[datetime]:
    """Обратное преобразование (нужно для переноса данных из SQLite)."""
    if value is None or isinstance(value, datetime):
        return value
    text = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _reading(row: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(row)
    data["recorded_at"] = to_iso(data.get("recorded_at"))
    return data


def _user(row: Dict[str, Any]) -> Dict[str, Any]:
    """Строка пользователя с временем создания в формате SQLite-версии."""
    data = dict(row)
    data["created_at"] = to_iso(data.get("created_at"))
    return data


def _entry(row: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(row)
    data["updated_at"] = to_iso(data.get("updated_at"))
    return data


def _nature_list(value: Any) -> List[str]:
    """Стихии лежат в текстовой колонке как JSON-массив — отдаём их списком."""
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    try:
        parsed = json.loads(value or "[]")
    except (TypeError, ValueError):
        return []
    return [str(item) for item in parsed] if isinstance(parsed, list) else []


def _character(row: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(row)
    data["nature"] = _nature_list(data.get("nature"))
    data["updated_at"] = to_iso(data.get("updated_at"))
    return data


def _match(row: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(row)
    for key in ("id", "round_number", "winner_attempts", "loser_attempts"):
        if data.get(key) is not None:
            data[key] = int(data[key])
    data["played_at"] = to_iso(data.get("played_at"))
    return data


def _track(row: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(row)
    for key in ("clip_start", "clip_length"):
        data[key] = float(data.get(key) or 0)
    if data.get("id") is not None:
        data["id"] = int(data["id"])
    data["updated_at"] = to_iso(data.get("updated_at"))
    return data


class PostgresDatabase:
    """Тонкая обёртка над PostgreSQL. Соединение открывается на каждую операцию."""

    def __init__(self, dsn: str):
        self.dsn = dsn

    @contextmanager
    def connect(self):
        connection = psycopg.connect(self.dsn, row_factory=dict_row)
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    # ------------------------------------------------------------------ setup
    def initialize(self) -> None:
        with self.connect() as db:
            for statement in schema_statements():
                db.execute(statement)
            with db.cursor() as cur:
                cur.executemany(
                    "INSERT INTO zones (id, name, position) VALUES (%s, %s, %s) "
                    "ON CONFLICT (id) DO NOTHING",
                    [(i, name, i) for i, name in enumerate(ZONE_NAMES, start=1)],
                )
            cols = ", ".join(DEFAULT_SETTINGS)
            marks = ", ".join(["%s"] * len(DEFAULT_SETTINGS))
            values = tuple(
                bool(value) if key in BOOL_SETTINGS else value
                for key, value in DEFAULT_SETTINGS.items()
            )
            db.execute(
                f"INSERT INTO settings (id, {cols}) VALUES (1, {marks}) "
                "ON CONFLICT (id) DO NOTHING",
                values,
            )
            db.execute("INSERT INTO state (id) VALUES (1) ON CONFLICT (id) DO NOTHING")
            with db.cursor() as cur:
                cur.executemany(
                    "INSERT INTO zone_devices (zone_id, name, enabled) VALUES (%s, %s, FALSE) "
                    "ON CONFLICT (zone_id, name) DO NOTHING",
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
            row = db.execute(
                "SELECT tank, window_open, source, port, updated_at FROM state WHERE id = 1"
            ).fetchone()
        if not row:
            return {"tank": 78, "window_open": 0, "source": "simulator", "port": None,
                    "updated_at": to_iso(datetime.now(timezone.utc))}
        data = dict(row)
        data["tank"] = float(data["tank"])
        data["window_open"] = float(data["window_open"])
        data["updated_at"] = to_iso(data["updated_at"])
        return data

    def set_state(self, **fields) -> None:
        if not fields:
            return
        fields["updated_at"] = datetime.now(timezone.utc)
        assignments = ", ".join(f"{key} = %s" for key in fields)
        with self.connect() as db:
            db.execute(f"UPDATE state SET {assignments} WHERE id = 1", tuple(fields.values()))

    def settings(self) -> Dict[str, Any]:
        with self.connect() as db:
            row = db.execute("SELECT * FROM settings WHERE id = 1").fetchone()
        if not row:
            return dict(DEFAULT_SETTINGS)
        data = dict(row)
        data.pop("id", None)
        for key in BOOL_SETTINGS:
            data[key] = bool(data[key])
        return data

    def update_settings(self, values: Dict[str, Any]) -> Dict[str, Any]:
        allowed = set(DEFAULT_SETTINGS)
        clean = {k: v for k, v in values.items() if k in allowed}
        for key in BOOL_SETTINGS:
            if key in clean:
                clean[key] = bool(clean[key])
        if clean:
            assignments = ", ".join(f"{key} = %s" for key in clean)
            with self.connect() as db:
                db.execute(f"UPDATE settings SET {assignments} WHERE id = 1", tuple(clean.values()))
        return self.settings()

    # --------------------------------------------------------------- readings
    def add_reading(self, zone_id: int, temperature: Optional[float], moisture: Optional[float],
                    light: Optional[float]) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO readings (zone_id, temperature, moisture, light) VALUES (%s, %s, %s, %s)",
                (zone_id, temperature, moisture, light),
            )

    def latest_readings(self) -> Dict[int, Dict[str, Any]]:
        result: Dict[int, Dict[str, Any]] = {}
        with self.connect() as db:
            for zone_id in range(1, ZONE_COUNT + 1):
                row = db.execute(
                    "SELECT temperature, moisture, light, recorded_at FROM readings "
                    "WHERE zone_id = %s ORDER BY id DESC LIMIT 1",
                    (zone_id,),
                ).fetchone()
                result[zone_id] = _reading(row) if row else {
                    "temperature": None, "moisture": None, "light": None, "recorded_at": None,
                }
        return result

    def history(self, zone_id: Optional[int] = None, limit: int = 60) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 500))
        with self.connect() as db:
            if zone_id is None:
                rows = db.execute(
                    "SELECT zone_id, temperature, moisture, light, recorded_at FROM readings "
                    "ORDER BY id DESC LIMIT %s",
                    (limit,),
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT zone_id, temperature, moisture, light, recorded_at FROM readings "
                    "WHERE zone_id = %s ORDER BY id DESC LIMIT %s",
                    (zone_id, limit),
                ).fetchall()
        return [_reading(row) for row in reversed(rows)]

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
                "INSERT INTO zone_devices (zone_id, name, enabled, updated_at) VALUES (%s, %s, %s, %s) "
                "ON CONFLICT (zone_id, name) DO UPDATE SET enabled = EXCLUDED.enabled, "
                "updated_at = EXCLUDED.updated_at",
                (zone_id, name, bool(enabled), datetime.now(timezone.utc)),
            )

    # ------------------------------------------------------------------- logs
    def add_log(self, message: str, level: str = "info", zone_id: Optional[int] = None) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO logs (level, zone_id, message) VALUES (%s, %s, %s)",
                (level, zone_id, message),
            )

    def logs(self, limit: int = 100, level: Optional[str] = None) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 500))
        with self.connect() as db:
            if level and level != "all":
                rows = db.execute(
                    "SELECT id, ts, level, zone_id, message FROM logs WHERE level = %s "
                    "ORDER BY id DESC LIMIT %s",
                    (level, limit),
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT id, ts, level, zone_id, message FROM logs ORDER BY id DESC LIMIT %s",
                    (limit,),
                ).fetchall()
        result = []
        for row in rows:
            data = dict(row)
            data["ts"] = to_iso(data["ts"])
            result.append(data)
        return result

    def clear_logs(self) -> None:
        with self.connect() as db:
            db.execute("DELETE FROM logs")

    def has_recent_log(self, message: str, seconds: int = 120) -> bool:
        with self.connect() as db:
            row = db.execute(
                "SELECT 1 FROM logs WHERE message = %s "
                "AND ts >= now() - make_interval(secs => %s) LIMIT 1",
                (message, float(seconds)),
            ).fetchone()
        return row is not None

    def purge_history(self, keep_per_zone: int = 500) -> None:
        with self.connect() as db:
            db.execute(
                "DELETE FROM readings WHERE id NOT IN ("
                "  SELECT id FROM (SELECT id, ROW_NUMBER() OVER (PARTITION BY zone_id ORDER BY id DESC) AS rn "
                "  FROM readings) AS ranked WHERE rn <= %s)",
                (keep_per_zone,),
            )

    # ------------------------------------------------------------------ users
    def user_count(self) -> int:
        with self.connect() as db:
            return int(db.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"])

    def create_user(self, username: str, password_hash: str, role: str = "user") -> Dict[str, Any]:
        """Создаёт аккаунт. Логин уже приведён к нижнему регистру вызывающим кодом."""
        with self.connect() as db:
            existing = db.execute("SELECT id FROM users WHERE username = %s", (username,)).fetchone()
            if existing:
                raise ValueError(f"Пользователь «{username}» уже существует")
            row = db.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s) "
                "RETURNING id, username, role, created_at",
                (username, password_hash, role),
            ).fetchone()
        return _user(row)

    def list_users(self) -> List[Dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT id, username, role, created_at FROM users ORDER BY id"
            ).fetchall()
        return [_user(row) for row in rows]

    def find_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Строка пользователя вместе с хешем пароля — только для проверки входа."""
        with self.connect() as db:
            row = db.execute(
                "SELECT id, username, password_hash, role, created_at FROM users WHERE username = %s",
                (username,),
            ).fetchone()
        return _user(row) if row else None

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self.connect() as db:
            row = db.execute(
                "SELECT id, username, role, created_at FROM users WHERE id = %s", (user_id,)
            ).fetchone()
        return _user(row) if row else None

    def find_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Строка пользователя вместе с хешем пароля — для проверки смены пароля."""
        with self.connect() as db:
            row = db.execute(
                "SELECT id, username, password_hash, role, created_at FROM users WHERE id = %s",
                (user_id,),
            ).fetchone()
        return _user(row) if row else None

    def set_user_password(self, user_id: int, password_hash: str) -> bool:
        with self.connect() as db:
            cursor = db.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s", (password_hash, user_id)
            )
            return cursor.rowcount > 0

    def delete_user(self, user_id: int) -> bool:
        with self.connect() as db:
            cursor = db.execute("DELETE FROM users WHERE id = %s", (user_id,))
            return cursor.rowcount > 0

    # --------------------------------------------------------------- sessions
    def create_session(self, user_id: int, token: str, expires_at: datetime) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO auth_sessions (token, user_id, expires_at) VALUES (%s, %s, %s)",
                (token, user_id, expires_at),
            )

    def session_user(self, token: str) -> Optional[Dict[str, Any]]:
        """Пользователь по действующему (не истёкшему) токену входа."""
        if not token:
            return None
        with self.connect() as db:
            row = db.execute(
                "SELECT u.id, u.username, u.role, u.created_at FROM auth_sessions s "
                "JOIN users u ON u.id = s.user_id "
                "WHERE s.token = %s AND s.expires_at > now()",
                (token,),
            ).fetchone()
        return _user(row) if row else None

    def delete_session(self, token: str) -> None:
        if not token:
            return
        with self.connect() as db:
            db.execute("DELETE FROM auth_sessions WHERE token = %s", (token,))

    def purge_sessions(self) -> None:
        """Удаляет истёкшие токены: вызывается при старте сервера."""
        with self.connect() as db:
            db.execute("DELETE FROM auth_sessions WHERE expires_at <= now()")

    # ------------------------------------------------------------ user states
    def user_state(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Сохранённое состояние панели пользователя (или None, если не сохранено)."""
        with self.connect() as db:
            row = db.execute(
                "SELECT payload, updated_at FROM user_states WHERE user_id = %s", (user_id,)
            ).fetchone()
        if not row:
            return None
        try:
            payload = json.loads(row["payload"])
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    def save_user_state(self, user_id: int, payload: Dict[str, Any]) -> None:
        text = json.dumps(payload, ensure_ascii=False)
        with self.connect() as db:
            db.execute(
                "INSERT INTO user_states (user_id, payload, updated_at) VALUES (%s, %s, %s) "
                "ON CONFLICT (user_id) DO UPDATE SET payload = EXCLUDED.payload, "
                "updated_at = EXCLUDED.updated_at",
                (user_id, text, datetime.now(timezone.utc)),
            )

    # ----------------------------------------------------------- secret data
    def secret_data(self) -> List[Dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT id, name, value, updated_at FROM secret_data ORDER BY name"
            ).fetchall()
        return [_entry(row) for row in rows]

    def set_secret_data(self, name: str, value: str) -> Dict[str, Any]:
        with self.connect() as db:
            existing = db.execute(
                "SELECT id FROM secret_data WHERE name = %s", (name,)
            ).fetchone()
            if existing:
                db.execute(
                    "UPDATE secret_data SET value = %s, updated_at = %s WHERE id = %s",
                    (value, datetime.now(timezone.utc), existing["id"]),
                )
                entry_id = existing["id"]
            else:
                entry_id = db.execute(
                    "INSERT INTO secret_data (name, value) VALUES (%s, %s) RETURNING id", (name, value)
                ).fetchone()["id"]
            row = db.execute(
                "SELECT id, name, value, updated_at FROM secret_data WHERE id = %s", (entry_id,)
            ).fetchone()
        return _entry(row)

    def delete_secret_data(self, entry_id: int) -> bool:
        with self.connect() as db:
            cursor = db.execute("DELETE FROM secret_data WHERE id = %s", (entry_id,))
            return cursor.rowcount > 0

    # -------------------------------------------------------------- narutodle
    def narutodle_character_count(self) -> int:
        with self.connect() as db:
            row = db.execute("SELECT COUNT(*) AS n FROM narutodle_characters").fetchone()
        return int(row["n"])

    def narutodle_characters(self) -> List[Dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute("SELECT * FROM narutodle_characters ORDER BY name").fetchall()
        return [_character(row) for row in rows]

    def narutodle_save_characters(self, rows: Iterable[Dict[str, Any]]) -> int:
        """Добавляет персонажей и обновляет свойства уже известных.

        Пустые color и image в новых данных не затирают то, что уже стоит
        в базе: свои картинки и цвета должны переживать повторное наполнение.
        """
        saved = 0
        with self.connect() as db:
            for row in rows:
                db.execute(
                    "INSERT INTO narutodle_characters (name, gender, village, clan, nature, "
                    "kekkei, jinchuriki, debut, status, color, image, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT (name) DO UPDATE SET "
                    "gender = EXCLUDED.gender, village = EXCLUDED.village, clan = EXCLUDED.clan, "
                    "nature = EXCLUDED.nature, kekkei = EXCLUDED.kekkei, "
                    "jinchuriki = EXCLUDED.jinchuriki, debut = EXCLUDED.debut, "
                    "status = EXCLUDED.status, "
                    "color = CASE WHEN EXCLUDED.color <> '' THEN EXCLUDED.color "
                    "ELSE narutodle_characters.color END, "
                    "image = CASE WHEN EXCLUDED.image <> '' THEN EXCLUDED.image "
                    "ELSE narutodle_characters.image END, "
                    "updated_at = EXCLUDED.updated_at",
                    (
                        str(row.get("name") or ""),
                        str(row.get("gender") or ""),
                        str(row.get("village") or ""),
                        str(row.get("clan") or ""),
                        json.dumps(_nature_list(row.get("nature")), ensure_ascii=False),
                        str(row.get("kekkei") or ""),
                        str(row.get("jinchuriki") or ""),
                        str(row.get("debut") or ""),
                        str(row.get("status") or ""),
                        str(row.get("color") or ""),
                        str(row.get("image") or ""),
                        datetime.now(timezone.utc),
                    ),
                )
                saved += 1
        return saved

    def narutodle_set_image(self, name: str, image: str) -> bool:
        """Привязывает картинку к персонажу (пустая строка — снова аватар)."""
        with self.connect() as db:
            cursor = db.execute(
                "UPDATE narutodle_characters SET image = %s, updated_at = %s WHERE name = %s",
                (image, datetime.now(timezone.utc), name),
            )
            return cursor.rowcount > 0

    def narutodle_add_match(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Пишет матч в журнал и возвращает строку с присвоенным идентификатором."""
        with self.connect() as db:
            row = db.execute(
                "INSERT INTO narutodle_matches (room, round_number, target, player1_id, "
                "player1_name, player2_id, player2_name, winner_id, winner_name, loser_name, "
                "winner_attempts, loser_attempts, reason, played_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *",
                (
                    str(record.get("room") or ""),
                    int(record.get("round_number") or 1),
                    str(record.get("target") or ""),
                    record.get("player1_id"),
                    str(record.get("player1_name") or ""),
                    record.get("player2_id"),
                    str(record.get("player2_name") or ""),
                    record.get("winner_id"),
                    str(record.get("winner_name") or ""),
                    str(record.get("loser_name") or ""),
                    int(record.get("winner_attempts") or 0),
                    int(record.get("loser_attempts") or 0),
                    str(record.get("reason") or ""),
                    datetime.now(timezone.utc),
                ),
            ).fetchone()
        return _match(row)

    def narutodle_matches(self, user_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Журнал матчей: с участием игрока или все подряд (для администратора)."""
        size = max(1, min(int(limit), 500))
        with self.connect() as db:
            if user_id is None:
                rows = db.execute(
                    "SELECT * FROM narutodle_matches ORDER BY id DESC LIMIT %s", (size,)
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT * FROM narutodle_matches WHERE player1_id = %s OR player2_id = %s "
                    "ORDER BY id DESC LIMIT %s", (int(user_id), int(user_id), size)
                ).fetchall()
        return [_match(row) for row in rows]

    def narutodle_match_count(self) -> int:
        with self.connect() as db:
            row = db.execute("SELECT COUNT(*) AS n FROM narutodle_matches").fetchone()
        return int(row["n"])

    # -------------------------------------------------------------- songless
    def songless_track_count(self) -> int:
        with self.connect() as db:
            row = db.execute("SELECT COUNT(*) AS n FROM songless_tracks").fetchone()
        return int(row["n"])

    def songless_tracks(self) -> List[Dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute("SELECT * FROM songless_tracks ORDER BY anime").fetchall()
        return [_track(row) for row in rows]

    def songless_save_tracks(self, rows: Iterable[Dict[str, Any]]) -> int:
        """Добавляет треки и обновляет справочные сведения уже известных.

        Запись (audio), начало и длина фрагмента при повторном наполнении
        не трогаются: это то, что владелец сайта настраивает под свою версию
        трека, и затирать это нельзя.
        """
        saved = 0
        with self.connect() as db:
            for row in rows:
                db.execute(
                    "INSERT INTO songless_tracks (anime, song, artist, year, audio, "
                    "clip_start, clip_length, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT (anime) DO UPDATE SET "
                    "song = EXCLUDED.song, artist = EXCLUDED.artist, year = EXCLUDED.year, "
                    "updated_at = EXCLUDED.updated_at",
                    (
                        str(row.get("anime") or ""),
                        str(row.get("song") or ""),
                        str(row.get("artist") or ""),
                        str(row.get("year") or ""),
                        str(row.get("audio") or ""),
                        float(row.get("clip_start") or 0),
                        float(row.get("clip_length") or DEFAULT_CLIP_LENGTH),
                        datetime.now(timezone.utc),
                    ),
                )
                saved += 1
        return saved

    def songless_set_audio(self, anime: str, audio: str,
                           clip_start: Optional[float] = None,
                           clip_length: Optional[float] = None) -> bool:
        """Привязывает запись к треку; пустая строка — снова «без записи»."""
        fields = ["audio = %s", "updated_at = %s"]
        values: List[Any] = [audio, datetime.now(timezone.utc)]
        if clip_start is not None:
            fields.append("clip_start = %s")
            values.append(float(clip_start))
        if clip_length is not None:
            fields.append("clip_length = %s")
            values.append(float(clip_length))
        values.append(anime)
        with self.connect() as db:
            cursor = db.execute(
                "UPDATE songless_tracks SET " + ", ".join(fields) + " WHERE anime = %s",
                tuple(values),
            )
            return cursor.rowcount > 0

    def songless_set_clip(self, anime: str,
                          clip_start: Optional[float] = None,
                          clip_length: Optional[float] = None) -> bool:
        """Меняет место и длину фрагмента, не трогая саму запись."""
        fields = ["updated_at = %s"]
        values: List[Any] = [datetime.now(timezone.utc)]
        if clip_start is not None:
            fields.append("clip_start = %s")
            values.append(float(clip_start))
        if clip_length is not None:
            fields.append("clip_length = %s")
            values.append(float(clip_length))
        values.append(anime)
        with self.connect() as db:
            cursor = db.execute(
                "UPDATE songless_tracks SET " + ", ".join(fields) + " WHERE anime = %s",
                tuple(values),
            )
            return cursor.rowcount > 0

    def songless_delete_track(self, anime: str) -> bool:
        """Убирает трек из набора (например, чтобы удалить лишнюю строку)."""
        with self.connect() as db:
            cursor = db.execute("DELETE FROM songless_tracks WHERE anime = %s", (anime,))
            return cursor.rowcount > 0


# Правила переноса данных из SQLite (используются backend/migrate_to_postgres.py):
# таблица, колонки и ключ, по которому разрешаются конфликты повторного запуска.
TRANSFERS: Tuple[Tuple[str, Tuple[str, ...], Tuple[str, ...]], ...] = (
    ("zones", ("id", "name", "position"), ("id",)),
    ("readings", ("id", "zone_id", "temperature", "moisture", "light", "recorded_at"), ("id",)),
    ("zone_devices", ("zone_id", "name", "enabled", "updated_at"), ("zone_id", "name")),
    ("settings", ("id", "mode", "moisture_target", "moisture_threshold", "temperature_threshold",
                  "light_threshold", "photoperiod", "watering_duration", "ventilation_duration",
                  "auto_watering", "auto_ventilation", "auto_lighting"), ("id",)),
    ("state", ("id", "tank", "window_open", "source", "port", "updated_at"), ("id",)),
    ("logs", ("id", "ts", "level", "zone_id", "message"), ("id",)),
    ("users", ("id", "username", "password_hash", "role", "created_at"), ("id",)),
    ("auth_sessions", ("token", "user_id", "expires_at", "created_at"), ("token",)),
    ("user_states", ("user_id", "payload", "updated_at"), ("user_id",)),
    ("secret_data", ("id", "name", "value", "updated_at"), ("id",)),
    ("narutodle_characters", ("id", "name", "gender", "village", "clan", "nature", "kekkei",
                              "jinchuriki", "debut", "status", "color", "image", "updated_at"),
     ("id",)),
    ("narutodle_matches", ("id", "room", "round_number", "target", "player1_id", "player1_name",
                           "player2_id", "player2_name", "winner_id", "winner_name", "loser_name",
                           "winner_attempts", "loser_attempts", "reason", "played_at"), ("id",)),
    ("songless_tracks", ("id", "anime", "song", "artist", "year", "audio", "clip_start",
                         "clip_length", "updated_at"), ("id",)),
)

# Колонки, значения которых при переносе нужно привести к типу PostgreSQL.
BOOL_COLUMNS = ("enabled", "auto_watering", "auto_ventilation", "auto_lighting")
TIME_COLUMNS = ("recorded_at", "ts", "updated_at", "created_at", "expires_at", "played_at")
