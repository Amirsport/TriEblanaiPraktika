# -*- coding: utf-8 -*-
"""Игра «Аниме-сонглесс»: угадай аниме по фрагменту опенинга.

Два режима:
    * **соло** — серия раундов без соперников: три ошибки (или три пропуска)
      и заход закончен, очки копятся за скорость и точность;
    * **онлайн** — комната на 2..8 человек, пять раундов на всех: раунд идёт
      одновременно, за правильный ответ дают очки, за скорость — добавку;
      после пяти раундов видна общая таблица.

Ответ всегда один — название аниме, а вариантов четыре: верный и три «обманки».
Верный вариант живёт только здесь, на сервере: страница получает варианты и
адрес фрагмента, а название аниме узнаёт лишь после раунда.

Треки приходят из таблицы `songless_tracks` (читает сервер), поэтому набор
правится в базе. Играть можно только те треки, у которых есть запись: сами
записи опенингов защищены авторским правом, поэтому их добавляет владелец
сайта — файлами или ссылками (см. backend/seed_songless.py).

Соло-заходы и комнаты живут в памяти процесса: это партии на несколько минут,
перезапуск сервера им переживать не нужно.
"""
from __future__ import annotations

import random
import sys
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Sequence

try:  # запуск как модуль: python -m backend.server
    from .songless_data import (
        DEFAULT_CLIP,
        DEFAULT_START,
        OPTION_COUNT,
        TRACKS,
        playable,
        public_track,
    )
except ImportError:  # запуск как файл: python backend/server.py
    from songless_data import (  # type: ignore
        DEFAULT_CLIP,
        DEFAULT_START,
        OPTION_COUNT,
        TRACKS,
        playable,
        public_track,
    )

# Брошенная комната живёт два часа, потом исчезает вместе со счётом.
ROOM_TTL_SECONDS = 2 * 60 * 60
# Заброшенный соло-заход убираем быстрее: их можно начать сколько угодно.
RUN_TTL_SECONDS = 30 * 60

MIN_PLAYERS = 2
MAX_PLAYERS = 8
MAX_ROOMS = 200
MAX_RUNS = 400
ROUNDS_PER_GAME = 5

# Сколько даётся на ответ и сколько показываем разбор раунда.
ANSWER_SECONDS = 20.0
REVEAL_SECONDS = 8.0

# Очки: базовые за верный ответ плюс добавка за скорость.
BASE_POINTS = 100
SPEED_POINTS = 60

SOLO_LIVES = 3

# Без похожих символов (I/1, O/0): код диктуют голосом и вводят руками.
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 4


class SonglessError(ValueError):
    """Ошибка правил игры: превращается в ответ 400 с понятным текстом."""


