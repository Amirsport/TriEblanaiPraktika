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
    from .db import (
        DEFAULT_CLIP_LENGTH,
        DEFAULT_SETTINGS,
        DEVICES,
        LATE_COLUMNS,
        LATE_INDEXES,
        ZONE_COUNT,
        ZONE_NAMES,
        narutodle_secret_metrics,
        songless_metrics_from_runs,
    )
except ImportError:  # запуск как файл: python backend/server.py
    from db import (  # type: ignore
        DEFAULT_CLIP_LENGTH,
        DEFAULT_SETTINGS,
        DEVICES,
        LATE_COLUMNS,
        LATE_INDEXES,
        ZONE_COUNT,
        ZONE_NAMES,
        narutodle_secret_metrics,
        songless_metrics_from_runs,
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
    # Доски в JSON нужны только достижениям: в журнале матчей они лишние.
    data.pop("boards_json", None)
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


def _players(value: Any) -> List[Dict[str, Any]]:
    """Игроки пака «87-0» лежат JSON-строкой: ник, роль и три оценки."""
    if isinstance(value, (list, tuple)):
        source = value
    else:
        try:
            source = json.loads(value or "[]")
        except (TypeError, ValueError):
            source = []
    players: List[Dict[str, Any]] = []
    for item in source if isinstance(source, list) else []:
        if not isinstance(item, dict):
            continue
        players.append({
            "name": str(item.get("name") or ""),
            "role": str(item.get("role") or ""),
            "aim": float(item.get("aim") or 0),
            "clutch": float(item.get("clutch") or 0),
            "impact": float(item.get("impact") or 0),
        })
    return players


def _pack_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Пак «87-0» из базы: карты и игроки разбираются из JSON."""
    data = dict(row)
    data["year"] = int(data.get("year") or 0)
    data["major"] = bool(data.get("major"))
    data["maps"] = _nature_list(data.get("maps"))
    data["players"] = _players(data.get("players"))
    data["updated_at"] = to_iso(data.get("updated_at"))
    return data


def _run_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Строка журнала прогонов «87-0»."""
    data = dict(row)
    data["champion"] = bool(data.get("champion"))
    data["user_id"] = int(data["user_id"]) if data.get("user_id") is not None else None
    data["id"] = int(data["id"])
    for key in ("wins", "losses"):
        data[key] = int(data.get(key) or 0)
    data["rating"] = float(data.get("rating") or 0)
    data["played_at"] = to_iso(data.get("played_at"))
    return data


def _dotadraft_player(row: Dict[str, Any]) -> Dict[str, Any]:
    """Игрок из пула «322-0»: ник, стоимость и своя позиция (0 — неизвестна)."""
    data = dict(row)
    data["id"] = str(data.get("id") or "")
    data["nickname"] = str(data.get("nickname") or "")
    data["cost"] = int(data.get("cost") or 0)
    data["position"] = int(data.get("position") or 0)
    return data


def _dotadraft_player_hero(row: Dict[str, Any]) -> Dict[str, Any]:
    """Оценка героя под игрока: пара «игрок + герой» и её оценка силы."""
    data = dict(row)
    data["player_id"] = str(data.get("player_id") or "")
    data["hero_id"] = str(data.get("hero_id") or "")
    data["rating"] = int(data.get("rating") or 0)
    return data


def _dotadraft_hero(row: Dict[str, Any]) -> Dict[str, Any]:
    """Герой из пула «322-0»: имя, позиция (1–5) и игровая оценка."""
    data = dict(row)
    data["id"] = str(data.get("id") or "")
    data["name"] = str(data.get("name") or "")
    data["name_en"] = str(data.get("name_en") or "")
    data["position"] = int(data.get("position") or 1)
    data["rating"] = int(data.get("rating") or 0)
    return data


def _songguess_track(row: Dict[str, Any]) -> Dict[str, Any]:
    """Песня «Угадай песню за 10 секунд»: тема, название, исполнитель, запись."""
    data = dict(row)
    data["id"] = str(data.get("id") or "")
    data["category"] = str(data.get("category") or "")
    data["title"] = str(data.get("title") or "")
    data["artist"] = str(data.get("artist") or "")
    data["year"] = str(data.get("year") or "")
    data["source"] = str(data.get("source") or "")
    data["audio"] = str(data.get("audio") or "")
    data["clip_start"] = float(data.get("clip_start") or 0)
    data["clip_length"] = float(data.get("clip_length") or 0)
    return data


def _songguess_run(row: Dict[str, Any]) -> Dict[str, Any]:
    """Строка журнала заходов «Угадай песню за 10 секунд»."""
    data = dict(row)
    data["id"] = int(data.get("id") or 0)
    data["user_id"] = int(data["user_id"]) if data.get("user_id") is not None else None
    data["category"] = str(data.get("category") or "")
    data["difficulty"] = str(data.get("difficulty") or "")
    data["seconds"] = float(data.get("seconds") or 0)
    for key in ("rounds", "correct", "score"):
        data[key] = int(data.get(key) or 0)
    data["fastest"] = float(data["fastest"]) if data.get("fastest") is not None else None
    data["detail"] = str(data.get("detail") or "")
    data["played_at"] = to_iso(data.get("played_at"))
    return data


def _rap_track(row: Dict[str, Any]) -> Dict[str, Any]:
    """Трек «Рэп-хронологии»: идентификатор, исполнитель, название, год."""
    data = dict(row)
    data["id"] = str(data.get("id") or "")
    data["artist"] = str(data.get("artist") or "")
    data["title"] = str(data.get("title") or "")
    data["year"] = int(data.get("year") or 0)
    return data


def _rap_match(row: Dict[str, Any]) -> Dict[str, Any]:
    """Строка журнала партий «Рэп-хронологии»."""
    data = dict(row)
    data["id"] = int(data.get("id") or 0)
    data["rounds"] = int(data.get("rounds") or 0)
    for key in ("player1_score", "player2_score"):
        data[key] = int(data.get(key) or 0)
    for key in ("player1_id", "player2_id", "winner_id"):
        data[key] = int(data[key]) if data.get(key) is not None else None
    data["played_at"] = to_iso(data.get("played_at"))
    return data


def _command(row: Dict[str, Any]) -> Dict[str, Any]:
    """Строка очереди команд в том виде, в каком её ждёт домашний агент."""
    data = dict(row)
    data["id"] = int(data["id"])
    data["zone_id"] = int(data["zone_id"])
    data["on"] = bool(data["on_state"])
    data["seconds"] = float(data["seconds"]) if data.get("seconds") is not None else None
    for key in ("created_at", "delivered_at", "applied_at"):
        data[key] = to_iso(data.get(key))
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
            self._migrate(db)
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

    @staticmethod
    def _migrate(db: Any) -> None:
        """Догоняет схему на базах, созданных прошлыми версиями сервера."""
        for table, column, definition in LATE_COLUMNS:
            db.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {definition}")
        for statement in LATE_INDEXES:
            db.execute(statement)
        # Один сериал может дать несколько опенингов: ключ трека уникален,
        # а аниме — обычный индекс.
        db.execute("UPDATE songless_tracks SET track_key = anime WHERE track_key = ''")
        db.execute("DROP INDEX IF EXISTS idx_songless_tracks_anime")
        db.execute("CREATE INDEX IF NOT EXISTS idx_songless_tracks_anime "
                   "ON songless_tracks (anime)")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_songless_tracks_key "
                   "ON songless_tracks (track_key)")

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

    # ------------------------------------------------- команды устройству
    def device_command_add(self, zone_id: int, device: str, on: bool,
                           seconds: Optional[float] = None) -> int:
        """Кладёт команду в очередь: её заберёт домашний агент у платы."""
        with self.connect() as db:
            row = db.execute(
                "INSERT INTO device_commands (zone_id, device, on_state, seconds) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                (int(zone_id), device, bool(on), seconds),
            ).fetchone()
            return int(row["id"]) if row else 0

    def device_commands_pending(self, limit: int = 50,
                                max_age: Optional[float] = None) -> List[Dict[str, Any]]:
        """Отдаёт неподтверждённые команды и помечает их выданными агенту.

        Команды старше max_age секунд закрываются как просроченные: полив,
        который включился бы через час после нажатия кнопки, опаснее пропуска.
        """
        with self.connect() as db:
            if max_age:
                db.execute(
                    "UPDATE device_commands SET applied_at = now(), error = %s "
                    "WHERE applied_at IS NULL AND created_at < now() - make_interval(secs => %s)",
                    ("просрочена: агент не был на связи", float(max_age)),
                )
            db.execute(
                "UPDATE device_commands SET delivered_at = now() "
                "WHERE applied_at IS NULL AND delivered_at IS NULL"
            )
            rows = db.execute(
                "SELECT id, zone_id, device, on_state, seconds, created_at, delivered_at, applied_at, error "
                "FROM device_commands WHERE applied_at IS NULL ORDER BY id LIMIT %s",
                (int(limit),),
            ).fetchall()
        return [_command(row) for row in rows]

    def device_commands_ack(self, applied: Iterable[int],
                            errors: Optional[Dict[Any, str]] = None) -> int:
        """Отмечает команды выполненными: агент применил их к плате либо сообщил об ошибке."""
        problems = {int(key): str(value) for key, value in (errors or {}).items()}
        ids = [int(item) for item in applied] + list(problems)
        if not ids:
            return 0
        now = datetime.now(timezone.utc)
        done = 0
        with self.connect() as db:
            for command_id in ids:
                cursor = db.execute(
                    "UPDATE device_commands SET applied_at = %s, error = %s "
                    "WHERE id = %s AND applied_at IS NULL",
                    (now, problems.get(command_id, ""), command_id),
                )
                done += cursor.rowcount
        return done

    def device_commands_prune(self, keep_hours: float = 24.0) -> int:
        """Убирает старые выполненные команды, чтобы очередь не росла."""
        with self.connect() as db:
            cursor = db.execute(
                "DELETE FROM device_commands WHERE applied_at IS NOT NULL "
                "AND applied_at < now() - make_interval(secs => %s)",
                (float(keep_hours) * 3600.0,),
            )
            return cursor.rowcount

    def device_commands(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Последние команды для журнала и диагностики связи с агентом."""
        with self.connect() as db:
            rows = db.execute(
                "SELECT id, zone_id, device, on_state, seconds, created_at, delivered_at, applied_at, error "
                "FROM device_commands ORDER BY id DESC LIMIT %s",
                (int(limit),),
            ).fetchall()
        return [_command(row) for row in rows]

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

    # -------------------------------------------------------------- profiles
    def user_profile(self, user_id: int) -> Dict[str, Any]:
        """Поля профиля игрока; пустые значения, если профиль не заполняли."""
        with self.connect() as db:
            row = db.execute(
                "SELECT display_name, bio, favorite_game, accent, frame, card, status, "
                "CASE WHEN avatar_mime <> '' THEN 1 ELSE 0 END AS has_avatar, updated_at "
                "FROM user_profiles WHERE user_id = %s",
                (int(user_id),),
            ).fetchone()
        if not row:
            return {"display_name": "", "bio": "", "favorite_game": "", "accent": "",
                    "frame": "", "card": "", "status": "", "has_avatar": 0, "updated_at": None}
        data = dict(row)
        data["has_avatar"] = int(data.get("has_avatar") or 0)
        data["updated_at"] = to_iso(data.get("updated_at"))
        return data

    PROFILE_FIELDS = ("display_name", "bio", "favorite_game", "accent", "frame", "card", "status")

    def save_user_profile(self, user_id: int, values: Dict[str, Any]) -> Dict[str, Any]:
        fields = {name: str(values.get(name) or "") for name in self.PROFILE_FIELDS}
        with self.connect() as db:
            db.execute(
                "INSERT INTO user_profiles (user_id, display_name, bio, favorite_game, accent, "
                "frame, card, status, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (user_id) DO UPDATE SET display_name = EXCLUDED.display_name, "
                "bio = EXCLUDED.bio, favorite_game = EXCLUDED.favorite_game, "
                "accent = EXCLUDED.accent, frame = EXCLUDED.frame, card = EXCLUDED.card, "
                "status = EXCLUDED.status, updated_at = EXCLUDED.updated_at",
                (int(user_id), fields["display_name"], fields["bio"],
                 fields["favorite_game"], fields["accent"], fields["frame"], fields["card"],
                 fields["status"], datetime.now(timezone.utc)),
            )
        return self.user_profile(user_id)

    def set_user_avatar(self, user_id: int, mime: str, data: bytes) -> None:
        """Сохраняет картинку профиля (BYTEA в той же строке профиля)."""
        with self.connect() as db:
            db.execute(
                "INSERT INTO user_profiles (user_id, avatar_mime, avatar_data, updated_at) "
                "VALUES (%s, %s, %s, %s) "
                "ON CONFLICT (user_id) DO UPDATE SET avatar_mime = EXCLUDED.avatar_mime, "
                "avatar_data = EXCLUDED.avatar_data, updated_at = EXCLUDED.updated_at",
                (int(user_id), str(mime), psycopg.Binary(bytes(data)),
                 datetime.now(timezone.utc)),
            )

    def clear_user_avatar(self, user_id: int) -> bool:
        with self.connect() as db:
            cursor = db.execute(
                "UPDATE user_profiles SET avatar_mime = '', avatar_data = NULL, updated_at = %s "
                "WHERE user_id = %s AND avatar_mime <> ''",
                (datetime.now(timezone.utc), int(user_id)),
            )
            return cursor.rowcount > 0

    def user_avatar(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Картинка профиля: {"mime": ..., "data": bytes} или None."""
        with self.connect() as db:
            row = db.execute(
                "SELECT avatar_mime AS mime, avatar_data AS data FROM user_profiles "
                "WHERE user_id = %s AND avatar_mime <> ''",
                (int(user_id),),
            ).fetchone()
        if not row or not row["data"]:
            return None
        return {"mime": str(row["mime"] or "image/png"), "data": bytes(row["data"])}

    def profile_stats(self, user_id: int) -> Dict[str, int]:
        """Счётчики для профиля: сколько партий и прогонов записано за игроком."""
        uid = int(user_id)
        with self.connect() as db:
            row = db.execute(
                "SELECT "
                "(SELECT COUNT(*) FROM narutodle_matches WHERE player_ids LIKE %s "
                " OR player1_id = %s OR player2_id = %s) AS narutodle, "
                "(SELECT COUNT(*) FROM csdraft_runs WHERE user_id = %s) AS drafts, "
                "(SELECT COUNT(*) FROM songguess_runs WHERE user_id = %s) AS songguess, "
                "(SELECT COUNT(*) FROM raporder_matches WHERE player1_id = %s "
                " OR player2_id = %s) AS raporder",
                (f"%,{uid},%", uid, uid, uid, uid, uid, uid),
            ).fetchone()
        data = {key: int(row[key] or 0) for key in ("narutodle", "drafts", "songguess", "raporder")}
        data["total"] = sum(data.values())
        return data

    # ------------------------------------------------------------ достижения
    def game_metrics(self, user_id: int) -> Dict[str, int]:
        """Счётчики для достижений: партии, победы и очки по всем играм."""
        uid = int(user_id)
        with self.connect() as db:
            row = db.execute(
                "SELECT "
                "(SELECT COUNT(*) FROM narutodle_matches WHERE player_ids LIKE %s "
                " OR player1_id = %s OR player2_id = %s) AS narutodle_played, "
                "(SELECT COUNT(*) FROM narutodle_matches WHERE winner_id = %s) AS narutodle_wins, "
                "(SELECT COUNT(*) FROM songguess_runs WHERE user_id = %s) AS songguess_runs, "
                "(SELECT COALESCE(MAX(score), 0) FROM songguess_runs WHERE user_id = %s) AS songguess_best, "
                "(SELECT COALESCE(SUM(correct), 0) FROM songguess_runs WHERE user_id = %s) AS songguess_correct, "
                "(SELECT COUNT(*) FROM csdraft_runs WHERE user_id = %s) AS draft_runs, "
                "(SELECT COUNT(*) FROM csdraft_runs WHERE user_id = %s AND champion) AS draft_champions, "
                "(SELECT COUNT(*) FROM raporder_matches WHERE player1_id = %s "
                " OR player2_id = %s) AS raporder_played, "
                "(SELECT COUNT(*) FROM raporder_matches WHERE winner_id = %s) AS raporder_wins",
                (f"%,{uid},%",) + (uid,) * 11,
            ).fetchone()
            # Отдельный запрос: режимы, быстрые победы, коллекция персонажей.
            detail = db.execute(
                "SELECT "
                "(SELECT COUNT(*) FROM narutodle_matches WHERE mode = 'duel' "
                " AND (player_ids LIKE %s OR player1_id = %s OR player2_id = %s)) AS duel, "
                "(SELECT COUNT(*) FROM narutodle_matches WHERE mode = 'race' "
                " AND (player_ids LIKE %s OR player1_id = %s OR player2_id = %s)) AS race, "
                "(SELECT COUNT(*) FROM narutodle_matches WHERE mode = 'teams' "
                " AND (player_ids LIKE %s OR player1_id = %s OR player2_id = %s)) AS teams, "
                "(SELECT COUNT(*) FROM narutodle_matches WHERE winner_id = %s "
                " AND winner_attempts > 0 AND winner_attempts <= 3) AS fast_wins, "
                "(SELECT COUNT(DISTINCT target) FROM narutodle_matches "
                " WHERE winner_id = %s AND target <> '') AS guessed, "
                "(SELECT COUNT(*) FROM narutodle_matches WHERE winner_id IS NOT NULL "
                " AND winner_id <> %s AND (player_ids LIKE %s OR player1_id = %s "
                " OR player2_id = %s)) AS losses",
                (f"%,{uid},%", uid, uid) * 3 + (uid, uid, uid, f"%,{uid},%", uid, uid),
            ).fetchone()
            # Скрытые титулы: доски разбираем в Python — так одинаково работает
            # и SQLite, и PostgreSQL без JSON-функций.
            secret_rows = db.execute(
                "SELECT mode, winner_team, boards_json FROM narutodle_matches "
                "WHERE boards_json <> '' AND player_ids LIKE %s",
                (f"%,{uid},%",),
            ).fetchall()
        keys = ("narutodle_played", "narutodle_wins", "songguess_runs", "songguess_best",
                "songguess_correct", "draft_runs", "draft_champions", "raporder_played",
                "raporder_wins")
        data = {key: int(row[key] or 0) for key in keys}
        touched = (data["narutodle_played"], data["songguess_runs"],
                   data["draft_runs"], data["raporder_played"])
        data["games_touched"] = sum(1 for value in touched if value)
        data["total_games"] = sum(touched)
        data["narutodle_duel"] = int(detail["duel"] or 0)
        data["narutodle_race"] = int(detail["race"] or 0)
        data["narutodle_teams"] = int(detail["teams"] or 0)
        data["narutodle_fast_wins"] = int(detail["fast_wins"] or 0)
        data["narutodle_chars"] = int(detail["guessed"] or 0)
        data["narutodle_losses"] = int(detail["losses"] or 0)
        data.update(narutodle_secret_metrics(secret_rows, uid))
        data.update(songless_metrics_from_runs(self.songless_metric_rows(uid)))
        return data

    def achievements_unlocked(self, user_id: int) -> Dict[str, Any]:
        """Выданные достижения: {"идентификатор": момент выдачи}."""
        with self.connect() as db:
            rows = db.execute(
                "SELECT achievement_id, unlocked_at FROM user_achievements WHERE user_id = %s",
                (int(user_id),),
            ).fetchall()
        return {str(row["achievement_id"]): to_iso(row["unlocked_at"]) for row in rows}

    def achievement_unlock(self, user_id: int, achievement_id: str) -> bool:
        """Выдаёт достижение один раз; True, если оно выдано именно сейчас."""
        with self.connect() as db:
            cursor = db.execute(
                "INSERT INTO user_achievements (user_id, achievement_id, unlocked_at) "
                "VALUES (%s, %s, %s) ON CONFLICT (user_id, achievement_id) DO NOTHING",
                (int(user_id), str(achievement_id), datetime.now(timezone.utc)),
            )
            return cursor.rowcount > 0

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

    def narutodle_portrait(self, character_id: int) -> str:
        """Картинка персонажа как она лежит в базе (строка data:image/... или путь)."""
        with self.connect() as db:
            row = db.execute("SELECT image FROM narutodle_characters WHERE id = %s",
                             (int(character_id),)).fetchone()
        return str((row or {}).get("image") or "")

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
                    "kekkei, jinchuriki, debut, color, image, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT (name) DO UPDATE SET "
                    "gender = EXCLUDED.gender, village = EXCLUDED.village, clan = EXCLUDED.clan, "
                    "nature = EXCLUDED.nature, kekkei = EXCLUDED.kekkei, "
                    "jinchuriki = EXCLUDED.jinchuriki, debut = EXCLUDED.debut, "
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
        """Пишет партию в журнал и возвращает строку с присвоенным идентификатором."""
        player_ids = [int(value) for value in (record.get("player_ids") or [])
                      if value is not None]
        ids_text = "," + ",".join(str(value) for value in player_ids) + "," if player_ids else ""
        with self.connect() as db:
            row = db.execute(
                "INSERT INTO narutodle_matches (room, round_number, mode, target, players, "
                "player_ids, player1_id, player1_name, player2_id, player2_name, winner_id, "
                "winner_name, loser_name, winner_attempts, loser_attempts, winner_team, "
                "boards_json, reason, played_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "RETURNING *",
                (
                    str(record.get("room") or ""),
                    int(record.get("round_number") or 1),
                    str(record.get("mode") or "duel"),
                    str(record.get("target") or ""),
                    str(record.get("players") or ""),
                    ids_text,
                    record.get("player1_id"),
                    str(record.get("player1_name") or ""),
                    record.get("player2_id"),
                    str(record.get("player2_name") or ""),
                    record.get("winner_id"),
                    str(record.get("winner_name") or ""),
                    str(record.get("loser_name") or ""),
                    int(record.get("winner_attempts") or 0),
                    int(record.get("loser_attempts") or 0),
                    str(record.get("winner_team") or ""),
                    str(record.get("boards_json") or ""),
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
                    "SELECT * FROM narutodle_matches WHERE player_ids LIKE %s "
                    "OR player1_id = %s OR player2_id = %s ORDER BY id DESC LIMIT %s",
                    (f"%,{int(user_id)},%", int(user_id), int(user_id), size),
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
                    "INSERT INTO songless_tracks (track_key, anime, song, artist, year, audio, cover, video, "
                    "clip_start, clip_length, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT (track_key) DO UPDATE SET "
                    "anime = EXCLUDED.anime, song = EXCLUDED.song, artist = EXCLUDED.artist, "
                    "year = EXCLUDED.year, "
                    "cover = CASE WHEN EXCLUDED.cover <> '' THEN EXCLUDED.cover "
                    "ELSE songless_tracks.cover END, "
                    "video = CASE WHEN EXCLUDED.video <> '' THEN EXCLUDED.video "
                    "ELSE songless_tracks.video END, "
                    "updated_at = EXCLUDED.updated_at",
                    (
                        str(row.get("track_key") or row.get("anime") or ""),
                        str(row.get("anime") or ""),
                        str(row.get("song") or ""),
                        str(row.get("artist") or ""),
                        str(row.get("year") or ""),
                        str(row.get("audio") or ""),
                        str(row.get("cover") or ""),
                        str(row.get("video") or ""),
                        float(row.get("clip_start") or 0),
                        float(row.get("clip_length") or DEFAULT_CLIP_LENGTH),
                        datetime.now(timezone.utc),
                    ),
                )
                saved += 1
        return saved

    def songless_set_audio(self, anime: str, audio: str,
                           clip_start: Optional[float] = None,
                           clip_length: Optional[float] = None,
                           track_key: Optional[str] = None) -> bool:
        """Привязывает запись к треку; пустая строка — снова «без записи».

        ``track_key`` нужен, когда у одного аниме несколько опенингов: иначе
        одна запись привязалась бы ко всем строкам сериала.
        """
        fields = ["audio = %s", "updated_at = %s"]
        values: List[Any] = [audio, datetime.now(timezone.utc)]
        if clip_start is not None:
            fields.append("clip_start = %s")
            values.append(float(clip_start))
        if clip_length is not None:
            fields.append("clip_length = %s")
            values.append(float(clip_length))
        where = "track_key = %s" if track_key is not None else "anime = %s"
        values.append(str(track_key) if track_key is not None else anime)
        with self.connect() as db:
            cursor = db.execute(
                "UPDATE songless_tracks SET " + ", ".join(fields) + " WHERE " + where,
                tuple(values),
            )
            return cursor.rowcount > 0

    def songless_set_clip(self, anime: str,
                          clip_start: Optional[float] = None,
                          clip_length: Optional[float] = None,
                          track_key: Optional[str] = None) -> bool:
        """Меняет место и длину фрагмента, не трогая саму запись."""
        fields = ["updated_at = %s"]
        values: List[Any] = [datetime.now(timezone.utc)]
        if clip_start is not None:
            fields.append("clip_start = %s")
            values.append(float(clip_start))
        if clip_length is not None:
            fields.append("clip_length = %s")
            values.append(float(clip_length))
        where = "track_key = %s" if track_key is not None else "anime = %s"
        values.append(str(track_key) if track_key is not None else anime)
        with self.connect() as db:
            cursor = db.execute(
                "UPDATE songless_tracks SET " + ", ".join(fields) + " WHERE " + where,
                tuple(values),
            )
            return cursor.rowcount > 0

    def songless_delete_track(self, anime: str) -> bool:
        """Убирает трек из набора (например, чтобы удалить лишнюю строку)."""
        with self.connect() as db:
            cursor = db.execute("DELETE FROM songless_tracks WHERE anime = %s", (anime,))
            return cursor.rowcount > 0

    def songless_add_run(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Пишет итог захода/партии «Аниме-сонглесса» для достижений."""
        detail = record.get("detail") or []
        with self.connect() as db:
            row = db.execute(
                "INSERT INTO songless_runs (username, user_id, mode, rounds, correct, "
                "score, perfect, fast, place, winner, detail, played_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *",
                (
                    str(record.get("username") or ""),
                    record.get("user_id"),
                    str(record.get("mode") or "solo"),
                    int(record.get("rounds") or 0),
                    int(record.get("correct") or 0),
                    int(record.get("score") or 0),
                    1 if record.get("perfect") else 0,
                    int(record.get("fast") or 0),
                    int(record.get("place") or 0),
                    1 if record.get("winner") else 0,
                    json.dumps(list(detail), ensure_ascii=False),
                    datetime.now(timezone.utc),
                ),
            ).fetchone()
        return dict(row)

    def songless_metric_rows(self, user_id: int) -> List[Dict[str, Any]]:
        """Заходы игрока для метрик достижений (detail разбирается в Python)."""
        with self.connect() as db:
            rows = db.execute(
                "SELECT rounds, correct, score, perfect, fast, winner, detail "
                "FROM songless_runs WHERE user_id = %s",
                (int(user_id),),
            ).fetchall()
        return [dict(row) for row in rows]

    def songless_leaderboard(self, limit: int = 20, mode: Optional[str] = None,
                             since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Лидерборд: лучший результат, сумма верных ответов и число заходов.

        ``mode`` — «solo» или «online»: соло-заходы и партии в комнатах считаются
        отдельно. ``since`` — начало периода (для «лучших за сегодняшний день»).
        """
        size = max(1, min(int(limit), 100))
        where = ["user_id IS NOT NULL"]
        params: List[Any] = []
        if mode in ("solo", "online"):
            where.append("mode = %s")
            params.append(mode)
        if since is not None:
            where.append("played_at >= %s")
            params.append(since)
        params.append(size)
        with self.connect() as db:
            rows = db.execute(
                "SELECT MAX(username) AS username, user_id, MAX(score) AS best, "
                "SUM(correct) AS correct, COUNT(1) AS games "
                "FROM songless_runs WHERE " + " AND ".join(where) + " "
                "GROUP BY user_id "
                "ORDER BY best DESC, correct DESC, games ASC LIMIT %s",
                tuple(params),
            ).fetchall()
        return [dict(row) for row in rows]

    # ------------------------------------------------- драфт-рогалики (игры)
    def csdraft_pack_count(self, game: Optional[str] = None) -> int:
        with self.connect() as db:
            if game:
                row = db.execute("SELECT COUNT(*) AS n FROM csdraft_packs WHERE game = %s",
                                 (str(game),)).fetchone()
            else:
                row = db.execute("SELECT COUNT(*) AS n FROM csdraft_packs").fetchone()
            return int(row["n"])

    def csdraft_packs(self, game: Optional[str] = None) -> List[Dict[str, Any]]:
        """Паки одной игры (или всех): источник правды для движка драфта."""
        with self.connect() as db:
            if game:
                rows = db.execute(
                    "SELECT * FROM csdraft_packs WHERE game = %s ORDER BY era, year, id",
                    (str(game),)).fetchall()
            else:
                rows = db.execute(
                    "SELECT * FROM csdraft_packs ORDER BY game, era, year, id").fetchall()
        return [_pack_row(dict(row)) for row in rows]

    def csdraft_save_packs(self, rows: Iterable[Dict[str, Any]]) -> int:
        """Добавляет и обновляет паки (по идентификатору): ими правит владелец сайта."""
        saved = 0
        with self.connect() as db:
            for row in rows:
                db.execute(
                    "INSERT INTO csdraft_packs (id, game, team, event, year, place, major, region, "
                    "era, maps, players, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now()) "
                    "ON CONFLICT(id) DO UPDATE SET game = excluded.game, team = excluded.team, "
                    "event = excluded.event, year = excluded.year, place = excluded.place, "
                    "major = excluded.major, region = excluded.region, era = excluded.era, "
                    "maps = excluded.maps, players = excluded.players, "
                    "updated_at = excluded.updated_at",
                    (
                        str(row.get("id") or ""),
                        str(row.get("game") or "cs"),
                        str(row.get("team") or ""),
                        str(row.get("event") or ""),
                        int(row.get("year") or 0),
                        str(row.get("place") or ""),
                        bool(row.get("major")),
                        str(row.get("region") or ""),
                        str(row.get("era") or "legacy"),
                        json.dumps(list(row.get("maps") or ()), ensure_ascii=False),
                        json.dumps(list(row.get("players") or ()), ensure_ascii=False),
                    ),
                )
                saved += 1
        return saved

    def csdraft_delete_pack(self, pack_id: str) -> bool:
        with self.connect() as db:
            cursor = db.execute("DELETE FROM csdraft_packs WHERE id = %s", (str(pack_id),))
            return cursor.rowcount > 0

    def csdraft_add_run(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Пишет прогон в журнал: кто играл, каким составом и чем закончилось."""
        with self.connect() as db:
            row = db.execute(
                "INSERT INTO csdraft_runs (game, username, user_id, difficulty, era, champion, "
                "wins, losses, stage, rating, squad, packs, score, played_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now()) RETURNING *",
                (
                    str(record.get("game") or "cs"),
                    str(record.get("username") or ""),
                    record.get("user_id"),
                    str(record.get("difficulty") or "hard"),
                    str(record.get("era") or "legacy"),
                    bool(record.get("champion")),
                    int(record.get("wins") or 0),
                    int(record.get("losses") or 0),
                    str(record.get("stage") or ""),
                    float(record.get("rating") or 0),
                    str(record.get("squad") or ""),
                    str(record.get("packs") or ""),
                    str(record.get("score") or ""),
                ),
            ).fetchone()
        return _run_row(dict(row))

    def csdraft_runs(self, user_id: Optional[int] = None, limit: int = 50,
                     game: Optional[str] = None) -> List[Dict[str, Any]]:
        """Журнал прогонов: свои или все подряд (для администратора), по игре или всем."""
        size = max(1, min(int(limit), 500))
        where: List[str] = []
        values: List[Any] = []
        if game:
            where.append("game = %s")
            values.append(str(game))
        if user_id is not None:
            where.append("user_id = %s")
            values.append(int(user_id))
        condition = f" WHERE {' AND '.join(where)}" if where else ""
        with self.connect() as db:
            rows = db.execute(
                f"SELECT * FROM csdraft_runs{condition} ORDER BY id DESC LIMIT %s",
                (*values, size),
            ).fetchall()
        return [_run_row(dict(row)) for row in rows]

    def csdraft_run_count(self, game: Optional[str] = None) -> int:
        with self.connect() as db:
            if game:
                row = db.execute("SELECT COUNT(*) AS n FROM csdraft_runs WHERE game = %s",
                                 (str(game),)).fetchone()
            else:
                row = db.execute("SELECT COUNT(*) AS n FROM csdraft_runs").fetchone()
            return int(row["n"])

    # ------------------------------------------------- «322-0» (драфт по Dota)
    def dotadraft_player_count(self) -> int:
        with self.connect() as db:
            return int(db.execute("SELECT COUNT(*) AS n FROM dotadraft_players").fetchone()["n"])

    def dotadraft_players(self) -> List[Dict[str, Any]]:
        """Пул игроков «322-0»: источник правды для движка."""
        with self.connect() as db:
            rows = db.execute(
                "SELECT id, nickname, cost, position FROM dotadraft_players "
                "ORDER BY cost DESC, id"
            ).fetchall()
        return [_dotadraft_player(dict(row)) for row in rows]

    def dotadraft_save_players(self, rows: Iterable[Dict[str, Any]]) -> int:
        """Добавляет и обновляет игроков пула (по идентификатору).

        Нулевая позиция в наборе значит «позиция неизвестна» и уже
        заполненную позицию в базе не затирает: её правят руками.
        """
        saved = 0
        with self.connect() as db:
            for row in rows:
                player_id = str(row.get("id") or "").strip()
                if not player_id:
                    continue
                db.execute(
                    "INSERT INTO dotadraft_players (id, nickname, cost, position, updated_at) "
                    "VALUES (%s, %s, %s, %s, now()) "
                    "ON CONFLICT(id) DO UPDATE SET nickname = excluded.nickname, "
                    "cost = excluded.cost, "
                    "position = CASE WHEN excluded.position > 0 THEN excluded.position "
                    "ELSE dotadraft_players.position END, "
                    "updated_at = excluded.updated_at",
                    (
                        player_id,
                        str(row.get("nickname") or player_id),
                        int(row.get("cost") or 0),
                        int(row.get("position") or 0),
                    ),
                )
                saved += 1
        return saved

    def dotadraft_set_player_position(self, player_id: str, position: int) -> bool:
        """Своя позиция игрока (0 — сбросить): правка пула на ходу."""
        with self.connect() as db:
            cursor = db.execute(
                "UPDATE dotadraft_players SET position = %s, updated_at = now() WHERE id = %s",
                (int(position or 0), str(player_id)),
            )
            return cursor.rowcount > 0

    def dotadraft_delete_player(self, player_id: str) -> bool:
        with self.connect() as db:
            cursor = db.execute("DELETE FROM dotadraft_players WHERE id = %s", (str(player_id),))
            return cursor.rowcount > 0

    def dotadraft_hero_count(self) -> int:
        with self.connect() as db:
            return int(db.execute("SELECT COUNT(*) AS n FROM dotadraft_heroes").fetchone()["n"])

    def dotadraft_heroes(self) -> List[Dict[str, Any]]:
        """Пул героев «322-0» вместе с позициями: источник правды для движка."""
        with self.connect() as db:
            rows = db.execute(
                "SELECT id, name, name_en, position, rating FROM dotadraft_heroes "
                "ORDER BY position, rating DESC, name"
            ).fetchall()
        return [_dotadraft_hero(dict(row)) for row in rows]

    def dotadraft_save_heroes(self, rows: Iterable[Dict[str, Any]]) -> int:
        """Добавляет и обновляет героев пула (по идентификатору)."""
        saved = 0
        with self.connect() as db:
            for row in rows:
                hero_id = str(row.get("id") or "").strip()
                if not hero_id:
                    continue
                db.execute(
                    "INSERT INTO dotadraft_heroes (id, name, name_en, position, rating, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s, now()) "
                    "ON CONFLICT(id) DO UPDATE SET name = excluded.name, "
                    "name_en = excluded.name_en, position = excluded.position, "
                    "rating = excluded.rating, updated_at = excluded.updated_at",
                    (
                        hero_id,
                        str(row.get("name") or hero_id),
                        str(row.get("name_en") or ""),
                        int(row.get("position") or 1),
                        int(row.get("rating") or 0),
                    ),
                )
                saved += 1
        return saved

    def dotadraft_delete_hero(self, hero_id: str) -> bool:
        with self.connect() as db:
            cursor = db.execute("DELETE FROM dotadraft_heroes WHERE id = %s", (str(hero_id),))
            return cursor.rowcount > 0

    def dotadraft_player_hero_count(self) -> int:
        with self.connect() as db:
            return int(db.execute(
                "SELECT COUNT(*) AS n FROM dotadraft_player_heroes"
            ).fetchone()["n"])

    def dotadraft_player_hero_ratings(self) -> List[Dict[str, Any]]:
        """Оценки героев под игроков: пары «игрок + герой», источник для движка."""
        with self.connect() as db:
            rows = db.execute(
                "SELECT player_id, hero_id, rating FROM dotadraft_player_heroes "
                "ORDER BY player_id, hero_id"
            ).fetchall()
        return [_dotadraft_player_hero(dict(row)) for row in rows]

    def dotadraft_save_player_hero_ratings(self, rows: Iterable[Dict[str, Any]]) -> int:
        """Добавляет и обновляет оценки пар «игрок + герой» (по паре)."""
        saved = 0
        with self.connect() as db:
            for row in rows:
                player_id = str(row.get("player_id") or "").strip()
                hero_id = str(row.get("hero_id") or "").strip()
                if not player_id or not hero_id:
                    continue
                db.execute(
                    "INSERT INTO dotadraft_player_heroes "
                    "(player_id, hero_id, rating, updated_at) VALUES (%s, %s, %s, now()) "
                    "ON CONFLICT(player_id, hero_id) DO UPDATE SET "
                    "rating = excluded.rating, updated_at = excluded.updated_at",
                    (player_id, hero_id, int(row.get("rating") or 0)),
                )
                saved += 1
        return saved

    def dotadraft_delete_player_hero(self, player_id: str, hero_id: str) -> bool:
        with self.connect() as db:
            cursor = db.execute(
                "DELETE FROM dotadraft_player_heroes WHERE player_id = %s AND hero_id = %s",
                (str(player_id), str(hero_id)),
            )
            return cursor.rowcount > 0

    # ----------------------------------- «Угадай песню за 10 секунд» (песни)
    def songguess_track_count(self, category: Optional[str] = None) -> int:
        with self.connect() as db:
            if category:
                row = db.execute("SELECT COUNT(*) AS n FROM songguess_tracks WHERE category = %s",
                                 (str(category),)).fetchone()
            else:
                row = db.execute("SELECT COUNT(*) AS n FROM songguess_tracks").fetchone()
            return int(row["n"])

    def songguess_tracks(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Песни одной темы (или всех): источник правды для движка игры."""
        with self.connect() as db:
            if category:
                rows = db.execute(
                    "SELECT * FROM songguess_tracks WHERE category = %s ORDER BY title, artist",
                    (str(category),)).fetchall()
            else:
                rows = db.execute(
                    "SELECT * FROM songguess_tracks ORDER BY category, title, artist").fetchall()
        return [_songguess_track(dict(row)) for row in rows]

    def songguess_save_tracks(self, rows: Iterable[Dict[str, Any]]) -> int:
        """Добавляет песни и обновляет справочные сведения уже известных.

        Запись (audio), начало и длина фрагмента при повторном наполнении
        не трогаются: это то, что владелец сайта настраивает под свою версию
        песни, и затирать это нельзя.
        """
        saved = 0
        with self.connect() as db:
            for row in rows:
                track_id = str(row.get("id") or "").strip()
                if not track_id:
                    continue
                db.execute(
                    "INSERT INTO songguess_tracks (id, category, title, artist, year, source,"
                    " audio, clip_start, clip_length, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now()) "
                    "ON CONFLICT(id) DO UPDATE SET category = excluded.category, "
                    "title = excluded.title, artist = excluded.artist, year = excluded.year, "
                    "source = excluded.source, updated_at = excluded.updated_at",
                    (
                        track_id,
                        str(row.get("category") or "anime"),
                        str(row.get("title") or track_id),
                        str(row.get("artist") or ""),
                        str(row.get("year") or ""),
                        str(row.get("source") or ""),
                        str(row.get("audio") or ""),
                        float(row.get("clip_start") or 0),
                        float(row.get("clip_length") or DEFAULT_CLIP_LENGTH),
                    ),
                )
                saved += 1
        return saved

    def songguess_set_audio(self, track_id: str, audio: str,
                            clip_start: Optional[float] = None,
                            clip_length: Optional[float] = None) -> bool:
        """Привязывает запись к песне; пустая строка — снова «без записи»."""
        fields = ["audio = %s", "updated_at = now()"]
        values: List[Any] = [str(audio)]
        if clip_start is not None:
            fields.append("clip_start = %s")
            values.append(float(clip_start))
        if clip_length is not None:
            fields.append("clip_length = %s")
            values.append(float(clip_length))
        values.append(str(track_id))
        with self.connect() as db:
            cursor = db.execute(
                "UPDATE songguess_tracks SET " + ", ".join(fields) + " WHERE id = %s",
                tuple(values),
            )
            return cursor.rowcount > 0

    def songguess_delete_track(self, track_id: str) -> bool:
        """Убирает песню из набора (например, чтобы удалить лишнюю строку)."""
        with self.connect() as db:
            cursor = db.execute("DELETE FROM songguess_tracks WHERE id = %s", (str(track_id),))
            return cursor.rowcount > 0

    def songguess_add_run(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Пишет заход в журнал: кто играл, в какой теме и с каким счётом."""
        with self.connect() as db:
            row = db.execute(
                "INSERT INTO songguess_runs (username, user_id, category, difficulty, seconds,"
                " rounds, correct, score, fastest, detail, played_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now()) RETURNING *",
                (
                    str(record.get("username") or ""),
                    record.get("user_id"),
                    str(record.get("category") or "anime"),
                    str(record.get("difficulty") or "normal"),
                    float(record.get("seconds") or 0),
                    int(record.get("rounds") or 0),
                    int(record.get("correct") or 0),
                    int(record.get("score") or 0),
                    float(record["fastest"]) if record.get("fastest") is not None else None,
                    str(record.get("detail") or ""),
                ),
            ).fetchone()
        return _songguess_run(dict(row))

    def songguess_matches(self, user_id: Optional[int] = None, limit: int = 50,
                          category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Журнал заходов: свои или все подряд (для администратора), по теме или всем."""
        size = max(1, min(int(limit), 500))
        where: List[str] = []
        values: List[Any] = []
        if category:
            where.append("category = %s")
            values.append(str(category))
        if user_id is not None:
            where.append("user_id = %s")
            values.append(int(user_id))
        condition = f" WHERE {' AND '.join(where)}" if where else ""
        with self.connect() as db:
            rows = db.execute(
                f"SELECT * FROM songguess_runs{condition} ORDER BY id DESC LIMIT %s",
                (*values, size),
            ).fetchall()
        return [_songguess_run(dict(row)) for row in rows]

    def songguess_run_count(self, category: Optional[str] = None) -> int:
        with self.connect() as db:
            if category:
                row = db.execute("SELECT COUNT(*) AS n FROM songguess_runs WHERE category = %s",
                                 (str(category),)).fetchone()
            else:
                row = db.execute("SELECT COUNT(*) AS n FROM songguess_runs").fetchone()
            return int(row["n"])

    # ------------------------------------------- «Рэп-хронология» (порядок лет)
    def raporder_track_count(self) -> int:
        with self.connect() as db:
            return int(db.execute("SELECT COUNT(*) AS n FROM raporder_tracks").fetchone()["n"])

    def raporder_tracks(self) -> List[Dict[str, Any]]:
        """Треки: источник правды для движка игры."""
        with self.connect() as db:
            rows = db.execute(
                "SELECT id, artist, title, year FROM raporder_tracks ORDER BY year, id"
            ).fetchall()
        return [_rap_track(dict(row)) for row in rows]

    def raporder_save_tracks(self, rows: Iterable[Dict[str, Any]]) -> int:
        """Добавляет и обновляет треки (по идентификатору): ими правит владелец сайта."""
        saved = 0
        with self.connect() as db:
            for row in rows:
                db.execute(
                    "INSERT INTO raporder_tracks (id, artist, title, year, updated_at) "
                    "VALUES (%s, %s, %s, %s, now()) "
                    "ON CONFLICT(id) DO UPDATE SET artist = excluded.artist, "
                    "title = excluded.title, year = excluded.year, "
                    "updated_at = excluded.updated_at",
                    (
                        str(row.get("id") or ""),
                        str(row.get("artist") or ""),
                        str(row.get("title") or ""),
                        int(row.get("year") or 0),
                    ),
                )
                saved += 1
        return saved

    def raporder_delete_track(self, track_id: str) -> bool:
        with self.connect() as db:
            cursor = db.execute("DELETE FROM raporder_tracks WHERE id = %s", (str(track_id),))
            return cursor.rowcount > 0

    def raporder_add_match(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Пишет партию в журнал: кто играл, в каком режиме и чем закончилось."""
        with self.connect() as db:
            row = db.execute(
                "INSERT INTO raporder_matches (mode, room, rounds, player1_id, player1_name, "
                "player1_score, player2_id, player2_name, player2_score, winner_id, winner_name, "
                "detail, played_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now()) RETURNING *",
                (
                    str(record.get("mode") or "solo"),
                    str(record.get("room") or ""),
                    int(record.get("rounds") or 0),
                    record.get("player1_id"),
                    str(record.get("player1_name") or ""),
                    int(record.get("player1_score") or 0),
                    record.get("player2_id"),
                    str(record.get("player2_name") or ""),
                    int(record.get("player2_score") or 0),
                    record.get("winner_id"),
                    str(record.get("winner_name") or ""),
                    str(record.get("detail") or ""),
                ),
            ).fetchone()
        return _rap_match(dict(row))

    def raporder_matches(self, user_id: Optional[int] = None, limit: int = 50,
                         mode: Optional[str] = None) -> List[Dict[str, Any]]:
        """Журнал партий: свои (как игрок или соперник) или все подряд для админа."""
        size = max(1, min(int(limit), 500))
        where: List[str] = []
        values: List[Any] = []
        if user_id is not None:
            where.append("(player1_id = %s OR player2_id = %s)")
            values.extend([int(user_id), int(user_id)])
        if mode:
            where.append("mode = %s")
            values.append(str(mode))
        condition = f" WHERE {' AND '.join(where)}" if where else ""
        with self.connect() as db:
            rows = db.execute(
                f"SELECT * FROM raporder_matches{condition} ORDER BY id DESC LIMIT %s",
                (*values, size),
            ).fetchall()
        return [_rap_match(dict(row)) for row in rows]

    def raporder_match_count(self) -> int:
        with self.connect() as db:
            return int(db.execute("SELECT COUNT(*) AS n FROM raporder_matches").fetchone()["n"])

    # ------------------------------------------------------ записи игр в базе
    def audio_clip_save(self, game: str, track_key: str, data: bytes,
                        mime: str = "audio/mpeg", duration_ms: int = 0,
                        source: str = "") -> None:
        """Кладёт аудиофрагмент игры в базу, перезаписывая прежний."""
        if not data:
            raise ValueError("Пустая запись")
        with self.connect() as db:
            db.execute(
                "INSERT INTO audio_clips (game, track_key, mime, duration_ms, source, data, "
                "updated_at) VALUES (%s, %s, %s, %s, %s, %s, now()) "
                "ON CONFLICT (game, track_key) DO UPDATE SET mime = excluded.mime, "
                "duration_ms = excluded.duration_ms, source = excluded.source, "
                "data = excluded.data, updated_at = now()",
                (
                    str(game),
                    str(track_key),
                    str(mime or "audio/mpeg"),
                    int(duration_ms or 0),
                    str(source or ""),
                    bytes(data),
                ),
            )

    def audio_clip_get(self, game: str, track_key: str) -> Optional[Dict[str, Any]]:
        """Достаёт аудиофрагмент: байты, тип и длительность (None, если его нет)."""
        with self.connect() as db:
            row = db.execute(
                "SELECT mime, duration_ms, source, data, updated_at FROM audio_clips "
                "WHERE game = %s AND track_key = %s",
                (str(game), str(track_key)),
            ).fetchone()
        if not row:
            return None
        data = row["data"]
        return {
            "game": str(game),
            "track_key": str(track_key),
            "mime": str(row["mime"] or "audio/mpeg"),
            "duration_ms": int(row["duration_ms"] or 0),
            "source": str(row["source"] or ""),
            "updated_at": to_iso(row["updated_at"]),
            "data": bytes(data) if data is not None else b"",
        }

    def audio_clip_has(self, game: str, track_key: str) -> bool:
        with self.connect() as db:
            row = db.execute(
                "SELECT 1 AS ok FROM audio_clips WHERE game = %s AND track_key = %s LIMIT 1",
                (str(game), str(track_key)),
            ).fetchone()
        return bool(row)

    def audio_clip_keys(self, game: str) -> List[str]:
        """Ключи треков, у которых уже есть запись в базе (для отчётов и пропусков)."""
        with self.connect() as db:
            rows = db.execute(
                "SELECT track_key FROM audio_clips WHERE game = %s ORDER BY track_key",
                (str(game),),
            ).fetchall()
        return [str(row["track_key"]) for row in rows]

    def audio_clip_delete(self, game: str, track_key: str) -> bool:
        with self.connect() as db:
            cursor = db.execute(
                "DELETE FROM audio_clips WHERE game = %s AND track_key = %s",
                (str(game), str(track_key)),
            )
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
    ("user_profiles", ("user_id", "display_name", "bio", "favorite_game", "accent",
                       "frame", "card", "status", "avatar_mime", "avatar_data", "updated_at"),
     ("user_id",)),
    ("user_achievements", ("user_id", "achievement_id", "unlocked_at"),
     ("user_id", "achievement_id")),
    ("secret_data", ("id", "name", "value", "updated_at"), ("id",)),
    ("narutodle_characters", ("id", "name", "gender", "village", "clan", "nature", "kekkei",
                              "jinchuriki", "debut", "color", "image", "updated_at"),
     ("id",)),
    ("narutodle_matches", ("id", "room", "round_number", "target", "player1_id", "player1_name",
                           "player2_id", "player2_name", "winner_id", "winner_name", "loser_name",
                           "winner_attempts", "loser_attempts", "winner_team", "boards_json",
                           "reason", "played_at"), ("id",)),
    ("songless_tracks", ("id", "track_key", "anime", "song", "artist", "year", "audio", "cover", "video",
                         "clip_start", "clip_length", "updated_at"), ("id",)),
    ("songless_runs", ("id", "username", "user_id", "mode", "rounds", "correct", "score",
                       "perfect", "fast", "place", "winner", "detail", "played_at"), ("id",)),
    ("device_commands", ("id", "zone_id", "device", "on_state", "seconds", "created_at",
                         "delivered_at", "applied_at", "error"), ("id",)),
    ("csdraft_packs", ("id", "game", "team", "event", "year", "place", "major", "region", "era",
                       "maps", "players", "updated_at"), ("id",)),
    ("csdraft_runs", ("id", "game", "username", "user_id", "difficulty", "era", "champion", "wins",
                      "losses", "stage", "rating", "squad", "packs", "score", "played_at"), ("id",)),
    ("raporder_tracks", ("id", "artist", "title", "year", "updated_at"), ("id",)),
    ("raporder_matches", ("id", "mode", "room", "rounds", "player1_id", "player1_name",
                          "player1_score", "player2_id", "player2_name", "player2_score",
                          "winner_id", "winner_name", "detail", "played_at"), ("id",)),
    ("dotadraft_players", ("id", "nickname", "cost", "updated_at"), ("id",)),
    ("dotadraft_heroes", ("id", "name", "name_en", "position", "rating", "updated_at"), ("id",)),
    ("songguess_tracks", ("id", "category", "title", "artist", "year", "source", "audio",
                          "clip_start", "clip_length", "updated_at"), ("id",)),
    ("songguess_runs", ("id", "username", "user_id", "category", "difficulty", "seconds",
                        "rounds", "correct", "score", "fastest", "detail", "played_at"),
     ("id",)),
)

# Колонки, значения которых при переносе нужно привести к типу PostgreSQL.
BOOL_COLUMNS = ("enabled", "auto_watering", "auto_ventilation", "auto_lighting", "on_state",
                "major", "champion")
TIME_COLUMNS = ("recorded_at", "ts", "updated_at", "created_at", "expires_at", "played_at",
                "delivered_at", "applied_at", "unlocked_at")
