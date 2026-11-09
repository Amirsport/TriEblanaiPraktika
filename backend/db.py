# -*- coding: utf-8 -*-
"""Слой доступа к данным (SQLite) для теплицы из 12 участков.

Схема:
    zones        — 12 участков (секций парника);
    readings     — показания датчиков по каждому участку (история);
    zone_devices — исполнители (полив/проветривание/досветка) по участкам;
    settings     — глобальные настройки и пороги (одна строка id=1);
    state        — глобальное состояние: бак, форточка, источник данных;
    logs         — журнал событий;
    users        — аккаунты панели (логин, хеш пароля, роль);
    auth_sessions— выданные токены входа;
    user_states  — сохранённое состояние панели каждого пользователя;
    secret_data  — именованные записи секретной страницы /TriEblanaiPraktika;
    narutodle_characters / narutodle_matches — игра «Narutodle» и её журнал;
    songless_tracks — игра «Аниме-сонглесс»: треки и записи к ним;
    songguess_tracks — игра «Угадай песню»: песни и записи к ним;
    audio_clips  — аудиофрагменты игр, сохранённые прямо в базе (MP3-байты);
    csdraft_packs / csdraft_runs — игра «87-0»: составы турниров и журнал прогонов;
    device_commands — очередь команд домашнему агенту (когда сервер не рядом с платой).

Второй бэкенд — PostgreSQL (backend/db_postgres.py) с тем же набором методов.
Бэкенд выбирается функцией open_database().
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Set, Union

if TYPE_CHECKING:  # psycopg нужен только при работе с PostgreSQL
    from .arduino import ArduinoLink
    from .db_postgres import PostgresDatabase
    from .device_link import RemoteDeviceLink

ZONE_COUNT = 12
ZONE_NAMES = [f"Участок {i}" for i in range(1, ZONE_COUNT + 1)]

# Длина фрагмента трека по умолчанию («Аниме-сонглесс»), секунды.
DEFAULT_CLIP_LENGTH = 8.0
DEVICES = ("watering", "ventilation", "lighting")

# Значение колонки audio, когда запись лежит не файлом и не ссылкой, а
# в таблице audio_clips. Пишет его songs.py, читает раздача записей сервера.
AUDIO_IN_DB = "db:clip"

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

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL DEFAULT 'user' CHECK(role IN ('admin','user')),
    created_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_name ON users(username);

CREATE TABLE IF NOT EXISTS auth_sessions (
    token      TEXT    PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TEXT    NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON auth_sessions(user_id);

CREATE TABLE IF NOT EXISTS user_states (
    user_id    INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    payload    TEXT    NOT NULL,
    updated_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- Профиль игрока: имя, описание, любимая игра, цвет и аватар. Отдельная
-- таблица, чтобы картинка не попадала в каждый SELECT списка пользователей.
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id       INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    display_name  TEXT    NOT NULL DEFAULT '',
    bio           TEXT    NOT NULL DEFAULT '',
    favorite_game TEXT    NOT NULL DEFAULT '',
    accent        TEXT    NOT NULL DEFAULT '',
    frame         TEXT    NOT NULL DEFAULT '',
    card          TEXT    NOT NULL DEFAULT '',
    status        TEXT    NOT NULL DEFAULT '',
    avatar_mime   TEXT    NOT NULL DEFAULT '',
    avatar_data   BLOB,
    updated_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- Достижения игрока: выданное один раз не отбирается, поэтому unlocked_at —
-- момент первой выдачи. Награды (статус, ободок, оформление) не хранятся
-- здесь: они выводятся из этого набора по каталогу backend/achievements.py.
CREATE TABLE IF NOT EXISTS user_achievements (
    user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    achievement_id TEXT    NOT NULL,
    unlocked_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    PRIMARY KEY (user_id, achievement_id)
);

CREATE TABLE IF NOT EXISTS secret_data (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    value      TEXT    NOT NULL DEFAULT '',
    updated_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_secret_name ON secret_data(name);

-- Игра Narutodle: набор персонажей и журнал матчей. Набор хранится в базе,
-- чтобы его можно было править и дополнять без правки кода; image — путь
-- к своей картинке (пусто — страница рисует аватар из инициалов и color).
CREATE TABLE IF NOT EXISTS narutodle_characters (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    gender     TEXT    NOT NULL DEFAULT '',
    village    TEXT    NOT NULL DEFAULT '',
    clan       TEXT    NOT NULL DEFAULT '',
    nature     TEXT    NOT NULL DEFAULT '[]',
    kekkei     TEXT    NOT NULL DEFAULT '',
    jinchuriki TEXT    NOT NULL DEFAULT '',
    debut      TEXT    NOT NULL DEFAULT '',
    color      TEXT    NOT NULL DEFAULT '',
    image      TEXT    NOT NULL DEFAULT '',
    updated_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_narutodle_characters_name ON narutodle_characters(name);

-- Журнал партий: кто играл, чем закончилось и с какого раза.
-- mode — режим («duel», «race», «teams»), players — доски с результатом,
-- player_ids — все участники (через запятую, с запятыми по краям): по нему
-- партия находится в «Моих матчах», даже когда игроков больше двух.
-- Ссылок на users нет намеренно: история матчей должна переживать удаление аккаунта.
CREATE TABLE IF NOT EXISTS narutodle_matches (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    room            TEXT    NOT NULL DEFAULT '',
    round_number    INTEGER NOT NULL DEFAULT 1,
    mode            TEXT    NOT NULL DEFAULT 'duel',
    target          TEXT    NOT NULL DEFAULT '',
    players         TEXT    NOT NULL DEFAULT '',
    player_ids      TEXT    NOT NULL DEFAULT '',
    player1_id      INTEGER,
    player1_name    TEXT    NOT NULL DEFAULT '',
    player2_id      INTEGER,
    player2_name    TEXT    NOT NULL DEFAULT '',
    winner_id       INTEGER,
    winner_name     TEXT    NOT NULL DEFAULT '',
    loser_name      TEXT    NOT NULL DEFAULT '',
    winner_attempts INTEGER NOT NULL DEFAULT 0,
    loser_attempts  INTEGER NOT NULL DEFAULT 0,
    -- Итог для скрытых достижений: победившая команда и доски с тем, кто
    -- закрывал персонажа и с какой попытки (JSON, см. _log_match).
    winner_team     TEXT    NOT NULL DEFAULT '',
    boards_json     TEXT    NOT NULL DEFAULT '',
    reason          TEXT    NOT NULL DEFAULT '',
    played_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_narutodle_matches_played ON narutodle_matches(id DESC);
CREATE INDEX IF NOT EXISTS idx_narutodle_matches_players ON narutodle_matches(player1_id, player2_id);

-- Треки «Аниме-сонглесса»: справочные сведения плюс запись, которую слушают.
-- Самих записей в репозитории нет: audio указывает на свой файл в папке игры,
-- на внешнюю ссылку или на db:clip (MP3 лежит в audio_clips); пока он пуст,
-- раунд на треке не строится.
CREATE TABLE IF NOT EXISTS songless_tracks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    track_key   TEXT    NOT NULL DEFAULT '',
    anime       TEXT    NOT NULL,
    song        TEXT    NOT NULL DEFAULT '',
    artist      TEXT    NOT NULL DEFAULT '',
    year        TEXT    NOT NULL DEFAULT '',
    audio       TEXT    NOT NULL DEFAULT '',
    cover       TEXT    NOT NULL DEFAULT '',
    video       TEXT    NOT NULL DEFAULT '',
    clip_start  REAL    NOT NULL DEFAULT 0,
    clip_length REAL    NOT NULL DEFAULT 8,
    updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_songless_tracks_anime ON songless_tracks(anime);

-- Итоги заходов «Аниме-сонглесса»: по ним считаются достижения. detail —
-- JSON-массив угаданных аниме, чтобы считать коллекцию без отдельной таблицы.
CREATE TABLE IF NOT EXISTS songless_runs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username   TEXT    NOT NULL DEFAULT '',
    user_id    INTEGER,
    mode       TEXT    NOT NULL DEFAULT 'solo',
    rounds     INTEGER NOT NULL DEFAULT 0,
    correct    INTEGER NOT NULL DEFAULT 0,
    score      INTEGER NOT NULL DEFAULT 0,
    perfect    INTEGER NOT NULL DEFAULT 0,
    fast       INTEGER NOT NULL DEFAULT 0,
    place      INTEGER NOT NULL DEFAULT 0,
    winner     INTEGER NOT NULL DEFAULT 0,
    detail     TEXT    NOT NULL DEFAULT '[]',
    played_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_songless_runs_user ON songless_runs (user_id, id DESC);

-- Очередь команд домашнему агенту: сервер на VPS не держит COM-порт, поэтому
-- записывает команду сюда, агент забирает её, применяет к плате и подтверждает.
CREATE TABLE IF NOT EXISTS device_commands (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    zone_id      INTEGER NOT NULL,
    device       TEXT    NOT NULL,
    on_state     INTEGER NOT NULL,
    seconds      REAL,
    created_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    delivered_at TEXT,
    applied_at   TEXT,
    error        TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_device_commands_open ON device_commands (applied_at, id);

-- Драфт-рогалики («87-0» по CS, «13-0» по Valorant, «4-0» по Rocket League):
-- составы прошлых турниров (паки) и журнал прогонов. Паки правятся владельцем
-- сайта: карты и игроки лежат JSON-строками, чтобы не заводить по таблице на
-- каждую сущность. Колонка game отделяет наборы паков друг от друга.
CREATE TABLE IF NOT EXISTS csdraft_packs (
    id         TEXT    PRIMARY KEY,
    game       TEXT    NOT NULL DEFAULT 'cs',
    team       TEXT    NOT NULL,
    event      TEXT    NOT NULL,
    year       INTEGER NOT NULL DEFAULT 0,
    place      TEXT    NOT NULL DEFAULT '',
    major      INTEGER NOT NULL DEFAULT 0,
    region     TEXT    NOT NULL DEFAULT '',
    era        TEXT    NOT NULL DEFAULT 'legacy',
    maps       TEXT    NOT NULL DEFAULT '[]',
    players    TEXT    NOT NULL DEFAULT '[]',
    updated_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE IF NOT EXISTS csdraft_runs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    game       TEXT    NOT NULL DEFAULT 'cs',
    username   TEXT    NOT NULL DEFAULT '',
    user_id    INTEGER,
    difficulty TEXT    NOT NULL DEFAULT 'hard',
    era        TEXT    NOT NULL DEFAULT 'legacy',
    champion   INTEGER NOT NULL DEFAULT 0,
    wins       INTEGER NOT NULL DEFAULT 0,
    losses     INTEGER NOT NULL DEFAULT 0,
    stage      TEXT    NOT NULL DEFAULT '',
    rating     REAL    NOT NULL DEFAULT 0,
    squad      TEXT    NOT NULL DEFAULT '',
    packs      TEXT    NOT NULL DEFAULT '',
    score      TEXT    NOT NULL DEFAULT '',
    played_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_csdraft_runs_user ON csdraft_runs (user_id, id DESC);

-- «Рэп-хронология»: треки (исполнитель, название, год) и журнал партий.
-- Год — единственное, что важно игре: по нему треки и расставляются.
CREATE TABLE IF NOT EXISTS raporder_tracks (
    id         TEXT    PRIMARY KEY,
    artist     TEXT    NOT NULL DEFAULT '',
    title      TEXT    NOT NULL DEFAULT '',
    year       INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE IF NOT EXISTS raporder_matches (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    mode         TEXT    NOT NULL DEFAULT 'solo',
    room         TEXT    NOT NULL DEFAULT '',
    rounds       INTEGER NOT NULL DEFAULT 0,
    player1_id   INTEGER,
    player1_name TEXT    NOT NULL DEFAULT '',
    player1_score INTEGER NOT NULL DEFAULT 0,
    player2_id   INTEGER,
    player2_name TEXT    NOT NULL DEFAULT '',
    player2_score INTEGER NOT NULL DEFAULT 0,
    winner_id    INTEGER,
    winner_name  TEXT    NOT NULL DEFAULT '',
    detail       TEXT    NOT NULL DEFAULT '',
    played_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_raporder_matches_player ON raporder_matches (player1_id, id DESC);

-- «322-0» (драфт по Dota 2 на Streamers Battle 13): пул игроков со стоимостью
-- и своей позицией (1–5, 0 — позиция неизвестна), пул героев с позицией и
-- игровой оценкой и оценки героев под конкретных игроков (пары «игрок + герой»
-- по их матчам). Стоимости и позиции правит владелец сайта.
-- Журнал прогонов общий с драфт-рогаликами (csdraft_runs, game = 'dota322').
CREATE TABLE IF NOT EXISTS dotadraft_players (
    id         TEXT    PRIMARY KEY,
    nickname   TEXT    NOT NULL,
    cost       INTEGER NOT NULL DEFAULT 0,
    position   INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_dotadraft_players_cost ON dotadraft_players (cost DESC, id);
CREATE TABLE IF NOT EXISTS dotadraft_heroes (
    id         TEXT    PRIMARY KEY,
    name       TEXT    NOT NULL,
    name_en    TEXT    NOT NULL DEFAULT '',
    position   INTEGER NOT NULL DEFAULT 1,
    rating     INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_dotadraft_heroes_pos ON dotadraft_heroes (position, rating DESC);
CREATE TABLE IF NOT EXISTS dotadraft_player_heroes (
    player_id  TEXT    NOT NULL,
    hero_id    TEXT    NOT NULL,
    rating     INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    PRIMARY KEY (player_id, hero_id)
);

-- «Угадай песню за 10 секунд»: песни по темам (аниме, русский рэп, хип-хоп)
-- и журнал заходов. Записи добавляет владелец сайта — файлами, ссылками или
-- через songs.py прямо в audio_clips (тогда в audio стоит db:clip); пока
-- записи нет, раунд на песне не строится.
CREATE TABLE IF NOT EXISTS songguess_tracks (
    id          TEXT    PRIMARY KEY,
    category    TEXT    NOT NULL DEFAULT 'anime',
    title       TEXT    NOT NULL,
    artist      TEXT    NOT NULL DEFAULT '',
    year        TEXT    NOT NULL DEFAULT '',
    source      TEXT    NOT NULL DEFAULT '',
    audio       TEXT    NOT NULL DEFAULT '',
    clip_start  REAL    NOT NULL DEFAULT 0,
    clip_length REAL    NOT NULL DEFAULT 10,
    updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_songguess_tracks_category ON songguess_tracks (category, title);
CREATE TABLE IF NOT EXISTS songguess_runs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username   TEXT    NOT NULL DEFAULT '',
    user_id    INTEGER,
    category   TEXT    NOT NULL DEFAULT 'anime',
    difficulty TEXT    NOT NULL DEFAULT 'normal',
    seconds    REAL    NOT NULL DEFAULT 10,
    rounds     INTEGER NOT NULL DEFAULT 0,
    correct    INTEGER NOT NULL DEFAULT 0,
    score      INTEGER NOT NULL DEFAULT 0,
    fastest    REAL,
    detail     TEXT    NOT NULL DEFAULT '',
    played_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_songguess_runs_user ON songguess_runs (user_id, id DESC);

-- Аудиофрагменты игр («Угадай песню» и «Аниме-сонглесс») прямо в базе:
-- game — ключ игры, track_key — id песни или название аниме, data — MP3-байты.
CREATE TABLE IF NOT EXISTS audio_clips (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    game        TEXT    NOT NULL,
    track_key   TEXT    NOT NULL,
    mime        TEXT    NOT NULL DEFAULT 'audio/mpeg',
    duration_ms INTEGER NOT NULL DEFAULT 0,
    source      TEXT    NOT NULL DEFAULT '',
    data        BLOB    NOT NULL,
    updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE(game, track_key)
);
"""