def _positive(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if number > 0 else default


def _clip_of(track: Dict[str, Any]) -> Dict[str, Any]:
    """Что и как долго слушать: начало и длина фрагмента."""
    start = track.get("clip_start")
    length = track.get("clip_length")
    return {
        "start": float(start) if start is not None else DEFAULT_START,
        "length": _positive(length, DEFAULT_CLIP),
    }


class Songless:
    """Соло-заходы и комнаты «Аниме-сонглесса»."""

    def __init__(self, tracks: Optional[Sequence[Dict[str, Any]]] = None,
                 rng: Optional[random.Random] = None,
                 provider: Optional[Callable[[], List[Dict[str, Any]]]] = None) -> None:
        self._lock = threading.Lock()
        self._rooms: Dict[str, Dict[str, Any]] = {}
        self._runs: Dict[str, Dict[str, Any]] = {}
        self._rng = rng or random.Random()
        # Источник набора (обычно таблица в базе): перечитывается перед новым
        # раундом, поэтому правки видны без перезапуска сервера.
        self._provider = provider
        self.reload_tracks(tracks)

    # --------------------------------------------------------------- набор
    def reload_tracks(self, tracks: Optional[Sequence[Dict[str, Any]]] = None) -> int:
        """Берёт набор треков; играбельными считаются только записанные."""
        source = list(tracks) if tracks is not None else [dict(item) for item in TRACKS]
        if not source:
            source = [dict(item) for item in TRACKS]
        self._tracks = [dict(track) for track in source]
        self._playable = [track for track in self._tracks if playable(track)]
        return len(self._tracks)

    def refresh(self) -> int:
        """Перечитывает набор из источника; при сбое остаётся прежний набор."""
        if not self._provider:
            return len(self._tracks)
        try:
            tracks = self._provider()
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"  набор треков недоступен, играем прежним: {exc}\n")
            return len(self._tracks)
        return self.reload_tracks(tracks) if tracks else len(self._tracks)

    def track_count(self) -> int:
        return len(self._tracks)

    def playable_count(self) -> int:
        return len(self._playable)

    def ready(self) -> bool:
        """Играть можно, когда записей хватает на четыре варианта ответа."""
        return len(self._playable) >= OPTION_COUNT

    def _pick_track(self, used: Sequence[str]) -> Dict[str, Any]:
        """Случайный играбельный трек, которого ещё не было в этой партии."""
        fresh = [track for track in self._playable if str(track["anime"]) not in used]
        pool = fresh or self._playable
        return dict(self._rng.choice(pool))

    def _options(self, track: Dict[str, Any]) -> List[str]:
        """Четыре варианта ответа: верный и три чужих аниме, порядок случайный.

        Названия в вариантах не повторяются даже если в наборе случайно
        оказались тёзки: иначе «обманка» совпала бы с верным ответом.
        """
        target = str(track["anime"])
        others = sorted({str(item["anime"]) for item in self._tracks} - {target})
        self._rng.shuffle(others)
        options = [target] + others[:OPTION_COUNT - 1]
        self._rng.shuffle(options)
        return options

    # -------------------------------------------------------------- служебное
    def _cleanup(self, now: float) -> None:
        """Убирает заброшенные комнаты и заходы (вызывать под замком)."""
        for code in [code for code, room in self._rooms.items()
                     if now - room["updated"] > ROOM_TTL_SECONDS]:
            del self._rooms[code]
        for run_id in [run_id for run_id, run in self._runs.items()
                       if now - run["updated"] > RUN_TTL_SECONDS]:
            del self._runs[run_id]

    def _new_code(self) -> str:
        while True:
            code = "".join(self._rng.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
            if code not in self._rooms:
                return code

    def _new_run_id(self) -> str:
        return "s" + "".join(self._rng.choice(CODE_ALPHABET) for _ in range(8))

    def _room(self, code: str) -> Dict[str, Any]:
        room = self._rooms.get((code or "").strip().upper())
        if not room:
            raise SonglessError("Комната не найдена — проверьте код приглашения")
        return room

    def _run(self, run_id: str) -> Dict[str, Any]:
        run = self._runs.get((run_id or "").strip())
        if not run:
            raise SonglessError("Заход не найден — начните новый")
        return run

    @staticmethod
    def _player(room: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        player = room["players"].get(user["id"])
        if not player:
            raise SonglessError("Вы не участник этой комнаты")
        return player

    def _points(self, seconds_left: float) -> int:
        """Очки за верный ответ: базовые плюс доля за оставшееся время."""
        share = max(0.0, min(1.0, seconds_left / _positive(ANSWER_SECONDS, 20.0)))
        return BASE_POINTS + int(round(SPEED_POINTS * share))

    # ------------------------------------------------------------- снимок раунда
    # ------------------------------------------------------------------- соло
    def solo_start(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Начинает соло-заход: раунды идут один за другим до трёх ошибок."""
        now = time.time()
        with self._lock:
            self._cleanup(now)
            self.refresh()
            if not self.ready():
                raise SonglessError(
                    "К игре пока не добавлено ни одной записи: положите файлы в"
                    " front/games/animesongless/audio или укажите ссылки в базе")
            if len(self._runs) >= MAX_RUNS:
                raise SonglessError("Слишком много заходов сразу, попробуйте через минуту")
            run_id = self._new_run_id()
            run: Dict[str, Any] = {
                "id": run_id,
                "user_id": user["id"],
                "user_name": user["username"],
                "created": now,
                "updated": now,
                "score": 0,
                "lives": SOLO_LIVES,
                "rounds": 0,
                "correct": 0,
                "used": [],
                "finished": False,
                "round": None,
            }
            self._start_solo_round(run, now)
            self._runs[run_id] = run
            return self._solo_payload(run, now)

    def solo_state(self, run_id: str, user: Dict[str, Any]) -> Dict[str, Any]:
        now = time.time()
        with self._lock:
            self._cleanup(now)
            run = self._run(run_id)
            self._check_owner(run, user)
            self._advance_solo(run, now)
            return self._solo_payload(run, now)

    def solo_answer(self, run_id: str, user: Dict[str, Any], choice: int) -> Dict[str, Any]:
        now = time.time()
        with self._lock:
            self._cleanup(now)
            run = self._run(run_id)
            self._check_owner(run, user)
            self._advance_solo(run, now)
            self._take_answer(run, run["round"], choice, now)
            run["updated"] = now
            return self._solo_payload(run, now)

    def solo_clip_track(self, run_id: str, user: Dict[str, Any],
                        number: Optional[int]) -> Dict[str, Any]:
        """Трек текущего раунда захода — для отдачи аудио."""
        now = time.time()
        with self._lock:
            self._cleanup(now)
            run = self._run(run_id)
            self._check_owner(run, user)
            self._advance_solo(run, now)
            round_ = run["round"]
            if round_ is None or (number is not None and int(number) != round_["number"]):
                raise SonglessError("Этот раунд уже прошёл")
            return dict(round_["track"])

    @staticmethod
    def _check_owner(run: Dict[str, Any], user: Dict[str, Any]) -> None:
        if run["user_id"] != user["id"]:
            raise SonglessError("Это чужой заход")

    def _start_solo_round(self, run: Dict[str, Any], now: float) -> None:
        self.refresh()
        if len(run["used"]) >= max(1, len(self._playable)):
            run["used"] = []      # записей меньше, чем раундов: начинаем по кругу
        track = self._pick_track(run["used"])
        run["used"].append(str(track["anime"]))
        options = self._options(track)
        run["round"] = {
            "number": run["rounds"] + 1,
            "track": track,
            "options": options,
            "answer_index": options.index(str(track["anime"])),
            "started": now,
            "deadline": now + _positive(ANSWER_SECONDS, 20.0),
            "choice": None,
            "correct": None,
            "points": 0,
            "missed": False,
            "reveal_until": None,
        }
        run["rounds"] = run["round"]["number"]
        run["updated"] = now

    def _advance_solo(self, run: Dict[str, Any], now: float) -> None:
        """Ленивые переходы: время вышло — засчитываем пропуск, разбор кончился — новый раунд."""
        round_ = run["round"]
        if round_ is None:
            return
        if round_["choice"] is None and not round_["missed"] and now > round_["deadline"]:
            self._miss(run, round_, now)
        if round_["reveal_until"] and now >= round_["reveal_until"]:
            if run["lives"] > 0:
                self._start_solo_round(run, now)
            else:
                run["finished"] = True
                run["round"] = None

    def _miss(self, run: Dict[str, Any], round_: Dict[str, Any], now: float) -> None:
        """Пропуск по времени в соло: это такая же ошибка, как неверный ответ."""
        round_["missed"] = True
        round_["points"] = 0
        run["lives"] = max(0, run.get("lives", SOLO_LIVES) - 1)
        round_["reveal_until"] = now + _positive(REVEAL_SECONDS, 8.0)

    def _take_answer(self, run: Dict[str, Any], round_: Dict[str, Any],
                     choice: Any, now: float) -> None:
        """Принимает выбор игрока: очки, жизнь и переход к разбору."""
        if round_ is None:
            raise SonglessError("Заход закончен — начните новый")
        if round_["choice"] is not None or round_["missed"]:
            raise SonglessError("Вы уже ответили в этом раунде")
        try:
            index = int(choice)
        except (TypeError, ValueError):
            raise SonglessError("Выберите один из вариантов") from None
        if not 0 <= index < len(round_["options"]):
            raise SonglessError("Такого варианта ответа нет")
        correct = index == round_["answer_index"]
        round_["choice"] = index
        round_["correct"] = correct
        round_["reveal_until"] = now + _positive(REVEAL_SECONDS, 8.0)
        if correct:
            points = self._points(round_["deadline"] - now)
            round_["points"] = points
            run["score"] = run.get("score", 0) + points
            run["correct"] = run.get("correct", 0) + 1
        else:
            run["lives"] = max(0, run.get("lives", SOLO_LIVES) - 1)

    def _solo_payload(self, run: Dict[str, Any], now: float) -> Dict[str, Any]:
        round_ = run["round"]
        finished = bool(run["finished"]) or round_ is None
        revealed = bool(round_ and (round_["choice"] is not None or round_["missed"]))
        payload: Dict[str, Any] = {
            "run": run["id"],
            "mode": "solo",
            "player": {"id": run["user_id"], "name": run["user_name"]},
            "score": run["score"],
            "lives": run["lives"],
            "lives_total": SOLO_LIVES,
            "rounds": run["rounds"],
            "round": run["rounds"],
            "correct": run["correct"],
            "finished": finished,
            "phase": "finished" if finished else ("reveal" if revealed else "round"),
            "track_count": len(self._tracks),
            "playable_count": len(self._playable),
            "seconds_left": None,
            "reveal_in": None,
            "options": [],
            "choice": None,
            "correct_choice": None,
            "points": None,
            "answer": None,
            "clip": None,
            "updated": round(run["updated"], 3),
        }
        if round_ is None:
            return payload
        payload["round"] = round_["number"]
        payload["options"] = list(round_["options"])
        payload["choice"] = round_["choice"]
        payload["correct_choice"] = round_["answer_index"]
        payload["points"] = round_["points"]
        payload["clip"] = {
            "url": f"/api/games/songless/solo/{run['id']}/clip?round={round_['number']}",
            "start": _clip_of(round_["track"])["start"],
            "length": _clip_of(round_["track"])["length"],
        }
        if revealed:
            payload["answer"] = public_track(round_["track"])
            payload["missed"] = bool(round_["missed"])
            payload["reveal_in"] = max(0.0, round((round_["reveal_until"] or now) - now, 1))
        else:
            payload["seconds_left"] = max(0.0, round(round_["deadline"] - now, 1))
        return payload

    # ------------------------------------------------------------------ онлайн
    def create(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Создаёт комнату: игрок становится первым и ждёт остальных."""
        now = time.time()
        with self._lock:
            self._cleanup(now)
            self.refresh()
            if not self.ready():
                raise SonglessError(
                    "К игре пока не добавлено ни одной записи: положите файлы в"
                    " front/games/animesongless/audio или укажите ссылки в базе")
            if len(self._rooms) >= MAX_ROOMS:
                raise SonglessError("На сервере слишком много активных комнат, попробуйте позже")
            code = self._new_code()
            room: Dict[str, Any] = {
                "code": code,
                "created": now,
                "updated": now,
                "phase": "waiting",
                "host_id": user["id"],
                "players": {user["id"]: self._new_player(user)},
                "order": [user["id"]],
                "round": None,
                "rounds": 0,
                "used": [],
                "history": [],
                "standings": [],
            }
            self._rooms[code] = room
            return self._payload(room, user, now)

    @staticmethod
    def _new_player(user: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": user["id"],
            "name": user["username"],
            "score": 0,
            "correct": 0,
            "time": 0.0,
            "choice": None,
            "correct_choice": None,
            "points": 0,
            "missed": False,
        }

    def join(self, code: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Входит в комнату до начала игры (повторный вход ничего не ломает)."""
        now = time.time()
        with self._lock:
            self._cleanup(now)
            room = self._room(code)
            if user["id"] not in room["players"]:
                if room["phase"] != "waiting":
                    raise SonglessError("Игра уже началась — дождитесь следующей")
                if len(room["players"]) >= MAX_PLAYERS:
                    raise SonglessError(f"В комнате уже {MAX_PLAYERS} игроков")
                room["players"][user["id"]] = self._new_player(user)
                room["order"].append(user["id"])
            room["updated"] = now
            return self._payload(room, user, now)

    def start(self, code: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Начинает партию: только хозяин комнаты и не меньше двух игроков."""
        now = time.time()
        with self._lock:
            self._cleanup(now)
            room = self._room(code)
            self._player(room, user)
            if room["phase"] != "waiting":
                raise SonglessError("Игра уже идёт")
            if user["id"] != room["host_id"]:
                raise SonglessError("Игру начинает тот, кто создал комнату")
            if len(room["players"]) < MIN_PLAYERS:
                raise SonglessError("Нужен хотя бы один соперник: отправьте ссылку другу")
            self._start_round(room, now)
            return self._payload(room, user, now)

    def state(self, code: str, user: Dict[str, Any]) -> Dict[str, Any]:
        now = time.time()
        with self._lock:
            self._cleanup(now)
            room = self._room(code)
            self._player(room, user)
            self._advance(room, now)
            return self._payload(room, user, now)

    def answer(self, code: str, user: Dict[str, Any], choice: Any) -> Dict[str, Any]:
        now = time.time()
        with self._lock:
            self._cleanup(now)
            room = self._room(code)
            player = self._player(room, user)
            self._advance(room, now)
            round_ = room["round"]
            if room["phase"] != "round" or round_ is None:
                raise SonglessError("Сейчас не время отвечать")
            if player["choice"] is not None or player["missed"]:
                raise SonglessError("Вы уже ответили в этом раунде")
            try:
                index = int(choice)
            except (TypeError, ValueError):
                raise SonglessError("Выберите один из вариантов") from None
            if not 0 <= index < len(round_["options"]):
                raise SonglessError("Такого варианта ответа нет")
            correct = index == round_["answer_index"]
            player["choice"] = index
            player["correct_choice"] = correct
            if correct:
                points = self._points(round_["deadline"] - now)
                player["points"] = points
                player["score"] += points
                player["correct"] += 1
            player["time"] += max(0.0, round(now - round_["started"], 3))
            room["updated"] = now
            self._maybe_reveal(room, now)
            return self._payload(room, user, now)

    def rematch(self, code: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Начинает новую партию в той же комнате (счёт обнуляется)."""
        now = time.time()
        with self._lock:
            self._cleanup(now)
            room = self._room(code)
            self._player(room, user)
            if room["phase"] != "finished":
                raise SonglessError("Партия ещё идёт")
            for player in room["players"].values():
                player.update(
                    score=0, correct=0, time=0.0, choice=None,
                    correct_choice=None, points=0, missed=False)
            room["used"] = []
            room["rounds"] = 0
            room["round"] = None
            room["history"] = []
            room["standings"] = []
            self._start_round(room, now)
            return self._payload(room, user, now)

    def clip_track(self, code: str, user: Dict[str, Any],
                   number: Optional[int]) -> Dict[str, Any]:
        """Трек текущего раунда комнаты — для отдачи аудио."""
        now = time.time()
        with self._lock:
            self._cleanup(now)
            room = self._room(code)
            self._player(room, user)
            self._advance(room, now)
            round_ = room["round"]
            if round_ is None or (number is not None and int(number) != round_["number"]):
                raise SonglessError("Этот раунд уже прошёл")
            return dict(round_["track"])

    def stats(self) -> Dict[str, int]:
        with self._lock:
            self._cleanup(time.time())
            return {
                "rooms": len(self._rooms),
                "runs": len(self._runs),
                "players": sum(len(room["players"]) for room in self._rooms.values()),
                "playable": len(self._playable),
                "tracks": len(self._tracks),
            }

    # -------------------------------------------------------- ход партии
    def _start_round(self, room: Dict[str, Any], now: float) -> None:
        self.refresh()
        if len(room["used"]) >= max(1, len(self._playable)):
            room["used"] = []
        track = self._pick_track(room["used"])
        room["used"].append(str(track["anime"]))
        options = self._options(track)
        room["round"] = {
            "number": room["rounds"] + 1,
            "track": track,
            "options": options,
            "answer_index": options.index(str(track["anime"])),
            "started": now,
            "deadline": now + _positive(ANSWER_SECONDS, 20.0),
            "reveal_until": None,
        }
        room["rounds"] = room["round"]["number"]
        room["phase"] = "round"
        for player in room["players"].values():
            player["choice"] = None
            player["correct_choice"] = None
            player["points"] = 0
            player["missed"] = False
        room["updated"] = now

    def _maybe_reveal(self, room: Dict[str, Any], now: float) -> None:
        """Раунд кончается, когда ответили все (или вышло время)."""
        if room["phase"] != "round" or room["round"] is None:
            return
        round_ = room["round"]
        answered = all(player["choice"] is not None or player["missed"]
                       for player in room["players"].values())
        if answered or now >= round_["deadline"]:
            for player in room["players"].values():
                if player["choice"] is None and not player["missed"]:
                    player["missed"] = True
            round_["reveal_until"] = now + _positive(REVEAL_SECONDS, 8.0)
            room["phase"] = "reveal"
            room["updated"] = now
            room["history"].append({
                "round": round_["number"],
                "answer": public_track(round_["track"]),
                "choices": {player["name"]: player["choice"]
                            for player in room["players"].values()},
                "points": {player["name"]: player["points"]
                           for player in room["players"].values()},
            })

    def _advance(self, room: Dict[str, Any], now: float) -> None:
        """Ленивые переходы: раунд → разбор → следующий раунд → итог."""
        if room["phase"] == "round":
            self._maybe_reveal(room, now)
        if room["phase"] == "reveal" and room["round"] is not None:
            if now >= (room["round"]["reveal_until"] or now):
                if room["rounds"] >= ROUNDS_PER_GAME:
                    room["standings"] = self._standings(room)
                    room["phase"] = "finished"
                    room["round"] = None
                    room["updated"] = now
                else:
                    self._start_round(room, now)

    def _standings(self, room: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Таблица очков: очки, потом точность, потом меньшее время."""
        players = sorted(
            room["players"].values(),
            key=lambda player: (-player["score"], -player["correct"], player["time"],
                                room["order"].index(player["id"])),
        )
        best = max([player["score"] for player in players] or [0])
        return [
            {
                "place": place,
                "id": player["id"],
                "name": player["name"],
                "score": player["score"],
                "correct": player["correct"],
                "time": round(player["time"], 1),
                "winner": bool(player["score"] == best and best > 0),
            }
            for place, player in enumerate(players, start=1)
        ]

    def _payload(self, room: Dict[str, Any], user: Dict[str, Any], now: float) -> Dict[str, Any]:
        """Состояние комнаты с точки зрения одного игрока.

        Верного варианта здесь нет, пока раунд не закончился: иначе ответ
        читался бы прямо из ответа сервера.
        """
        player = room["players"][user["id"]]
        round_ = room["round"]
        phase = room["phase"]
        revealed = phase in ("reveal", "finished")
        payload: Dict[str, Any] = {
            "code": room["code"],
            "mode": "online",
            "phase": phase,
            "round": round_["number"] if round_ else room["rounds"],
            "rounds_planned": ROUNDS_PER_GAME,
            "min_players": MIN_PLAYERS,
            "max_players": MAX_PLAYERS,
            "host": room["host_id"] == user["id"],
            "players": [
                {
                    "id": item["id"],
                    "name": item["name"],
                    "score": item["score"],
                    "answered": item["choice"] is not None or item["missed"],
                }
                for item in room["players"].values()
            ],
            "you": {
                "id": player["id"],
                "name": player["name"],
                "score": player["score"],
                "correct": player["correct"],
                "choice": player["choice"],
                "correct_choice": player["correct_choice"],
                "points": player["points"],
                "missed": player["missed"],
            },
            "track_count": len(self._tracks),
            "playable_count": len(self._playable),
            "options": [],
            "clip": None,
            "answer": None,
            "choices": {},
            "history": list(room["history"]),
            "standings": list(room["standings"]),
            "seconds_left": None,
            "reveal_in": None,
            "updated": round(room["updated"], 3),
        }
        if round_ is None:
            return payload
        payload["clip"] = {
            "url": f"/api/games/songless/rooms/{room['code']}/clip?round={round_['number']}",
            "start": _clip_of(round_["track"])["start"],
            "length": _clip_of(round_["track"])["length"],
        }
        payload["options"] = list(round_["options"])
        payload["choices"] = {
            item["name"]: item["choice"] for item in room["players"].values()
        }
        if revealed:
            payload["answer"] = public_track(round_["track"])
            payload["correct_choice"] = round_["answer_index"]
            if phase == "reveal":
                payload["reveal_in"] = max(0.0, round((round_["reveal_until"] or now) - now, 1))
        else:
            payload["seconds_left"] = max(0.0, round(round_["deadline"] - now, 1))
        return payload


__all__ = [
    "ANSWER_SECONDS",
    "MAX_PLAYERS",
    "MIN_PLAYERS",
    "ROUNDS_PER_GAME",
    "SOLO_LIVES",
    "Songless",
    "SonglessError",
]
