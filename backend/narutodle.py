# -*- coding: utf-8 -*-
"""Дуэль «Narutodle»: одна загадка на двоих, побеждает тот, кто угадает первым.

Правила:
    * комната создаётся по коду приглашения и ждёт второго игрока;
    * обоим загадан один и тот же персонаж, у каждого своя таблица попыток;
    * решивший первым забирает раунд; сдавшийся отдаёт раунд сопернику;
    * после раунда видно ответ и обе таблицы, дальше — новый раунд.
    * за дуэлью можно наблюдать: зритель видит обе таблицы, но не загадку.

Комнаты живут в памяти процесса: это партии на несколько минут, переживать
перезапуск сервера им не нужно. Доступ к комнатам закрыт аккаунтом панели,
поэтому модуль оперирует уже проверенными пользователями.

Набор персонажей модуль получает готовым списком — его читает сервер из таблицы
narutodle_characters, поэтому набор правится в базе, а не в коде. Итог каждого
раунда уходит в переданный обработчик (сервер пишет его в журнал матчей).
"""
from __future__ import annotations

import random
import sys
import threading
import time
from typing import Any, Callable, Dict, List, Optional

try:  # запуск как модуль: python -m backend.server
    from .narutodle_data import (
        ARCS,
        CHARACTERS,
        UNKNOWN,
        attribute_list,
        portrait_ref,
        public_character,
    )
except ImportError:  # запуск как файл: python backend/server.py
    from narutodle_data import (  # type: ignore
        ARCS,
        CHARACTERS,
        UNKNOWN,
        attribute_list,
        portrait_ref,
        public_character,
    )

# Заброшенная комната живёт два часа, потом исчезает вместе с историей.
ROOM_TTL_SECONDS = 2 * 60 * 60
# Потолок попыток в раунде: защита от перебора всего списка персонажей.
MAX_ATTEMPTS = 80
# Одновременных комнат на сервере — с запасом для домашнего использования.
MAX_ROOMS = 200
MAX_PLAYERS = 2

# Без похожих символов (I/1, O/0): код диктуют голосом и вводят руками.
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 4

# Значения «ничего нет» — по ним считается «оба владеют, но разным».
NONE_VALUES = {"нет", "нет клана"}


class NarutodleError(ValueError):
    """Ошибка правил игры: превращается в ответ 400 с понятным текстом."""


def _has_value(value: Any) -> bool:
    """Есть ли у персонажа свойство (кеккей генкай, хвостатый зверь)."""
    return bool(value) and value not in NONE_VALUES and value != UNKNOWN


def compare_attribute(key: str, guess: Any, target: Any, multi: bool = False) -> str:
    """Сравнивает одну графу догадки с загадкой.

    match — совпало, near — похоже (частично), miss — не совпало.
    """
    if multi:
        guess_set = {value for value in guess if value != UNKNOWN}
        target_set = {value for value in target if value != UNKNOWN}
        if not guess_set and not target_set:
            return "match"
        if guess_set == target_set:
            return "match"
        if guess_set & target_set:
            return "near"
        return "miss"

    if guess == target:
        return "match"

    # «У обоих есть кеккей генкай, но разный» — это подсказка, а не промах.
    if key in ("kekkei", "jinchuriki") and _has_value(guess) and _has_value(target):
        return "near"
    return "miss"


def compare_order(key: str, guess: Any, target: Any) -> str:
    """Куда смотреть по упорядоченной графе: раньше или позже загадка.

    Арки идут по сюжету, поэтому у «первой арки» есть направление: игрок видит
    стрелку, а не просто «не совпало». Пусто — когда графа не упорядочена,
    значения неизвестны или совпали.
    """
    if key != "debut":
        return ""
    try:
        guess_index = ARCS.index(guess)
        target_index = ARCS.index(target)
    except ValueError:
        return ""
    if guess_index == target_index:
        return ""
    return "earlier" if target_index < guess_index else "later"


