# -*- coding: utf-8 -*-
"""«Narutodle»: комната до шести игроков, три режима и доски с автопереходом.

Правила:
    * комната открывается по коду приглашения и вмещает до шести игроков;
    * в лобби видно, кто пришёл, кто хозяин и сколько мест свободно; хозяин
      выбирает режим и запускает игру — начать можно с любым числом игроков;
    * у каждого игрока своя доска. Персонажи открываются по одному: засчитывается
      только текущий, догадка про другого персонажа из набора — обычная ошибка,
      поэтому подсказка не выдаёт загаданное имя;
    * после верного ответа доска очищается сама, а её подсказки уходят в архив:
      в конце партии видно, кто сколько попыток потратил на каждого персонажа;
    * «Дуэль»: всем загадан один и тот же персонаж, кто угадает первым — тот и
      победил; по ходу игры в комнате копится счёт, кто сколько угадал;
    * «Гонка»: у всех один и тот же набор из пяти персонажей и своя доска,
      побеждает тот, кто первым закроет весь набор;
    * «Команды»: две команды, одинаковый набор персонажей и своя доска у
      каждого игрока. Хозяин выбирает, сколько всего персонажей на команду —
      число, кратное числу игроков в командах, поэтому набор делится поровну.
      Игрок угадывает свои персонажи по порядку, а когда закрыл свои — помогает
      команде: его догадки идут на доску товарища, которую ещё не закрыли;
    * за комнатой можно наблюдать: зритель видит счёт и доски, но не загадки,
      пока партия не закончилась.

Комнаты живут в памяти процесса: это партии на несколько минут, переживать
перезапуск сервера им не нужно. Доступ к комнатам закрыт аккаунтом панели,
поэтому модуль оперирует уже проверенными пользователями.

Набор персонажей модуль получает готовым списком — его читает сервер из таблицы
narutodle_characters, поэтому набор правится в базе, а не в коде. Итог каждой
партии уходит в переданный обработчик (сервер пишет его в журнал матчей).
"""
from __future__ import annotations

import math
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
# Потолок попыток на одну доску: защита от перебора всего списка персонажей.
MAX_ATTEMPTS = 80
# Одновременных комнат на сервере — с запасом для домашнего использования.
MAX_ROOMS = 200
# За одним столом — до шести игроков, как в лобби на странице игры.
MAX_PLAYERS = 6
# Сколько персонажей нужно закрыть в «Гонке»; в «Дуэли» — ровно один.
RACE_TARGETS = 5
DUEL_TARGETS = 1
# Предел набора на команду: дальше партия становится слишком долгой.
MAX_TEAM_TOTAL = 12

