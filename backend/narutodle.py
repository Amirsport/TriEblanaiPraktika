# -*- coding: utf-8 -*-
"""«Narutodle»: комната до шести игроков и три режима игры.

Правила:
    * комната открывается по коду приглашения и вмещает до шести игроков;
    * в лобби видно, кто пришёл, кто хозяин и сколько мест свободно; хозяин
      выбирает режим и запускает игру — начать можно с любым числом игроков;
    * «Дуэль»: один общий персонаж, кто угадает его первым, тот и забирает
      раунд; после итога можно сыграть следующий;
    * «Гонка»: у всех один и тот же набор из пяти персонажей, у каждого своя
      доска подсказок; побеждает тот, кто первым закроет все пять;
    * «Команды»: игроки делятся на две команды, набор из пяти персонажей у
      обеих одинаковый, а доска у команды общая — подсказки видят все её
      игроки. Побеждает команда, которая первой закроет весь набор;
    * за комнатой можно наблюдать: зритель видит доски, но не загадки, пока
      игра не закончилась.

Комнаты живут в памяти процесса: это партии на несколько минут, переживать
перезапуск сервера им не нужно. Доступ к комнатам закрыт аккаунтом панели,
поэтому модуль оперирует уже проверенными пользователями.

Набор персонажей модуль получает готовым списком — его читает сервер из таблицы
narutodle_characters, поэтому набор правится в базе, а не в коде. Итог каждой
партии уходит в переданный обработчик (сервер пишет его в журнал матчей).
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
# Потолок попыток на доску: защита от перебора всего списка персонажей.
MAX_ATTEMPTS = 80
# Одновременных комнат на сервере — с запасом для домашнего использования.
MAX_ROOMS = 200
# За одним столом — до шести игроков, как в лобби на странице игры.
MAX_PLAYERS = 6
# Сколько персонажей нужно закрыть в «Гонке» и «Командах».
RACE_TARGETS = 5

MODES: tuple = ("duel", "race", "teams")
MODE_LABELS: Dict[str, str] = {
    "duel": "Дуэль",
    "race": "Гонка",
    "teams": "Команды",
}
MODE_HINTS: Dict[str, str] = {
    "duel": "Один общий персонаж: кто угадает первым, тот и победил.",
    "race": "Пять персонажей у всех одинаковые: кто первым закроет все пять, тот и победил.",
    "teams": "Две команды, одинаковый набор из пяти персонажей и общая доска у команды.",
}
TEAM_KEYS = ("a", "b")
TEAM_NAMES: Dict[str, str] = {"a": "Команда A", "b": "Команда B"}

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
    """Комнаты игры: лобби, режимы, попытки и итог партии."""

    def __init__(self, characters: Optional[List[Dict[str, Any]]] = None,
                 rng: Optional[random.Random] = None,
                 on_finish: Optional[Callable[[Dict[str, Any]], None]] = None,
                 provider: Optional[Callable[[], List[Dict[str, Any]]]] = None) -> None:
        self._lock = threading.Lock()
        self._rooms: Dict[str, Dict[str, Any]] = {}
        self._rng = rng or random.Random()
        self._on_finish = on_finish
        # Источник набора (обычно таблица в базе) — набор перечитывается
        # перед каждой новой партией, поэтому правки видны без перезапуска.
        self._provider = provider
        self.reload_characters(characters)

    # ------------------------------------------------------------------ данные
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

    def modes(self) -> List[Dict[str, str]]:
        """Режимы для выбора в лобби: ключ, название и подсказка."""
        return [{"key": key, "label": MODE_LABELS[key], "hint": MODE_HINTS[key]}
                for key in MODES]

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

    def _room(self, code: str) -> Dict[str, Any]:
        room = self._rooms.get((code or "").strip().upper())
        if not room:
            raise NarutodleError("Комната не найдена — проверьте код приглашения")
        return room

    @staticmethod
    def _ordered(room: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Игроки в порядке входа: первый пришёл — первым в списке."""
        return [room["players"][player_id] for player_id in room["order"]
                if player_id in room["players"]]

    def _player(self, room: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        player = room["players"].get(user["id"])
        if not player:
            raise NarutodleError("Вы не участник этой комнаты")
        return player

    @staticmethod
    def _new_player(user: Dict[str, Any], now: float) -> Dict[str, Any]:
        return {
            "id": user["id"],
            "name": user["username"],
            "joined": now,
            "team": None,
            "ready": False,
            "gave_up": False,
        }

    @staticmethod
    def _new_group(key: str, name: str, team: Optional[str]) -> Dict[str, Any]:
        return {"key": key, "name": name, "team": team,
                "attempts": [], "found": [], "finished_at": None}

    def _group_key(self, room: Dict[str, Any], player: Dict[str, Any]) -> str:
        """Ключ доски: у команд общая доска, у остальных — своя."""
        match = room.get("match")
        if match and match["mode"] == "teams":
            return str(player.get("team") or "")
        return str(player["id"])

    def _group_for(self, room: Dict[str, Any], player: Dict[str, Any]
                   ) -> Optional[Dict[str, Any]]:
        match = room.get("match")
        if not match:
            return None
        return match["groups"].get(self._group_key(room, player))

    # --------------------------------------------------------------- команды
    def _assign_teams(self, room: Dict[str, Any]) -> None:
        """Делит игроков на две команды по очереди входа (первый — в A)."""
        for index, player in enumerate(self._ordered(room)):
            player["team"] = TEAM_KEYS[index % len(TEAM_KEYS)]

    def _team_members(self, room: Dict[str, Any], team: str) -> List[Dict[str, Any]]:
        return [player for player in self._ordered(room) if player.get("team") == team]

    # ---------------------------------------------------------------- партия
    def _start_match(self, room: Dict[str, Any], now: float) -> None:
        """Разыгрывает новый набор и открывает партию в выбранном режиме."""
        mode = room["mode"]
        self.refresh()
        count = 1 if mode == "duel" else RACE_TARGETS
        if len(self._characters) < count:
            raise NarutodleError(f"В наборе меньше {count} персонажей — этот режим не запустить")
        targets = self._rng.sample(self._characters, count)
        groups: Dict[str, Dict[str, Any]] = {}
        if mode == "teams":
            for team in TEAM_KEYS:
                if self._team_members(room, team):
                    groups[team] = self._new_group(team, TEAM_NAMES[team], team)
        else:
            for player in self._ordered(room):
                groups[str(player["id"])] = self._new_group(
                    str(player["id"]), player["name"], player.get("team"))
        previous = room.get("match") or {}
        room["match_count"] = int(room.get("match_count") or 0) + 1
        room["match"] = {
            "number": room["match_count"],
            "mode": mode,
            "targets": [dict(target) for target in targets],
            "groups": groups,
            "winner": None,
            "draw": False,
            "finished": False,
            "reason": None,
            "started": now,
            "ended": None,
        }
        room["status"] = "playing"
        room["ready"] = set()
        for player in room["players"].values():
            player["ready"] = False
            player["gave_up"] = False
        room["updated"] = now

    def _finish_match(self, room: Dict[str, Any], now: float, reason: str) -> None:
        match = room["match"]
        match["finished"] = True
        match["ended"] = now
        match["reason"] = reason
        room["status"] = "finished"
        room["ready"] = set()
        for player in room["players"].values():
            player["ready"] = False
        room["history"].append({
            "number": match["number"],
            "mode": match["mode"],
            "reason": reason,
            "winner_name": (match["groups"][match["winner"]]["name"]
                            if match.get("winner") else None),
            "targets": [str(target["name"]) for target in match["targets"]],
            "groups": [
                {"name": group["name"],
                 "found_count": len(group["found"]),
                 "total": len(match["targets"]),
                 "seconds": (round(group["finished_at"] - match["started"], 1)
                             if group["finished_at"] else None)}
                for group in match["groups"].values()
            ],
        })
        room["history"] = room["history"][-20:]
        room["updated"] = now
        self._log_match(room, reason)

    def _log_match(self, room: Dict[str, Any], reason: str) -> None:
        """Передаёт итог партии наружу — сервер пишет его в журнал матчей.

        Ошибка журнала не должна ломать партию: партия уже закончилась, игроки
        видят результат, поэтому сбой записи только отмечаем в stderr.
        """
        if not self._on_finish:
            return
        match = room["match"]
        players = self._ordered(room)
        winner = match["groups"].get(match.get("winner") or "")
        winner_player = None
        if winner and winner.get("team"):
            members = [player for player in players if player.get("team") == winner["team"]]
            winner_player = members[0] if members else None
        elif winner:
            winner_player = next(
                (player for player in players if str(player["id"]) == winner["key"]), None)
        others = [group for key, group in match["groups"].items()
                  if key != (match.get("winner") or "")]
        first = players[0] if players else {"id": None, "name": ""}
        second = players[1] if len(players) > 1 else {"id": None, "name": ""}
        try:
            self._on_finish({
                "room": room["code"],
                "round_number": match["number"],
                "mode": match["mode"],
                "target": "; ".join(str(target["name"]) for target in match["targets"]),
                "players": "; ".join(
                    f"{group['name']}: {len(group['found'])}/{len(match['targets'])}"
                    for group in match["groups"].values()),
                "player_ids": [player["id"] for player in players],
                "player1_id": first.get("id"),
                "player1_name": str(first.get("name") or ""),
                "player2_id": second.get("id"),
                "player2_name": str(second.get("name") or ""),
                "winner_id": winner_player["id"] if winner_player else None,
                "winner_name": str(winner["name"]) if winner else "",
                "loser_name": str(others[0]["name"]) if others else "",
                "winner_attempts": len(winner["attempts"]) if winner else 0,
                "loser_attempts": max((len(group["attempts"]) for group in others), default=0),
                "reason": reason,
            })
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"  не удалось записать итог партии в журнал: {exc}\n")

    # ---------------------------------------------------------------- вывод
    @staticmethod
    def _group_public(match: Dict[str, Any], group: Dict[str, Any],
                      mine: bool) -> Dict[str, Any]:
        """Доска группы: чужие подсказки открываются только после итога."""
        reveal = mine or match["finished"]
        return {
            "key": group["key"],
            "name": group["name"],
            "team": group.get("team"),
            "mine": mine,
            "found": list(group["found"]) if reveal else None,
            "found_count": len(group["found"]),
            "total": len(match["targets"]),
            "attempts": group["attempts"] if reveal else None,
            "finished": bool(group["finished_at"]),
            "seconds": (round(group["finished_at"] - match["started"], 1)
                        if group["finished_at"] else None),
        }

    def _payload(self, room: Dict[str, Any], user: Dict[str, Any],
                 watcher: bool = False) -> Dict[str, Any]:
        """Публичное состояние комнаты с точки зрения игрока или зрителя."""
        now = time.time()
        match = room.get("match")
        ordered = self._ordered(room)
        you = room["players"].get(user["id"])
        mine_key = self._group_key(room, you) if (you and match) else None
        is_host = room.get("host") == user["id"]

        players_public = []
        for player in ordered:
            group = match["groups"].get(self._group_key(room, player)) if match else None
            players_public.append({
                "id": player["id"],
                "name": player["name"],
                "you": player["id"] == user["id"],
                "host": player["id"] == room.get("host"),
                "team": player.get("team"),
                "team_label": TEAM_NAMES.get(player.get("team") or "", ""),
                "ready": player["id"] in room["ready"],
                "gave_up": bool(player["gave_up"]),
                "found_count": len(group["found"]) if group else 0,
                "finished": bool(group and group["finished_at"]),
            })

        match_public = None
        you_public = None
        if match:
            groups = []
            for key, group in match["groups"].items():
                groups.append(self._group_public(
                    match, group, bool(you and key == mine_key)))
            my_group = match["groups"].get(mine_key) if you else None
            match_public = {
                "number": match["number"],
                "mode": match["mode"],
                "mode_label": MODE_LABELS.get(match["mode"], match["mode"]),
                "targets_total": len(match["targets"]),
                "finished": match["finished"],
                "reason": match["reason"],
                "draw": bool(match["draw"]),
                "winner": ({"key": match["winner"],
                            "name": match["groups"][match["winner"]]["name"],
                            "mine": bool(mine_key and match["winner"] == mine_key)}
                           if match.get("winner") else None),
                "elapsed": round((match["ended"] or now) - match["started"], 1),
                "groups": groups,
                "answers": ([public_character(target) for target in match["targets"]]
                            if match["finished"] else None),
            }
            if you:
                you_public = {
                    "id": you["id"],
                    "name": you["name"],
                    "ready": you["id"] in room["ready"],
                    "gave_up": bool(you["gave_up"]),
                    "team": you.get("team"),
                    "team_label": TEAM_NAMES.get(you.get("team") or "", ""),
                    "group": mine_key,
                    "found": list(my_group["found"]) if my_group else [],
                    "found_count": len(my_group["found"]) if my_group else 0,
                    "total": len(match["targets"]),
                    "attempts": my_group["attempts"] if my_group else [],
                    "finished": bool(my_group and my_group["finished_at"]),
                }

        teams = [
            {"key": team, "label": TEAM_NAMES[team],
             "members": [player["name"] for player in self._team_members(room, team)]}
            for team in TEAM_KEYS
        ] if room["mode"] == "teams" else []

        return {
            "code": room["code"],
            "status": room["status"],
            "mode": room["mode"],
            "mode_label": MODE_LABELS.get(room["mode"], room["mode"]),
            "modes": self.modes(),
            "capacity": MAX_PLAYERS,
            "free": max(0, MAX_PLAYERS - len(ordered)),
            "players_count": len(ordered),
            "host_name": (room["players"][room["host"]]["name"]
                          if room.get("host") in room["players"] else ""),
            "is_host": is_host,
            "watching": watcher,
            "member": bool(you),
            "you": you_public,
            "players": players_public,
            "teams": teams,
            "match": match_public,
            "history": list(room["history"]),
            "updated": round(room["updated"], 3),
        }

    def state(self, code: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Состояние комнаты для участника: его доска плюс сводка по другим."""
        with self._lock:
            room = self._room(code)
            self._player(room, user)
            return self._payload(room, user)

    def watch(self, code: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Наблюдение: любой вошедший, участник получает member=true."""
        with self._lock:
            room = self._room(code)
            return self._payload(room, user, watcher=True)

    # --------------------------------------------------------------- действия
    def create(self, user: Dict[str, Any], mode: str = "duel") -> Dict[str, Any]:
        """Создаёт комнату-лобби: хозяин ждёт остальных, до шести игроков."""
        if mode not in MODES:
            raise NarutodleError("Неизвестный режим игры")
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
                "host": user["id"],
                "mode": mode,
                "status": "lobby",
                "players": {user["id"]: self._new_player(user, now)},
                "order": [user["id"]],
                "ready": set(),
                "match": None,
                "history": [],
            }
            self._assign_teams(room)
            self._rooms[code] = room
            return self._payload(room, user)

    def join(self, code: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Занимает свободное место в лобби (повторный вход ничего не ломает)."""
        now = time.time()
        with self._lock:
            self._cleanup(now)
            room = self._room(code)
            if user["id"] not in room["players"]:
                if room["status"] != "lobby":
                    raise NarutodleError("Игра уже началась — можно смотреть или дождаться новой")
                if len(room["players"]) >= MAX_PLAYERS:
                    raise NarutodleError(f"Все {MAX_PLAYERS} мест заняты — можно смотреть")
                room["players"][user["id"]] = self._new_player(user, now)
                room["order"].append(user["id"])
                self._assign_teams(room)
            room["updated"] = now
            return self._payload(room, user)

    def leave(self, code: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Выходит из комнаты; если шла партия — сначала засчитывается сдача."""
        now = time.time()
        with self._lock:
            room = self._room(code)
            self._player(room, user)
            if room["status"] == "playing" and not self._player(room, user)["gave_up"]:
                self._give_up_locked(room, user, now)
            room["players"].pop(user["id"], None)
            if user["id"] in room["order"]:
                room["order"].remove(user["id"])
            room["ready"].discard(user["id"])
            if not room["players"]:
                self._rooms.pop(room["code"], None)
                return {"code": room["code"], "status": "closed", "closed": True}
            if room.get("host") == user["id"]:
                room["host"] = room["order"][0]
            self._assign_teams(room)
            room["updated"] = now
            return {"code": room["code"], "status": room["status"],
                    "left": True, "closed": False}

    def set_mode(self, code: str, user: Dict[str, Any], mode: str) -> Dict[str, Any]:
        """Хозяин выбирает режим; меняется только в лобби."""
        if mode not in MODES:
            raise NarutodleError("Неизвестный режим игры")
        now = time.time()
        with self._lock:
            room = self._room(code)
            self._player(room, user)
            if user["id"] != room.get("host"):
                raise NarutodleError("Режим выбирает хозяин комнаты")
            if room["status"] != "lobby":
                raise NarutodleError("Режим можно менять только в лобби")
            room["mode"] = mode
            self._assign_teams(room)
            room["updated"] = now
            return self._payload(room, user)

    def start(self, code: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Хозяин запускает игру — с любым числом игроков, от одного."""
        now = time.time()
        with self._lock:
            room = self._room(code)
            self._player(room, user)
            if user["id"] != room.get("host"):
                raise NarutodleError("Игру запускает хозяин комнаты")
            if room["status"] != "lobby":
                raise NarutodleError("Игра уже идёт")
            if room["mode"] == "teams":
                present = {player.get("team") for player in self._ordered(room)}
                if len(present) < 2 or not all(present):
                    raise NarutodleError(
                        "Для режима «Команды» нужны игроки в обеих командах — позовите ещё кого-нибудь")
            self._start_match(room, now)
            return self._payload(room, user)

    def to_lobby(self, code: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Возвращает комнату в лобби после партии: режим снова можно менять."""
        now = time.time()
        with self._lock:
            room = self._room(code)
            self._player(room, user)
            if room["status"] == "playing":
                raise NarutodleError("Сначала доиграйте партию")
            room["status"] = "lobby"
            room["match"] = None
            room["ready"] = set()
            for player in room["players"].values():
                player["ready"] = False
                player["gave_up"] = False
            room["updated"] = now
            return self._payload(room, user)

    def guess(self, code: str, user: Dict[str, Any], name: str) -> Dict[str, Any]:
        """Проверяет догадку и возвращает обновлённое состояние комнаты."""
        now = time.time()
        with self._lock:
            self._cleanup(now)
            room = self._room(code)
            player = self._player(room, user)
            match = room.get("match")
            if not match:
                raise NarutodleError("Партия ещё не началась")
            if room["status"] == "finished":
                raise NarutodleError("Партия закончена — начните новую")
            if room["status"] != "playing":
                raise NarutodleError("Партия ещё не началась")
            group = self._group_for(room, player)
            if not group:
                raise NarutodleError("Вашей доски в этой партии нет")
            if group["finished_at"]:
                raise NarutodleError("Вы уже закрыли свой набор")
            if player["gave_up"]:
                raise NarutodleError("Вы сдались в этой партии")
            if len(group["attempts"]) >= MAX_ATTEMPTS:
                raise NarutodleError(f"Больше {MAX_ATTEMPTS} попыток за партию не бывает")

            character = self.find_character(name)
            if not character:
                raise NarutodleError("Такого персонажа нет в наборе — выберите из подсказки")
            if any(found.casefold() == character["name"].casefold()
                   for found in group["found"]):
                raise NarutodleError(f"{character['name']} уже найден")

            # Подсказки ведут к первому незакрытому персонажу, но засчитывается
            # любой из оставшихся: набор можно закрывать в любом порядке.
            remaining = [target for target in match["targets"]
                         if target["name"] not in group["found"]]
            hint_target = remaining[0]
            result = [
                {
                    "key": attribute["key"],
                    "value": character[attribute["key"]],
                    "state": compare_attribute(attribute["key"],
                                               character[attribute["key"]],
                                               hint_target[attribute["key"]],
                                               bool(attribute.get("multi"))),
                    # Стрелка «нужная арка раньше/позже» — пустая строка, когда
                    # подсказка не нужна (графа не упорядочена или совпала).
                    "hint": compare_order(attribute["key"],
                                          character[attribute["key"]],
                                          hint_target[attribute["key"]]),
                }
                for attribute in attribute_list()
            ]
            correct = any(target["name"] == character["name"] for target in remaining)
            group["attempts"].append({
                "name": character["name"],
                "result": result,
                "correct": correct,
                "by": player["name"],
            })
            if correct:
                group["found"].append(character["name"])
                if len(group["found"]) >= len(match["targets"]):
                    group["finished_at"] = now
                    match["winner"] = group["key"]
                    self._finish_match(room, now, "solved")

            room["updated"] = now
            return self._payload(room, user)

    def give_up(self, code: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Сдача: в дуэли отдаёт партию остальным, в командах — команду."""
        now = time.time()
        with self._lock:
            self._cleanup(now)
            room = self._room(code)
            self._player(room, user)
            if room["status"] != "playing":
                raise NarutodleError("Партия ещё не началась")
            self._give_up_locked(room, user, now)
            return self._payload(room, user)

    def _give_up_locked(self, room: Dict[str, Any], user: Dict[str, Any],
                        now: float) -> None:
        """Общая логика сдачи (вызывать под замком)."""
        match = room["match"]
        player = self._player(room, user)
        if player["gave_up"]:
            raise NarutodleError("Вы уже сдались")
        player["gave_up"] = True
        if match["mode"] == "teams":
            mate_groups = self._team_members(room, player.get("team") or "")
            if all(mate["gave_up"] for mate in mate_groups):
                group = match["groups"].get(player.get("team") or "")
                if group and not group["finished_at"]:
                    group["finished_at"] = now
                others = [other for key, other in match["groups"].items()
                          if key != player.get("team")]
                if others:
                    match["winner"] = others[0]["key"]
                else:
                    match["draw"] = True
                self._finish_match(room, now, "gave_up")
            return

        group = self._group_for(room, player)
        if group and not group["finished_at"]:
            group["finished_at"] = now
        active = [item for item in match["groups"].values() if not item["finished_at"]]
        if len(active) == 1:
            match["winner"] = active[0]["key"]
            self._finish_match(room, now, "gave_up")
        elif not active:
            match["draw"] = True
            self._finish_match(room, now, "gave_up")

    def rematch(self, code: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Игрок готов к новой партии; она начинается, когда готовы все.

        Иначе выходило бы так: один нажал «Ещё игру» и уже угадывает, пока
        остальные дочитывают итог. Теперь нажатие — это только «готов».
        """
        now = time.time()
        with self._lock:
            self._cleanup(now)
            room = self._room(code)
            player = self._player(room, user)
            if room["status"] != "finished":
                raise NarutodleError("Партия ещё идёт")
            room["ready"].add(user["id"])
            player["ready"] = True
            present = set(room["players"])
            if present and present <= room["ready"]:
                self._start_match(room, now)
            room["updated"] = now
            return self._payload(room, user)

    def stats(self) -> Dict[str, int]:
        """Сколько комнат и партий сейчас на сервере — для служебной консоли."""
        with self._lock:
            self._cleanup(time.time())
            return {
                "rooms": len(self._rooms),
                "matches": sum(len(room["history"]) for room in self._rooms.values()),
                "players": sum(len(room["players"]) for room in self._rooms.values()),
            }


__all__ = [
    "MAX_ATTEMPTS",
    "MAX_PLAYERS",
    "MODES",
    "MODE_HINTS",
    "MODE_LABELS",
    "Narutodle",
    "NarutodleError",
    "RACE_TARGETS",
    "ROOM_TTL_SECONDS",
    "compare_attribute",
]