class Narutodle:
    """Комнаты дуэли: создание, вход, попытки, итог раунда."""

    def __init__(self, characters: Optional[List[Dict[str, Any]]] = None,
                 rng: Optional[random.Random] = None,
                 on_finish: Optional[Callable[[Dict[str, Any]], None]] = None,
                 provider: Optional[Callable[[], List[Dict[str, Any]]]] = None) -> None:
        self._lock = threading.Lock()
        self._rooms: Dict[str, Dict[str, Any]] = {}
        self._rng = rng or random.Random()
        self._on_finish = on_finish
        # Источник набора (обычно таблица в базе) — набор перечитывается
        # перед каждым новым раундом, поэтому правки видны без перезапуска.
        self._provider = provider
        self.reload_characters(characters)

    def reload_characters(self, characters: Optional[List[Dict[str, Any]]] = None) -> int:
        """Берёт набор персонажей и пересобирает поиск по имени."""
        self._characters = [dict(character) for character in (characters or CHARACTERS)]
        if not self._characters:
            self._characters = [dict(character) for character in CHARACTERS]
        self._index = {str(character["name"]).casefold(): character
                       for character in self._characters}
        return len(self._characters)

    def refresh(self) -> int:
        """Перечитывает набор из источника; при сбое остаётся прежний набор."""
        if not self._provider:
            return len(self._characters)
        try:
            characters = self._provider()
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"  набор персонажей недоступен, играем прежним: {exc}\n")
            return len(self._characters)
        return self.reload_characters(characters) if characters else len(self._characters)

    def find_character(self, name: str) -> Optional[Dict[str, Any]]:
        """Персонаж по названию: регистр и лишние пробелы не важны."""
        return self._index.get((name or "").strip().casefold())

    def character_names(self) -> List[str]:
        return [str(character["name"]) for character in self._characters]

    def catalog(self) -> List[Dict[str, Any]]:
        """Список для подсказки в поле ввода: имя, цвет аватара и портрет.

        Скрытых свойств здесь нет — только то, что нужно нарисовать аватар.
        Портрет отдаётся ссылкой (см. portrait_ref): base64 в этом ответе весит
        мегабайты, и страница на медленном канале его не дожидалась.
        """
        return [
            {
                "name": str(character["name"]),
                "color": str(character.get("color") or ""),
                "image": portrait_ref(character),
            }
            for character in self._characters
        ]

    # ------------------------------------------------------------ служебное
    def _cleanup(self, now: float) -> None:
        """Убирает комнаты, в которые давно никто не заходил (вызывать под замком)."""
        stale = [code for code, room in self._rooms.items()
                 if now - room["updated"] > ROOM_TTL_SECONDS]
        for code in stale:
            del self._rooms[code]

    def _new_code(self) -> str:
        while True:
            code = "".join(self._rng.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
            if code not in self._rooms:
                return code

    def _pick_target(self, exclude: Optional[str] = None) -> Dict[str, Any]:
        """Случайный персонаж; в новом раунде — не тот же, что был."""
        pool = [character for character in self._characters if character["name"] != exclude]
        return self._rng.choice(pool or self._characters)

    def _room(self, code: str) -> Dict[str, Any]:
        room = self._rooms.get((code or "").strip().upper())
        if not room:
            raise NarutodleError("Комната не найдена — проверьте код приглашения")
        return room

    def _player(self, room: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        player = room["players"].get(user["id"])
        if not player:
            raise NarutodleError("Вы не участник этой комнаты")
        return player

    def _rival(self, room: Dict[str, Any], user_id: int) -> Optional[Dict[str, Any]]:
        for player_id, player in room["players"].items():
            if player_id != user_id:
                return player
        return None

    def _score(self, room: Dict[str, Any], user_id: int) -> Dict[str, int]:
        """Счёт по раундам: победы каждого участника."""
        mine = rival = 0
        for result in room["history"]:
            if result["winner"] == user_id:
                mine += 1
            elif result["winner"] is not None:
                rival += 1
        return {"you": mine, "rival": rival, "rounds": len(room["history"])}

    def _start_round(self, room: Dict[str, Any], now: float,
                     exclude: Optional[str] = None) -> None:
        target = self._pick_target(exclude)
        room["round"] = {
            "number": room["round"]["number"] + 1 if room.get("round") else 1,
            "target": target,
            "winner": None,
            "finished": False,
            "reason": None,
            "started": now,
        }
        for player in room["players"].values():
            player["attempts"] = []
            player["solved_in"] = None
            player["gave_up"] = False
        room["updated"] = now

    def _finish_round(self, room: Dict[str, Any], now: float,
                      winner_id: Optional[int], reason: str, answer: bool = True) -> None:
        round_ = room["round"]
        round_["finished"] = True
        round_["winner"] = winner_id
        round_["reason"] = reason
        room["history"].append({
            "round": round_["number"],
            "winner": winner_id,
            "winner_name": (room["players"][winner_id]["name"] if winner_id in room["players"] else None),
            "reason": reason,
            "target": public_character(round_["target"]) if answer else None,
            "attempts": {player["name"]: len(player["attempts"])
                         for player in room["players"].values()},
        })
        room["updated"] = now
        self._log_match(room, winner_id, reason)

    def _log_match(self, room: Dict[str, Any], winner_id: Optional[int],
                   reason: str) -> None:
        """Передаёт итог раунда наружу — сервер пишет его в журнал матчей.

        Ошибка журнала не должна ломать партию: раунд уже закончился, игроки
        видят результат, поэтому сбой записи только отмечаем в stderr.
        """
        if not self._on_finish:
            return
        players = list(room["players"].values())
        first = players[0] if players else {"id": None, "name": ""}
        second = players[1] if len(players) > 1 else {"id": None, "name": ""}
        winner = room["players"].get(winner_id) if winner_id is not None else None
        loser = next((player for player in players if player["id"] != winner_id), None)
        round_ = room["round"]
        try:
            self._on_finish({
                "room": room["code"],
                "round_number": round_["number"],
                "target": str(round_["target"]["name"]),
                "player1_id": first.get("id"),
                "player1_name": str(first.get("name") or ""),
                "player2_id": second.get("id"),
                "player2_name": str(second.get("name") or ""),
                "winner_id": winner["id"] if winner else None,
                "winner_name": str(winner["name"]) if winner else "",
                "loser_name": str(loser["name"]) if loser else "",
                "winner_attempts": len(winner["attempts"]) if winner else 0,
                "loser_attempts": len(loser["attempts"]) if loser else 0,
                "reason": reason,
            })
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"  журнал матчей недоступен: {exc}\n")

    # ------------------------------------------------------------- состояние
    def state(self, code: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Состояние комнаты по коду — то, что видит игрок."""
        with self._lock:
            self._cleanup(time.time())
            return self._payload(self._room(code), user)

    def watch(self, code: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Состояние комнаты глазами зрителя: обе таблицы, загадка — только в итоге.

        Зрителем может быть любой вошедший в аккаунт: по ссылке-приглашению
        человек сам выбирает, играть ему или смотреть. Участник комнаты тоже
        может смотреть, но тогда ответ помечен `member` — страница отправит его
        в обычную дуэль.
        """
        with self._lock:
            self._cleanup(time.time())
            return self._watch_payload(self._room(code), user)

    def _watch_payload(self, room: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """Публичное состояние комнаты для наблюдателя.

        Отличие от `_payload` в том, что «моей» стороны здесь нет: отдаются
        обе таблицы попыток, чтобы за дуэлью было интересно следить. Загадка
        при этом остаётся закрытой до конца раунда — иначе зритель просто
        выкрикнул бы ответ игрокам.
        """
        round_ = room["round"]
        finished = round_["finished"]
        waiting = len(room["players"]) < MAX_PLAYERS
        status = "finished" if finished else ("waiting" if waiting else "playing")

        players: List[Dict[str, Any]] = []
        for player in room["players"].values():
            wins = sum(1 for result in room["history"] if result["winner"] == player["id"])
            players.append({
                "id": player["id"],
                "name": player["name"],
                "wins": wins,
                "guess_count": len(player["attempts"]),
                "solved_in": player["solved_in"],
                "gave_up": player["gave_up"],
                "attempts": player["attempts"],
            })

        winner = room["players"].get(round_["winner"]) if finished and round_["winner"] else None
        return {
            "code": room["code"],
            "status": status,
            "round": round_["number"],
            "watching": True,
            "member": user["id"] in room["players"],
            "players": players,
            "rounds": len(room["history"]),
            "winner_name": str(winner["name"]) if winner else None,
            "draw": bool(finished and round_["winner"] is None),
            "finish_reason": round_["reason"],
            "answer": public_character(round_["target"]) if finished else None,
            "history": [
                {"round": item["round"],
                 "winner_name": item["winner_name"],
                 "attempts": item["attempts"],
                 "target": item["target"]["name"] if item["target"] else None}
                for item in room["history"]
            ],
            "updated": round(room["updated"], 3),
        }

    def _payload(self, room: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """Публичное состояние комнаты с точки зрения одного игрока.

        Загадка не попадает в ответ, пока раунд не закончился, а таблица
        соперника скрыта до итога — иначе подсказки утекали бы сопернику.
        """
        viewer = self._player(room, user)
        rival = self._rival(room, user["id"])
        round_ = room["round"]
        finished = round_["finished"]
        waiting = len(room["players"]) < MAX_PLAYERS

        if finished:
            status = "finished"
        elif waiting:
            status = "waiting"
        else:
            status = "playing"

        winner = None
        if finished:
            if round_["winner"] is None:
                winner = "draw"
            else:
                winner = "you" if round_["winner"] == user["id"] else "rival"

        return {
            "code": room["code"],
            "status": status,
            "round": round_["number"],
            "you": {
                "name": viewer["name"],
                "attempts": viewer["attempts"],
                "guess_count": len(viewer["attempts"]),
                "solved_in": viewer["solved_in"],
                "gave_up": viewer["gave_up"],
            },
            "rival": None if not rival else {
                "name": rival["name"],
                "guess_count": len(rival["attempts"]),
                "solved_in": rival["solved_in"],
                "gave_up": rival["gave_up"],
                # чужую таблицу открываем только после итога раунда
                "attempts": rival["attempts"] if finished else None,
            },
            "winner": winner,
            "finish_reason": round_["reason"],
            "answer": public_character(round_["target"]) if finished else None,
            "score": self._score(room, user["id"]),
            "history": [
                {"round": item["round"],
                 "winner": ("you" if item["winner"] == user["id"]
                            else ("draw" if item["winner"] is None else "rival")),
                 "winner_name": item["winner_name"],
                 "attempts": item["attempts"],
                 "target": item["target"]["name"] if item["target"] else None}
                for item in room["history"]
            ],
            "updated": round(room["updated"], 3),
        }

    # ------------------------------------------------------------- команды
    def create(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Создаёт комнату: игрок становится первым участником и ждёт соперника."""
        now = time.time()
        with self._lock:
            self._cleanup(now)
            self.refresh()
            if len(self._rooms) >= MAX_ROOMS:
                raise NarutodleError("На сервере слишком много активных комнат, попробуйте позже")
            code = self._new_code()
            room: Dict[str, Any] = {
                "code": code,
                "created": now,
                "updated": now,
                "players": {user["id"]: {
                    "id": user["id"], "name": user["username"],
                    "attempts": [], "solved_in": None, "gave_up": False,
                }},
                "history": [],
                "round": None,
            }
            self._start_round(room, now)
            self._rooms[code] = room
            return self._payload(room, user)

    def join(self, code: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Входит в комнату вторым игроком (повторный вход ничего не ломает)."""
        now = time.time()
        with self._lock:
            self._cleanup(now)
            room = self._room(code)
            if user["id"] not in room["players"]:
                if len(room["players"]) >= MAX_PLAYERS:
                    raise NarutodleError("В комнате уже двое игроков")
                if room["history"] or room["round"]["number"] > 1:
                    raise NarutodleError("Дуэль в этой комнате уже началась")
                room["players"][user["id"]] = {
                    "id": user["id"], "name": user["username"],
                    "attempts": [], "solved_in": None, "gave_up": False,
                }
            room["updated"] = now
            return self._payload(room, user)

    def guess(self, code: str, user: Dict[str, Any], name: str) -> Dict[str, Any]:
        """Проверяет догадку и возвращает обновлённое состояние комнаты."""
        now = time.time()
        with self._lock:
            self._cleanup(now)
            room = self._room(code)
            player = self._player(room, user)
            round_ = room["round"]

            if round_["finished"]:
                raise NarutodleError("Раунд закончен — начните новый")
            if len(room["players"]) < MAX_PLAYERS:
                raise NarutodleError("Соперник ещё не подключился")
            if player["gave_up"]:
                raise NarutodleError("Вы сдались в этом раунде")
            if len(player["attempts"]) >= MAX_ATTEMPTS:
                raise NarutodleError(f"Больше {MAX_ATTEMPTS} попыток за раунд не бывает")

            character = self.find_character(name)
            if not character:
                raise NarutodleError("Такого персонажа нет в наборе — выберите из подсказки")

            target = round_["target"]
            result = [
                {
                    "key": attribute["key"],
                    "value": character[attribute["key"]],
                    "state": compare_attribute(attribute["key"],
                                               character[attribute["key"]],
                                               target[attribute["key"]],
                                               bool(attribute.get("multi"))),
                    # Стрелка «нужная арка раньше/позже» — пустая строка, когда
                    # подсказка не нужна (графа не упорядочена или совпала).
                    "hint": compare_order(attribute["key"],
                                          character[attribute["key"]],
                                          target[attribute["key"]]),
                }
                for attribute in attribute_list()
            ]
            correct = character["name"] == target["name"]
            player["attempts"].append({
                "name": character["name"],
                "result": result,
                "correct": correct,
            })
            if correct and player["solved_in"] is None:
                player["solved_in"] = len(player["attempts"])
                self._finish_round(room, now, user["id"], "solved")

            room["updated"] = now
            return self._payload(room, user)

    def give_up(self, code: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Сдаётся: раунд забирает соперник."""
        now = time.time()
        with self._lock:
            self._cleanup(now)
            room = self._room(code)
            player = self._player(room, user)
            round_ = room["round"]

            if round_["finished"]:
                raise NarutodleError("Раунд уже закончился")
            others = [other for other_id, other in room["players"].items()
                      if other_id != user["id"]]
            if not others:
                raise NarutodleError("Соперник ещё не подключился")
            player["gave_up"] = True
            self._finish_round(room, now, others[0]["id"], "gave_up")
            room["updated"] = now
            return self._payload(room, user)

    def rematch(self, code: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Начинает новый раунд после итога (игрок может нажать в любой момент)."""
        now = time.time()
        with self._lock:
            self._cleanup(now)
            room = self._room(code)
            self._player(room, user)
            if not room["round"]["finished"]:
                raise NarutodleError("Раунд ещё идёт")
            self.refresh()
            self._start_round(room, now, exclude=room["round"]["target"]["name"])
            return self._payload(room, user)

    def stats(self) -> Dict[str, int]:
        """Сколько комнат и партий сейчас на сервере — для служебной консоли."""
        with self._lock:
            self._cleanup(time.time())
            return {
                "rooms": len(self._rooms),
                "rounds": sum(len(room["history"]) for room in self._rooms.values()),
                "players": sum(len(room["players"]) for room in self._rooms.values()),
            }


__all__ = [
    "MAX_ATTEMPTS",
    "Narutodle",
    "NarutodleError",
    "ROOM_TTL_SECONDS",
    "compare_attribute",
]
