# -*- coding: utf-8 -*-
"""«Рэп-хронология» — игра про порядок треков русского рэпа по годам.

Правила простые и целиком про даты:
    * в раунде пять треков, все — разных годов, и их надо расставить от самого
      старого к самому новому (перетаскиванием или кнопками);
    * очки за раунд — сколько треков встало на своё место (от 0 до 5): угадать
      весь порядок целиком не обязательно, частичный ответ тоже считается;
    * соло — пять раундов подряд, игра идёт на сумму очков;
    * онлайн — компания в комнате по коду: один и тот же раунд у всех, раунд
      выигрывает тот, кто расставил лучше (при равенстве раунд ничейный),
      партия идёт три раунда.

Раунд кончается, когда ответили все (или вышло время); потом показывается
разбор с годами, и начинается следующий раунд. Текстов песен и аудио в игре
нет — только исполнитель, название и год.
"""
from __future__ import annotations

import random
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

try:  # запуск как модуль: python -m backend.server
    from .raporder_data import (
        DUEL_ROUNDS,
        ROUNDS_PER_GAME,
        TRACKS_PER_ROUND,
        tracks as default_tracks,
        validate,
    )
except ImportError:  # запуск как файл: python backend/server.py
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from raporder_data import (  # type: ignore
        DUEL_ROUNDS,
        ROUNDS_PER_GAME,
        TRACKS_PER_ROUND,
        tracks as default_tracks,
        validate,
    )

# Брошенная комната живёт два часа, заброшенный соло-заход — полчаса.
ROOM_TTL_SECONDS = 2 * 60 * 60
RUN_TTL_SECONDS = 30 * 60

MIN_PLAYERS = 2
MAX_PLAYERS = 8
MAX_ROOMS = 200
MAX_RUNS = 400

# Сколько даётся на расстановку и сколько показывается разбор раунда.
ANSWER_SECONDS = 120.0
REVEAL_SECONDS = 15.0

# Без похожих символов (I/1, O/0): код диктуют голосом и вводят руками.
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 4


class RapOrderError(ValueError):
    """Ошибка правил игры: превращается в ответ 400 с понятным текстом."""


