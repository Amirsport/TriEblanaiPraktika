# -*- coding: utf-8 -*-
"""Сервер «Умной AI-Теплицы»: REST API + автоматика + раздача PWA-фронтенда.

Запуск:
    python backend/server.py                          # эмулятор датчиков, порт 8000
    python backend/server.py --serial COM3            # реальная Arduino
    python backend/server.py --port 8000 --db data/greenhouse.sqlite3
    python backend/server.py --dsn postgresql://greenhouse:пароль@localhost:5432/greenhouse

Бэкенд БД выбирается ключом --dsn (или переменной окружения GREENHOUSE_DSN):
с DSN данные идут в PostgreSQL, без него — в файл SQLite.

Доступ к API закрывается ключом --token (или GREENHOUSE_TOKEN): тогда все
запросы /api/* требуют заголовок X-Api-Token либо параметр ?token=...
Исключение — разделы /api/auth/*, /api/admin/* и /api/secret/*: они защищены
паролем пользователя (Bearer-токен), иначе войти было бы невозможно.
Так же работает раздел игр /api/games/*: в него пускает аккаунт (Bearer),
а общий ключ не нужен — иначе он попал бы в ссылку-приглашение другу.

Учётные записи панели хранятся в таблице users (пароли — PBKDF2-SHA256),
токены входа — в auth_sessions, состояние панели пользователя — в user_states.
Регистрация в панели свободная: любой может создать себе аккаунт, роль всегда
«user». При первом запуске дополнительно создаётся администратор admin: пароль
берётся из GREENHOUSE_ADMIN_PASSWORD, иначе генерируется и печатается в консоль.
Секретная страница данных: /TriEblanaiPraktika (файл front/TriEblanaiPraktika).

API (JSON):
    GET  /api/health                     состояние сервиса
    GET  /api/state                      полное состояние (12 участков + агрегаты)
    GET  /api/zones                      список участков
    GET  /api/zones/<id>                 один участок
    GET  /api/zones/<id>/history?limit=  история показаний участка
    GET  /api/history?zone_id=&limit=    история (все или один участок)
    GET  /api/logs?limit=&level=         журнал событий
    GET  /api/settings                   глобальные настройки
    GET  /api/arduino                    статус канала с платой
    POST /api/devices                    {"zone_id":1,"device":"watering","on":true,"seconds":10}
    POST /api/settings                   {"moisture_target":55,...}
    POST /api/mode                       {"mode":"auto|eco|boost|manual"}
    POST /api/logs/clear                 очистить журнал
    POST /api/auth/login                 {"username":"...","password":"..."} → токен и состояние
    POST /api/auth/register              {"username":"...","password":"..."} свободная регистрация
    POST /api/auth/logout                (Bearer) завершить сессию
    GET  /api/auth/me                    (Bearer) текущий пользователь и его состояние
    GET  /api/auth/state                 (Bearer) сохранённое состояние панели
    POST /api/auth/state                 (Bearer) {"...": "..."} сохранить состояние
    POST /api/auth/password              (Bearer) {"current":"...","new":"..."} смена пароля
    GET  /api/admin/users                (admin) список аккаунтов
    POST /api/admin/users                (admin) {"username":"...","password":"...","role":"user"}
    POST /api/admin/users/<id>/password  (admin) {"new":"..."} сброс пароля
    DELETE /api/admin/users/<id>         (admin) удалить аккаунт (кроме последнего админа)
    GET  /api/secret/data                записи секретной страницы
    POST /api/secret/data                (admin) {"name":"...","value":"..."} создать/обновить
    DELETE /api/secret/data/<id>         (admin) удалить запись

Игры (Bearer-токен аккаунта, без общего ключа):
    GET  /api/games/narutodle/characters           набор персонажей, графы и режимы
    GET  /api/games/narutodle/portrait/<id>        портрет персонажа (картинка, кэшируется)
    GET  /api/games/narutodle/matches?limit=&scope= журнал матчей: свои или все (admin)
    POST /api/games/narutodle/rooms                создать комнату-лобби до 6 игроков
    POST /api/games/narutodle/rooms/<код>/join     занять место в лобби
    POST /api/games/narutodle/rooms/<код>/leave    выйти из комнаты
    POST /api/games/narutodle/rooms/<код>/mode     {"mode":"duel|race|teams"} — режим (хозяин)
    POST /api/games/narutodle/rooms/<код>/team     {"total":9} — сколько персонажей на команду (хозяин)
    POST /api/games/narutodle/rooms/<код>/side     {"team":"a|b"} — перейти в другую команду в лобби
    POST /api/games/narutodle/rooms/<код>/start    начать игру (хозяин)
    POST /api/games/narutodle/rooms/<код>/lobby    вернуться в лобби после партии
    GET  /api/games/narutodle/rooms/<код>          состояние комнаты (опрос страницей)
    GET  /api/games/narutodle/rooms/<код>/watch    наблюдение за комнатой
    POST /api/games/narutodle/rooms/<код>/guess    {"name":"..."} догадка
    POST /api/games/narutodle/rooms/<код>/giveup   сдаться
    POST /api/games/narutodle/rooms/<код>/rematch  новая партия

Игры «Аниме-сонглесс» (тоже по аккаунту):
    GET  /api/games/songless/status                 сколько треков и что можно играть
    POST /api/games/songless/solo                   начать соло-заход
    GET  /api/games/songless/solo/<id>              состояние захода
    POST /api/games/songless/solo/<id>/answer       {"choice": номер варианта}
    GET  /api/games/songless/solo/<id>/clip?round=  фрагмент текущего раунда
    POST /api/games/songless/rooms                  создать комнату
    POST /api/games/songless/rooms/<код>/join       войти в комнату
    POST /api/games/songless/rooms/<код>/start      начать партию (хозяин комнаты)
    GET  /api/games/songless/rooms/<код>            состояние партии (опрос страницей)
    POST /api/games/songless/rooms/<код>/answer     {"choice": номер варианта}
    POST /api/games/songless/rooms/<код>/rematch    новая партия
    GET  /api/games/songless/rooms/<код>/clip?round= фрагмент текущего раунда

Игра «87-0» (драфт-рогалик по Counter-Strike, тоже по аккаунту):
    GET  /api/games/csdraft/status                сколько составов, эпохи, сложности, роли
    POST /api/games/csdraft/runs                  начать прогон: {"difficulty","era","assign"}
    GET  /api/games/csdraft/runs/<id>             состояние прогона (опрос страницей)
    POST /api/games/csdraft/runs/<id>/take        {"player":"ник","role":"awp"} взять игрока
    POST /api/games/csdraft/runs/<id>/map         {"map":"Inferno"} карту в свой маппул
    POST /api/games/csdraft/runs/<id>/pack        следующий состав (реролл не тратится)
    POST /api/games/csdraft/runs/<id>/reroll      другой состав за реролл
    POST /api/games/csdraft/runs/<id>/assign      {"mode":"auto|manual"} способ расстановки
    POST /api/games/csdraft/runs/<id>/auto        расставить роли автоматически
    POST /api/games/csdraft/runs/<id>/play        играть стадию мейджора
    POST /api/games/csdraft/runs/<id>/boost       {"index":0..2} выбрать усиление
    GET  /api/games/csdraft/matches?limit=&scope= журнал прогонов: свои; scope=all — все (admin)

Другие драфт-игры («13-0» по Valorant, «4-0» по Rocket League) — тот же движок
и тот же набор действий, но адрес с ключом игры; «cs» — псевдоним «87-0»:
    GET  /api/games/draft/games                   список игр и их правила
    GET  /api/games/draft/<игра>/status           набор паков игры и её правила
    POST /api/games/draft/<игра>/runs             начать прогон
    GET  /api/games/draft/<игра>/runs/<id>        состояние прогона
    .../runs/<id>/take|map|pack|reroll|assign|auto|play|boost  — как у «87-0»
    GET  /api/games/draft/<игра>/matches?limit=   журнал прогонов игры

Домашний агент (только устройство-токен, режим --device-remote): когда сервер
стоит на VPS, а Arduino осталась дома, COM-порт держит agent (device_agent.py):
    POST /api/device/sync                показания агента → очередь команд к плате
    POST /api/device/ack                 {"applied":[1,2],"errors":{"3":"текст"}}
    GET  /api/device/status              состояние канала «сервер ↔ дом»
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hmac
import json
import mimetypes
import os
import re
import secrets
import sys
import threading
import time
import webbrowser
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

try:  # запуск как модуль: python -m backend.server
    from .auth import (
        ROLES, SESSION_DAYS, hash_password, new_token, normalize_username, public_user,
        validate_password, validate_role, validate_username, verify_password,
    )
    from .db import DEFAULT_SETTINGS, DEVICES, ZONE_COUNT, DatabaseLike, DeviceLink, open_database
    from .arduino import ArduinoLink
    from .device_link import RemoteDeviceLink
    from .csdraft import (
        ASSIGN_MODES,
        DIFFICULTIES,
        DIFFICULTY_LABELS,
        DIFFICULTY_REROLLS,
        Csdraft,
        CsdraftError,
    )
    from .draft_games import GAME_KEYS, game_block, games_block, seed_rows_for
    from .dotadraft import (
        DIFFICULTIES as DOTA_DIFFICULTIES,
        DIFFICULTY_BUDGETS as DOTA_BUDGETS,
        DIFFICULTY_LABELS as DOTA_DIFFICULTY_LABELS,
        DotaDraft,
        DotaDraftError,
    )
    from .dotadraft_data import (
        BUDGET as DOTA_BUDGET,
        GROUP_BEST_OF as DOTA_GROUP_BEST_OF,
        GROUPS as DOTA_GROUPS,
        GROUP_SIZE as DOTA_GROUP_SIZE,
        MID_COST_LIMIT as DOTA_MID_COST_LIMIT,
        MID_POSITION as DOTA_MID_POSITION,
        OPPONENT_BUDGET_MAX as DOTA_OPPONENT_MAX,
        OPPONENT_BUDGET_MIN as DOTA_OPPONENT_MIN,
        PACK_HEROES as DOTA_PACK_HEROES,
        PACK_PLAYERS as DOTA_PACK_PLAYERS,
        POSITION_HINTS as DOTA_POSITION_HINTS,
        POSITION_LABELS as DOTA_POSITION_LABELS,
        SQUAD_SIZE as DOTA_SQUAD_SIZE,
        hero_rows as dotadraft_hero_rows,
        player_rows as dotadraft_player_rows,
    )
    from .narutodle import (
        MAX_ATTEMPTS as NARUTODLE_MAX_ATTEMPTS,
        MAX_PLAYERS as NARUTODLE_MAX_PLAYERS,
        Narutodle,
        NarutodleError,
    )
    from .narutodle_data import attribute_list, seed_rows
    from .raporder import (
        ANSWER_SECONDS as RAP_ANSWER_SECONDS,
        DUEL_ROUNDS,
        MAX_PLAYERS as RAP_MAX_PLAYERS,
        MIN_PLAYERS as RAP_MIN_PLAYERS,
        ROUNDS_PER_GAME as RAP_ROUNDS,
        RapOrder,
        RapOrderError,
    )
    from .raporder_data import seed_rows as raporder_seed_rows
    from .raporder_data import TRACKS_PER_ROUND as RAP_TRACKS_PER_ROUND
    from .songguess import SongGuess, SongGuessError
    from .songguess_data import (
        CATEGORIES as SONGGUESS_CATEGORIES,
        DIFFICULTIES as SONGGUESS_DIFFICULTIES,
        ROUNDS_PER_GAME as SONGGUESS_ROUNDS,
        SLICE_SECONDS as SONGGUESS_SLICE,
        seed_rows as songguess_seed_rows,
    )
    from .songless import (
        ANSWER_SECONDS,
        MAX_PLAYERS,
        MIN_PLAYERS,
        ROUNDS_PER_GAME,
        SOLO_LIVES,
        Songless,
        SonglessError,
    )
    from .songless_data import seed_rows as songless_seed_rows
except ImportError:  # запуск как файл: python backend/server.py
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from auth import (  # type: ignore
        ROLES, SESSION_DAYS, hash_password, new_token, normalize_username, public_user,
        validate_password, validate_role, validate_username, verify_password,
    )
    from db import (  # type: ignore
        DEFAULT_SETTINGS, DEVICES, ZONE_COUNT, DatabaseLike, DeviceLink, open_database,
    )
    from arduino import ArduinoLink  # type: ignore
    from device_link import RemoteDeviceLink  # type: ignore
    from csdraft import (  # type: ignore
        ASSIGN_MODES,
        DIFFICULTIES,
        DIFFICULTY_LABELS,
        DIFFICULTY_REROLLS,
        Csdraft,
        CsdraftError,
    )
    from draft_games import GAME_KEYS, game_block, games_block, seed_rows_for  # type: ignore
    from dotadraft import (  # type: ignore
        DIFFICULTIES as DOTA_DIFFICULTIES,
        DIFFICULTY_BUDGETS as DOTA_BUDGETS,
        DIFFICULTY_LABELS as DOTA_DIFFICULTY_LABELS,
        DotaDraft,
        DotaDraftError,
    )
    from dotadraft_data import (  # type: ignore
        BUDGET as DOTA_BUDGET,
        GROUP_BEST_OF as DOTA_GROUP_BEST_OF,
        GROUPS as DOTA_GROUPS,
        GROUP_SIZE as DOTA_GROUP_SIZE,
        MID_COST_LIMIT as DOTA_MID_COST_LIMIT,
        MID_POSITION as DOTA_MID_POSITION,
        OPPONENT_BUDGET_MAX as DOTA_OPPONENT_MAX,
        OPPONENT_BUDGET_MIN as DOTA_OPPONENT_MIN,
        PACK_HEROES as DOTA_PACK_HEROES,
        PACK_PLAYERS as DOTA_PACK_PLAYERS,
        POSITION_HINTS as DOTA_POSITION_HINTS,
        POSITION_LABELS as DOTA_POSITION_LABELS,
        SQUAD_SIZE as DOTA_SQUAD_SIZE,
        hero_rows as dotadraft_hero_rows,
        player_rows as dotadraft_player_rows,
    )
    from narutodle import (  # type: ignore
        MAX_ATTEMPTS as NARUTODLE_MAX_ATTEMPTS,
        MAX_PLAYERS as NARUTODLE_MAX_PLAYERS,
        Narutodle,
        NarutodleError,
    )
    from narutodle_data import attribute_list, seed_rows  # type: ignore
    from raporder import (  # type: ignore
        ANSWER_SECONDS as RAP_ANSWER_SECONDS,
        DUEL_ROUNDS,
        MAX_PLAYERS as RAP_MAX_PLAYERS,
        MIN_PLAYERS as RAP_MIN_PLAYERS,
        ROUNDS_PER_GAME as RAP_ROUNDS,
        RapOrder,
        RapOrderError,
    )
    from raporder_data import seed_rows as raporder_seed_rows  # type: ignore
    from raporder_data import TRACKS_PER_ROUND as RAP_TRACKS_PER_ROUND  # type: ignore
    from songless import (  # type: ignore
        ANSWER_SECONDS,
        MAX_PLAYERS,
        MIN_PLAYERS,
        ROUNDS_PER_GAME,
        SOLO_LIVES,
        Songless,
        SonglessError,
    )
    from songguess import SongGuess, SongGuessError  # type: ignore
    from songguess_data import (  # type: ignore
        CATEGORIES as SONGGUESS_CATEGORIES,
        DIFFICULTIES as SONGGUESS_DIFFICULTIES,
        ROUNDS_PER_GAME as SONGGUESS_ROUNDS,
        SLICE_SECONDS as SONGGUESS_SLICE,
        seed_rows as songguess_seed_rows,
    )
    from songless_data import seed_rows as songless_seed_rows  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
FRONT = ROOT / "front"
DEFAULT_DB = ROOT / "data" / "greenhouse.sqlite3"

# Логин администратора, который создаётся при первом запуске сервера.
ADMIN_NAME = "admin"

# Ограничитель попыток входа и регистрации: не больше N за окно, в расчёте на адрес.
AUTH_ATTEMPTS = 10
AUTH_WINDOW_SECONDS = 60

# Игровые действия лимитируются отдельно и мягче: через туннель все игроки
# приходят с одного адреса, и общий счётчик входа им мешал бы.
GAME_ATTEMPTS = 30
GAME_WINDOW_SECONDS = 60

# Типы записей, которые принимает «Аниме-сонглесс» (по расширению файла).
AUDIO_TYPES = {
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".mp4": "audio/mp4",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".opus": "audio/ogg",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".webm": "audio/webm",
}

MODE_PRESETS: Dict[str, Optional[Dict[str, Any]]] = {
    "auto": {"moisture_target": 55, "moisture_threshold": 35, "temperature_threshold": 30, "light_threshold": 8000},
    "eco": {"moisture_target": 45, "moisture_threshold": 28, "temperature_threshold": 32, "light_threshold": 5000},
    "boost": {"moisture_target": 65, "moisture_threshold": 45, "temperature_threshold": 27, "light_threshold": 12000},
    "manual": None,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Application:
    """Связывает БД, канал Arduino и правила автоматики."""

    def __init__(self, db: DatabaseLike, arduino: DeviceLink, token: Optional[str] = None):
        self.db = db
        self.arduino = arduino
        # В режиме агента COM-порт держит домашний ПК: раздел /api/device/* открыт
        # ему одному, поэтому ссылку на канал храним отдельно.
        self.device_link: Optional[RemoteDeviceLink] = (
            arduino if isinstance(arduino, RemoteDeviceLink) else None)
        self.token = token or None
        self._timers: Dict[Tuple[int, str], float] = {}
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._zone_names = {zone["id"]: zone["name"] for zone in db.zones()}
        self._attempts: Dict[Tuple[str, str], list] = {}
        self._attempts_lock = threading.Lock()
        self.narutodle = Narutodle(characters=self._narutodle_characters(),
                                   on_finish=self._log_narutodle_match,
                                   provider=self.db.narutodle_characters)
        self.songless = Songless(tracks=self._songless_tracks(),
                                 provider=self.db.songless_tracks)
        # «Угадай песню за 10 секунд»: своя таблица песен по темам, но записи
        # владелец сайта кладёт так же — файлами или ссылками.
        self.songguess = SongGuess(tracks=self._songguess_tracks(),
                                   provider=self.db.songguess_tracks,
                                   on_finish=self._log_songguess_run)
        self.raporder = RapOrder(tracks=self._raporder_tracks(),
                                 provider=self.db.raporder_tracks,
                                 on_finish=self._log_raporder_match)
        # Драфт-рогалики: движок один, но у каждой игры свой набор паков и свои
        # прогоны — поэтому экземпляр на игру («87-0», «13-0», «4-0»).
        self.drafts: Dict[str, Csdraft] = {
            game: Csdraft(
                game=game,
                packs=self._draft_packs(game),
                provider=(lambda key=game: self.db.csdraft_packs(key)),
                on_finish=(lambda record, key=game: self._log_draft_run(key, record)),
            )
            for game in GAME_KEYS
        }
        # Короткий путь для игры по умолчанию: им пользуется страница «87-0».
        self.csdraft = self.drafts["cs"]
        # «322-0»: движок свой (бюджет, герои по позициям), а журнал общий с
        # драфт-рогаликами — та же таблица csdraft_runs с game = 'dota322'.
        self.dotadraft = DotaDraft(
            players=self._dotadraft_players(),
            heroes=self._dotadraft_heroes(),
            player_heroes=self.db.dotadraft_player_hero_ratings(),
            players_provider=self.db.dotadraft_players,
            heroes_provider=self.db.dotadraft_heroes,
            ratings_provider=self.db.dotadraft_player_hero_ratings,
            on_finish=self._log_dota_run,
        )

    # ------------------------------------------------------------------- доступ
    def authorized(self, headers: Any, query: Dict[str, str]) -> bool:
        """Проверяет API-ключ. Без заданного ключа доступ открыт (локальный режим)."""
        if not self.token:
            return True
        provided = headers.get("X-Api-Token") or query.get("token") or ""
        return hmac.compare_digest(provided, self.token)

    # ----------------------------------------------------------------- аккаунты
    def ensure_admin(self, password: Optional[str] = None) -> Optional[str]:
        """Создаёт администратора, пока аккаунтов нет.

        Возвращает сгенерированный пароль (если он не задан явно) — чтобы
        сервер мог один раз показать его в консоли. Иначе возвращает None.
        """
        if self.db.user_count():
            return None
        generated: Optional[str] = None
        if not password:
            generated = secrets.token_urlsafe(9)
            password = generated
        validate_password(password)
        self.db.create_user(ADMIN_NAME, hash_password(password), "admin")
        return generated

    def user_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        return self.db.session_user(token) if token else None

    def allow_attempt(self, client: str) -> bool:
        """Свободная регистрация и вход открыты всем, поэтому попытки ограничиваем.

        Скользящее окно на адрес: без него пароль можно было бы перебирать
        без ограничений. Ограничитель живёт в памяти и обнуляется при перезапуске.
        """
        return self._allow("auth", client, AUTH_ATTEMPTS, AUTH_WINDOW_SECONDS)

    def allow_game_action(self, client: str) -> bool:
        """То же для игр: комнаты создаются и открываются по коду.

        Код комнаты короткий, поэтому перебор входов тоже надо ограничивать —
        но своим счётчиком, чтобы игра не съедала попытки входа в аккаунт.
        """
        return self._allow("games", client, GAME_ATTEMPTS, GAME_WINDOW_SECONDS)

    def _allow(self, bucket: str, client: str, limit: int, window: float) -> bool:
        """Скользящее окно попыток для пары «раздел + адрес»."""
        now = time.time()
        key = (bucket, client)
        with self._attempts_lock:
            recent = [moment for moment in self._attempts.get(key, []) if now - moment < window]
            if len(recent) >= limit:
                self._attempts[key] = recent
                return False
            recent.append(now)
            self._attempts[key] = recent
        return True

    # ------------------------------------------------------- игра Narutodle
    def _narutodle_characters(self) -> List[Dict[str, Any]]:
        """Набор персонажей из базы; на пустой таблице заливает исходный набор.

        Дальше источник правды — база: персонажей можно править и дополнять
        прямо в ней (backend/seed_narutodle.py умеет и то, и другое).
        """
        if not self.db.narutodle_character_count():
            seeded = self.db.narutodle_save_characters(seed_rows())
            self.db.add_log(f"Narutodle: набор персонажей залит в базу ({seeded})", "info")
        return self.db.narutodle_characters()

    def reload_narutodle_characters(self) -> int:
        """Сбрасывает и перечитывает набор из базы (на случай правок на ходу)."""
        return self.narutodle.refresh()

    def _songless_tracks(self) -> List[Dict[str, Any]]:
        """Набор треков из базы; на пустой таблице заливает справочный набор.

        Записей опенингов в наборе нет: аудио добавляет владелец сайта
        (backend/seed_songless.py --audio или --url), и до этого играть
        попросту нечего — это честно показано на странице игры.
        """
        if not self.db.songless_track_count():
            seeded = self.db.songless_save_tracks(songless_seed_rows())
            self.db.add_log(f"Сонглесс: набор треков залит в базу ({seeded})", "info")
        return self.db.songless_tracks()

    def reload_songless_tracks(self) -> int:
        """Перечитывает набор треков из базы (на случай правок на ходу)."""
        return self.songless.refresh()

    # -------------------------------------------- «Угадай песню за 10 секунд»
    def _songguess_tracks(self) -> List[Dict[str, Any]]:
        """Песни из базы; на пустой таблице заливает исходный набор.

        Дальше источник правды — база: песни, темы и записи можно править прямо
        в ней (backend/seed_songguess.py умеет и то, и другое).
        """
        if not self.db.songguess_track_count():
            seeded = self.db.songguess_save_tracks(songguess_seed_rows())
            self.db.add_log(f"Угадай песню: набор песен залит в базу ({seeded})", "info")
        return self.db.songguess_tracks()

    def reload_songguess_tracks(self) -> int:
        """Перечитывает набор песен из базы (на случай правок на ходу)."""
        return self.songguess.refresh()

    def _log_songguess_run(self, record: Dict[str, Any]) -> None:
        """Пишет итог захода в журнал игры и в общий журнал событий."""
        entry = self.db.songguess_add_run(record)
        fastest = entry.get("fastest")
        note = f", лучший ответ {fastest:.1f} с" if fastest else ""
        self.db.add_log(
            f"Угадай песню: заход #{entry['id']} у {entry['username']} — "
            f"{entry['correct']} из {entry['rounds']} верных, {entry['score']} очков "
            f"(тема «{record.get('category_label') or entry['category']}», "
            f"{entry['difficulty']}{note})",
            "info",
        )

    # ---------------------------------------------- игра «Рэп-хронология»
    def _raporder_tracks(self) -> List[Dict[str, Any]]:
        """Треки из базы; на пустой таблице заливает исходный набор.

        Дальше источник правды — база: годы, исполнителей и названия можно
        править прямо в ней (backend/seed_raporder.py умеет и то, и другое).
        """
        if not self.db.raporder_track_count():
            seeded = self.db.raporder_save_tracks(raporder_seed_rows())
            self.db.add_log(f"Рэп-хронология: набор треков залит в базу ({seeded})", "info")
        return self.db.raporder_tracks()

    def reload_raporder_tracks(self) -> int:
        """Перечитывает набор треков из базы (на случай правок на ходу)."""
        return self.raporder.refresh()

    def _log_raporder_match(self, record: Dict[str, Any]) -> None:
        """Пишет итог партии в журнал игры и в общий журнал событий."""
        entry = self.db.raporder_add_match(record)
        where = "соло" if entry["mode"] == "solo" else f"комната {entry['room']}"
        winner = entry.get("winner_name") or "ничья"
        self.db.add_log(
            f"Рэп-хронология: партия #{entry['id']} ({where}) — {winner}, "
            f"{entry['player1_name']} {entry['player1_score']}"
            + (f": {entry['player2_name']} {entry['player2_score']}"
               if entry.get("player2_name") else "")
            + f" [{entry['detail']}]",
            "info",
        )

    # ------------------------------------------------- драфт-рогалики (игры)
    def _draft_packs(self, game: str) -> List[Dict[str, Any]]:
        """Паки игры из базы; на пустом наборе заливает исходный набор из кода.

        Дальше источник правды — база: составы, роли и оценки можно править
        прямо в ней (backend/seed_csdraft.py умеет и то, и другое).
        """
        if not self.db.csdraft_pack_count(game):
            seeded = self.db.csdraft_save_packs(seed_rows_for(game))
            self.db.add_log(f"{self._game_title(game)}: набор составов залит в базу "
                            f"({seeded})", "info")
        return self.db.csdraft_packs(game)

    @staticmethod
    def _game_title(game: str) -> str:
        """Название игры для журнала: у неизвестной остаётся её ключ."""
        return game_block(game)["title"] if game in GAME_KEYS else str(game)

    def _csdraft_packs(self) -> List[Dict[str, Any]]:
        """Паки «87-0» (CS): короткий путь для игры по умолчанию."""
        return self._draft_packs("cs")

    def draft_engine(self, game: str) -> Csdraft:
        """Движок игры: у каждой игры свои прогоны и свой набор паков."""
        key = str(game or "").strip().lower()
        if key not in self.drafts:
            raise CsdraftError(f"Неизвестная игра: {game}")
        return self.drafts[key]

    def reload_draft_packs(self, game: Optional[str] = None) -> int:
        """Сбрасывает и перечитывает составы из базы (по одной игре или по всем)."""
        keys = [str(game).strip().lower()] if game else list(self.drafts)
        for key in keys:
            if key in self.drafts:
                self.drafts[key].refresh()
        return sum(engine.pack_count() for engine in self.drafts.values())

    def reload_csdraft_packs(self) -> int:
        """Сбрасывает и перечитывает составы «87-0» из базы."""
        return self.drafts["cs"].refresh()

    def _log_draft_run(self, game: str, record: Dict[str, Any]) -> None:
        """Пишет итог прогона в журнал игры и в общий журнал событий."""
        entry = self.db.csdraft_add_run({**record, "game": game})
        tournament = game_block(game)["tournament"] if game in GAME_KEYS else "турнир"
        result = f"титул {tournament}" if entry.get("champion") else \
            f"вылет на стадии «{entry['stage']}»"
        self.db.add_log(
            f"{self._game_title(game)}: прогон #{entry['id']} у {entry['username']} — {result} "
            f"({entry['wins']}:{entry['losses']}, состав {entry['squad']})",
            "info",
        )

    # --------------------------------------------------- «322-0» (драфт Dota 2)
    def _dotadraft_players(self) -> List[Dict[str, Any]]:
        """Пул игроков «322-0» из базы; на пустой таблице заливает набор из кода.

        Дальше источник правды — база: стоимости и ники можно править прямо в
        ней (backend/seed_dotadraft.py умеет и то, и другое).
        """
        if not self.db.dotadraft_player_count():
            seeded = self.db.dotadraft_save_players(dotadraft_player_rows())
            self.db.add_log(f"322-0: пул игроков залит в базу ({seeded})", "info")
        return self.db.dotadraft_players()

    def _dotadraft_heroes(self) -> List[Dict[str, Any]]:
        """Пул героев «322-0» из базы; на пустой таблице заливает набор из кода."""
        if not self.db.dotadraft_hero_count():
            seeded = self.db.dotadraft_save_heroes(dotadraft_hero_rows())
            self.db.add_log(f"322-0: пул героев залит в базу ({seeded})", "info")
        return self.db.dotadraft_heroes()

    def reload_dotadraft_pool(self) -> int:
        """Перечитывает пул «322-0» из базы (на случай правок на ходу)."""
        return self.dotadraft.refresh()

    def _log_dota_run(self, record: Dict[str, Any]) -> None:
        """Пишет итог прогона «322-0» в журнал прогонов и в общий журнал событий."""
        entry = self.db.csdraft_add_run(record)
        titles = {item["key"]: item["title"] for item in self.dotadraft.rounds_catalog()}
        stage = titles.get(str(entry.get("stage") or ""), str(entry.get("stage") or ""))
        result = "титул Streamers Battle 13" if entry.get("champion") else \
            f"вылет на стадии «{stage}»"
        self.db.add_log(
            f"322-0: прогон #{entry['id']} у {entry['username']} — {result} "
            f"({entry['wins']}:{entry['losses']}, состав {entry['squad']})",
            "info",
        )

    def _log_narutodle_match(self, record: Dict[str, Any]) -> None:
        """Пишет итог партии в журнал матчей и в общий журнал событий."""
        entry = self.db.narutodle_add_match(record)
        winner = entry.get("winner_name") or "никто"
        players = entry.get("players") or ""
        self.db.add_log(
            f"Narutodle: партия #{entry['id']} в комнате {entry['room']}, "
            f"режим «{entry.get('mode') or 'duel'}» — победил {winner}"
            f" ({players or 'без доски'}; попыток: {entry['winner_attempts']} "
            f"против {entry['loser_attempts']})",
            "info",
        )

    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Проверяет логин и пароль и открывает сессию."""
        user = self.db.find_user(normalize_username(username))
        if not user or not verify_password(password, user.get("password_hash")):
            raise ValueError("Неверный логин или пароль")
        token = new_token()
        expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
        self.db.create_session(user["id"], token, expires)
        self.db.add_log(f"Вход в панель: {user['username']}", "info")
        return {
            "token": token,
            "user": public_user(user),
            "state": self.db.user_state(user["id"]),
            "expires_in_days": SESSION_DAYS,
        }

    def logout(self, token: str) -> None:
        self.db.delete_session(token)

    def register(self, username: str, password: str) -> Dict[str, Any]:
        """Свободная регистрация: роль всегда «user», сразу открываем сессию.

        Администратора самому себе выдать нельзя — роль меняет только владелец
        аккаунта admin с секретной страницы. Регистрация открыта всем, поэтому
        обработчик входа вызывается тем же путём, что и обычный вход.
        """
        user = self.create_user(username, password, "user")
        result = self.login(user["username"], password)
        result["created"] = True
        return result

    def create_user(self, username: str, password: str, role: str = "user") -> Dict[str, Any]:
        name = validate_username(username)
        validate_password(password)
        user = self.db.create_user(name, hash_password(password), validate_role(role))
        self.db.add_log(f"Создан пользователь {name} ({user['role']})", "info")
        return user

    def delete_user(self, user_id: int) -> Dict[str, Any]:
        user = self.db.get_user(user_id)
        if not user:
            raise ValueError("Пользователь не найден")
        if user["role"] == "admin" and len(self.admins()) <= 1:
            raise ValueError("Нельзя удалить последнего администратора")
        self.db.delete_user(user_id)
        self.db.add_log(f"Удалён пользователь {user['username']}", "info")
        return user

    def admins(self) -> List[Dict[str, Any]]:
        return [user for user in self.db.list_users() if user["role"] == "admin"]

    def change_password(self, user_id: int, current: str, new: str) -> None:
        """Смена пароля: свой пароль требует подтверждения текущим."""
        user = self.db.find_user_by_id(user_id)
        if not user or not verify_password(current, user.get("password_hash")):
            raise ValueError("Текущий пароль указан неверно")
        self.db.set_user_password(user_id, hash_password(validate_password(new)))
        self.db.add_log(f"Смена пароля: {user['username']}", "info")

    def reset_password(self, user_id: int, new: str) -> None:
        """Сброс пароля администратором — текущий пароль не спрашивается."""
        if not self.db.get_user(user_id):
            raise ValueError("Пользователь не найден")
        self.db.set_user_password(user_id, hash_password(validate_password(new)))

    def save_user_state(self, user_id: int, payload: Dict[str, Any]) -> None:
        self.db.save_user_state(user_id, payload)

    # ---------------------------------------------------------------- lifecycle
    def start(self) -> None:
        self.arduino.start()
        self._stop.clear()
        self._thread = threading.Thread(target=self._automation_loop, name="automation", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
        self.arduino.stop()

    # ------------------------------------------------------------------- state
    def state_payload(self) -> Dict[str, Any]:
        state_row = self.db.state()
        settings = self.db.settings()
        readings = self.db.latest_readings()
        devices = self.db.devices()

        zones = []
        temps: list = []
        moistures: list = []
        lights: list = []

        for zone in self.db.zones():
            zone_id = zone["id"]
            reading = readings.get(zone_id, {})
            zone_devices = devices.get(zone_id, {d: False for d in DEVICES})

            if reading.get("temperature") is not None:
                temps.append(reading["temperature"])
            if reading.get("moisture") is not None:
                moistures.append(reading["moisture"])
            if reading.get("light") is not None:
                lights.append(reading["light"])

            zones.append({
                "id": zone_id,
                "name": zone["name"],
                "sensors": {
                    "temperature": reading.get("temperature"),
                    "moisture": reading.get("moisture"),
                    "light": reading.get("light"),
                },
                "devices": {
                    device: {"on": bool(zone_devices.get(device)), "remaining": self.remaining(zone_id, device)}
                    for device in DEVICES
                },
                "target": settings["moisture_target"],
                "status": self._zone_status(reading, settings),
                "updated_at": reading.get("recorded_at"),
            })

        def avg(values: list) -> Optional[float]:
            return round(sum(values) / len(values), 2) if values else None

        return {
            "online": True,
            "server_time": _now_iso(),
            "mode": settings["mode"],
            "tank": state_row.get("tank"),
            "window_open": state_row.get("window_open"),
            "source": state_row.get("source"),
            "arduino": self.arduino.status(),
            "settings": settings,
            "sensors": {
                "temperature": avg(temps),
                "moisture": avg(moistures),
                "light": avg(lights),
            },
            "devices": {
                device: {"on": any(devices[z].get(device) for z in range(1, ZONE_COUNT + 1))}
                for device in DEVICES
            },
            "zones": zones,
        }

    def zone_payload(self, zone_id: int) -> Optional[Dict[str, Any]]:
        payload = self.state_payload()
        for zone in payload["zones"]:
            if zone["id"] == zone_id:
                zone["history"] = self.db.history(zone_id=zone_id, limit=60)
                return zone
        return None

    def _zone_status(self, reading: Dict[str, Any], settings: Dict[str, Any]) -> str:
        moisture = reading.get("moisture")
        temperature = reading.get("temperature")
        light = reading.get("light")
        if moisture is not None and moisture < settings["moisture_threshold"]:
            return "dry"
        if temperature is not None and temperature > settings["temperature_threshold"]:
            return "hot"
        if light is not None and light < settings["light_threshold"]:
            return "dark"
        return "ok"

    # ----------------------------------------------------------------- devices
    def remaining(self, zone_id: int, device: str) -> float:
        end = self._timers.get((zone_id, device))
        if not end:
            return 0.0
        return max(0.0, round(end - time.time(), 1))

    def set_device(
        self,
        zone_id: int,
        device: str,
        on: bool,
        seconds: Optional[float] = None,
        reason: str = "",
        log: bool = True,
    ) -> None:
        if device not in DEVICES:
            raise ValueError(f"Неизвестный исполнитель: {device}")
        if not 1 <= zone_id <= ZONE_COUNT:
            raise ValueError(f"Неизвестный участок: {zone_id}")

        self.db.set_device(zone_id, device, on)

        if on and seconds:
            self._timers[(zone_id, device)] = time.time() + float(seconds)
        elif not on:
            self._timers.pop((zone_id, device), None)

        self.arduino.send_command(zone_id, device, on, seconds)

        if not log:
            return
        name = self._zone_names.get(zone_id, f"Участок {zone_id}")
        labels = {"watering": "Полив", "ventilation": "Проветривание", "lighting": "Досветка"}
        suffix = f" на {int(seconds)} с" if (on and seconds) else ""
        tail = f" ({reason})" if reason else ""
        self.db.add_log(f"{name}: {labels[device]} {'запущен' if on else 'остановлен'}{suffix}{tail}", "info", zone_id)

    def set_device_all(
        self,
        device: str,
        on: bool,
        seconds: Optional[float] = None,
        reason: str = "",
    ) -> None:
        """Команда сразу всем 12 участкам (zone_id = 0 в API)."""
        for zone_id in range(1, ZONE_COUNT + 1):
            self.set_device(zone_id, device, on, seconds, reason=reason, log=False)
        labels = {"watering": "Полив", "ventilation": "Проветривание", "lighting": "Досветка"}
        scope = "включён" if on else "выключен"
        suffix = f" на {int(seconds)} с" if (on and seconds) else ""
        tail = f" ({reason})" if reason else ""
        self.db.add_log(f"Все 12 участков: {labels[device]} {scope}{suffix}{tail}", "info")

    # ---------------------------------------------------------------- settings
    def update_settings(self, values: Dict[str, Any]) -> Dict[str, Any]:
        return self.db.update_settings(values)

    def apply_mode(self, mode: str) -> Dict[str, Any]:
        if mode not in MODE_PRESETS:
            raise ValueError(f"Неизвестный режим: {mode}")
        values: Dict[str, Any] = {"mode": mode}
        preset = MODE_PRESETS[mode]
        if preset:
            values.update(preset)
        return self.db.update_settings(values)

    # --------------------------------------------------------------- automatic
    def _automation_loop(self) -> None:
        while not self._stop.wait(2.0):
            try:
                self._automation_tick()
            except Exception as exc:  # noqa: BLE001
                self.db.add_log(f"Ошибка автоматики: {exc}", "err")

    def _automation_tick(self) -> None:
        self._expire_timers()

        # Через домашнего агента показания приходят снаружи: если он молчит,
        # последние данные устарели, и решения по ним были бы выдуманными.
        link = self.arduino.status()
        if link.get("mode") == "remote" and not link.get("connected"):
            if not self.db.has_recent_log("Автоматика ждёт связи с платой", 300):
                self.db.add_log("Автоматика ждёт связи с платой: показания устарели", "warn")
            return

        settings = self.db.settings()
        if settings["mode"] == "manual":
            return

        readings = self.db.latest_readings()
        devices = self.db.devices()
        tank = float(self.db.state().get("tank") or 0.0)

        for zone_id in range(1, ZONE_COUNT + 1):
            reading = readings.get(zone_id, {})
            device_row = devices.get(zone_id, {})
            name = self._zone_names.get(zone_id, f"Участок {zone_id}")

            moisture = reading.get("moisture")
            temperature = reading.get("temperature")
            light = reading.get("light")

            if (settings["auto_watering"] and moisture is not None
                    and moisture < settings["moisture_threshold"] and not device_row.get("watering")):
                if tank > 5:
                    if not self.db.has_recent_log(f"{name}: автополив", 120):
                        self.db.add_log(f"{name}: автополив", "warn", zone_id)
                        self.set_device(zone_id, "watering", True, settings["watering_duration"],
                                        reason="низкая влажность")
                elif not self.db.has_recent_log("Бак пуст — полив остановлен", 300):
                    self.db.add_log("Бак пуст — полив остановлен", "warn")

            if (settings["auto_ventilation"] and temperature is not None
                    and temperature > settings["temperature_threshold"] and not device_row.get("ventilation")):
                if not self.db.has_recent_log(f"{name}: автопроветривание", 120):
                    self.db.add_log(f"{name}: автопроветривание", "warn", zone_id)
                    self.set_device(zone_id, "ventilation", True, settings["ventilation_duration"],
                                    reason="перегрев")

            if settings["auto_lighting"] and light is not None:
                should_glow = light < settings["light_threshold"]
                if should_glow != bool(device_row.get("lighting")):
                    self.set_device(zone_id, "lighting", should_glow, reason="фотопериод")

    def _expire_timers(self) -> None:
        now = time.time()
        for (zone_id, device), end in list(self._timers.items()):
            if end and now >= end:
                self._timers.pop((zone_id, device), None)
                self.set_device(zone_id, device, False, reason="таймер завершён")


# ============================================================================
# HTTP-слой
# ============================================================================
class Handler(BaseHTTPRequestHandler):
    server_version = "GreenhouseServer/2.0"
    protocol_version = "HTTP/1.1"
    # Тело запроса читается один раз (см. _read_body) и сбрасывается на каждом
    # запросе: соединение остаётся живым и обслуживает следующий запрос.
    _raw_body: Optional[bytes] = None

    def handle_one_request(self) -> None:
        self._raw_body = None
        super().handle_one_request()

    @property
    def app(self) -> Application:
        return self.server.app  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args: Any) -> None:
        if self.path.startswith("/api/"):
            sys.stderr.write("  %s\n" % (fmt % args))

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Api-Token, Authorization")

    def _json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _error(self, message: str, status: int = 400) -> None:
        self._json({"error": message, "status": status}, status)

    def _image(self, body: bytes, mime: str, max_age: int) -> None:
        """Отдаёт картинку с браузерным кэшем: портреты не меняются каждый день."""
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=%d" % int(max_age))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _serve_portrait(self, character_id: int) -> None:
        """Портрет персонажа: data-строку из базы превращаем в обычную картинку.

        В каталоге вместо base64 стоит ссылка сюда: иначе страница тянула
        несколько мегабайт и на медленном канале не успевала за таймаут.
        """
        raw = self.app.db.narutodle_portrait(character_id) or ""
        if not raw:
            return self._error("Портрет не найден", 404)
        if not raw.startswith("data:"):
            # Путь или ссылку на файл отдаёт владелец сайта, а не сервер игры.
            return self._error("Портрет хранится не в базе", 404)
        header, _, payload = raw.partition(",")
        mime = header[5:].split(";")[0] or "image/webp"
        if ";base64" not in header:
            return self._error("Портрет хранится не в base64", 500)
        try:
            body = base64.b64decode(payload, validate=True)
        except (binascii.Error, ValueError):
            return self._error("Портрет повреждён", 500)
        return self._image(body, mime, 86400)

    def _read_body(self) -> bytes:
        """Читает тело запроса один раз и держит его до конца обработки.

        Тело нельзя оставлять непрочитанным: Windows при закрытии сокета с
        непрочитанными данными отвечает RST, и клиент теряет уже отправленный
        ответ — например, POST на создание комнаты приходит с телом `{}`, а этот
        обработчик тело не читает. Запрос отвечал 201, но клиент видел обрыв.
        """
        if self._raw_body is None:
            length = int(self.headers.get("Content-Length") or 0)
            self._raw_body = self.rfile.read(length) if length else b""
        return self._raw_body

    def _body(self) -> Dict[str, Any]:
        raw = self._read_body()
        if not raw:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _query(self) -> Dict[str, str]:
        params = parse_qs(urlparse(self.path).query)
        return {key: values[0] for key, values in params.items() if values}

    # ------------------------------------------------------------- verbs
    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path.startswith("/api/"):
            self._handle_api("GET", path)
        else:
            self._serve_static(path)

    def do_HEAD(self) -> None:  # noqa: N802
        self.do_GET()

    def do_POST(self) -> None:  # noqa: N802
        self._read_body()
        path = urlparse(self.path).path
        if path.startswith("/api/"):
            self._handle_api("POST", path)
        else:
            self._error("Только API принимает POST", 405)

    def do_DELETE(self) -> None:  # noqa: N802
        self._read_body()
        path = urlparse(self.path).path
        if path.startswith("/api/"):
            self._handle_api("DELETE", path)
        else:
            self._error("Только API принимает DELETE", 405)

    # ------------------------------------------------------------- API routes
    def _bearer_token(self) -> str:
        """Токен входа из заголовка Authorization: Bearer <token>."""
        header = self.headers.get("Authorization") or ""
        if header.lower().startswith("bearer "):
            return header[7:].strip()
        return ""

    def _handle_api(self, method: str, path: str) -> None:
        app = self.app
        query = self._query()

        # Вход и секретная страница защищены паролем пользователя, а не общим
        # ключом, иначе войти было бы невозможно. Общий ключ их не закрывает.
        if path.startswith(("/api/auth/", "/api/admin/", "/api/secret/")):
            return self._handle_accounts_api(method, path)

        # Игры: в них пускает аккаунт (Bearer), а общий ключ не нужен — он попал бы
        # в ссылку-приглашение, которую пересылают другу.
        if path.startswith("/api/games/"):
            return self._handle_games_api(method, path)

        # Домашний агент приходит со своих устройств и своего токена: общий ключ
        # панели лежит в браузере, поэтому ему он не подходит.
        if path.startswith("/api/device/"):
            return self._handle_device_api(method, path)

        if not app.authorized(self.headers, query):
            return self._error("Неверный или отсутствующий API-ключ", 401)

        try:
            if method == "GET" and path == "/api/health":
                return self._json({"status": "ok", "time": _now_iso(), "zones": ZONE_COUNT,
                                   "arduino": app.arduino.status()})

            if method == "GET" and path == "/api/state":
                return self._json(app.state_payload())

            if method == "GET" and path == "/api/zones":
                return self._json({"zones": app.state_payload()["zones"]})

            match = re.fullmatch(r"/api/zones/(\d+)/history", path)
            if method == "GET" and match:
                zone_id = int(match.group(1))
                return self._json({"zone_id": zone_id, "history": app.db.history(zone_id, int(query.get("limit", 60)))})

            match = re.fullmatch(r"/api/zones/(\d+)", path)
            if method == "GET" and match:
                zone = app.zone_payload(int(match.group(1)))
                return self._json(zone) if zone else self._error("Участок не найден", 404)

            if method == "GET" and path == "/api/history":
                zone_id = int(query["zone_id"]) if query.get("zone_id") else None
                return self._json({"history": app.db.history(zone_id, int(query.get("limit", 60)))})

            if method == "GET" and path == "/api/logs":
                return self._json({"logs": app.db.logs(int(query.get("limit", 100)), query.get("level"))})

            if method == "GET" and path == "/api/settings":
                return self._json(app.db.settings())

            if method == "GET" and path == "/api/arduino":
                return self._json(app.arduino.status())

            if method == "POST" and path == "/api/devices":
                data = self._body()
                zone_id = int(data.get("zone_id") or 0)
                device = str(data.get("device") or "")
                on = bool(data.get("on"))
                seconds = float(data["seconds"]) if data.get("seconds") else None
                if not device:
                    return self._error("Не указан исполнитель (device)")
                if zone_id == 0:
                    app.set_device_all(device, on, seconds, reason="команда оператора")
                    return self._json({"ok": True, "scope": "all"})
                app.set_device(zone_id, device, on, seconds, reason="команда оператора")
                return self._json({"ok": True, "zone": app.zone_payload(zone_id)})

            if method == "POST" and path == "/api/settings":
                return self._json({"settings": app.update_settings(self._body())})

            if method == "POST" and path == "/api/mode":
                mode = str(self._body().get("mode") or "")
                app.apply_mode(mode)
                app.db.add_log(f"Режим переключён: {mode}", "info")
                return self._json({"ok": True, "settings": app.db.settings()})

            if method == "POST" and path == "/api/logs/clear":
                app.db.clear_logs()
                return self._json({"ok": True})

            return self._error(f"Не найдено: {method} {path}", 404)
        except ValueError as exc:
            return self._error(str(exc), 400)
        except Exception as exc:  # noqa: BLE001
            return self._error(f"Внутренняя ошибка: {exc}", 500)

    # -------------------------------------------- аккаунты и записи секретной стр.
    def _handle_accounts_api(self, method: str, path: str) -> None:
        """Вход, состояние пользователя, управление аккаунтами и данные страницы."""
        app = self.app
        try:
            token = self._bearer_token()
            user = app.user_by_token(token)
            client = self.client_address[0] if self.client_address else "?"

            if method == "POST" and path == "/api/auth/login":
                if not app.allow_attempt(client):
                    return self._error("Слишком много попыток входа. Подождите минуту и повторите", 429)
                data = self._body()
                try:
                    result = app.login(str(data.get("username") or ""), str(data.get("password") or ""))
                except ValueError as exc:
                    return self._error(str(exc), 401)
                return self._json(result)

            if method == "POST" and path == "/api/auth/register":
                if not app.allow_attempt(client):
                    return self._error("Слишком много попыток регистрации. Подождите минуту и повторите", 429)
                data = self._body()
                try:
                    result = app.register(str(data.get("username") or ""), str(data.get("password") or ""))
                except ValueError as exc:
                    return self._error(str(exc), 400)
                return self._json(result, 201)

            if method == "POST" and path == "/api/auth/logout":
                app.logout(token)
                return self._json({"ok": True})

            if method == "GET" and path == "/api/auth/me":
                if not user:
                    return self._error("Требуется вход", 401)
                return self._json({"user": user})

            if path == "/api/auth/state":
                if not user:
                    return self._error("Требуется вход", 401)
                if method == "GET":
                    return self._json({"state": app.db.user_state(user["id"])})
                if method == "POST":
                    app.save_user_state(user["id"], self._body())
                    return self._json({"ok": True, "saved_at": _now_iso()})

            if method == "POST" and path == "/api/auth/password":
                if not user:
                    return self._error("Требуется вход", 401)
                data = self._body()
                app.change_password(user["id"], str(data.get("current") or ""), str(data.get("new") or ""))
                app.logout(token)  # после смены пароля токен закрываем: нужен новый вход
                return self._json({"ok": True, "relogin": True})

            if path == "/api/admin/users":
                if not self._require_admin(user):
                    return self._error("Нужны права администратора", 403)
                if method == "GET":
                    return self._json({"users": app.db.list_users()})
                if method == "POST":
                    data = self._body()
                    created = app.create_user(str(data.get("username") or ""),
                                              str(data.get("password") or ""),
                                              str(data.get("role") or "user"))
                    return self._json({"user": created}, 201)

            match = re.fullmatch(r"/api/admin/users/(\d+)/password", path)
            if method == "POST" and match:
                if not self._require_admin(user):
                    return self._error("Нужны права администратора", 403)
                app.reset_password(int(match.group(1)), str(self._body().get("new") or ""))
                return self._json({"ok": True})

            match = re.fullmatch(r"/api/admin/users/(\d+)", path)
            if method == "DELETE" and match:
                if not self._require_admin(user):
                    return self._error("Нужны права администратора", 403)
                return self._json({"ok": True, "user": app.delete_user(int(match.group(1)))})

            if path == "/api/secret/data":
                if not user:
                    return self._error("Требуется вход", 401)
                if method == "GET":
                    return self._json({"data": app.db.secret_data()})
                if not self._require_admin(user):
                    return self._error("Нужны права администратора", 403)
                if method == "POST":
                    data = self._body()
                    name = str(data.get("name") or "").strip()
                    if not name:
                        return self._error("Не указано имя записи (name)")
                    entry = app.db.set_secret_data(name, str(data.get("value") or ""))
                    return self._json({"entry": entry})

            match = re.fullmatch(r"/api/secret/data/(\d+)", path)
            if method == "DELETE" and match:
                if not self._require_admin(user):
                    return self._error("Нужны права администратора", 403)
                if not app.db.delete_secret_data(int(match.group(1))):
                    return self._error("Запись не найдена", 404)
                return self._json({"ok": True})

            return self._error(f"Не найдено: {method} {path}", 404)
        except ValueError as exc:
            return self._error(str(exc), 400)
        except Exception as exc:  # noqa: BLE001
            return self._error(f"Внутренняя ошибка: {exc}", 500)

    # ------------------------------------------------------- игры: Narutodle
    def _handle_games_api(self, method: str, path: str) -> None:
        """«Narutodle»: комнаты до шести игроков, лобби и три режима игры.

        Вход — по аккаунту панели (Bearer), общий API-ключ здесь не спрашивается:
        ссылку-приглашение пересылают другу, и ключ в ней был бы утечкой.
        Комнаты живут в памяти процесса, поэтому перезапуск сервера их не сохраняет.
        """
        app = self.app
        prefix = "/api/games/narutodle"
        client = self.client_address[0] if self.client_address else "?"
        query = self._query()

        if path.startswith("/api/games/songless"):
            return self._handle_songless_api(method, path)

        if path.startswith("/api/games/songguess"):
            return self._handle_songguess_api(method, path)

        if path.startswith("/api/games/raporder"):
            return self._handle_raporder_api(method, path)

        if path.startswith("/api/games/csdraft"):
            return self._handle_csdraft_api(method, path)

        if path.startswith("/api/games/dota322"):
            return self._handle_dota322_api(method, path)

        if re.fullmatch(r"/api/games/draft/[a-z0-9]+", path):
            game = path.rsplit("/", 1)[-1]
            if game == "games":
                return self._handle_draft_games_api(method, path)
            return self._handle_draft_api(method, path, game, path)

        draft = re.fullmatch(r"/api/games/draft/([a-z0-9]+)/(.+)", path)
        if draft:
            prefix = f"/api/games/draft/{draft.group(1)}"
            return self._handle_draft_api(method, path, draft.group(1), prefix)

        try:
            user = app.user_by_token(self._bearer_token())

            if method == "GET" and path == f"{prefix}/characters":
                return self._json({
                    "characters": app.narutodle.catalog(),
                    "attributes": attribute_list(),
                    "max_attempts": NARUTODLE_MAX_ATTEMPTS,
                    "max_players": NARUTODLE_MAX_PLAYERS,
                    "modes": app.narutodle.modes(),
                })

            # Портрет открыт без входа: это картинка из того же открытого каталога.
            portrait = re.fullmatch(rf"{prefix}/portrait/(\d+)", path)
            if method == "GET" and portrait:
                return self._serve_portrait(int(portrait.group(1)))

            if not user:
                return self._error("Требуется вход в аккаунт", 401)

            if method == "GET" and path == f"{prefix}/matches":
                scope = str(query.get("scope") or "mine").lower()
                limit = int(query.get("limit", 50))
                if scope == "all":
                    # Чужую историю игр видит только администратор.
                    if not self._require_admin(user):
                        return self._error("Нужны права администратора", 403)
                    return self._json({
                        "scope": "all",
                        "matches": app.db.narutodle_matches(None, limit),
                        "total": app.db.narutodle_match_count(),
                        "characters": app.db.narutodle_character_count(),
                    })
                return self._json({
                    "scope": "mine",
                    "user": {"id": user["id"], "username": user["username"]},
                    "matches": app.db.narutodle_matches(user["id"], limit),
                })

            if method == "POST" and path == f"{prefix}/rooms":
                if not app.allow_game_action(client):
                    return self._error("Слишком много комнат за минуту — подождите немного", 429)
                mode = str(self._body().get("mode") or "duel")
                return self._json({"state": app.narutodle.create(user, mode)}, 201)

            match = re.fullmatch(rf"{prefix}/rooms/([A-Za-z0-9]{{4}})", path)
            if method == "GET" and match:
                return self._json({"state": app.narutodle.state(match.group(1), user)})

            # Наблюдение: пускает любого вошедшего, участник получает member=true
            # и уходит в свою комнату. Поле живёт на опросе, поэтому без лимита.
            match = re.fullmatch(rf"{prefix}/rooms/([A-Za-z0-9]{{4}})/watch", path)
            if method == "GET" and match:
                return self._json({"state": app.narutodle.watch(match.group(1), user)})

            match = re.fullmatch(rf"{prefix}/rooms/([A-Za-z0-9]{{4}})/join", path)
            if method == "POST" and match:
                if not app.allow_game_action(client):
                    return self._error("Слишком много попыток войти — подождите минуту", 429)
                return self._json({"state": app.narutodle.join(match.group(1), user)})

            match = re.fullmatch(rf"{prefix}/rooms/([A-Za-z0-9]{{4}})/leave", path)
            if method == "POST" and match:
                return self._json({"state": app.narutodle.leave(match.group(1), user)})

            match = re.fullmatch(rf"{prefix}/rooms/([A-Za-z0-9]{{4}})/mode", path)
            if method == "POST" and match:
                mode = str(self._body().get("mode") or "")
                return self._json({"state": app.narutodle.set_mode(match.group(1), user, mode)})

            match = re.fullmatch(rf"{prefix}/rooms/([A-Za-z0-9]{{4}})/team", path)
            if method == "POST" and match:
                total = self._body().get("total")
                return self._json({"state": app.narutodle.set_team_total(
                    match.group(1), user, total)})

            match = re.fullmatch(rf"{prefix}/rooms/([A-Za-z0-9]{{4}})/side", path)
            if method == "POST" and match:
                team = str(self._body().get("team") or "")
                return self._json({"state": app.narutodle.move_team(
                    match.group(1), user, team)})

            match = re.fullmatch(rf"{prefix}/rooms/([A-Za-z0-9]{{4}})/start", path)
            if method == "POST" and match:
                return self._json({"state": app.narutodle.start(match.group(1), user)})

            match = re.fullmatch(rf"{prefix}/rooms/([A-Za-z0-9]{{4}})/lobby", path)
            if method == "POST" and match:
                return self._json({"state": app.narutodle.to_lobby(match.group(1), user)})

            match = re.fullmatch(rf"{prefix}/rooms/([A-Za-z0-9]{{4}})/guess", path)
            if method == "POST" and match:
                name = str(self._body().get("name") or "")
                return self._json({"state": app.narutodle.guess(match.group(1), user, name)})

            match = re.fullmatch(rf"{prefix}/rooms/([A-Za-z0-9]{{4}})/giveup", path)
            if method == "POST" and match:
                return self._json({"state": app.narutodle.give_up(match.group(1), user)})

            match = re.fullmatch(rf"{prefix}/rooms/([A-Za-z0-9]{{4}})/rematch", path)
            if method == "POST" and match:
                return self._json({"state": app.narutodle.rematch(match.group(1), user)})

            return self._error(f"Не найдено: {method} {path}", 404)
        except NarutodleError as exc:
            return self._error(str(exc), 400)
        except Exception as exc:  # noqa: BLE001
            return self._error(f"Внутренняя ошибка: {exc}", 500)

    # ------------------------------------------------------ домашний агент (VPS)
    def _device_token(self) -> str:
        """Токен агента: заголовок X-Device-Token либо обычный Bearer."""
        value = self.headers.get("X-Device-Token")
        if value:
            return value.strip()
        return self._bearer_token()

    def _handle_device_api(self, method: str, path: str) -> None:
        """Приём показаний от домашнего агента и выдача ему команд к плате.

        Раздел отделён от /api/* намеренно: общий ключ панели лежит в браузере,
        а агенту нужен свой секрет, который известен только домашнему ПК.
        """
        app = self.app
        link = app.device_link
        if link is None:
            return self._error("Сервер работает с платой напрямую: раздел агента выключен", 404)
        provided = self._device_token()
        if not provided or not hmac.compare_digest(provided, link.token):
            return self._error("Неверный или отсутствующий токен устройства", 401)

        try:
            if method == "GET" and path == "/api/device/status":
                return self._json(link.status())

            if method == "POST" and path == "/api/device/sync":
                result = link.ingest(self._body())
                link.prune()
                result["server_time"] = _now_iso()
                # Агенту нужны включённые исполнители: дома он эмулирует датчики,
                # а полив и досветка меняют их показания.
                result["devices"] = link.devices_payload()
                return self._json(result)

            if method == "POST" and path == "/api/device/ack":
                data = self._body()
                done = link.acknowledge(data.get("applied") or [], data.get("errors") or {})
                return self._json({"ok": True, "applied": done})

            return self._error(f"Не найдено: {method} {path}", 404)
        except ValueError as exc:
            return self._error(str(exc), 400)
        except Exception as exc:  # noqa: BLE001
            return self._error(f"Внутренняя ошибка: {exc}", 500)

    @staticmethod
    def _require_admin(user: Optional[Dict[str, Any]]) -> bool:
        return bool(user and user.get("role") == "admin")

    @staticmethod
    def _limit_arg(query: Dict[str, str], default: int = 50) -> int:
        """Предел выдачи из строки запроса: мусор в ссылке не должен ронять журнал."""
        try:
            value = int(str(query.get("limit", default)).strip())
        except (TypeError, ValueError):
            return default
        return max(1, min(value, 500))

    def _handle_draft_api(self, method: str, path: str, game: str = "cs",
                          prefix: str = "/api/games/csdraft") -> None:
        """Драфт-рогалик: драфт состава из прошлых турниров и прогон по сетке.

        Один обработчик обслуживает все игры — «87-0» (CS, старый адрес
        /api/games/csdraft), «13-0» (Valorant) и «4-0» (Rocket League), у которых
        адрес /api/games/draft/<игра>. Отличаются они только конфигурацией из
        backend/draft_games.py.

        Вход — по аккаунту панели (Bearer): прогон принадлежит игроку, и чужой
        его продолжить не может. Прогоны живут в памяти процесса, поэтому
        перезапуск сервера их теряет; итог каждого уходит в журнал, он и
        переживает перезапуск.
        """
        app = self.app
        client = self.client_address[0] if self.client_address else "?"
        query = self._query()

        try:
            engine = app.draft_engine(game)
            user = app.user_by_token(self._bearer_token())

            # Состояние набора открыто до входа: страница сразу объясняет, что
            # играть можно, и какие есть эпохи, сложности и роли.
            if method == "GET" and path == f"{prefix}/status":
                engine.refresh()
                return self._json({
                    "game": game_block(engine.game),
                    "packs": engine.pack_count(),
                    "eras": engine.era_counts(),
                    "ready": {era: engine.ready(era) for era in engine.eras},
                    "difficulties": [
                        {"key": key, "label": DIFFICULTY_LABELS[key],
                         "rerolls": DIFFICULTY_REROLLS[key]} for key in DIFFICULTIES],
                    "stages": [{"key": stage["key"], "title": stage["title"],
                                "best_of": stage["best_of"],
                                "swiss": bool(stage.get("swiss"))} for stage in engine.stages],
                    "roles": [{"key": role, "label": engine.role_labels[role]}
                              for role in engine.roles],
                    "pool_size": engine.pool_size,
                })

            if not user:
                return self._error("Требуется вход в аккаунт", 401)

            if method == "POST" and path == f"{prefix}/runs":
                if not app.allow_game_action(client):
                    return self._error("Слишком много прогонов за минуту — подождите немного", 429)
                data = self._body()
                return self._json({"state": engine.start(
                    user,
                    difficulty=str(data.get("difficulty") or "hard"),
                    era=str(data.get("era") or "legacy"),
                    assign=str(data.get("assign") or "auto"),
                )}, 201)

            if method == "GET" and path == f"{prefix}/matches":
                scope = str(query.get("scope") or "mine").lower()
                limit = self._limit_arg(query)
                if scope == "all":
                    if not self._require_admin(user):
                        return self._error("Журнал всех прогонов доступен только администратору", 403)
                    return self._json({"matches": app.db.csdraft_runs(None, limit, engine.game)})
                return self._json({"matches": app.db.csdraft_runs(user["id"], limit, engine.game)})

            run_pattern = rf"{prefix}/runs/([0-9a-f]{{8}})"
            match = re.fullmatch(run_pattern, path)
            if method == "GET" and match:
                return self._json({"state": engine.state(match.group(1), user)})

            match = re.fullmatch(rf"{run_pattern}/take", path)
            if method == "POST" and match:
                if not app.allow_game_action(client):
                    return self._error("Слишком много действий за минуту — подождите немного", 429)
                data = self._body()
                role = str(data.get("role") or "").strip() or None
                return self._json({"state": engine.take(
                    match.group(1), user, str(data.get("player") or ""), role)})

            match = re.fullmatch(rf"{run_pattern}/map", path)
            if method == "POST" and match:
                map_name = str(self._body().get("map") or "")
                return self._json({"state": engine.take_map(match.group(1), user, map_name)})

            match = re.fullmatch(rf"{run_pattern}/pack", path)
            if method == "POST" and match:
                return self._json({"state": engine.skip_pack(match.group(1), user)})

            match = re.fullmatch(rf"{run_pattern}/reroll", path)
            if method == "POST" and match:
                return self._json({"state": engine.reroll(match.group(1), user)})

            match = re.fullmatch(rf"{run_pattern}/assign", path)
            if method == "POST" and match:
                mode = str(self._body().get("mode") or "")
                return self._json({"state": engine.set_assign(match.group(1), user, mode)})

            match = re.fullmatch(rf"{run_pattern}/auto", path)
            if method == "POST" and match:
                return self._json({"state": engine.auto_assign(match.group(1), user)})

            match = re.fullmatch(rf"{run_pattern}/play", path)
            if method == "POST" and match:
                if not app.allow_game_action(client):
                    return self._error("Слишком много матчей за минуту — подождите немного", 429)
                return self._json({"state": engine.play(match.group(1), user)})

            match = re.fullmatch(rf"{run_pattern}/boost", path)
            if method == "POST" and match:
                return self._json({"state": engine.boost(
                    match.group(1), user, self._body().get("index"))})

            return self._error(f"Не найдено: {method} {path}", 404)
        except CsdraftError as exc:
            return self._error(str(exc), 400)
        except Exception as exc:  # noqa: BLE001
            return self._error(f"Внутренняя ошибка: {exc}", 500)

    def _handle_csdraft_api(self, method: str, path: str) -> None:
        """«87-0»: старый адрес игры по CS (страница пользуется именно им)."""
        return self._handle_draft_api(method, path, "cs", "/api/games/csdraft")

    def _handle_dota322_api(self, method: str, path: str) -> None:
        """«322-0»: драфт по Dota 2 на Streamers Battle 13 с бюджетом на состав.

        Вход — по аккаунту панели (Bearer): прогон принадлежит игроку, чужой его
        продолжить не может. Драфт идёт паками: в паке пять игроков и пять
        героев, из пака берут одно — игрока либо героя, — после чего пак
        меняется целиком. Пять героев закрывают пять позиций, на мид берут
        игрока дешевле порога. Дальше турнир: две группы по четыре команды,
        круговая Bo3 и плей-офф с двойным выбыванием. Прогоны живут в памяти
        процесса, поэтому перезапуск сервера их теряет; итог каждого уходит в
        журнал, он и переживает перезапуск.
        """
        app = self.app
        prefix = "/api/games/dota322"
        client = self.client_address[0] if self.client_address else "?"
        query = self._query()

        try:
            engine = app.dotadraft
            user = app.user_by_token(self._bearer_token())

            # Состояние пула открыто до входа: страница сразу объясняет, что
            # играть можно, и сколько героев на каждую позицию.
            if method == "GET" and path == f"{prefix}/status":
                engine.refresh()
                return self._json({
                    "title": "322-0",
                    "event": "Streamers Battle 13",
                    "players": engine.player_count(),
                    "heroes": engine.hero_count(),
                    "pairs": engine.pair_count(),
                    "known_positions": engine.known_positions(),
                    "positions": [{"position": position, "label": DOTA_POSITION_LABELS[position],
                                   "hint": DOTA_POSITION_HINTS.get(position, ""),
                                   "heroes": engine.position_counts().get(position, 0)}
                                  for position, _ in DOTA_POSITION_LABELS.items()],
                    "budget": DOTA_BUDGET,
                    "squad_size": DOTA_SQUAD_SIZE,
                    "pack": {"players": DOTA_PACK_PLAYERS, "heroes": DOTA_PACK_HEROES},
                    "mid": {"position": DOTA_MID_POSITION,
                            "label": DOTA_POSITION_LABELS.get(DOTA_MID_POSITION, ""),
                            "cost_limit": DOTA_MID_COST_LIMIT},
                    "tournament": {"groups": DOTA_GROUPS, "group_size": DOTA_GROUP_SIZE,
                                   "group_best_of": DOTA_GROUP_BEST_OF,
                                   "opponent_budget_min": DOTA_OPPONENT_MIN,
                                   "opponent_budget_max": DOTA_OPPONENT_MAX},
                    "difficulties": [
                        {"key": key, "label": DOTA_DIFFICULTY_LABELS[key],
                         "budget": DOTA_BUDGETS[key]}
                        for key in DOTA_DIFFICULTIES],
                    "rounds": engine.rounds_catalog(),
                    "ready": engine.ready(),
                    "problems": engine.problems()[:10],
                })

            if method == "GET" and path == f"{prefix}/pool":
                engine.refresh()
                return self._json(engine.pool())

            if not user:
                return self._error("Требуется вход в аккаунт", 401)

            if method == "POST" and path == f"{prefix}/runs":
                if not app.allow_game_action(client):
                    return self._error("Слишком много прогонов за минуту — подождите немного", 429)
                data = self._body()
                return self._json({"state": engine.start(
                    user, difficulty=str(data.get("difficulty") or "hard"))}, 201)

            if method == "GET" and path == f"{prefix}/matches":
                scope = str(query.get("scope") or "mine").lower()
                limit = self._limit_arg(query)
                if scope == "all":
                    if not self._require_admin(user):
                        return self._error("Журнал всех прогонов доступен только администратору", 403)
                    return self._json({"matches": app.db.csdraft_runs(None, limit, "dota322")})
                return self._json({"matches": app.db.csdraft_runs(user["id"], limit, "dota322")})

            run_pattern = rf"{prefix}/runs/(d[0-9a-f]{{7}})"
            match = re.fullmatch(run_pattern, path)
            if method == "GET" and match:
                return self._json({"state": engine.state(match.group(1), user)})

            match = re.fullmatch(rf"{run_pattern}/pack/player", path)
            if method == "POST" and match:
                return self._json({"state": engine.take_player(
                    match.group(1), user, str(self._body().get("player") or ""))})

            match = re.fullmatch(rf"{run_pattern}/pack/hero", path)
            if method == "POST" and match:
                data = self._body()
                return self._json({"state": engine.take_hero(
                    match.group(1), user, str(data.get("hero") or ""),
                    str(data.get("player") or ""))})

            match = re.fullmatch(rf"{run_pattern}/play", path)
            if method == "POST" and match:
                if not app.allow_game_action(client):
                    return self._error("Слишком много матчей за минуту — подождите немного", 429)
                return self._json({"state": engine.play(match.group(1), user)})

            return self._error(f"Не найдено: {method} {path}", 404)
        except DotaDraftError as exc:
            return self._error(str(exc), 400)
        except Exception as exc:  # noqa: BLE001
            return self._error(f"Внутренняя ошибка: {exc}", 500)

    def _handle_draft_games_api(self, method: str, path: str) -> None:
        """Список драфт-игр и их правил: этим страница выбирает игру."""
        if method != "GET" or path != "/api/games/draft/games":
            return self._error(f"Не найдено: {method} {path}", 404)
        return self._json({"games": [game_block(key) for key in GAME_KEYS],
                           "short": games_block()})

    def _handle_raporder_api(self, method: str, path: str) -> None:
        """«Рэп-хронология»: соло-заходы и комнаты, где треки ставят по годам.

        Вход — по аккаунту панели (Bearer): ссылку с кодом комнаты пересылают
        друзьям, и общий ключ в ней был бы утечкой. Правильного порядка и годов
        нет в ответах сервера, пока раунд не закончился: иначе их можно было бы
        просто прочитать.
        """
        app = self.app
        prefix = "/api/games/raporder"
        client = self.client_address[0] if self.client_address else "?"
        query = self._query()

        try:
            user = app.user_by_token(self._bearer_token())

            # Состояние набора открыто: страница должна объяснить, что играть
            # пока нечего, ещё до входа в аккаунт.
            if method == "GET" and path == f"{prefix}/status":
                app.raporder.refresh()
                problems = app.raporder.problems()
                return self._json({
                    "tracks": app.raporder.track_count(),
                    "playable": app.raporder.playable_count(),
                    "years": app.raporder.year_count(),
                    "ready": app.raporder.ready(),
                    "tracks_per_round": RAP_TRACKS_PER_ROUND,
                    "solo_rounds": RAP_ROUNDS,
                    "duel_rounds": DUEL_ROUNDS,
                    "min_players": RAP_MIN_PLAYERS,
                    "max_players": RAP_MAX_PLAYERS,
                    "answer_seconds": RAP_ANSWER_SECONDS,
                    "problems": problems[:10],
                })

            if not user:
                return self._error("Требуется вход в аккаунт", 401)

            if method == "GET" and path == f"{prefix}/matches":
                scope = str(query.get("scope") or "mine").lower()
                mode = str(query.get("mode") or "").strip().lower() or None
                limit = self._limit_arg(query)
                if scope == "all":
                    if not self._require_admin(user):
                        return self._error("Журнал всех партий доступен только администратору", 403)
                    return self._json({"matches": app.db.raporder_matches(None, limit, mode)})
                return self._json({"matches": app.db.raporder_matches(user["id"], limit, mode)})

            if method == "POST" and path == f"{prefix}/solo":
                if not app.allow_game_action(client):
                    return self._error("Слишком много попыток за минуту — подождите немного", 429)
                return self._json({"state": app.raporder.solo_start(user)}, 201)

            match = re.fullmatch(rf"{prefix}/solo/([A-Za-z0-9]+)", path)
            if method == "GET" and match:
                return self._json({"state": app.raporder.solo_state(match.group(1), user)})

            match = re.fullmatch(rf"{prefix}/solo/([A-Za-z0-9]+)/answer", path)
            if method == "POST" and match:
                if not app.allow_game_action(client):
                    return self._error("Слишком много ответов за минуту — подождите немного", 429)
                return self._json({"state": app.raporder.solo_answer(
                    match.group(1), user, self._body().get("order"))})

            if method == "POST" and path == f"{prefix}/rooms":
                if not app.allow_game_action(client):
                    return self._error("Слишком много комнат за минуту — подождите немного", 429)
                return self._json({"state": app.raporder.create(user)}, 201)

            match = re.fullmatch(rf"{prefix}/rooms/([A-Za-z0-9]{{4}})", path)
            if method == "GET" and match:
                return self._json({"state": app.raporder.state(match.group(1), user)})

            match = re.fullmatch(rf"{prefix}/rooms/([A-Za-z0-9]{{4}})/join", path)
            if method == "POST" and match:
                if not app.allow_game_action(client):
                    return self._error("Слишком много попыток войти — подождите минуту", 429)
                return self._json({"state": app.raporder.join(match.group(1), user)})

            match = re.fullmatch(rf"{prefix}/rooms/([A-Za-z0-9]{{4}})/start", path)
            if method == "POST" and match:
                return self._json({"state": app.raporder.start(match.group(1), user)})

            match = re.fullmatch(rf"{prefix}/rooms/([A-Za-z0-9]{{4}})/answer", path)
            if method == "POST" and match:
                if not app.allow_game_action(client):
                    return self._error("Слишком много ответов за минуту — подождите немного", 429)
                return self._json({"state": app.raporder.answer(
                    match.group(1), user, self._body().get("order"))})

            match = re.fullmatch(rf"{prefix}/rooms/([A-Za-z0-9]{{4}})/rematch", path)
            if method == "POST" and match:
                return self._json({"state": app.raporder.rematch(match.group(1), user)})

            return self._error(f"Не найдено: {method} {path}", 404)
        except RapOrderError as exc:
            return self._error(str(exc), 400)
        except Exception as exc:  # noqa: BLE001
            return self._error(f"Внутренняя ошибка: {exc}", 500)

    def _handle_songguess_api(self, method: str, path: str) -> None:
        """«Угадай песню за 10 секунд»: быстрые заходы по темам.

        Вход — по аккаунту панели (Bearer): заход принадлежит игроку, чужой его
        продолжить не может. Верного варианта нет в ответах, пока раунд не
        закончился, а фрагмент отдаётся отдельным адресом — по имени файла песню
        тоже не угадать. Заходы живут в памяти процесса, итог уходит в журнал.
        """
        app = self.app
        prefix = "/api/games/songguess"
        client = self.client_address[0] if self.client_address else "?"
        query = self._query()

        try:
            engine = app.songguess
            user = app.user_by_token(self._bearer_token())

            # Состояние набора открыто до входа: страница сразу объясняет, что
            # играть можно, и в каких темах уже есть записи.
            if method == "GET" and path == f"{prefix}/status":
                engine.refresh()
                return self._json({
                    "title": "Угадай песню за 10 секунд",
                    "tracks": engine.track_count(),
                    "playable": engine.playable_count(),
                    "ready": engine.ready(),
                    "rounds": SONGGUESS_ROUNDS,
                    "slice_seconds": SONGGUESS_SLICE,
                    "categories": engine.categories(),
                    "difficulties": engine.difficulty_blocks(),
                    "problems": engine.problems()[:6],
                })

            if not user:
                return self._error("Требуется вход в аккаунт", 401)

            if method == "POST" and path == f"{prefix}/runs":
                if not app.allow_game_action(client):
                    return self._error("Слишком много попыток за минуту — подождите немного", 429)
                data = self._body()
                return self._json({"state": engine.start(
                    user,
                    category=str(data.get("category") or "anime"),
                    difficulty=str(data.get("difficulty") or "normal"),
                )}, 201)

            if method == "GET" and path == f"{prefix}/matches":
                scope = str(query.get("scope") or "mine").lower()
                category = str(query.get("category") or "").strip().lower() or None
                limit = self._limit_arg(query)
                if scope == "all":
                    if not self._require_admin(user):
                        return self._error("Журнал всех заходов доступен только администратору", 403)
                    return self._json({"matches": app.db.songguess_matches(None, limit, category)})
                return self._json({"matches": app.db.songguess_matches(
                    user["id"], limit, category)})

            run_pattern = rf"{prefix}/runs/(g[0-9a-f]{{7}})"
            match = re.fullmatch(run_pattern, path)
            if method == "GET" and match:
                return self._json({"state": engine.state(match.group(1), user)})

            match = re.fullmatch(rf"{run_pattern}/answer", path)
            if method == "POST" and match:
                return self._json({"state": engine.answer(
                    match.group(1), user, self._body().get("choice"))})

            match = re.fullmatch(rf"{run_pattern}/clip", path)
            if method == "GET" and match:
                track = engine.clip_track(match.group(1), user, self._round_param(query))
                return self._send_clip(track, "songguess")

            return self._error(f"Не найдено: {method} {path}", 404)
        except SongGuessError as exc:
            return self._error(str(exc), 400)
        except Exception as exc:  # noqa: BLE001
            return self._error(f"Внутренняя ошибка: {exc}", 500)

    def _handle_songless_api(self, method: str, path: str) -> None:
        """«Аниме-сонглесс»: соло-заходы и комнаты на несколько игроков.

        Вход — по аккаунту панели (Bearer): ссылку с кодом комнаты пересылают
        друзьям, и общий ключ в ней был бы утечкой. Правильного варианта ответа
        в ответах нет до конца раунда, а фрагмент отдаётся отдельным адресом —
        по имени файла аниме тоже не угадать.
        """
        app = self.app
        prefix = "/api/games/songless"
        client = self.client_address[0] if self.client_address else "?"
        query = self._query()

        try:
            user = app.user_by_token(self._bearer_token())

            # Состояние набора открыто: страница должна объяснить, что играть
            # пока нечего, ещё до входа в аккаунт.
            if method == "GET" and path == f"{prefix}/status":
                app.songless.refresh()
                return self._json({
                    "tracks": app.songless.track_count(),
                    "playable": app.songless.playable_count(),
                    "ready": app.songless.ready(),
                    "rounds": ROUNDS_PER_GAME,
                    "min_players": MIN_PLAYERS,
                    "max_players": MAX_PLAYERS,
                    "answer_seconds": ANSWER_SECONDS,
                    "solo_lives": SOLO_LIVES,
                })

            if not user:
                return self._error("Требуется вход в аккаунт", 401)

            if method == "POST" and path == f"{prefix}/solo":
                if not app.allow_game_action(client):
                    return self._error("Слишком много попыток за минуту — подождите немного", 429)
                return self._json({"state": app.songless.solo_start(user)}, 201)

            match = re.fullmatch(rf"{prefix}/solo/([A-Za-z0-9]+)", path)
            if method == "GET" and match:
                return self._json({"state": app.songless.solo_state(match.group(1), user)})

            match = re.fullmatch(rf"{prefix}/solo/([A-Za-z0-9]+)/answer", path)
            if method == "POST" and match:
                choice = self._body().get("choice")
                return self._json({"state": app.songless.solo_answer(match.group(1), user, choice)})

            match = re.fullmatch(rf"{prefix}/solo/([A-Za-z0-9]+)/clip", path)
            if method == "GET" and match:
                track = app.songless.solo_clip_track(match.group(1), user, self._round_param(query))
                return self._send_clip(track)

            if method == "POST" and path == f"{prefix}/rooms":
                if not app.allow_game_action(client):
                    return self._error("Слишком много комнат за минуту — подождите немного", 429)
                return self._json({"state": app.songless.create(user)}, 201)

            match = re.fullmatch(rf"{prefix}/rooms/([A-Za-z0-9]{{4}})", path)
            if method == "GET" and match:
                return self._json({"state": app.songless.state(match.group(1), user)})

            match = re.fullmatch(rf"{prefix}/rooms/([A-Za-z0-9]{{4}})/join", path)
            if method == "POST" and match:
                if not app.allow_game_action(client):
                    return self._error("Слишком много попыток войти — подождите минуту", 429)
                return self._json({"state": app.songless.join(match.group(1), user)})

            match = re.fullmatch(rf"{prefix}/rooms/([A-Za-z0-9]{{4}})/start", path)
            if method == "POST" and match:
                return self._json({"state": app.songless.start(match.group(1), user)})

            match = re.fullmatch(rf"{prefix}/rooms/([A-Za-z0-9]{{4}})/answer", path)
            if method == "POST" and match:
                choice = self._body().get("choice")
                return self._json({"state": app.songless.answer(match.group(1), user, choice)})

            match = re.fullmatch(rf"{prefix}/rooms/([A-Za-z0-9]{{4}})/rematch", path)
            if method == "POST" and match:
                return self._json({"state": app.songless.rematch(match.group(1), user)})

            match = re.fullmatch(rf"{prefix}/rooms/([A-Za-z0-9]{{4}})/clip", path)
            if method == "GET" and match:
                track = app.songless.clip_track(match.group(1), user, self._round_param(query))
                return self._send_clip(track)

            return self._error(f"Не найдено: {method} {path}", 404)
        except SonglessError as exc:
            return self._error(str(exc), 400)
        except Exception as exc:  # noqa: BLE001
            return self._error(f"Внутренняя ошибка: {exc}", 500)

    @staticmethod
    def _round_param(query: Dict[str, str]) -> Optional[int]:
        """Номер раунда из адреса фрагмента: он же защищает от кеша браузера."""
        raw = query.get("round")
        if raw in (None, ""):
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    # ------------------------------------------------------------- static files
    def _serve_static(self, path: str) -> None:
        if path in ("", "/"):
            path = "/index.html"
        target = (FRONT / path.lstrip("/")).resolve()

        try:
            target.relative_to(FRONT.resolve())
        except ValueError:
            return self._error("Недопустимый путь", 403)

        if target.is_dir():
            target = target / "index.html"
        if not target.exists() or not target.is_file():
            return self._error("Файл не найден", 404)

        mime, _ = mimetypes.guess_type(str(target))
        if target.name.endswith(".webmanifest"):
            mime = "application/manifest+json"
        mime = mime or "application/octet-stream"
        if mime.startswith(("text/", "application/javascript", "application/json")) or target.suffix in (".js", ".css"):
            mime += "; charset=utf-8"
        body = target.read_bytes()

        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self._cors()
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    # ------------------------------------------------------------- songless files
    def _send_clip(self, track: Dict[str, Any], game: str = "animesongless") -> None:
        """Отдаёт запись трека: свой файл — потоком, внешнюю ссылку — перенаправлением.

        Адрес фрагмента не выдаёт, что за песня играет: клиент получает не имя
        файла из базы, а служебный путь комнаты или захода. У игры свои записи
        (`front/games/<игра>/audio`), поэтому каталог передаётся аргументом.
        """
        audio = str(track.get("audio") or "")
        if not audio:
            return self._error("У этой песни нет записи", 404)

        if audio.startswith(("http://", "https://")):
            self.send_response(302)
            self.send_header("Location", audio)
            self.send_header("Content-Length", "0")
            self.send_header("Cache-Control", "no-store")
            self._cors()
            self.end_headers()
            return

        base = (FRONT / "games" / game).resolve()
        target = (base / audio.lstrip("/")).resolve()
        try:
            target.relative_to(base)
        except ValueError:
            return self._error("Недопустимый путь к записи", 403)
        if not target.is_file():
            return self._error("Файл записи не найден на сервере", 404)

        body = target.read_bytes()
        mime = AUDIO_TYPES.get(target.suffix.lower(), "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "private, max-age=600")
        self._cors()
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)