# Колонки, появившиеся после первых версий базы: на старых базах их догоняет
# ALTER TABLE (см. Database._migrate и PostgresDatabase._migrate).
LATE_COLUMNS: Tuple[Tuple[str, str, str], ...] = (
    ("csdraft_packs", "game", "TEXT NOT NULL DEFAULT 'cs'"),
    ("csdraft_runs", "game", "TEXT NOT NULL DEFAULT 'cs'"),
    ("dotadraft_players", "position", "INTEGER NOT NULL DEFAULT 0"),
    ("narutodle_matches", "mode", "TEXT NOT NULL DEFAULT 'duel'"),
    ("narutodle_matches", "players", "TEXT NOT NULL DEFAULT ''"),
    ("narutodle_matches", "player_ids", "TEXT NOT NULL DEFAULT ''"),
    # Скрытые достижения Narutodle: победившая команда и доски с попытками.
    ("narutodle_matches", "winner_team", "TEXT NOT NULL DEFAULT ''"),
    ("narutodle_matches", "boards_json", "TEXT NOT NULL DEFAULT ''"),
    # Обложка и ссылка на опенинг для страницы «Аниме-сонглесса».
    ("songless_tracks", "cover", "TEXT NOT NULL DEFAULT ''"),
    ("songless_tracks", "video", "TEXT NOT NULL DEFAULT ''"),
    # Аниме может встречаться несколько раз (разные опенинги): ключ трека.
    ("songless_tracks", "track_key", "TEXT NOT NULL DEFAULT ''"),
    # Персонализация профиля, появившаяся позже: ободок аватара и оформление
    # карточки (см. backend/auth.py, FRAMES и CARDS).
    ("user_profiles", "frame", "TEXT NOT NULL DEFAULT ''"),
    ("user_profiles", "card", "TEXT NOT NULL DEFAULT ''"),
    ("user_profiles", "status", "TEXT NOT NULL DEFAULT ''"),
)