def _positive(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if number > 0 else default


def public_track(track: Dict[str, Any], with_year: bool = False) -> Dict[str, Any]:
    """Трек для страницы: год отдаём только в разборе раунда."""
    item = {
        "id": str(track["id"]),
        "artist": str(track["artist"]),
        "title": str(track["title"]),
    }
    if with_year:
        item["year"] = int(track["year"])
    return item


class RapOrder:
    """Соло-заходы и комнаты «Рэп-хронологии»."""

    def __init__(self, tracks: Optional[Sequence[Dict[str, Any]]] = None,
                 rng: Optional[random.Random] = None,
                 provider: Optional[Callable[[], List[Dict[str, Any]]]] = None,
                 on_finish: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        self._lock = threading.Lock()
        self._rooms: Dict[str, Dict[str, Any]] = {}
        self._runs: Dict[str, Dict[str, Any]] = {}
        self._rng = rng or random.Random()
        # Источник набора (обычно таблица в базе): перечитывается перед новым
        # раундом, поэтому правки годов видны без перезапуска сервера.
        self._provider = provider
        self._on_finish = on_finish
        self.reload_tracks(tracks)

    # --------------------------------------------------------------- набор
    def reload_tracks(self, tracks: Optional[Sequence[Dict[str, Any]]] = None) -> int:
        """Берёт набор треков: играбельными считаются записи с годом."""
        source = list(tracks) if tracks is not None else [dict(item) for item in default_tracks()]
        if not source:
            source = [dict(item) for item in default_tracks()]
        self._tracks = [self._normalize(track) for track in source]
        self._playable = [track for track in self._tracks if int(track.get("year") or 0) > 0]
        return len(self._tracks)

    @staticmethod
    def _normalize(track: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": str(track.get("id") or ""),
            "artist": str(track.get("artist") or ""),
            "title": str(track.get("title") or ""),
            "year": int(track.get("year") or 0),
        }

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
        """Сколько треков годится для раундов: нужен заполненный год."""
        return len([track for track in self._playable if track["id"] and track["title"]])

    def year_count(self) -> int:
        """Сколько разных годов в наборе: раунду нужно пять."""
        return len({int(track["year"]) for track in self._playable})

    def ready(self) -> bool:
        """Играть можно, когда в наборе хватает разных годов на раунд."""
        return self.playable_count() >= TRACKS_PER_ROUND and self.year_count() >= TRACKS_PER_ROUND

    def stats(self) -> Dict[str, int]:
        with self._lock:
            self._cleanup(time.time())
            return {
                "rooms": len(self._rooms),
                "runs": len(self._runs),
                "tracks": len(self._tracks),
                "years": self.year_count(),
                "players": sum(len(room["players"]) for room in self._rooms.values()),
            }

    def problems(self) -> List[str]:
        """Что не так с набором: пустые поля, повтор id, мало разных годов."""
        return validate(self._tracks)

    # ------------------------------------------------------------ раунды
    def _round_tracks(self, used: Sequence[str]) -> List[Dict[str, Any]]:
        """Пять треков разных годов, которых ещё не было в этой партии.

        Годы в раунде обязаны отличаться: иначе «правильный порядок» был бы
        неоднозначным и игрок мог угадать верно, а получить меньше очков.
        """
        used_ids = {str(item) for item in used}
        fresh = [track for track in self._playable if track["id"] not in used_ids]
        pool = fresh if len({track["year"] for track in fresh}) >= TRACKS_PER_ROUND \
            else list(self._playable)
        by_year: Dict[int, List[Dict[str, Any]]] = {}
        for track in pool:
            by_year.setdefault(int(track["year"]), []).append(track)
        years = list(by_year)
        self._rng.shuffle(years)
        chosen: List[Dict[str, Any]] = []
        for year in years[:TRACKS_PER_ROUND]:
            chosen.append(dict(self._rng.choice(by_year[year])))
        self._rng.shuffle(chosen)
        return chosen

    def _round(self, number: int, now: float, used: Sequence[str]) -> Dict[str, Any]:
        tracks = self._round_tracks(used)
        correct = sorted(tracks, key=lambda track: (int(track["year"]), track["title"]))
        return {
            "number": number,
            "tracks": tracks,
            "answer": [track["id"] for track in correct],
            "started": now,
            "deadline": now + _positive(ANSWER_SECONDS, 120.0),
            "reveal_until": None,
        }

    @staticmethod
    def _score(order: Sequence[str], round_: Dict[str, Any]) -> int:
        """Очки за расстановку: сколько треков стоит на своём месте."""
        answer = [str(item) for item in round_["answer"]]
        given = [str(item) for item in order]
        return sum(1 for index, item in enumerate(given[:len(answer)]) if item == answer[index])

    @staticmethod
    def _clean_order(order: Any, round_: Dict[str, Any]) -> List[str]:
        """Приводит присланную расстановку к списку треков раунда.

        Принимаются только треки этого раунда и без повторов: всё остальное
        отбрасывается, чтобы нельзя было подсунуть свои идентификаторы.
        """
        valid = [str(track["id"]) for track in round_["tracks"]]
        if order is None:
            raise RapOrderError("Пришлите порядок треков: order — список идентификаторов")
        if not isinstance(order, (list, tuple)):
            raise RapOrderError("Порядок треков должен быть списком идентификаторов")
        result: List[str] = []
        for item in order:
            track_id = str(item)
            if track_id in valid and track_id not in result:
                result.append(track_id)
        for track_id in valid:
            if track_id not in result:
                result.append(track_id)
        return result

    def _finish_report(self, record: Dict[str, Any]) -> None:
        """Итог партии уходит в журнал: он виден и игроку, и админу."""
        if self._on_finish is None:
            return
        try:
            self._on_finish(record)
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"  итог партии не попал в журнал: {exc}\n")

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
        return "r" + "".join(self._rng.choice(CODE_ALPHABET) for _ in range(8))

    def _room(self, code: str) -> Dict[str, Any]:
        room = self._rooms.get((code or "").strip().upper())
        if not room:
            raise RapOrderError("Комната не найдена — проверьте код приглашения")
        return room

    def _run(self, run_id: str) -> Dict[str, Any]:
        run = self._runs.get((run_id or "").strip())
        if not run:
            raise RapOrderError("Заход не найден — начните новый")
        return run

    @staticmethod
    def _player(room: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        player = room["players"].get(user["id"])
        if not player:
            raise RapOrderError("Вы не участник этой комнаты")
        return player

    @staticmethod
    def _check_owner(run: Dict[str, Any], user: Dict[str, Any]) -> None:
        if user.get("role") == "admin":
            return
        if int(run["user_id"]) != int(user.get("id") or 0):
            raise RapOrderError("Это чужой заход")

    # ------------------------------------------------------------------- соло
    def solo_start(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Начинает соло-заход: пять раундов подряд, игра на сумму очков."""
        now = time.time()
        with self._lock:
            self._cleanup(now)
            self.refresh()
            if not self.ready():
                raise RapOrderError(
                    "К игре пока не добавлено достаточно треков с годами: нужно"
                    " минимум пять разных годов (см. backend/seed_raporder.py)")
            if len(self._runs) >= MAX_RUNS:
                oldest = min(self._runs, key=lambda key: self._runs[key]["updated"])
                self._runs.pop(oldest, None)
            run: Dict[str, Any] = {
                "id": self._new_run_id(),
                "mode": "solo",
                "user_id": int(user.get("id") or 0),
                "username": user.get("username") or "",
                "created": now,
                "updated": now,
                "phase": "round",
                "rounds": 0,
                "round": None,
                "used": [],
                "history": [],
                "total": 0,
                "perfect": 0,
                "finished": False,
            }
            self._start_solo_round(run, now)
            self._runs[run["id"]] = run
            return self._solo_payload(run, user, now)

    def solo_state(self, run_id: str, user: Dict[str, Any]) -> Dict[str, Any]:
        now = time.time()
        with self._lock:
            self._cleanup(now)
            run = self._run(run_id)
            self._check_owner(run, user)
            self._advance_solo(run, now)
            return self._solo_payload(run, user, now)

    def solo_answer(self, run_id: str, user: Dict[str, Any], order: Any) -> Dict[str, Any]:
        """Принимает расстановку раунда и сразу показывает разбор."""
        now = time.time()
        with self._lock:
            self._cleanup(now)
            run = self._run(run_id)
            self._check_owner(run, user)
            self._advance_solo(run, now)
            round_ = run["round"]
            if run["phase"] != "round" or round_ is None:
                raise RapOrderError("Сейчас не время расставлять треки")
            self._take_solo_answer(run, round_, order, now)
            return self._solo_payload(run, user, now)

    def _start_solo_round(self, run: Dict[str, Any], now: float) -> None:
        self.refresh()
        round_ = self._round(run["rounds"] + 1, now, run["used"])
        run["round"] = round_
        run["rounds"] = round_["number"]
        run["phase"] = "round"
        for track in round_["tracks"]:
            run["used"].append(str(track["id"]))
        run["updated"] = now

    def _take_solo_answer(self, run: Dict[str, Any], round_: Dict[str, Any],
                          order: Any, now: float, missed: bool = False) -> None:
        given = [] if missed else self._clean_order(order, round_)
        points = self._score(given, round_)
        round_["order"] = given
        round_["points"] = points
        round_["missed"] = bool(missed)
        round_["reveal_until"] = now + _positive(REVEAL_SECONDS, 15.0)
        run["total"] += points
        if points == len(round_["answer"]):
            run["perfect"] += 1
        run["phase"] = "reveal"
        run["history"].append({
            "round": round_["number"],
            "points": points,
            "best": len(round_["answer"]),
            "tracks": [public_track(track, True) for track in self._reveal_order(round_)],
        })
        run["updated"] = now

    @staticmethod
    def _reveal_order(round_: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Треки раунда в правильном порядке — для разбора."""
        by_id = {str(track["id"]): track for track in round_["tracks"]}
        return [by_id[track_id] for track_id in round_["answer"] if track_id in by_id]

    def _advance_solo(self, run: Dict[str, Any], now: float) -> None:
        """Ленивые переходы: раунд → разбор → следующий раунд → итог."""
        if run["phase"] == "round" and run["round"] is not None:
            if now >= run["round"]["deadline"]:
                self._take_solo_answer(run, run["round"], [], now, missed=True)
        if run["phase"] == "reveal" and run["round"] is not None:
            if now >= (run["round"]["reveal_until"] or now):
                if run["rounds"] >= ROUNDS_PER_GAME:
                    run["phase"] = "finished"
                    run["round"] = None
                    run["updated"] = now
                    if not run["finished"]:
                        run["finished"] = True
                        self._finish_solo(run)
                else:
                    self._start_solo_round(run, now)

    def _finish_solo(self, run: Dict[str, Any]) -> None:
        best = ROUNDS_PER_GAME * TRACKS_PER_ROUND
        self._finish_report({
            "mode": "solo",
            "room": "",
            "rounds": ROUNDS_PER_GAME,
            "player1_id": run["user_id"],
            "player1_name": run["username"],
            "player1_score": int(run["total"]),
            "player2_id": None,
            "player2_name": "",
            "player2_score": 0,
            "winner_id": run["user_id"],
            "winner_name": run["username"],
            "detail": f"{run['total']} из {best}, идеальных раундов {run['perfect']}",
        })

    def _solo_payload(self, run: Dict[str, Any], user: Dict[str, Any],
                      now: float) -> Dict[str, Any]:
        """Состояние захода: правильный порядок виден только в разборе."""
        round_ = run["round"]
        payload: Dict[str, Any] = {
            "id": run["id"],
            "mode": "solo",
            "game": "raporder",
            "phase": run["phase"],
            "round": round_["number"] if round_ else run["rounds"],
            "rounds_planned": ROUNDS_PER_GAME,
            "tracks_per_round": TRACKS_PER_ROUND,
            "total": int(run["total"]),
            "perfect": int(run["perfect"]),
            "best_possible": ROUNDS_PER_GAME * TRACKS_PER_ROUND,
            "rounds_left": max(0, ROUNDS_PER_GAME - run["rounds"]),
            "history": list(run["history"]),
            "seconds_left": None,
            "reveal_in": None,
            "tracks": [],
            "answer": [],
            "points": None,
            "missed": False,
            "track_count": len(self._tracks),
        }
        if round_ is None:
            return payload
        revealed = run["phase"] in ("reveal", "finished")
        payload["tracks"] = [public_track(track) for track in round_["tracks"]]
        if revealed:
            payload["answer"] = [public_track(track, True) for track in self._reveal_order(round_)]
            payload["points"] = int(round_.get("points") or 0)
            payload["best"] = len(round_["answer"])
            payload["missed"] = bool(round_.get("missed"))
            if run["phase"] == "reveal":
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
                raise RapOrderError(
                    "К игре пока не добавлено достаточно треков с годами: нужно"
                    " минимум пять разных годов (см. backend/seed_raporder.py)")
            if len(self._rooms) >= MAX_ROOMS:
                raise RapOrderError("На сервере слишком много активных комнат, попробуйте позже")
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
                "finished": False,
            }
            self._rooms[code] = room
            return self._payload(room, user, now)

    @staticmethod
    def _new_player(user: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": user["id"],
            "name": user["username"],
            "order": [],
            "points": 0,
            "rounds_won": 0,
            "total": 0,
            "submitted": False,
            "missed": False,
        }

    def join(self, code: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Входит в комнату до начала партии (повторный вход ничего не ломает)."""
        now = time.time()
        with self._lock:
            self._cleanup(now)
            room = self._room(code)
            if user["id"] not in room["players"]:
                if room["phase"] != "waiting":
                    raise RapOrderError("Партия уже началась — дождитесь следующей")
                if len(room["players"]) >= MAX_PLAYERS:
                    raise RapOrderError(f"В комнате уже {MAX_PLAYERS} игроков")
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
                raise RapOrderError("Партия уже идёт")
            if user["id"] != room["host_id"]:
                raise RapOrderError("Партию начинает тот, кто создал комнату")
            if len(room["players"]) < MIN_PLAYERS:
                raise RapOrderError("Нужен хотя бы один соперник: отправьте ссылку другу")
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

    def answer(self, code: str, user: Dict[str, Any], order: Any) -> Dict[str, Any]:
        """Принимает расстановку игрока; раунд кончается, когда ответили все."""
        now = time.time()
        with self._lock:
            self._cleanup(now)
            room = self._room(code)
            player = self._player(room, user)
            self._advance(room, now)
            round_ = room["round"]
            if room["phase"] != "round" or round_ is None:
                raise RapOrderError("Сейчас не время расставлять треки")
            if player["submitted"]:
                raise RapOrderError("Вы уже ответили в этом раунде")
            given = self._clean_order(order, round_)
            player["order"] = given
            player["points"] = self._score(given, round_)
            player["total"] += player["points"]
            player["submitted"] = True
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
                raise RapOrderError("Партия ещё идёт")
            for player in room["players"].values():
                player.update(order=[], points=0, rounds_won=0, total=0,
                              submitted=False, missed=False)
            room["used"] = []
            room["rounds"] = 0
            room["round"] = None
            room["history"] = []
            room["standings"] = []
            room["finished"] = False
            self._start_round(room, now)
            return self._payload(room, user, now)

    # -------------------------------------------------------- ход партии
    def _start_round(self, room: Dict[str, Any], now: float) -> None:
        self.refresh()
        round_ = self._round(room["rounds"] + 1, now, room["used"])
        room["round"] = round_
        room["rounds"] = round_["number"]
        room["phase"] = "round"
        for track in round_["tracks"]:
            room["used"].append(str(track["id"]))
        for player in room["players"].values():
            player["order"] = []
            player["points"] = 0
            player["submitted"] = False
            player["missed"] = False
        room["updated"] = now

    def _maybe_reveal(self, room: Dict[str, Any], now: float) -> None:
        """Раунд кончается, когда ответили все (или вышло время)."""
        if room["phase"] != "round" or room["round"] is None:
            return
        round_ = room["round"]
        answered = all(player["submitted"] or player["missed"]
                       for player in room["players"].values())
        if answered or now >= round_["deadline"]:
            for player in room["players"].values():
                if not player["submitted"] and not player["missed"]:
                    player["missed"] = True
            best = max(player["points"] for player in room["players"].values())
            winners = [player for player in room["players"].values()
                       if player["points"] == best] if best > 0 else []
            if len(winners) == 1:
                winners[0]["rounds_won"] += 1
            round_["reveal_until"] = now + _positive(REVEAL_SECONDS, 15.0)
            round_["winners"] = [player["name"] for player in winners] if len(winners) == 1 else []
            round_["drawn"] = len(winners) != 1
            room["phase"] = "reveal"
            room["updated"] = now
            room["history"].append({
                "round": round_["number"],
                "points": {player["name"]: player["points"]
                           for player in room["players"].values()},
                "won": (winners[0]["name"] if len(winners) == 1 else ""),
                "drawn": len(winners) != 1,
                "tracks": [public_track(track, True) for track in self._reveal_order(round_)],
            })

    def _advance(self, room: Dict[str, Any], now: float) -> None:
        """Ленивые переходы: раунд → разбор → следующий раунд → итог."""
        if room["phase"] == "round":
            self._maybe_reveal(room, now)
        if room["phase"] == "reveal" and room["round"] is not None:
            if now >= (room["round"]["reveal_until"] or now):
                if room["rounds"] >= DUEL_ROUNDS:
                    room["standings"] = self._standings(room)
                    room["phase"] = "finished"
                    room["round"] = None
                    room["updated"] = now
                    if not room["finished"]:
                        room["finished"] = True
                        self._finish_room(room)
                else:
                    self._start_round(room, now)

    def _standings(self, room: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Таблица: выигранные раунды, потом очки за расстановки."""
        players = sorted(
            room["players"].values(),
            key=lambda player: (-player["rounds_won"], -player["total"],
                                room["order"].index(player["id"])),
        )
        best = max([player["rounds_won"] for player in players] or [0])
        leaders = [player for player in players if player["rounds_won"] == best]
        return [
            {
                "place": place,
                "id": player["id"],
                "name": player["name"],
                "rounds_won": player["rounds_won"],
                "score": player["total"],
                "winner": bool(len(leaders) == 1 and player is leaders[0] and best > 0),
            }
            for place, player in enumerate(players, start=1)
        ]

    def _finish_room(self, room: Dict[str, Any]) -> None:
        standings = room["standings"] or self._standings(room)
        winner = next((item for item in standings if item["winner"]), None)
        names = [item["name"] for item in standings]
        scores = {item["name"]: item["score"] for item in standings}
        self._finish_report({
            "mode": "online",
            "room": room["code"],
            "rounds": DUEL_ROUNDS,
            "player1_id": standings[0]["id"] if standings else None,
            "player1_name": standings[0]["name"] if standings else "",
            "player1_score": standings[0]["score"] if standings else 0,
            "player2_id": standings[1]["id"] if len(standings) > 1 else None,
            "player2_name": standings[1]["name"] if len(standings) > 1 else "",
            "player2_score": standings[1]["score"] if len(standings) > 1 else 0,
            "winner_id": winner["id"] if winner else None,
            "winner_name": winner["name"] if winner else "",
            "detail": (f"победил {winner['name']}" if winner else "ничья")
            + "; " + ", ".join(f"{name} {scores[name]}" for name in names),
        })

    def _payload(self, room: Dict[str, Any], user: Dict[str, Any],
                 now: float) -> Dict[str, Any]:
        """Состояние комнаты с точки зрения одного игрока.

        Правильный порядок и годы видны только в разборе раунда: иначе их
        можно было бы прочитать прямо из ответа сервера.
        """
        player = room["players"][user["id"]]
        round_ = room["round"]
        phase = room["phase"]
        revealed = phase in ("reveal", "finished")
        payload: Dict[str, Any] = {
            "code": room["code"],
            "mode": "online",
            "game": "raporder",
            "phase": phase,
            "round": round_["number"] if round_ else room["rounds"],
            "rounds_planned": DUEL_ROUNDS,
            "tracks_per_round": TRACKS_PER_ROUND,
            "min_players": MIN_PLAYERS,
            "max_players": MAX_PLAYERS,
            "host": room["host_id"] == user["id"],
            "players": [
                {
                    "id": item["id"],
                    "name": item["name"],
                    "rounds_won": item["rounds_won"],
                    "score": item["total"],
                    "submitted": item["submitted"] or item["missed"],
                }
                for item in room["players"].values()
            ],
            "you": {
                "id": player["id"],
                "name": player["name"],
                "points": player["points"],
                "score": player["total"],
                "rounds_won": player["rounds_won"],
                "submitted": player["submitted"],
                "order": list(player["order"]),
                "missed": player["missed"],
            },
            "history": list(room["history"]),
            "standings": list(room["standings"]),
            "tracks": [],
            "answer": [],
            "points": None,
            "round_winner": "",
            "round_drawn": False,
            "seconds_left": None,
            "reveal_in": None,
            "track_count": len(self._tracks),
            "updated": round(room["updated"], 3),
        }
        if round_ is None:
            return payload
        payload["tracks"] = [public_track(track) for track in round_["tracks"]]
        if revealed:
            payload["answer"] = [public_track(track, True) for track in self._reveal_order(round_)]
            payload["points"] = int(player["points"])
            payload["best"] = len(round_["answer"])
            winners = round_.get("winners") or []
            payload["round_winner"] = str(winners[0]) if winners else ""
            payload["round_drawn"] = bool(round_.get("drawn"))
            if phase == "reveal":
                payload["reveal_in"] = max(0.0, round((round_["reveal_until"] or now) - now, 1))
        else:
            payload["seconds_left"] = max(0.0, round(round_["deadline"] - now, 1))
        return payload


__all__ = [
    "ANSWER_SECONDS",
    "DUEL_ROUNDS",
    "MAX_PLAYERS",
    "MIN_PLAYERS",
    "ROUNDS_PER_GAME",
    "RapOrder",
    "RapOrderError",
    "public_track",
]