def create_server(host: str, port: int, database: DatabaseLike, serial_port: Optional[str],
                  baud: int, simulator: bool, token: Optional[str] = None,
                  admin_password: Optional[str] = None, device_remote: bool = False,
                  device_token: Optional[str] = None) -> ThreadingHTTPServer:
    database.initialize()
    database.purge_sessions()
    link: DeviceLink
    if device_remote:
        # Плата осталась дома: COM-порт держит агент, а сервер только принимает
        # показания и отдаёт ему команды из очереди.
        link = RemoteDeviceLink(database, token=device_token or "")
    else:
        link = ArduinoLink(database, port=serial_port, baudrate=baud, allow_simulator=simulator)
    app = Application(database, link, token)

    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    server.app = app  # type: ignore[attr-defined]
    # Пароль админа показываем один раз — при самом первом создании аккаунта.
    server.admin_password = app.ensure_admin(admin_password)  # type: ignore[attr-defined]
    app.start()
    return server


def _mask_dsn(dsn: str) -> str:
    """Скрывает пароль в строке подключения, чтобы он не попал в вывод."""
    return re.sub(r"://([^:/@]+):[^@]*@", r"://\1:***@", dsn)


def main() -> None:
    parser = argparse.ArgumentParser(description="Сервер умной теплицы (12 участков)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB,
                        help="файл SQLite (используется, если не задан --dsn)")
    parser.add_argument("--dsn", default=os.environ.get("GREENHOUSE_DSN"),
                        help="строка подключения PostgreSQL, например "
                             "postgresql://greenhouse:пароль@localhost:5432/greenhouse")
    parser.add_argument("--token", default=os.environ.get("GREENHOUSE_TOKEN"),
                        help="API-ключ: если задан, все запросы /api/* требуют заголовок "
                             "X-Api-Token или параметр ?token=...")
    parser.add_argument("--admin-password", default=os.environ.get("GREENHOUSE_ADMIN_PASSWORD"),
                        help="пароль администратора «admin» при самом первом запуске; "
                             "если не задан, сервер сгенерирует и напечатает его")
    parser.add_argument("--serial", dest="serial_port", default=None, help="COM-порт Arduino, например COM3")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--no-simulator", action="store_true", help="запретить эмулятор (нужна реальная плата)")
    parser.add_argument("--device-remote", action="store_true",
                        help="режим домашнего агента: плата не здесь, показания приносит "
                             "device_agent.py, команды уходят через очередь")
    parser.add_argument("--device-token", default=os.environ.get("GREENHOUSE_DEVICE_TOKEN"),
                        help="токен домашнего агента (обязателен вместе с --device-remote)")
    parser.add_argument("--open", action="store_true", help="открыть панель в браузере")
    args = parser.parse_args()

    if args.device_remote and not args.device_token:
        parser.error("режим --device-remote требует --device-token (или GREENHOUSE_DEVICE_TOKEN): "
                     "агент дома доказывает им, что он свой")

    database = open_database(args.db, args.dsn)
    server = create_server(args.host, args.port, database,
                           args.serial_port, args.baud, not args.no_simulator, args.token,
                           args.admin_password, args.device_remote, args.device_token)
    url = f"http://{args.host}:{server.server_port}/"
    print(f"Теплица: {url}")
    print(f"Участков: {ZONE_COUNT}, БД: {_mask_dsn(args.dsn) if args.dsn else args.db}")
    print(f"API-ключ: {'включён' if args.token else 'выключен'}")
    generated = getattr(server, "admin_password", None)
    if generated:
        print(f"Создан администратор «{ADMIN_NAME}». Пароль: {generated}")
        print("Смените пароль после входа или задайте GREENHOUSE_ADMIN_PASSWORD до первого запуска.")
    print(f"Секретная страница: {url}TriEblanaiPraktika")
    # flush: сервер часто запускают как фоновый процесс, и буферизованный вывод
    # со сгенерированным паролем администратора был бы потерян.
    sys.stdout.flush()
    if not args.token and args.host not in ("127.0.0.1", "localhost", "::1"):
        print("ВНИМАНИЕ: сервер опубликован по сети без API-ключа — команды теплице "
              "доступны любому. Задайте --token или GREENHOUSE_TOKEN.", file=sys.stderr)
    if args.device_remote:
        print("Датчики: домашний агент — плата подключена к другому компьютеру "
              "(backend/device_agent.py)")
        print("Раздел агента: POST /api/device/sync и /api/device/ack по устройство-токену")
    else:
        print("Датчики: " + (f"Arduino {args.serial_port}" if args.serial_port
                             else "эмулятор (Arduino не подключена)"))
    if args.open:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановка...")
    finally:
        server.app.stop()  # type: ignore[attr-defined]
        server.server_close()


if __name__ == "__main__":
    main()