# Индексы, которые зависят от поздних колонок: создаются после миграции, иначе
# на старой базе индекс по ещё не существующей колонке оборвал бы инициализацию.
LATE_INDEXES: Tuple[str, ...] = (
    "CREATE INDEX IF NOT EXISTS idx_csdraft_packs_game ON csdraft_packs (game, era, year)",
)


def _iso(value: datetime) -> str:
    """Момент времени в формате, который хранит SQLite: 2026-10-12T20:23:39.739Z."""
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _now() -> str:
    return _iso(datetime.now(timezone.utc))


def _nature_list(value: Any) -> List[str]:
    """Стихии хранятся в текстовой колонке как JSON-массив — читаем как список."""
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
    return data


def _match(row: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(row)
    # Доски в JSON нужны только достижениям: в журнале матчей они лишние.
    data.pop("boards_json", None)
    for key in ("id", "round_number", "winner_attempts", "loser_attempts"):
        if data.get(key) is not None:
            data[key] = int(data[key])
    return data


# Персонаж, за угадывание которого с первой попытки дают скрытый титул.
NARUTODLE_MADARA = "Мадара Учиха"


def _as_int(value: Any) -> int:
    """Число из журнала: JSON приходит без типов, пустое значение — ноль."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def narutodle_secret_metrics(rows: Iterable[Dict[str, Any]],
                             user_id: int) -> Dict[str, int]:
    """Счётчики скрытых титулов Narutodle по полю boards_json.

    * narutodle_team_carry  — победа в командах, где игрок сам не закрыл ни
      одного персонажа (доску могли закрыть товарищи);
    * narutodle_madara_first — Мадара, угаданный этим игроком с первой попытки.

    Старые записи журнала досок не хранят, поэтому в счёт не попадают.
    """
    uid = int(user_id)
    carry = 0
    madara = 0
    for row in rows:
        try:
            boards = json.loads(str(row.get("boards_json") or "") or "[]")
        except (TypeError, ValueError):
            continue
        if not isinstance(boards, list):
            continue
        mine = [board for board in boards
                if isinstance(board, dict) and _as_int(board.get("id")) == uid]
        personal = 0
        for board in boards:
            if not isinstance(board, dict):
                continue
            for step in board.get("history") or []:
                if not isinstance(step, dict) or _as_int(step.get("by_id")) != uid:
                    continue
                personal += 1
                if (str(step.get("target") or "") == NARUTODLE_MADARA
                        and _as_int(step.get("attempts")) == 1):
                    madara = 1
        winner_team = str(row.get("winner_team") or "")
        if (str(row.get("mode") or "") == "teams" and winner_team and personal == 0
                and any(str(board.get("team") or "") == winner_team for board in mine)):
            carry += 1
    return {"narutodle_team_carry": carry, "narutodle_madara_first": madara}


def songless_metrics_from_runs(rows: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    """Счётчики достижений «Аниме-сонглесса» по журналу заходов."""
    played = wins = correct = best = perfect = fast = 0
    guessed: Set[str] = set()
    rezero: Set[str] = set()
    for row in rows:
        played += 1
        wins += 1 if _as_int(row.get("winner")) else 0
        correct += _as_int(row.get("correct"))
        best = max(best, _as_int(row.get("score")))
        perfect += 1 if _as_int(row.get("perfect")) else 0
        fast += _as_int(row.get("fast"))
        try:
            detail = json.loads(str(row.get("detail") or "[]"))
        except (TypeError, ValueError):
            detail = []
        if isinstance(detail, list):
            for value in detail:
                if isinstance(value, dict):
                    anime = str(value.get("anime") or "")
                    key = str(value.get("track_key") or value.get("song") or anime)
                    if anime:
                        guessed.add(anime)
                    if "re:zero" in anime.casefold() or "rezero" in anime.casefold():
                        if key:
                            rezero.add(key)
                elif value:
                    guessed.add(str(value))
    return {
        "songless_played": played,
        "songless_wins": wins,
        "songless_correct": correct,
        "songless_best": best,
        "songless_perfect": perfect,
        "songless_fast": fast,
        "songless_guesses": len(guessed),
        "songless_rezero": len(rezero),
    }


def _track(row: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(row)
    for key in ("clip_start", "clip_length"):
        data[key] = float(data.get(key) or 0)
    if data.get("id") is not None:
        data["id"] = int(data["id"])
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
    return data


def _run_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Строка журнала прогонов «87-0»."""
    data = dict(row)
    data["champion"] = bool(data.get("champion"))
    for key in ("wins", "losses"):
        data[key] = int(data.get(key) or 0)
    if data.get("rating") is not None:
        data["rating"] = float(data["rating"])
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


def _command(row: Dict[str, Any]) -> Dict[str, Any]:
    """Строка очереди команд в том виде, в каком её ждёт домашний агент."""
    data = dict(row)
    data["id"] = int(data["id"])
    data["zone_id"] = int(data["zone_id"])
    data["on"] = bool(data["on_state"])
    data["seconds"] = float(data["seconds"]) if data.get("seconds") is not None else None
    return data


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
            self._migrate(db)
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

    @staticmethod
    def _migrate(db: sqlite3.Connection) -> None:
        """Догоняет схему на базах, созданных прошлыми версиями сервера."""
        for table, column, definition in LATE_COLUMNS:
            known = {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}
            if column not in known:
                db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        for statement in LATE_INDEXES:
            db.execute(statement)
        # Аниме больше не уникально: один сериал может дать несколько опенингов.
        # Старым строкам ключом становится само название, а ключ трека — уникален.
        db.execute("UPDATE songless_tracks SET track_key = anime WHERE track_key = ''")
        db.execute("DROP INDEX IF EXISTS idx_songless_tracks_anime")
        db.execute("CREATE INDEX IF NOT EXISTS idx_songless_tracks_anime "
                   "ON songless_tracks(anime)")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_songless_tracks_key "
                   "ON songless_tracks(track_key)")

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

    # ------------------------------------------------- команды устройству
    def device_command_add(self, zone_id: int, device: str, on: bool,
                           seconds: Optional[float] = None) -> int:
        """Кладёт команду в очередь: её заберёт домашний агент у платы."""
        with self.connect() as db:
            cursor = db.execute(
                "INSERT INTO device_commands (zone_id, device, on_state, seconds) VALUES (?, ?, ?, ?)",
                (int(zone_id), device, 1 if on else 0, seconds),
            )
            return int(cursor.lastrowid or 0)

    def device_commands_pending(self, limit: int = 50,
                                max_age: Optional[float] = None) -> List[Dict[str, Any]]:
        """Отдаёт неподтверждённые команды и помечает их выданными агенту.

        Команды старше max_age секунд закрываются как просроченные: полив,
        который включился бы через час после нажатия кнопки, опаснее пропуска.
        """
        with self.connect() as db:
            if max_age:
                border = _iso(datetime.now(timezone.utc) - timedelta(seconds=float(max_age)))
                db.execute(
                    "UPDATE device_commands SET applied_at = ?, error = ? "
                    "WHERE applied_at IS NULL AND created_at < ?",
                    (_now(), "просрочена: агент не был на связи", border),
                )
            db.execute(
                "UPDATE device_commands SET delivered_at = ? "
                "WHERE applied_at IS NULL AND delivered_at IS NULL",
                (_now(),),
            )
            rows = db.execute(
                "SELECT id, zone_id, device, on_state, seconds, created_at, delivered_at, applied_at, error "
                "FROM device_commands WHERE applied_at IS NULL ORDER BY id LIMIT ?",
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
        stamp = _now()
        with self.connect() as db:
            done = 0
            for command_id in ids:
                cursor = db.execute(
                    "UPDATE device_commands SET applied_at = ?, error = ? WHERE id = ? AND applied_at IS NULL",
                    (stamp, problems.get(command_id, ""), command_id),
                )
                done += cursor.rowcount
        return done

    def device_commands_prune(self, keep_hours: float = 24.0) -> int:
        """Убирает старые выполненные команды, чтобы очередь не росла."""
        border = _iso(datetime.now(timezone.utc) - timedelta(hours=float(keep_hours)))
        with self.connect() as db:
            cursor = db.execute(
                "DELETE FROM device_commands WHERE applied_at IS NOT NULL AND applied_at < ?",
                (border,),
            )
            return cursor.rowcount

    def device_commands(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Последние команды для журнала и диагностики связи с агентом."""
        with self.connect() as db:
            rows = db.execute(
                "SELECT id, zone_id, device, on_state, seconds, created_at, delivered_at, applied_at, error "
                "FROM device_commands ORDER BY id DESC LIMIT ?",
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
            existing = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
            if existing:
                raise ValueError(f"Пользователь «{username}» уже существует")
            inserted = db.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (username, password_hash, role),
            )
            row = db.execute(
                "SELECT id, username, role, created_at FROM users WHERE id = ?", (inserted.lastrowid,)
            ).fetchone()
        return dict(row)

    def list_users(self) -> List[Dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT id, username, role, created_at FROM users ORDER BY id"
            ).fetchall()
        return [dict(row) for row in rows]

    def find_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Строка пользователя вместе с хешем пароля — только для проверки входа."""
        with self.connect() as db:
            row = db.execute(
                "SELECT id, username, password_hash, role, created_at FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        return dict(row) if row else None

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self.connect() as db:
            row = db.execute(
                "SELECT id, username, role, created_at FROM users WHERE id = ?", (user_id,)
            ).fetchone()
        return dict(row) if row else None

    def find_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Строка пользователя вместе с хешем пароля — для проверки смены пароля."""
        with self.connect() as db:
            row = db.execute(
                "SELECT id, username, password_hash, role, created_at FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        return dict(row) if row else None

    def set_user_password(self, user_id: int, password_hash: str) -> bool:
        with self.connect() as db:
            cursor = db.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id)
            )
            return cursor.rowcount > 0

    def delete_user(self, user_id: int) -> bool:
        with self.connect() as db:
            cursor = db.execute("DELETE FROM users WHERE id = ?", (user_id,))
            return cursor.rowcount > 0

    # --------------------------------------------------------------- sessions
    def create_session(self, user_id: int, token: str, expires_at: datetime) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO auth_sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
                (token, user_id, _iso(expires_at)),
            )

    def session_user(self, token: str) -> Optional[Dict[str, Any]]:
        """Пользователь по действующему (не истёкшему) токену входа."""
        if not token:
            return None
        with self.connect() as db:
            row = db.execute(
                "SELECT u.id, u.username, u.role, u.created_at FROM auth_sessions s "
                "JOIN users u ON u.id = s.user_id "
                "WHERE s.token = ? AND s.expires_at > ?",
                (token, _now()),
            ).fetchone()
        return dict(row) if row else None

    def delete_session(self, token: str) -> None:
        if not token:
            return
        with self.connect() as db:
            db.execute("DELETE FROM auth_sessions WHERE token = ?", (token,))

    def purge_sessions(self) -> None:
        """Удаляет истёкшие токены: вызывается при старте сервера."""
        with self.connect() as db:
            db.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (_now(),))

    # ------------------------------------------------------------ user states
    def user_state(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Сохранённое состояние панели пользователя (или None, если не сохранено)."""
        with self.connect() as db:
            row = db.execute(
                "SELECT payload, updated_at FROM user_states WHERE user_id = ?", (user_id,)
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
                "INSERT INTO user_states (user_id, payload, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET payload = excluded.payload, "
                "updated_at = excluded.updated_at",
                (user_id, text, _now()),
            )

    # -------------------------------------------------------------- profiles
    def user_profile(self, user_id: int) -> Dict[str, Any]:
        """Поля профиля игрока; пустой словарь полей, если профиль не заполняли."""
        with self.connect() as db:
            row = db.execute(
                "SELECT display_name, bio, favorite_game, accent, frame, card, status, "
                "CASE WHEN avatar_mime <> '' THEN 1 ELSE 0 END AS has_avatar, updated_at "
                "FROM user_profiles WHERE user_id = ?",
                (int(user_id),),
            ).fetchone()
        if not row:
            return {"display_name": "", "bio": "", "favorite_game": "", "accent": "",
                    "frame": "", "card": "", "status": "", "has_avatar": 0, "updated_at": None}
        data = dict(row)
        data["has_avatar"] = int(data.get("has_avatar") or 0)
        return data

    PROFILE_FIELDS = ("display_name", "bio", "favorite_game", "accent", "frame", "card", "status")

    def save_user_profile(self, user_id: int, values: Dict[str, Any]) -> Dict[str, Any]:
        fields = {name: str(values.get(name) or "") for name in self.PROFILE_FIELDS}
        with self.connect() as db:
            db.execute(
                "INSERT INTO user_profiles (user_id, display_name, bio, favorite_game, accent, "
                "frame, card, status, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET display_name = excluded.display_name, "
                "bio = excluded.bio, favorite_game = excluded.favorite_game, "
                "accent = excluded.accent, frame = excluded.frame, card = excluded.card, "
                "status = excluded.status, updated_at = excluded.updated_at",
                (int(user_id), fields["display_name"], fields["bio"],
                 fields["favorite_game"], fields["accent"], fields["frame"], fields["card"],
                 fields["status"], _now()),
            )
        return self.user_profile(user_id)

    def set_user_avatar(self, user_id: int, mime: str, data: bytes) -> None:
        """Сохраняет картинку профиля (BLOB в той же строке профиля)."""
        with self.connect() as db:
            db.execute(
                "INSERT INTO user_profiles (user_id, avatar_mime, avatar_data, updated_at) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET avatar_mime = excluded.avatar_mime, "
                "avatar_data = excluded.avatar_data, updated_at = excluded.updated_at",
                (int(user_id), str(mime), bytes(data), _now()),
            )

    def clear_user_avatar(self, user_id: int) -> bool:
        with self.connect() as db:
            cursor = db.execute(
                "UPDATE user_profiles SET avatar_mime = '', avatar_data = NULL, updated_at = ? "
                "WHERE user_id = ? AND avatar_mime <> ''",
                (_now(), int(user_id)),
            )
            return cursor.rowcount > 0

    def user_avatar(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Картинка профиля: {"mime": ..., "data": bytes} или None."""
        with self.connect() as db:
            row = db.execute(
                "SELECT avatar_mime AS mime, avatar_data AS data FROM user_profiles "
                "WHERE user_id = ? AND avatar_mime <> ''",
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
                "(SELECT COUNT(*) FROM narutodle_matches WHERE player_ids LIKE ? "
                " OR player1_id = ? OR player2_id = ?) AS narutodle, "
                "(SELECT COUNT(*) FROM csdraft_runs WHERE user_id = ?) AS drafts, "
                "(SELECT COUNT(*) FROM songguess_runs WHERE user_id = ?) AS songguess, "
                "(SELECT COUNT(*) FROM raporder_matches WHERE player1_id = ? "
                " OR player2_id = ?) AS raporder",
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
                "(SELECT COUNT(*) FROM narutodle_matches WHERE player_ids LIKE ? "
                " OR player1_id = ? OR player2_id = ?) AS narutodle_played, "
                "(SELECT COUNT(*) FROM narutodle_matches WHERE winner_id = ?) AS narutodle_wins, "
                "(SELECT COUNT(*) FROM songguess_runs WHERE user_id = ?) AS songguess_runs, "
                "(SELECT COALESCE(MAX(score), 0) FROM songguess_runs WHERE user_id = ?) AS songguess_best, "
                "(SELECT COALESCE(SUM(correct), 0) FROM songguess_runs WHERE user_id = ?) AS songguess_correct, "
                "(SELECT COUNT(*) FROM csdraft_runs WHERE user_id = ?) AS draft_runs, "
                "(SELECT COUNT(*) FROM csdraft_runs WHERE user_id = ? AND champion = 1) AS draft_champions, "
                "(SELECT COUNT(*) FROM raporder_matches WHERE player1_id = ? "
                " OR player2_id = ?) AS raporder_played, "
                "(SELECT COUNT(*) FROM raporder_matches WHERE winner_id = ?) AS raporder_wins",
                (f"%,{uid},%",) + (uid,) * 11,
            ).fetchone()
            # Отдельный запрос: режимы, быстрые победы, коллекция персонажей.
            detail = db.execute(
                "SELECT "
                "(SELECT COUNT(*) FROM narutodle_matches WHERE mode = 'duel' "
                " AND (player_ids LIKE ? OR player1_id = ? OR player2_id = ?)) AS duel, "
                "(SELECT COUNT(*) FROM narutodle_matches WHERE mode = 'race' "
                " AND (player_ids LIKE ? OR player1_id = ? OR player2_id = ?)) AS race, "
                "(SELECT COUNT(*) FROM narutodle_matches WHERE mode = 'teams' "
                " AND (player_ids LIKE ? OR player1_id = ? OR player2_id = ?)) AS teams, "
                "(SELECT COUNT(*) FROM narutodle_matches WHERE winner_id = ? "
                " AND winner_attempts > 0 AND winner_attempts <= 3) AS fast_wins, "
                "(SELECT COUNT(DISTINCT target) FROM narutodle_matches "
                " WHERE winner_id = ? AND target <> '') AS guessed, "
                "(SELECT COUNT(*) FROM narutodle_matches WHERE winner_id IS NOT NULL "
                " AND winner_id <> ? AND (player_ids LIKE ? OR player1_id = ? "
                " OR player2_id = ?)) AS losses",
                (f"%,{uid},%", uid, uid) * 3 + (uid, uid, uid, f"%,{uid},%", uid, uid),
            ).fetchone()
            # Скрытые титулы: разбираем доски из JSON в Python, чтобы одинаково
            # работать и на SQLite, и на PostgreSQL без JSON-функций.
            secret_rows = db.execute(
                "SELECT mode, winner_team, boards_json FROM narutodle_matches "
                "WHERE boards_json <> '' AND player_ids LIKE ?",
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
        data.update(narutodle_secret_metrics([dict(item) for item in secret_rows], uid))
        data.update(songless_metrics_from_runs(self.songless_metric_rows(uid)))
        return data

    def achievements_unlocked(self, user_id: int) -> Dict[str, Any]:
        """Выданные достижения: {"идентификатор": момент выдачи}."""
        with self.connect() as db:
            rows = db.execute(
                "SELECT achievement_id, unlocked_at FROM user_achievements WHERE user_id = ?",
                (int(user_id),),
            ).fetchall()
        return {str(row["achievement_id"]): row["unlocked_at"] for row in rows}

    def achievement_unlock(self, user_id: int, achievement_id: str) -> bool:
        """Выдаёт достижение один раз; True, если оно выдано именно сейчас."""
        with self.connect() as db:
            cursor = db.execute(
                "INSERT INTO user_achievements (user_id, achievement_id, unlocked_at) "
                "VALUES (?, ?, ?) ON CONFLICT(user_id, achievement_id) DO NOTHING",
                (int(user_id), str(achievement_id), _now()),
            )
            return cursor.rowcount > 0

    # ----------------------------------------------------------- secret data
    def secret_data(self) -> List[Dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT id, name, value, updated_at FROM secret_data ORDER BY name"
            ).fetchall()
        return [dict(row) for row in rows]

    def set_secret_data(self, name: str, value: str) -> Dict[str, Any]:
        with self.connect() as db:
            existing = db.execute("SELECT id FROM secret_data WHERE name = ?", (name,)).fetchone()
            if existing:
                db.execute(
                    "UPDATE secret_data SET value = ?, updated_at = ? WHERE id = ?",
                    (value, _now(), existing["id"]),
                )
                entry_id = existing["id"]
            else:
                entry_id = db.execute(
                    "INSERT INTO secret_data (name, value) VALUES (?, ?)", (name, value)
                ).lastrowid
            row = db.execute(
                "SELECT id, name, value, updated_at FROM secret_data WHERE id = ?", (entry_id,)
            ).fetchone()
        return dict(row)

    def delete_secret_data(self, entry_id: int) -> bool:
        with self.connect() as db:
            cursor = db.execute("DELETE FROM secret_data WHERE id = ?", (entry_id,))
            return cursor.rowcount > 0

    # -------------------------------------------------------------- narutodle
    def narutodle_character_count(self) -> int:
        with self.connect() as db:
            row = db.execute("SELECT COUNT(*) AS n FROM narutodle_characters").fetchone()
        return int(row["n"])

    def narutodle_characters(self) -> List[Dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute("SELECT * FROM narutodle_characters ORDER BY name").fetchall()
        return [_character(dict(row)) for row in rows]

    def narutodle_portrait(self, character_id: int) -> str:
        """Картинка персонажа как она лежит в базе (строка data:image/... или путь)."""
        with self.connect() as db:
            row = db.execute(
                "SELECT image FROM narutodle_characters WHERE id = ?", (int(character_id),)
            ).fetchone()
        return str(row["image"] or "") if row else ""

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
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(name) DO UPDATE SET "
                    "gender = excluded.gender, village = excluded.village, clan = excluded.clan, "
                    "nature = excluded.nature, kekkei = excluded.kekkei, "
                    "jinchuriki = excluded.jinchuriki, debut = excluded.debut, "
                    "color = CASE WHEN excluded.color <> '' THEN excluded.color "
                    "ELSE narutodle_characters.color END, "
                    "image = CASE WHEN excluded.image <> '' THEN excluded.image "
                    "ELSE narutodle_characters.image END, "
                    "updated_at = excluded.updated_at",
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
                        _now(),
                    ),
                )
                saved += 1
        return saved

    def narutodle_set_image(self, name: str, image: str) -> bool:
        """Привязывает картинку к персонажу (пустая строка — снова аватар)."""
        with self.connect() as db:
            cursor = db.execute(
                "UPDATE narutodle_characters SET image = ?, updated_at = ? WHERE name = ?",
                (image, _now(), name),
            )
            return cursor.rowcount > 0

    def narutodle_add_match(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Пишет партию в журнал и возвращает строку с присвоенным идентификатором."""
        player_ids = [int(value) for value in (record.get("player_ids") or [])
                      if value is not None]
        ids_text = "," + ",".join(str(value) for value in player_ids) + "," if player_ids else ""
        with self.connect() as db:
            entry_id = db.execute(
                "INSERT INTO narutodle_matches (room, round_number, mode, target, players, "
                "player_ids, player1_id, player1_name, player2_id, player2_name, winner_id, "
                "winner_name, loser_name, winner_attempts, loser_attempts, winner_team, "
                "boards_json, reason, played_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                    _now(),
                ),
            ).lastrowid
            row = db.execute("SELECT * FROM narutodle_matches WHERE id = ?", (entry_id,)).fetchone()
        return _match(dict(row))

    def narutodle_matches(self, user_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Журнал матчей: с участием игрока или все подряд (для администратора)."""
        size = max(1, min(int(limit), 500))
        with self.connect() as db:
            if user_id is None:
                rows = db.execute(
                    "SELECT * FROM narutodle_matches ORDER BY id DESC LIMIT ?", (size,)
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT * FROM narutodle_matches WHERE player_ids LIKE ? "
                    "OR player1_id = ? OR player2_id = ? ORDER BY id DESC LIMIT ?",
                    (f"%,{int(user_id)},%", int(user_id), int(user_id), size),
                ).fetchall()
        return [_match(dict(row)) for row in rows]

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
        return [_track(dict(row)) for row in rows]

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
                    "clip_start, clip_length, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(track_key) DO UPDATE SET "
                    "anime = excluded.anime, song = excluded.song, artist = excluded.artist, "
                    "year = excluded.year, "
                    "cover = CASE WHEN excluded.cover <> '' THEN excluded.cover "
                    "ELSE songless_tracks.cover END, "
                    "video = CASE WHEN excluded.video <> '' THEN excluded.video "
                    "ELSE songless_tracks.video END, "
                    "updated_at = excluded.updated_at",
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
                        _now(),
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
        fields = ["audio = ?", "updated_at = ?"]
        values: List[Any] = [audio, _now()]
        if clip_start is not None:
            fields.append("clip_start = ?")
            values.append(float(clip_start))
        if clip_length is not None:
            fields.append("clip_length = ?")
            values.append(float(clip_length))
        where = "track_key = ?" if track_key is not None else "anime = ?"
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
        fields = ["updated_at = ?"]
        values: List[Any] = [_now()]
        if clip_start is not None:
            fields.append("clip_start = ?")
            values.append(float(clip_start))
        if clip_length is not None:
            fields.append("clip_length = ?")
            values.append(float(clip_length))
        where = "track_key = ?" if track_key is not None else "anime = ?"
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
            cursor = db.execute("DELETE FROM songless_tracks WHERE anime = ?", (anime,))
            return cursor.rowcount > 0

    def songless_add_run(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Пишет итог захода/партии «Аниме-сонглесса» для достижений."""
        detail = record.get("detail") or []
        with self.connect() as db:
            entry_id = db.execute(
                "INSERT INTO songless_runs (username, user_id, mode, rounds, correct, "
                "score, perfect, fast, place, winner, detail, played_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                    _now(),
                ),
            ).lastrowid
            row = db.execute("SELECT * FROM songless_runs WHERE id = ?", (entry_id,)).fetchone()
        return dict(row)

    def songless_metric_rows(self, user_id: int) -> List[Dict[str, Any]]:
        """Заходы игрока для метрик достижений (detail разбирается в Python)."""
        with self.connect() as db:
            rows = db.execute(
                "SELECT rounds, correct, score, perfect, fast, winner, detail "
                "FROM songless_runs WHERE user_id = ?",
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
            where.append("mode = ?")
            params.append(mode)
        if since is not None:
            where.append("played_at >= ?")
            params.append(_iso(since))
        params.append(size)
        with self.connect() as db:
            rows = db.execute(
                "SELECT MAX(username) AS username, user_id, MAX(score) AS best, "
                "SUM(correct) AS correct, COUNT(1) AS games "
                "FROM songless_runs WHERE " + " AND ".join(where) + " "
                "GROUP BY user_id "
                "ORDER BY best DESC, correct DESC, games ASC LIMIT ?",
                tuple(params),
            ).fetchall()
        return [dict(row) for row in rows]

    # ------------------------------------------------- драфт-рогалики (игры)
    def csdraft_pack_count(self, game: Optional[str] = None) -> int:
        with self.connect() as db:
            if game:
                row = db.execute("SELECT COUNT(*) AS n FROM csdraft_packs WHERE game = ?",
                                 (str(game),)).fetchone()
            else:
                row = db.execute("SELECT COUNT(*) AS n FROM csdraft_packs").fetchone()
        return int(row["n"])

    def csdraft_packs(self, game: Optional[str] = None) -> List[Dict[str, Any]]:
        """Паки одной игры (или всех): источник правды для движка драфта."""
        with self.connect() as db:
            if game:
                rows = db.execute(
                    "SELECT * FROM csdraft_packs WHERE game = ? ORDER BY era, year, id",
                    (str(game),)).fetchall()
            else:
                rows = db.execute("SELECT * FROM csdraft_packs ORDER BY game, era, year, id").fetchall()
        return [_pack_row(dict(row)) for row in rows]

    def csdraft_save_packs(self, rows: Iterable[Dict[str, Any]]) -> int:
        """Добавляет и обновляет паки (по идентификатору): ими правит владелец сайта."""
        saved = 0
        with self.connect() as db:
            for row in rows:
                db.execute(
                    "INSERT INTO csdraft_packs (id, game, team, event, year, place, major, region, "
                    "era, maps, players, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
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
                        1 if row.get("major") else 0,
                        str(row.get("region") or ""),
                        str(row.get("era") or "legacy"),
                        json.dumps(list(row.get("maps") or ()), ensure_ascii=False),
                        json.dumps(list(row.get("players") or ()), ensure_ascii=False),
                        _now(),
                    ),
                )
                saved += 1
        return saved

    def csdraft_delete_pack(self, pack_id: str) -> bool:
        with self.connect() as db:
            cursor = db.execute("DELETE FROM csdraft_packs WHERE id = ?", (str(pack_id),))
            return cursor.rowcount > 0

    def csdraft_add_run(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Пишет прогон в журнал: кто играл, каким составом и чем закончилось."""
        with self.connect() as db:
            entry_id = db.execute(
                "INSERT INTO csdraft_runs (game, username, user_id, difficulty, era, champion, "
                "wins, losses, stage, rating, squad, packs, score, played_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(record.get("game") or "cs"),
                    str(record.get("username") or ""),
                    record.get("user_id"),
                    str(record.get("difficulty") or "hard"),
                    str(record.get("era") or "legacy"),
                    1 if record.get("champion") else 0,
                    int(record.get("wins") or 0),
                    int(record.get("losses") or 0),
                    str(record.get("stage") or ""),
                    float(record.get("rating") or 0),
                    str(record.get("squad") or ""),
                    str(record.get("packs") or ""),
                    str(record.get("score") or ""),
                    _now(),
                ),
            ).lastrowid
            row = db.execute("SELECT * FROM csdraft_runs WHERE id = ?", (entry_id,)).fetchone()
        return _run_row(dict(row))

    def csdraft_runs(self, user_id: Optional[int] = None, limit: int = 50,
                     game: Optional[str] = None) -> List[Dict[str, Any]]:
        """Журнал прогонов: свои или все подряд (для администратора), по игре или всем."""
        size = max(1, min(int(limit), 500))
        where: List[str] = []
        values: List[Any] = []
        if game:
            where.append("game = ?")
            values.append(str(game))
        if user_id is not None:
            where.append("user_id = ?")
            values.append(int(user_id))
        condition = f" WHERE {' AND '.join(where)}" if where else ""
        with self.connect() as db:
            rows = db.execute(
                f"SELECT * FROM csdraft_runs{condition} ORDER BY id DESC LIMIT ?",
                (*values, size),
            ).fetchall()
        return [_run_row(dict(row)) for row in rows]

    def csdraft_run_count(self, game: Optional[str] = None) -> int:
        with self.connect() as db:
            if game:
                row = db.execute("SELECT COUNT(*) AS n FROM csdraft_runs WHERE game = ?",
                                 (str(game),)).fetchone()
            else:
                row = db.execute("SELECT COUNT(*) AS n FROM csdraft_runs").fetchone()
        return int(row["n"])

    # ------------------------------------------------- «322-0» (драфт по Dota)
    def dotadraft_player_count(self) -> int:
        with self.connect() as db:
            row = db.execute("SELECT COUNT(*) AS n FROM dotadraft_players").fetchone()
        return int(row["n"])

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
                    "VALUES (?, ?, ?, ?, ?) "
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
                        _now(),
                    ),
                )
                saved += 1
        return saved

    def dotadraft_set_player_position(self, player_id: str, position: int) -> bool:
        """Своя позиция игрока (0 — сбросить): правка пула на ходу."""
        with self.connect() as db:
            cursor = db.execute(
                "UPDATE dotadraft_players SET position = ?, updated_at = ? WHERE id = ?",
                (int(position or 0), _now(), str(player_id)),
            )
            return cursor.rowcount > 0

    def dotadraft_delete_player(self, player_id: str) -> bool:
        with self.connect() as db:
            cursor = db.execute("DELETE FROM dotadraft_players WHERE id = ?", (str(player_id),))
            return cursor.rowcount > 0

    def dotadraft_hero_count(self) -> int:
        with self.connect() as db:
            row = db.execute("SELECT COUNT(*) AS n FROM dotadraft_heroes").fetchone()
        return int(row["n"])

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
                    "VALUES (?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(id) DO UPDATE SET name = excluded.name, "
                    "name_en = excluded.name_en, position = excluded.position, "
                    "rating = excluded.rating, updated_at = excluded.updated_at",
                    (
                        hero_id,
                        str(row.get("name") or hero_id),
                        str(row.get("name_en") or ""),
                        int(row.get("position") or 1),
                        int(row.get("rating") or 0),
                        _now(),
                    ),
                )
                saved += 1
        return saved

    def dotadraft_delete_hero(self, hero_id: str) -> bool:
        with self.connect() as db:
            cursor = db.execute("DELETE FROM dotadraft_heroes WHERE id = ?", (str(hero_id),))
            return cursor.rowcount > 0

    def dotadraft_player_hero_count(self) -> int:
        with self.connect() as db:
            row = db.execute("SELECT COUNT(*) AS n FROM dotadraft_player_heroes").fetchone()
        return int(row["n"])

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
                    "(player_id, hero_id, rating, updated_at) VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(player_id, hero_id) DO UPDATE SET "
                    "rating = excluded.rating, updated_at = excluded.updated_at",
                    (player_id, hero_id, int(row.get("rating") or 0), _now()),
                )
                saved += 1
        return saved

    def dotadraft_delete_player_hero(self, player_id: str, hero_id: str) -> bool:
        with self.connect() as db:
            cursor = db.execute(
                "DELETE FROM dotadraft_player_heroes WHERE player_id = ? AND hero_id = ?",
                (str(player_id), str(hero_id)),
            )
            return cursor.rowcount > 0

    # ----------------------------------- «Угадай песню за 10 секунд» (песни)
    def songguess_track_count(self, category: Optional[str] = None) -> int:
        with self.connect() as db:
            if category:
                row = db.execute("SELECT COUNT(*) AS n FROM songguess_tracks WHERE category = ?",
                                 (str(category),)).fetchone()
            else:
                row = db.execute("SELECT COUNT(*) AS n FROM songguess_tracks").fetchone()
        return int(row["n"])

    def songguess_tracks(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Песни одной темы (или всех): источник правды для движка игры."""
        with self.connect() as db:
            if category:
                rows = db.execute(
                    "SELECT * FROM songguess_tracks WHERE category = ? ORDER BY title, artist",
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
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
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
                        _now(),
                    ),
                )
                saved += 1
        return saved

    def songguess_set_audio(self, track_id: str, audio: str,
                            clip_start: Optional[float] = None,
                            clip_length: Optional[float] = None) -> bool:
        """Привязывает запись к песне; пустая строка — снова «без записи»."""
        fields = ["audio = ?", "updated_at = ?"]
        values: List[Any] = [str(audio), _now()]
        if clip_start is not None:
            fields.append("clip_start = ?")
            values.append(float(clip_start))
        if clip_length is not None:
            fields.append("clip_length = ?")
            values.append(float(clip_length))
        values.append(str(track_id))
        with self.connect() as db:
            cursor = db.execute(
                "UPDATE songguess_tracks SET " + ", ".join(fields) + " WHERE id = ?",
                tuple(values),
            )
            return cursor.rowcount > 0

    def songguess_delete_track(self, track_id: str) -> bool:
        """Убирает песню из набора (например, чтобы удалить лишнюю строку)."""
        with self.connect() as db:
            cursor = db.execute("DELETE FROM songguess_tracks WHERE id = ?", (str(track_id),))
            return cursor.rowcount > 0

    def songguess_add_run(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Пишет заход в журнал: кто играл, в какой теме и с каким счётом."""
        with self.connect() as db:
            entry_id = db.execute(
                "INSERT INTO songguess_runs (username, user_id, category, difficulty, seconds,"
                " rounds, correct, score, fastest, detail, played_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                    _now(),
                ),
            ).lastrowid
            row = db.execute("SELECT * FROM songguess_runs WHERE id = ?", (entry_id,)).fetchone()
        return _songguess_run(dict(row))

    def songguess_matches(self, user_id: Optional[int] = None, limit: int = 50,
                          category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Журнал заходов: свои или все подряд (для администратора), по теме или всем."""
        size = max(1, min(int(limit), 500))
        where: List[str] = []
        values: List[Any] = []
        if category:
            where.append("category = ?")
            values.append(str(category))
        if user_id is not None:
            where.append("user_id = ?")
            values.append(int(user_id))
        condition = f" WHERE {' AND '.join(where)}" if where else ""
        with self.connect() as db:
            rows = db.execute(
                f"SELECT * FROM songguess_runs{condition} ORDER BY id DESC LIMIT ?",
                (*values, size),
            ).fetchall()
        return [_songguess_run(dict(row)) for row in rows]

    def songguess_run_count(self, category: Optional[str] = None) -> int:
        with self.connect() as db:
            if category:
                row = db.execute("SELECT COUNT(*) AS n FROM songguess_runs WHERE category = ?",
                                 (str(category),)).fetchone()
            else:
                row = db.execute("SELECT COUNT(*) AS n FROM songguess_runs").fetchone()
        return int(row["n"])

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
                "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(game, track_key) DO UPDATE SET mime = excluded.mime, "
                "duration_ms = excluded.duration_ms, source = excluded.source, "
                "data = excluded.data, updated_at = excluded.updated_at",
                (
                    str(game),
                    str(track_key),
                    str(mime or "audio/mpeg"),
                    int(duration_ms or 0),
                    str(source or ""),
                    sqlite3.Binary(bytes(data)),
                    _now(),
                ),
            )

    def audio_clip_get(self, game: str, track_key: str) -> Optional[Dict[str, Any]]:
        """Достаёт аудиофрагмент: байты, тип и длительность (None, если его нет)."""
        with self.connect() as db:
            row = db.execute(
                "SELECT mime, duration_ms, source, data, updated_at FROM audio_clips "
                "WHERE game = ? AND track_key = ?",
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
            "updated_at": row["updated_at"],
            "data": bytes(data) if data is not None else b"",
        }

    def audio_clip_has(self, game: str, track_key: str) -> bool:
        with self.connect() as db:
            row = db.execute(
                "SELECT 1 AS ok FROM audio_clips WHERE game = ? AND track_key = ? LIMIT 1",
                (str(game), str(track_key)),
            ).fetchone()
        return bool(row)

    def audio_clip_keys(self, game: str) -> List[str]:
        """Ключи треков, у которых уже есть запись в базе (для отчётов и пропусков)."""
        with self.connect() as db:
            rows = db.execute(
                "SELECT track_key FROM audio_clips WHERE game = ? ORDER BY track_key",
                (str(game),),
            ).fetchall()
        return [str(row["track_key"]) for row in rows]

    def audio_clip_delete(self, game: str, track_key: str) -> bool:
        with self.connect() as db:
            cursor = db.execute(
                "DELETE FROM audio_clips WHERE game = ? AND track_key = ?",
                (str(game), str(track_key)),
            )
            return cursor.rowcount > 0

    # ------------------------------------------- «Рэп-хронология» (порядок лет)
    def raporder_track_count(self) -> int:
        with self.connect() as db:
            row = db.execute("SELECT COUNT(*) AS n FROM raporder_tracks").fetchone()
        return int(row["n"])

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
                    "VALUES (?, ?, ?, ?, ?) "
                    "ON CONFLICT(id) DO UPDATE SET artist = excluded.artist, "
                    "title = excluded.title, year = excluded.year, updated_at = excluded.updated_at",
                    (
                        str(row.get("id") or ""),
                        str(row.get("artist") or ""),
                        str(row.get("title") or ""),
                        int(row.get("year") or 0),
                        _now(),
                    ),
                )
                saved += 1
        return saved

    def raporder_delete_track(self, track_id: str) -> bool:
        with self.connect() as db:
            cursor = db.execute("DELETE FROM raporder_tracks WHERE id = ?", (str(track_id),))
            return cursor.rowcount > 0

    def raporder_add_match(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Пишет партию в журнал: кто играл, в каком режиме и чем закончилось."""
        with self.connect() as db:
            entry_id = db.execute(
                "INSERT INTO raporder_matches (mode, room, rounds, player1_id, player1_name, "
                "player1_score, player2_id, player2_name, player2_score, winner_id, winner_name, "
                "detail, played_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                    _now(),
                ),
            ).lastrowid
            row = db.execute("SELECT * FROM raporder_matches WHERE id = ?",
                             (entry_id,)).fetchone()
        return _rap_match(dict(row))

    def raporder_matches(self, user_id: Optional[int] = None, limit: int = 50,
                         mode: Optional[str] = None) -> List[Dict[str, Any]]:
        """Журнал партий: свои (как игрок или соперник) или все подряд для админа."""
        size = max(1, min(int(limit), 500))
        where: List[str] = []
        values: List[Any] = []
        if user_id is not None:
            where.append("(player1_id = ? OR player2_id = ?)")
            values.extend([int(user_id), int(user_id)])
        if mode:
            where.append("mode = ?")
            values.append(str(mode))
        condition = f" WHERE {' AND '.join(where)}" if where else ""
        with self.connect() as db:
            rows = db.execute(
                f"SELECT * FROM raporder_matches{condition} ORDER BY id DESC LIMIT ?",
                (*values, size),
            ).fetchall()
        return [_rap_match(dict(row)) for row in rows]

    def raporder_match_count(self) -> int:
        with self.connect() as db:
            row = db.execute("SELECT COUNT(*) AS n FROM raporder_matches").fetchone()
        return int(row["n"])


# Любой из поддерживаемых бэкендов: SQLite (Database) или PostgreSQL (PostgresDatabase).
DatabaseLike = Union[Database, "PostgresDatabase"]

# Канал к плате: напрямую по COM-порту (ArduinoLink) либо через домашнего
# агента, когда сервер стоит на VPS (RemoteDeviceLink). Набор методов общий.
DeviceLink = Union["ArduinoLink", "RemoteDeviceLink"]


def open_database(path: str | Path | None = None, dsn: Optional[str] = None) -> DatabaseLike:
    """Выбирает бэкенд: при заданном DSN — PostgreSQL, иначе SQLite-файл."""
    if dsn:
        try:
            from .db_postgres import PostgresDatabase
        except ImportError:
            from db_postgres import PostgresDatabase  # type: ignore

        return PostgresDatabase(dsn)
    if path is None:
        raise ValueError("Не указан ни путь к файлу SQLite (path), ни строка подключения (dsn)")
    return Database(path)