MODES: tuple = ("duel", "race", "teams")
MODE_LABELS: Dict[str, str] = {
    "duel": "Дуэль",
    "race": "Гонка",
    "teams": "Команды",
}
MODE_HINTS: Dict[str, str] = {
    "duel": "Один общий персонаж: кто угадает первым, тот и победил.",
    "race": "Пять персонажей у всех одинаковые: кто первым закроет все пять, тот и победил.",
    "teams": "Две команды и одинаковый набор: у каждого своя доска, кто закрыл свои — помогает товарищу.",
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


def _lcm(left: int, right: int) -> int:
    return left * right // math.gcd(left, right)


class Narutodle:
    """Комнаты игры: лобби, режимы, доски игроков и итог партии."""

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
    def _new_board(player: Dict[str, Any], assigned: List[str]) -> Dict[str, Any]:
        """Доска игрока: очередь персонажей и подсказки только по текущему."""
        return {
            "key": str(player["id"]),
            "player_id": player["id"],
            "name": player["name"],
            "team": player.get("team"),
            "assigned": [str(name) for name in assigned],
            "index": 0,
            "attempts": [],
            "history": [],
            "started_at": None,
            "finished_at": None,
            "given_up": False,
        }

    def _group_key(self, room: Dict[str, Any], player: Dict[str, Any]) -> str:
        """Ключ доски игрока: у каждого своя доска в любом режиме."""
        return str(player["id"])

    def _team_members(self, room: Dict[str, Any], team: str) -> List[Dict[str, Any]]:
        return [player for player in self._ordered(room) if player.get("team") == team]

    def _assign_teams(self, room: Dict[str, Any]) -> None:
        """Делит игроков на две команды, не трогая выбранные вручную.

        Кто команду не выбрал, попадает в ту, где сейчас меньше игроков
        (при равенстве — в A): так при входе по очереди выходит «по одному
        в каждую», а ручной переход товарища не отменяется следующим входом.
        """
        counts = {key: 0 for key in TEAM_KEYS}
        for player in self._ordered(room):
            if player.get("team") in TEAM_KEYS:
                counts[player["team"]] += 1
        for player in self._ordered(room):
            if player.get("team") in TEAM_KEYS:
                continue
            target = (TEAM_KEYS[0] if counts[TEAM_KEYS[0]] <= counts[TEAM_KEYS[1]]
                      else TEAM_KEYS[1])
            player["team"] = target
            counts[target] += 1
        options = self._team_options(room)
        if options and int(room.get("team_total") or 0) not in options:
            room["team_total"] = self._default_team_total(room)

    # ------------------------------------------------------------ размер набора
    def _team_sizes(self, room: Dict[str, Any]) -> List[int]:
        return [len(self._team_members(room, key)) for key in TEAM_KEYS]

    def _team_options(self, room: Dict[str, Any]) -> List[int]:
        """Сколько персонажей можно взять на команду: кратно числу игроков.

        Набор делится поровну, поэтому общее число обязано делиться на размер
        каждой команды. Для 3 на 3 это 3, 6, 9, 12; для 2 на 2 — 2, 4, 6…;
        при разном размере (2 на 3) — общие кратные: 6, 12.
        """
        sizes = self._team_sizes(room)
        if not all(sizes):
            return []
        step = 1
        for size in sizes:
            step = _lcm(step, size)
        return list(range(step, MAX_TEAM_TOTAL + 1, step))

    def _default_team_total(self, room: Dict[str, Any]) -> int:
        """По умолчанию — по три персонажа на игрока (или ближайшее кратное)."""
        options = self._team_options(room)
        sizes = self._team_sizes(room)
        if not options or not all(sizes):
            return 0
        wanted = max(sizes) * 3
        return next((value for value in options if value >= wanted), options[-1])

    def _team_total(self, room: Dict[str, Any]) -> int:
        options = self._team_options(room)
        if not options:
            return 0
        current = int(room.get("team_total") or 0)
        return current if current in options else self._default_team_total(room)

    def team_options(self, room: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Варианты набора на команду с разбивкой по игрокам — для страницы."""
        options = self._team_options(room)
        sizes = self._team_sizes(room)
        if not all(sizes):
            return []
        result = []
        for total in options:
            per = [total // size for size in sizes]
            result.append({
                "total": total,
                "per_team": per,
                "label": f"{total} персонажей · по " + " и ".join(str(value) for value in per),
            })
        return result

    # ---------------------------------------------------------------- партия
    def _pick_targets(self, count: int) -> List[Dict[str, Any]]:
        if len(self._characters) < count:
            raise NarutodleError(
                f"В наборе всего {len(self._characters)} персонажей — для {count} не хватает")
        return [dict(item) for item in self._rng.sample(self._characters, count)]

    def _start_match(self, room: Dict[str, Any], now: float) -> None:
        """Разыгрывает набор и открывает партию в выбранном режиме."""
        mode = room["mode"]
        self.refresh()
        players = self._ordered(room)
        if not players:
            raise NarutodleError("В комнате нет игроков")

        boards: Dict[str, Dict[str, Any]] = {}
        if mode == "duel":
            targets = self._pick_targets(DUEL_TARGETS)
            names = [str(target["name"]) for target in targets]
            for player in players:
                board = self._new_board(player, names)
                boards[board["key"]] = board
            per_board = DUEL_TARGETS
            per_team = DUEL_TARGETS
            shared = len(names) == 1
        elif mode == "race":
            targets = self._pick_targets(RACE_TARGETS)
            names = [str(target["name"]) for target in targets]
            for player in players:
                board = self._new_board(player, names)
                boards[board["key"]] = board
            per_board = RACE_TARGETS
            per_team = RACE_TARGETS
            shared = True
        else:
            teams = {key: self._team_members(room, key) for key in TEAM_KEYS}
            if not all(teams[key] for key in TEAM_KEYS):
                raise NarutodleError(
                    "Для режима «Команды» нужны игроки в обеих командах — позовите ещё кого-нибудь")
            total = self._team_total(room)
            if not total:
                raise NarutodleError("Не выбрано, сколько персонажей взять на команду")
            targets = self._pick_targets(total)
            names = [str(target["name"]) for target in targets]
            per_team = total
            per_board = 0
            for key in TEAM_KEYS:
                members = teams[key]
                chunk = total // len(members)
                for index, player in enumerate(members):
                    board = self._new_board(
                        player, names[index * chunk:(index + 1) * chunk])
                    boards[board["key"]] = board
                per_board = chunk
            shared = True

        previous = room.get("match") or {}
        room["match_count"] = int(room.get("match_count") or 0) + 1
        room["match"] = {
            "number": room["match_count"],
            "mode": mode,
            "targets": targets,
            "shared": shared,
            "boards": boards,
            "per_board": per_board,
            "per_team": per_team,
            "team_total": per_team if mode == "teams" else 0,
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

    def _team_done(self, room: Dict[str, Any], match: Dict[str, Any], team: str) -> bool:
        """Команда закончила: все её доски закрыты или игроки сдались."""
        members = self._team_members(room, team)
        if not members:
            return False
        for player in members:
            board = match["boards"].get(str(player["id"]))
            if board and not board["finished_at"] and not board["given_up"]:
                return False
        return True

    def _check_finished(self, room: Dict[str, Any], now: float) -> None:
        """Кто победил: первый закрывший набор или команда, закрывшая всё."""
        match = room["match"]
        if match["finished"]:
            return
        if match["mode"] in ("duel", "race"):
            for board in match["boards"].values():
                if board["finished_at"] and not board["given_up"]:
                    match["winner"] = board["key"]
                    self._finish_match(room, now, "solved")
                    return
            active = [board for board in match["boards"].values()
                      if not board["given_up"] and not board["finished_at"]]
            if not active:
                match["draw"] = True
                self._finish_match(room, now, "gave_up")
            return

        for key in TEAM_KEYS:
            members = self._team_members(room, key)
            if not members:
                continue
            boards = [match["boards"].get(str(player["id"])) for player in members]
            if all(board and board["finished_at"] and not board["given_up"]
                   for board in boards):
                match["winner"] = key
                self._finish_match(room, now, "solved")
                return

        # Команда, которая сдалась целиком, выбывает: если вторая ещё играет,
        # победа сразу уходит ей.
        done = {key: self._team_done(room, match, key) for key in TEAM_KEYS
                if self._team_members(room, key)}
        if len(done) < len(TEAM_KEYS):
            return
        for key in TEAM_KEYS:
            if not done.get(key):
                continue
            others = [other for other in TEAM_KEYS if other != key]
            if others and not done.get(others[0]):
                match["winner"] = others[0]
                self._finish_match(room, now, "gave_up")
                return
        if not any(done.values()):
            return

        # Обе команды закончили, но набор никто не закрыл: считаем, кто успел
        # угадать больше, при равенстве — ничья.
        counts = {}
        for key in TEAM_KEYS:
            counts[key] = sum(match["boards"][str(player["id"])]["index"]
                              for player in self._team_members(room, key)
                              if str(player["id"]) in match["boards"])
        best = max(counts.values())
        leaders = [key for key, value in counts.items() if value == best]
        if len(leaders) == 1 and best > 0:
            match["winner"] = leaders[0]
        else:
            match["draw"] = True
        self._finish_match(room, now, "gave_up")

    def _finish_match(self, room: Dict[str, Any], now: float, reason: str) -> None:
        match = room["match"]
        match["finished"] = True
        match["ended"] = now
        match["reason"] = reason
        room["status"] = "finished"
        room["ready"] = set()
        for player in room["players"].values():
            player["ready"] = False

        winner = match.get("winner")
        if winner:
            if match["mode"] == "teams":
                for player in self._team_members(room, winner):
                    self._tally(room, player["id"])["wins"] += 1
            else:
                self._tally(room, int(winner))["wins"] += 1

        room["history"].append({
            "number": match["number"],
            "mode": match["mode"],
            "reason": reason,
            "winner_name": self._winner_name(room, match),
            "targets": [str(target["name"]) for target in match["targets"]],
            "boards": [
                {"name": board["name"],
                 "team": board["team"],
                 "found": board["index"],
                 "total": len(board["assigned"])}
                for board in match["boards"].values()
            ],
        })
        room["history"] = room["history"][-20:]
        room["updated"] = now
        self._log_match(room, reason)

    def _winner_name(self, room: Dict[str, Any], match: Dict[str, Any]) -> str:
        winner = match.get("winner")
        if not winner:
            return ""
        if match["mode"] == "teams":
            return TEAM_NAMES.get(winner, winner)
        return next((board["name"] for board in match["boards"].values()
                     if board["key"] == winner), str(winner))

    @staticmethod
    def _tally(room: Dict[str, Any], player_id: int) -> Dict[str, int]:
        """Счёт комнаты по игроку: сколько угадал сам и сколько партий выиграл."""
        return room.setdefault("tally", {}).setdefault(
            player_id, {"guessed": 0, "wins": 0})

    def _log_match(self, room: Dict[str, Any], reason: str) -> None:
        """Передаёт итог партии наружу — сервер пишет его в журнал матчей.

        Ошибка журнала не должна ломать партию: партия уже закончилась, игроки
        видят результат, поэтому сбой записи только отмечаем в stderr.
        """
        if not self._on_finish:
            return
        match = room["match"]
        players = self._ordered(room)
        winner_board = None
        if match.get("winner") and match["mode"] != "teams":
            winner_board = match["boards"].get(str(match["winner"]))
        winner_name = self._winner_name(room, match)
        first = players[0] if players else {"id": None, "name": ""}
        second = players[1] if len(players) > 1 else {"id": None, "name": ""}
        winner_player = None
        if winner_board:
            winner_player = room["players"].get(winner_board["player_id"])
        elif match["mode"] == "teams" and match.get("winner"):
            members = self._team_members(room, match["winner"])
            winner_player = members[0] if members else None
        others = [board["name"] for board in match["boards"].values()
                  if not winner_board or board["key"] != winner_board["key"]]
        summary = "; ".join(
            f"{board['name']}: {board['index']}/{len(board['assigned'])}"
            for board in match["boards"].values())
        try:
            self._on_finish({
                "room": room["code"],
                "round_number": match["number"],
                "mode": match["mode"],
                "target": "; ".join(str(target["name"]) for target in match["targets"]),
                "players": summary,
                "player_ids": [player["id"] for player in players],
                "player1_id": first.get("id"),
                "player1_name": str(first.get("name") or ""),
                "player2_id": second.get("id"),
                "player2_name": str(second.get("name") or ""),
                "winner_id": winner_player["id"] if winner_player else None,
                "winner_name": winner_name,
                "loser_name": "",
                "winner_attempts": (winner_board["index"] if winner_board
                                    else (match["per_team"] if winner_name else 0)),
                "loser_attempts": 0,
                "reason": reason,
            })
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"  не удалось записать итог партии в журнал: {exc}\n")

    # ---------------------------------------------------------------- вывод
    def _board_public(self, match: Dict[str, Any], board: Dict[str, Any],
                      reveal: bool, you_key: Optional[str]) -> Dict[str, Any]:
        """Доска игрока: чужие подсказки открываются только после итога.

        В командах своя команда видит доски друг друга и во время партии —
        иначе помогать товарищу было бы нельзя.
        """
        current = (board["assigned"][board["index"]]
                   if board["index"] < len(board["assigned"]) else None)
        show = reveal or match["finished"]
        return {
            "key": board["key"],
            "name": board["name"],
            "team": board.get("team"),
            "team_label": TEAM_NAMES.get(board.get("team") or "", ""),
            "total": len(board["assigned"]),
            "found_count": board["index"],
            "found": [item["target"] for item in board["history"]] if show else [],
            "attempts": board["attempts"] if show else None,
            "history": [
                {"target": item["target"],
                 "attempts": item["attempts"],
                 "seconds": item["seconds"],
                 "by": item["by"],
                 "helpers": item["helpers"]}
                for item in board["history"]
            ] if show else None,
            "finished": bool(board["finished_at"]),
            "given_up": bool(board["given_up"]),
            "current": current if show else None,
            "you": bool(you_key and board["key"] == you_key),
            "started": board["started_at"] is not None,
        }

    def _payload(self, room: Dict[str, Any], user: Dict[str, Any],
                 watcher: bool = False) -> Dict[str, Any]:
        """Публичное состояние комнаты с точки зрения игрока или зрителя."""
        now = time.time()
        match = room.get("match")
        ordered = self._ordered(room)
        you = room["players"].get(user["id"])
        is_host = room.get("host") == user["id"]
        you_team = you.get("team") if you else None
        you_key = str(you["id"]) if you else None

        players_public = []
        for player in ordered:
            tally = self._tally(room, player["id"])
            players_public.append({
                "id": player["id"],
                "name": player["name"],
                "you": player["id"] == user["id"],
                "host": player["id"] == room.get("host"),
                "team": player.get("team"),
                "team_label": TEAM_NAMES.get(player.get("team") or "", ""),
                "ready": player["id"] in room["ready"],
                "gave_up": bool(player["gave_up"]),
                "guessed": tally["guessed"],
                "wins": tally["wins"],
            })

        match_public = None
        active_board = None
        you_public = None
        if match:
            boards = []
            for board in match["boards"].values():
                mine = bool(you and board["player_id"] == you["id"])
                mate = bool(match["mode"] == "teams" and you_team
                            and board.get("team") == you_team)
                boards.append(self._board_public(match, board, mine or mate, you_key))
            if you:
                active_board = self._active_board(room, you)
            winner_mine = False
            if match.get("winner") and you:
                if match["mode"] == "teams":
                    winner_mine = match["winner"] == you_team
                else:
                    winner_mine = str(you["id"]) == str(match["winner"])
            match_public = {
                "number": match["number"],
                "mode": match["mode"],
                "mode_label": MODE_LABELS.get(match["mode"], match["mode"]),
                "finished": match["finished"],
                "reason": match["reason"],
                "draw": bool(match["draw"]),
                "winner": ({"name": self._winner_name(room, match),
                            "key": match["winner"],
                            "mine": winner_mine}
                           if match.get("winner") else None),
                "elapsed": round((match["ended"] or now) - match["started"], 1),
                "per_board": match["per_board"],
                "per_team": match["per_team"],
                "team_total": match["team_total"],
                "boards": boards,
                "teams": self._teams_public(room, match),
                "answers": ([public_character(target) for target in match["targets"]]
                            if match["finished"] else None),
            }
            if you:
                own = match["boards"].get(str(you["id"]))
                helping = bool(active_board and active_board["player_id"] != you["id"])
                you_public = {
                    "id": you["id"],
                    "name": you["name"],
                    "team": you.get("team"),
                    "team_label": TEAM_NAMES.get(you.get("team") or "", ""),
                    "ready": you["id"] in room["ready"],
                    "gave_up": bool(you["gave_up"]),
                    "board": own["key"] if own else None,
                    "found_count": own["index"] if own else 0,
                    "total": len(own["assigned"]) if own else 0,
                    "found": ([item["target"] for item in own["history"]] if own else []),
                    "finished": bool(own and own["finished_at"]),
                    "helping": ({"name": active_board["name"]} if helping else None),
                    "active": active_board["key"] if active_board else None,
                    "active_name": active_board["name"] if active_board else None,
                    "attempts": active_board["attempts"] if active_board else [],
                    "active_found": ([item["target"] for item in active_board["history"]]
                                     if active_board else []),
                    "active_total": (len(active_board["assigned"])
                                     if active_board else 0),
                    "active_index": active_board["index"] if active_board else 0,
                    "guessed": self._tally(room, you["id"])["guessed"],
                    "wins": self._tally(room, you["id"])["wins"],
                }

        teams = [
            {"key": team, "label": TEAM_NAMES[team],
             "size": len(self._team_members(room, team)),
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
            "you_team": you.get("team") if you else None,
            "players": players_public,
            "teams": teams,
            "team_total": self._team_total(room) if room["mode"] == "teams" else 0,
            "team_options": self.team_options(room) if room["mode"] == "teams" else [],
            "match": match_public,
            "history": list(room["history"]),
            "tally": [{"name": player["name"], "team_label": TEAM_NAMES.get(
                player.get("team") or "", ""), "guessed": self._tally(room, player["id"])["guessed"],
                "wins": self._tally(room, player["id"])["wins"]} for player in ordered],
            "updated": round(room["updated"], 3),
        }

    def _teams_public(self, room: Dict[str, Any], match: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Сводка по командам: сколько набрано из общего набора."""
        if match["mode"] != "teams":
            return []
        result = []
        for key in TEAM_KEYS:
            members = self._team_members(room, key)
            if not members:
                continue
            found = sum(match["boards"][str(player["id"])]["index"]
                        for player in members if str(player["id"]) in match["boards"])
            done = all(match["boards"].get(str(player["id"]))
                       and (match["boards"][str(player["id"])]["finished_at"]
                            or match["boards"][str(player["id"])]["given_up"])
                       for player in members)
            result.append({
                "key": key,
                "label": TEAM_NAMES[key],
                "total": match["team_total"],
                "found_count": found,
                "done": done,
                "winner": match.get("winner") == key,
            })
        return result

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
                "match_count": 0,
                "team_total": 0,
                "tally": {},
                "history": [],
            }
            self._tally(room, user["id"])
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
                self._tally(room, user["id"])
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
            room.get("tally", {}).pop(user["id"], None)
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
            if mode == "teams":
                room["team_total"] = 0
            self._assign_teams(room)
            room["updated"] = now
            return self._payload(room, user)

    def move_team(self, code: str, user: Dict[str, Any], team: Any) -> Dict[str, Any]:
        """Игрок переходит в другую команду — пока партия не началась.

        Раздача идёт по очереди входа, но если состав не устраивает, игрок
        меняет команду сам: иначе приглашённому пришлось бы выходить и
        заходить заново, чтобы оказаться с товарищем.
        """
        key = str(team or "").strip().lower()
        if key not in TEAM_KEYS:
            raise NarutodleError("Неизвестная команда: бывают только A и B")
        now = time.time()
        with self._lock:
            room = self._room(code)
            player = self._player(room, user)
            if room["mode"] != "teams":
                raise NarutodleError("Команды есть только в режиме «Команды»")
            if room["status"] != "lobby":
                raise NarutodleError("Команду можно сменить только до начала партии")
            if player.get("team") == key:
                return self._payload(room, user)
            player["team"] = key
            options = self._team_options(room)
            if options and int(room.get("team_total") or 0) not in options:
                room["team_total"] = self._default_team_total(room)
            room["updated"] = now
            return self._payload(room, user)

    def set_team_total(self, code: str, user: Dict[str, Any], total: Any) -> Dict[str, Any]:
        """Хозяин выбирает, сколько персонажей взять на команду.

        Число обязано быть кратным числу игроков в командах: набор делится
        поровну, иначе у одних было бы больше персонажей, чем у других.
        """
        now = time.time()
        with self._lock:
            room = self._room(code)
            self._player(room, user)
            if user["id"] != room.get("host"):
                raise NarutodleError("Размер набора выбирает хозяин комнаты")
            if room["status"] != "lobby":
                raise NarutodleError("Размер набора можно менять только в лобби")
            if room["mode"] != "teams":
                raise NarutodleError("Размер набора есть только в режиме «Команды»")
            options = self._team_options(room)
            try:
                value = int(total)
            except (TypeError, ValueError):
                raise NarutodleError("Размер набора должен быть числом") from None
            if value not in options:
                raise NarutodleError(
                    "Число персонажей должно делиться на игроков в командах: "
                    + ", ".join(str(item) for item in options))
            room["team_total"] = value
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

    def _active_board(self, room: Dict[str, Any],
                      player: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Доска, на которой сейчас играет участник (под замком или без победы).

        Своя доска, пока не закрыта. В командах закрывший свои персонажи
        подключается к незакрытой доске товарища и продолжает уже на ней.
        """
        match = room.get("match")
        if not match or player.get("gave_up"):
            return None
        own = match["boards"].get(str(player["id"]))
        if own and not own["finished_at"] and not own["given_up"]:
            return own
        if match["mode"] != "teams":
            return None
        for mate in self._team_members(room, player.get("team")):
            if mate["id"] == player["id"] or mate.get("gave_up"):
                continue
            board = match["boards"].get(str(mate["id"]))
            if board and not board["finished_at"] and not board["given_up"]:
                return board
        return None

    def guess(self, code: str, user: Dict[str, Any], name: str) -> Dict[str, Any]:
        """Проверяет догадку на активной доске и возвращает состояние комнаты."""
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
            if player["gave_up"]:
                raise NarutodleError("Вы сдались в этой партии")
            board = self._active_board(room, player)
            if not board:
                raise NarutodleError("Ваши доски закрыты — ждём остальных")
            if len(board["attempts"]) >= MAX_ATTEMPTS:
                raise NarutodleError(f"Больше {MAX_ATTEMPTS} попыток на доску не бывает")

            character = self.find_character(name)
            if not character:
                raise NarutodleError("Такого персонажа нет в наборе — выберите из подсказки")

            guessed_names = {item["target"] for item in board["history"]}
            if character["name"] in guessed_names:
                raise NarutodleError(f"{character['name']} уже найден на этой доске")

            target_name = board["assigned"][board["index"]]

            target = self.find_character(target_name) or {}
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
            if board["started_at"] is None:
                board["started_at"] = now
            board["attempts"].append({
                "name": character["name"],
                "result": result,
                "correct": character["name"] == target_name,
                "by": player["name"],
            })
            if character["name"] == target_name:
                contributors = {board["name"]}
                contributors.update(attempt["by"] for attempt in board["attempts"])
                board["history"].append({
                    "target": target_name,
                    "attempts": board["attempts"],
                    "seconds": round(now - (board["started_at"] or now), 1),
                    "by": player["name"],
                    "helpers": [name_ for name_ in sorted(contributors) if name_ != board["name"]],
                })
                board["index"] += 1
                # Доска очищается сама: подсказки прошлого персонажа уже в архиве.
                board["attempts"] = []
                board["started_at"] = now
                if board["index"] >= len(board["assigned"]):
                    board["finished_at"] = now
                self._tally(room, player["id"])["guessed"] += 1
                self._check_finished(room, now)

            room["updated"] = now
            return self._payload(room, user)

    def give_up(self, code: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Сдача: доска закрывается, в командах товарищи продолжают без вас."""
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
        match = room.get("match")
        player = self._player(room, user)
        if player["gave_up"]:
            raise NarutodleError("Вы уже сдались")
        player["gave_up"] = True
        own = match["boards"].get(str(player["id"])) if match else None
        if own and not own["finished_at"]:
            own["given_up"] = True
            own["finished_at"] = now
        if match:
            self._check_finished(room, now)
        room["updated"] = now

    def rematch(self, code: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Игрок готов к новой партии; она начинается, когда готовы все.

        Иначе выходило бы так: один нажал «Ещё игра» и уже угадывает, пока
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
    "DUEL_TARGETS",
    "MAX_ATTEMPTS",
    "MAX_PLAYERS",
    "MAX_TEAM_TOTAL",
    "MODES",
    "MODE_HINTS",
    "MODE_LABELS",
    "Narutodle",
    "NarutodleError",
    "RACE_TARGETS",
    "ROOM_TTL_SECONDS",
    "compare_attribute",
]
