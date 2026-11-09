# -*- coding: utf-8 -*-
"""«322-0» — драфт по Dota 2 на бюджет: Streamers Battle 13.

Правила игры:
    * пул — игроки Streamers Battle 13: у каждого в таблице своя стоимость
      (от 10 до 95 очков) и своя позиция (колонка position; 0 — неизвестна);
    * драфт идёт паками: в паке пять случайных игроков и пять героев, а из
      пака берут ровно одно — игрока либо героя, — после чего пак меняется
      целиком: и игроки, и герои;
    * состав — пять игроков, и сумма их стоимости не должна выйти за бюджет
      сложности (300, 305 или 310 очков);
    * героя игроку игрок выбирает сам (какой из паковских героев кому),
      а пять героев обязаны закрыть все пять позиций 1–5;
    * на мид (позиция 2) берут только игрока дешевле 75 очков;
    * игра на своей позиции даёт надбавку к силе состава, игра на чужой —
      заметный минус: своя позиция берётся из пула;
    * сила героя в связке — оценка пары «игрок + герой» из пула (его матчи
      на герое), а если пары нет, то обычная оценка героя;
    * дальше турнир: две группы по четыре команды, внутри группы круговая
      Bo3; места 1–2 уходят в верхнюю сетку, места 3–4 — в нижнюю. Верхняя
      сетка даёт право на ошибку: поражение опускает в нижнюю, а кто начал
      с нижней, вылетает после первого поражения в ней. Финал нижней сетки и
      гранд-финал играются Bo5. Усилений нет: победа сразу отправляет дальше.

Соперники собираются из того же пула: у каждой чужой команды свой бюджет
(300–315 очков), свои игроки со своими позициями и свои герои, а сила
считается той же формулой, что и ваша.

Стоимости и позиции игроков — из таблицы владельца сайта; оценки героев и
оценки пар — игровые (см. backend/dotadraft_data.py). Ники участников, Dota 2
и её герои — исторические названия и товарные знаки их владельцев; игра
некоммерческая.
"""
from __future__ import annotations

import random
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

try:  # запуск как модуль: python -m backend.server
    from .dotadraft_data import (
        BRACKET_ROUNDS,
        DIFFICULTIES,
        DIFFICULTY_BUDGETS,
        DIFFICULTY_LABELS,
        GROUPS,
        GROUP_BEST_OF,
        GROUP_SIZE,
        HERO_WEIGHT,
        MID_COST_LIMIT,
        MID_POSITION,
        OPPONENT_BUDGET_MAX,
        OPPONENT_BUDGET_MIN,
        OTHER_POSITION_PENALTY,
        OWN_POSITION_BONUS,
        PACK_HEROES,
        PACK_PLAYERS,
        PLAYER_WEIGHT,
        POSITIONS,
        POSITION_HINTS,
        POSITION_LABELS,
        SQUAD_SIZE,
        STAR_CARRY_WEAK_HERO,
        STAR_COST,
        STAR_PAIR,
        STRENGTH_SCALE,
        STRONG_HERO,
        WEAK_HERO,
        hero_rows,
        player_rows,
        validate_heroes,
        validate_players,
    )
except ImportError:  # запуск как файл: python backend/server.py
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from dotadraft_data import (  # type: ignore
        BRACKET_ROUNDS,
        DIFFICULTIES,
        DIFFICULTY_BUDGETS,
        DIFFICULTY_LABELS,
        GROUPS,
        GROUP_BEST_OF,
        GROUP_SIZE,
        HERO_WEIGHT,
        MID_COST_LIMIT,
        MID_POSITION,
        OPPONENT_BUDGET_MAX,
        OPPONENT_BUDGET_MIN,
        OTHER_POSITION_PENALTY,
        OWN_POSITION_BONUS,
        PACK_HEROES,
        PACK_PLAYERS,
        PLAYER_WEIGHT,
        POSITIONS,
        POSITION_HINTS,
        POSITION_LABELS,
        SQUAD_SIZE,
        STAR_CARRY_WEAK_HERO,
        STAR_COST,
        STAR_PAIR,
        STRENGTH_SCALE,
        STRONG_HERO,
        WEAK_HERO,
        hero_rows,
        player_rows,
        validate_heroes,
        validate_players,
    )

# Заброшенный прогон держим сутки: матчи идут не подряд.
RUN_TTL_SECONDS = 24 * 60 * 60
MAX_RUNS = 300

# Круговой этап на четыре команды: три тура по две серии.
GROUP_ROUNDS: Tuple[Tuple[Tuple[int, int], ...], ...] = (
    ((0, 1), (2, 3)),
    ((0, 2), (1, 3)),
    ((0, 3), (1, 2)),
)

# Сетка двойного выбывания: кто с кем играет и откуда берётся участник.
# «group» — место в группе, «winner»/«loser» — исход уже сыгранной серии.
BRACKET_PLAN: Tuple[Tuple[str, str, Tuple[Any, ...]], ...] = (
    ("ub1-0", "ub1", (("group", 1, "A"), ("group", 2, "B"))),
    ("ub1-1", "ub1", (("group", 1, "B"), ("group", 2, "A"))),
    ("lb1-0", "lb1", (("group", 3, "A"), ("group", 4, "B"))),
    ("lb1-1", "lb1", (("group", 3, "B"), ("group", 4, "A"))),
    ("ub2-0", "ub2", (("winner", "ub1-0"), ("winner", "ub1-1"))),
    ("lb2-0", "lb2", (("winner", "lb1-0"), ("loser", "ub1-1"))),
    ("lb2-1", "lb2", (("winner", "lb1-1"), ("loser", "ub1-0"))),
    ("lb3-0", "lb3", (("winner", "lb2-0"), ("winner", "lb2-1"))),
    ("lb4-0", "lb4", (("winner", "lb3-0"), ("loser", "ub2-0"))),
    ("gf-0", "gf", (("winner", "ub2-0"), ("winner", "lb4-0"))),
)

# Раунды плей-офф по ключу: название и формат серии.
ROUND_INFO: Dict[str, Dict[str, Any]] = {item["key"]: dict(item) for item in BRACKET_ROUNDS}


class DotaDraftError(ValueError):
    """Ошибка правил игры: превращается в ответ 400 с понятным текстом."""


def public_player(player: Dict[str, Any]) -> Dict[str, Any]:
    """Игрок в том виде, в каком его видит страница."""
    own = int(player.get("position") or 0)
    return {
        "id": str(player["id"]),
        "nickname": str(player["nickname"]),
        "cost": int(player["cost"]),
        "own_position": own,
        "own_position_label": POSITION_LABELS.get(own, ""),
    }


def public_hero(hero: Dict[str, Any]) -> Dict[str, Any]:
    """Герой в том виде, в каком его видит страница."""
    return {
        "id": str(hero["id"]),
        "name": str(hero["name"]),
        "name_en": str(hero["name_en"]),
        "position": int(hero["position"]),
        "position_label": POSITION_LABELS.get(int(hero["position"]), ""),
        "rating": int(hero["rating"]),
    }


class DotaDraft:
    """Прогоны «322-0»: паки, состав в бюджет, герои по позициям и сетка."""

    def __init__(self, players: Optional[Sequence[Dict[str, Any]]] = None,
                 heroes: Optional[Sequence[Dict[str, Any]]] = None,
                 player_heroes: Optional[Sequence[Dict[str, Any]]] = None,
                 rng: Optional[random.Random] = None,
                 players_provider: Optional[Callable[[], List[Dict[str, Any]]]] = None,
                 heroes_provider: Optional[Callable[[], List[Dict[str, Any]]]] = None,
                 ratings_provider: Optional[Callable[[], List[Dict[str, Any]]]] = None,
                 on_finish: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        self._lock = threading.Lock()
        self._runs: Dict[str, Dict[str, Any]] = {}
        self._rng = rng or random.Random()
        self._players_provider = players_provider
        self._heroes_provider = heroes_provider
        self._ratings_provider = ratings_provider
        self._on_finish = on_finish
        self._players: List[Dict[str, Any]] = []
        self._heroes: List[Dict[str, Any]] = []
        self._pair_ratings: Dict[Tuple[str, str], int] = {}
        # Раунды держим на движке: их показывают и страница, и API.
        self.rounds: List[Dict[str, Any]] = [dict(round_) for round_ in BRACKET_ROUNDS]
        self.reload_pool(players, heroes, player_heroes)

    # ------------------------------------------------------------------ данные
    def reload_pool(self, players: Optional[Sequence[Dict[str, Any]]] = None,
                    heroes: Optional[Sequence[Dict[str, Any]]] = None,
                    player_heroes: Optional[Sequence[Dict[str, Any]]] = None) -> int:
        """Перечитывает пул: обычно из базы, при первом запуске — из набора в коде."""
        if players is None and self._players_provider is not None:
            try:
                players = self._players_provider()
            except Exception:  # noqa: BLE001
                players = None
        if heroes is None and self._heroes_provider is not None:
            try:
                heroes = self._heroes_provider()
            except Exception:  # noqa: BLE001
                heroes = None
        if player_heroes is None and self._ratings_provider is not None:
            try:
                player_heroes = self._ratings_provider()
            except Exception:  # noqa: BLE001
                player_heroes = None
        if players is None:
            players = player_rows()
        if heroes is None:
            heroes = hero_rows()
        self._players = [self._normalize_player(row) for row in players if row.get("nickname")]
        self._heroes = [self._normalize_hero(row) for row in heroes if row.get("name")]
        self._pair_ratings = {
            (str(row.get("player_id")), str(row.get("hero_id"))): int(row.get("rating") or 0)
            for row in (player_heroes or ())
            if row.get("player_id") and row.get("hero_id")
        }
        return len(self._players)

    @staticmethod
    def _normalize_player(row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": str(row.get("id") or ""),
            "nickname": str(row.get("nickname") or ""),
            "cost": int(row.get("cost") or 0),
            "position": int(row.get("position") or 0),
        }

    @staticmethod
    def _normalize_hero(row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": str(row.get("id") or ""),
            "name": str(row.get("name") or ""),
            "name_en": str(row.get("name_en") or ""),
            "position": int(row.get("position") or 0),
            "rating": int(row.get("rating") or 0),
        }

    def refresh(self) -> int:
        """Перечитать пул перед новым прогоном: правки в базе видны сразу."""
        return self.reload_pool()

    def player_count(self) -> int:
        return len(self._players)

    def hero_count(self) -> int:
        return len(self._heroes)

    def pair_count(self) -> int:
        return len(self._pair_ratings)

    def known_positions(self) -> int:
        return len([1 for player in self._players if player["position"]])

    def position_counts(self) -> Dict[int, int]:
        counts = {position: 0 for position, _ in POSITIONS}
        for hero in self._heroes:
            counts[hero["position"]] = counts.get(hero["position"], 0) + 1
        return counts

    def ready(self) -> bool:
        """Играть можно, когда хватает игроков и на каждой позиции есть герой."""
        needed = max(SQUAD_SIZE * 6, PACK_PLAYERS + SQUAD_SIZE)
        if len(self._players) < needed:
            return False
        return all(count >= PACK_HEROES for count in self.position_counts().values())

    def problems(self) -> List[str]:
        """Что не так с пулом: пустые поля, повторы, мало героев на позицию."""
        return validate_players(self._players) + validate_heroes(self._heroes)

    def pool(self) -> Dict[str, Any]:
        """Весь пул для страницы: игроки и герои."""
        return {
            "players": [public_player(player) for player in self._players],
            "heroes": [public_hero(hero) for hero in self._heroes],
        }

    def pair_rating(self, player: Dict[str, Any], hero: Dict[str, Any]) -> int:
        """Оценка героя под игрока: пара из пула, иначе оценка героя."""
        return int(self._pair_ratings.get(
            (str(player["id"]), str(hero["id"])), hero["rating"]))

    def _player(self, player_id: str) -> Dict[str, Any]:
        wanted = str(player_id or "").strip().lower()
        for player in self._players:
            if player["id"].lower() == wanted or player["nickname"].lower() == wanted:
                return player
        raise DotaDraftError("Такого игрока нет в пуле")

    def _hero(self, hero_id: str) -> Dict[str, Any]:
        wanted = str(hero_id or "").strip().lower()
        for hero in self._heroes:
            if hero["id"].lower() == wanted or hero["name"].lower() == wanted:
                return hero
        raise DotaDraftError("Такого героя нет в наборе")

    # ---------------------------------------------------------------- служебное
    def _cleanup(self, now: float) -> None:
        for run_id, run in list(self._runs.items()):
            if now - run.get("updated_at", now) > RUN_TTL_SECONDS:
                self._runs.pop(run_id, None)

    def _new_run_id(self) -> str:
        while True:
            run_id = "d" + "%07x" % self._rng.getrandbits(28)
            if run_id not in self._runs:
                return run_id

    def _run(self, run_id: str) -> Dict[str, Any]:
        run = self._runs.get(str(run_id or "").strip())
        if not run:
            raise DotaDraftError("Прогон не найден: возможно, он устарел")
        return run

    def state(self, run_id: str, user: Dict[str, Any]) -> Dict[str, Any]:
        run = self._run(run_id)
        self._owner_check(run, user)
        return self._payload(run, user, time.time())

    @staticmethod
    def _owner_check(run: Dict[str, Any], user: Dict[str, Any]) -> None:
        if user.get("role") == "admin":
            return
        if int(run["user_id"]) != int(user.get("id") or 0):
            raise DotaDraftError("Это чужой прогон")

    # ------------------------------------------------------------------- старт
    def start(self, user: Dict[str, Any], difficulty: str = "hard") -> Dict[str, Any]:
        if difficulty not in DIFFICULTY_BUDGETS:
            raise DotaDraftError("Неизвестная сложность")
        self.refresh()
        if not self.ready():
            raise DotaDraftError("Пул пуст: нужны игроки и герои на все позиции")
        now = time.time()
        with self._lock:
            self._cleanup(now)
            if len(self._runs) >= MAX_RUNS:
                oldest = min(self._runs, key=lambda key: self._runs[key]["updated_at"])
                self._runs.pop(oldest, None)
            run: Dict[str, Any] = {
                "id": self._new_run_id(),
                "game": "dota322",
                "user_id": int(user.get("id") or 0),
                "username": user.get("username") or "",
                "created_at": now,
                "updated_at": now,
                "difficulty": difficulty,
                "budget": DIFFICULTY_BUDGETS[difficulty],
                "event": "Streamers Battle 13",
                "phase": "draft",
                "roster": [],
                "heroes": {},
                "pack": {"players": [], "heroes": []},
                "picks": 0,
                "tournament": None,
                "history": [],
                "seed": self._rng.getrandbits(32),
                "log": [],
            }
            self._runs[run["id"]] = run
            self._fresh_pack(run)
            self._say(run, f"Старт прогона: {DIFFICULTY_LABELS[difficulty]}, "
                           f"бюджет {run['budget']} очков на {SQUAD_SIZE} игроков")
            self._say(run, f"Пак драфта: {len(run['pack']['players'])} игроков и "
                           f"{len(run['pack']['heroes'])} героев — берите одно")
            return self._payload(run, user, now)

    # -------------------------------------------------------------------- паки
    def _fresh_pack(self, run: Dict[str, Any]) -> None:
        """Новый пак: пять игроков и пять героев; из пака берут одно.

        В пак по возможности попадают игроки по бюджету: если денег на всех
        не хватает, дорогие всё равно показываются — по ним видно, чего не
        хватило. Героев даём только по свободным позициям: пять героев обязаны
        закрыть все пять позиций.
        """
        taken = {player["id"] for player in run["roster"]}
        left = run["budget"] - self._spent(run)
        fits: List[Dict[str, Any]] = []
        rest: List[Dict[str, Any]] = []
        for player in self._players:
            if player["id"] in taken:
                continue
            (fits if player["cost"] <= left else rest).append(player)
        self._rng.shuffle(fits)
        self._rng.shuffle(rest)
        players = (fits + rest)[:PACK_PLAYERS]

        used_heroes = {hero["id"] for hero in run["heroes"].values()}
        used_positions = {int(hero["position"]) for hero in run["heroes"].values()}
        heroes = [hero for hero in self._heroes
                  if hero["id"] not in used_heroes and hero["position"] not in used_positions]
        self._rng.shuffle(heroes)
        run["pack"] = {
            "players": [dict(player) for player in players],
            "heroes": [dict(hero) for hero in heroes[:PACK_HEROES]],
        }

    def _pack_player(self, run: Dict[str, Any], player_id: str) -> Dict[str, Any]:
        wanted = str(player_id or "").strip().lower()
        for player in run["pack"]["players"]:
            if player["id"].lower() == wanted or player["nickname"].lower() == wanted:
                return player
        raise DotaDraftError("Этот игрок не из текущего пака")

    def _pack_hero(self, run: Dict[str, Any], hero_id: str) -> Dict[str, Any]:
        wanted = str(hero_id or "").strip().lower()
        for hero in run["pack"]["heroes"]:
            if hero["id"].lower() == wanted or hero["name"].lower() == wanted:
                return hero
        raise DotaDraftError("Этот герой не из текущего пака")

    @staticmethod
    def _need_draft(run: Dict[str, Any]) -> None:
        if run["phase"] != "draft":
            raise DotaDraftError("Турнир уже начался: состав и герои зафиксированы")

    def take_player(self, run_id: str, user: Dict[str, Any],
                    player_id: str) -> Dict[str, Any]:
        """Берёт игрока из пака, если он проходит по бюджету."""
        with self._lock:
            run = self._run(run_id)
            self._owner_check(run, user)
            self._need_draft(run)
            player = self._pack_player(run, player_id)
            if any(item["id"] == player["id"] for item in run["roster"]):
                raise DotaDraftError(f"{player['nickname']} уже в составе")
            if len(run["roster"]) >= SQUAD_SIZE:
                raise DotaDraftError(f"В составе уже {SQUAD_SIZE} игроков")
            if self._spent(run) + player["cost"] > run["budget"]:
                left = run["budget"] - self._spent(run)
                raise DotaDraftError(
                    f"{player['nickname']} стоит {player['cost']}, а в бюджете осталось {left}")
            run["roster"].append(dict(player))
            run["picks"] = int(run.get("picks") or 0) + 1
            self._say(run, f"Из пака взят {player['nickname']} за {player['cost']} "
                           f"(осталось {run['budget'] - self._spent(run)})")
            self._after_pick(run)
            return self._payload(run, user, run["updated_at"])

    def take_hero(self, run_id: str, user: Dict[str, Any], hero_id: str,
                  player_id: str) -> Dict[str, Any]:
        """Берёт героя из пака и отдаёт его выбранному игроку состава."""
        with self._lock:
            run = self._run(run_id)
            self._owner_check(run, user)
            self._need_draft(run)
            hero = self._pack_hero(run, hero_id)
            wanted = str(player_id or "").strip().lower()
            player = next((item for item in run["roster"]
                           if item["id"].lower() == wanted
                           or item["nickname"].lower() == wanted), None)
            if not player:
                raise DotaDraftError("Сначала возьмите этого игрока в состав")
            if player["id"] in run["heroes"]:
                raise DotaDraftError(f"У {player['nickname']} уже есть герой")
            position = int(hero["position"])
            if position == MID_POSITION and int(player["cost"]) >= MID_COST_LIMIT:
                raise DotaDraftError(
                    f"На мид (позиция {MID_POSITION}, {POSITION_LABELS[MID_POSITION]}) "
                    f"берут игрока дешевле {MID_COST_LIMIT} очков: "
                    f"{player['nickname']} стоит {player['cost']}")
            busy = {int(item["position"]): nick for nick, item in run["heroes"].items()}
            if position in busy:
                owner = next(item for item in run["roster"]
                             if item["id"] == busy[position])
                raise DotaDraftError(f"Позиция {position} уже за "
                                     f"{owner['nickname']}: пять героев закрывают пять позиций")
            run["heroes"][player["id"]] = dict(hero)
            run["picks"] = int(run.get("picks") or 0) + 1
            self._say(run, f"Из пака взят герой {hero['name']} для {player['nickname']} "
                           f"(позиция {position}, {POSITION_LABELS.get(position, '')})")
            self._after_pick(run)
            return self._payload(run, user, run["updated_at"])

    def _after_pick(self, run: Dict[str, Any]) -> None:
        """После любого пика: либо новый пак, либо старт турнира."""
        run["updated_at"] = time.time()
        if self._complete(run):
            run["phase"] = "group"
            self._start_tournament(run)
            self._say(run, "Состав собран: две группы по четыре команды, дальше двойное выбывание")
            return
        self._fresh_pack(run)

    # ------------------------------------------------------------------ оценки
    def _spent(self, run: Dict[str, Any]) -> int:
        return sum(int(item["cost"]) for item in run["roster"])

    def _complete(self, run: Dict[str, Any]) -> bool:
        """Состав собран: пять игроков и пять героев на все пять позиций."""
        if len(run["roster"]) != SQUAD_SIZE:
            return False
        if len(run["heroes"]) != SQUAD_SIZE:
            return False
        return len({hero["position"] for hero in run["heroes"].values()}) == SQUAD_SIZE

    def rating(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Разложение силы: игроки и герои, связки, своя позиция игрока."""
        pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        for player in entity.get("roster") or ():
            hero = (entity.get("heroes") or {}).get(player["id"])
            if hero:
                pairs.append((player, hero))

        base = 0.0
        for player, hero in pairs:
            base += PLAYER_WEIGHT * float(player["cost"]) \
                + HERO_WEIGHT * float(self.pair_rating(player, hero))
        base = base / len(pairs) if pairs else 0.0

        pair_bonus = 0.0
        for player, hero in pairs:
            rating = self.pair_rating(player, hero)
            if int(player["cost"]) >= STAR_COST and rating >= STRONG_HERO:
                pair_bonus += STAR_PAIR
            elif int(player["cost"]) >= STAR_COST and rating <= WEAK_HERO:
                pair_bonus += STAR_CARRY_WEAK_HERO

        positions = 0.0
        for player, hero in pairs:
            own = int(player.get("position") or 0)
            if not own:
                continue
            positions += OWN_POSITION_BONUS if own == int(hero["position"]) \
                else OTHER_POSITION_PENALTY

        total = base + pair_bonus + positions
        return {
            "base": round(base, 2),
            "pairs": round(pair_bonus, 2),
            "positions": round(positions, 2),
            "total": round(total, 2),
            "filled": len(pairs),
        }

    # --------------------------------------------------------------- турнир
    def _start_tournament(self, run: Dict[str, Any]) -> None:
        teams = self._build_teams(run)
        matches: List[Dict[str, Any]] = []
        for group_key in ("A", "B"):
            lineup = [team["id"] for team in teams if team["group"] == group_key]
            for index, pairs in enumerate(GROUP_ROUNDS):
                for order, (first, second) in enumerate(pairs):
                    matches.append({
                        "key": f"g{group_key}{index + 1}-{order}",
                        "phase": "group",
                        "group": group_key,
                        "round": f"group{index + 1}",
                        "title": f"Группа {group_key}, тур {index + 1}",
                        "best_of": GROUP_BEST_OF,
                        "sides": ({"team": lineup[first]}, {"team": lineup[second]}),
                        "result": None,
                    })
        run["tournament"] = {
            "teams": teams,
            "matches": matches,
            "bracket_at": None,
        }
        mine = self._my_team(run)
        self._say(run, f"Ваша команда «{mine['name']}» играет в группе "
                       f"{mine['group']}: три серии Bo{GROUP_BEST_OF}")

    def _build_teams(self, run: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Восемь команд: ваша из драфта и семь собранных из того же пула."""
        mine = {
            "id": "mine",
            "name": (run["username"] or "Ваш состав"),
            "mine": True,
            "budget": run["budget"],
            "roster": [dict(player) for player in run["roster"]],
            "heroes": {player_id: dict(hero)
                       for player_id, hero in run["heroes"].items()},
            "group": "A",
        }
        teams = [mine]
        used = {player["id"] for player in mine["roster"]}
        for index in range(1, GROUPS * GROUP_SIZE):
            budget = self._rng.randint(OPPONENT_BUDGET_MIN, OPPONENT_BUDGET_MAX)
            roster = self._draw_roster(budget, used)
            used |= {player["id"] for player in roster}
            teams.append({
                "id": f"t{index}",
                "name": self._team_name(roster),
                "mine": False,
                "budget": budget,
                "roster": roster,
                "heroes": self._draw_heroes(roster),
                "group": "A" if index < GROUP_SIZE else "B",
            })
        for team in teams:
            team["strength"] = self.rating(team)["total"]
        return teams

    def _team_name(self, roster: Sequence[Dict[str, Any]]) -> str:
        if not roster:
            return "Микс"
        best = max(roster, key=lambda player: (int(player["cost"]), player["nickname"]))
        return f"Микс «{best['nickname']}»"

    def _draw_roster(self, budget: int, used: set) -> List[Dict[str, Any]]:
        """Состав соперника: пять игроков, что укладываются в его бюджет."""
        pool = [player for player in self._players if player["id"] not in used]
        if len(pool) < SQUAD_SIZE:
            return []
        best: List[Dict[str, Any]] = []
        best_sum = -1
        for _ in range(600):
            candidate = self._rng.sample(pool, SQUAD_SIZE)
            total = sum(int(player["cost"]) for player in candidate)
            if total <= budget and total > best_sum:
                best, best_sum = candidate, total
                if total == budget:
                    break
        if not best:
            best = sorted(pool, key=lambda player: (player["cost"], player["id"]))[:SQUAD_SIZE]
        return [dict(player) for player in best]

    def _draw_heroes(self, roster: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Герои соперника: по одному на позицию, мид — не дороже порога."""
        heroes: Dict[str, Dict[str, Any]] = {}
        if not roster:
            return heroes
        waiting = [dict(player) for player in roster]
        cheap = [player for player in waiting if int(player["cost"]) < MID_COST_LIMIT]
        mid_player = self._rng.choice(cheap) if cheap \
            else min(waiting, key=lambda player: (int(player["cost"]), player["id"]))
        waiting = [player for player in waiting if player["id"] != mid_player["id"]]
        positions = [position for position, _ in POSITIONS if position != MID_POSITION]
        self._rng.shuffle(positions)
        for player, position in [(mid_player, MID_POSITION)] + list(zip(waiting, positions)):
            candidates = sorted((hero for hero in self._heroes
                                 if int(hero["position"]) == position),
                                key=lambda hero: (-hero["rating"], hero["name"]))
            if not candidates:
                continue
            top = candidates[:max(1, len(candidates) // 2)]
            heroes[player["id"]] = dict(self._rng.choice(top))
        return heroes

    @staticmethod
    def _my_team(run: Dict[str, Any]) -> Dict[str, Any]:
        return next(team for team in run["tournament"]["teams"] if team["mine"])

    @staticmethod
    def _find_match(run: Dict[str, Any], key: str) -> Optional[Dict[str, Any]]:
        for match in run["tournament"]["matches"]:
            if match["key"] == key:
                return match
        return None

    def _resolve_sides(self, run: Dict[str, Any],
                       match: Dict[str, Any]) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """Кто играет серию. Пока участники неизвестны — None."""
        by_id = {team["id"]: team for team in run["tournament"]["teams"]}
        resolved: List[Dict[str, Any]] = []
        for side in match["sides"]:
            if "team" in side:
                team = by_id.get(side["team"])
            else:
                source = self._find_match(run, side.get("winner") or side.get("loser"))
                if source is None or source["result"] is None:
                    return None
                key = "winner" if "winner" in side else "loser"
                team = by_id.get(source["result"][key])
            if team is None:
                return None
            resolved.append(team)
        return resolved[0], resolved[1]

    def _pending_match(self, run: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]],
                                                           Optional[Tuple[Any, Any]]]:
        """Ваша ближайшая несыгранная серия: её и играет кнопка «Играть»."""
        for match in run["tournament"]["matches"]:
            if match["result"] is not None:
                continue
            sides = self._resolve_sides(run, match)
            if sides is None:
                continue
            if any(team["mine"] for team in sides):
                return match, sides
        return None, None

    def _advance(self, run: Dict[str, Any]) -> None:
        """Доигрывает чужие серии: они не ждут игрока."""
        if not run.get("tournament"):
            return
        matches = run["tournament"]["matches"]
        while True:
            progressed = False
            for match in matches:
                if match["result"] is not None:
                    continue
                sides = self._resolve_sides(run, match)
                if sides is None or any(team["mine"] for team in sides):
                    continue
                self._play_series(run, match, sides)
                progressed = True
            if not progressed:
                break

    def _play_series(self, run: Dict[str, Any], match: Dict[str, Any],
                     sides: Tuple[Dict[str, Any], Dict[str, Any]]) -> None:
        """Серия до победы: Bo1/Bo3/Bo5 — по формату раунда."""
        first, second = sides
        rng = random.Random(f"{run['seed']}:{match['key']}")
        need = int(match["best_of"]) // 2 + 1
        chance = 1.0 / (1.0 + 10 ** ((second["strength"] - first["strength"]) / STRENGTH_SCALE))
        score = {first["id"]: 0, second["id"]: 0}
        games: List[Dict[str, Any]] = []
        guard = 0
        while (score[first["id"]] < need and score[second["id"]] < need
               and guard < int(match["best_of"])):
            guard += 1
            ours = rng.random() < chance
            score[first["id"]] += 1 if ours else 0
            score[second["id"]] += 0 if ours else 1
            games.append({"game": len(games) + 1,
                          "winner": first["id"] if ours else second["id"]})
        winner = first if score[first["id"]] > score[second["id"]] else second
        loser = second if winner["id"] == first["id"] else first
        match["result"] = {
            "winner": winner["id"],
            "loser": loser["id"],
            "score": {first["id"]: score[first["id"]], second["id"]: score[second["id"]]},
            "strength": {first["id"]: first["strength"], second["id"]: second["strength"]},
            "games": games,
        }
        if not (winner["mine"] or loser["mine"]):
            return
        mine = winner if winner["mine"] else loser
        rival = loser if winner["mine"] else winner
        self._record_series(run, match, mine, rival)
        verb = "победа над" if winner["mine"] else "поражение от"
        self._say(run, f"{match['title']}: {verb} {rival['name']} "
                       f"{score[mine['id']]}:{score[rival['id']]}")

    def _record_series(self, run: Dict[str, Any], match: Dict[str, Any],
                       mine: Dict[str, Any], rival: Dict[str, Any]) -> None:
        """Ваша серия уходит в историю прогона: её видно на странице."""
        result = match["result"]
        run["history"].append({
            "key": match["key"],
            "round": match["round"],
            "title": match["title"],
            "best_of": int(match["best_of"]),
            "won": bool(result["winner"] == mine["id"]),
            "score": f"{result['score'][mine['id']]}:{result['score'][rival['id']]}",
            "our_strength": round(float(mine["strength"]), 2),
            "opponent": self._opponent_public(rival),
            "games": [{"game": game["game"], "won": game["winner"] == mine["id"]}
                      for game in result["games"]],
        })

    @staticmethod
    def _opponent_public(team: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "name": team["name"],
            "budget": int(team["budget"]),
            "strength": round(float(team["strength"]), 2),
            "roster": [public_player(player) for player in team["roster"]],
            "heroes": [public_hero(hero) for hero in team["heroes"].values()],
        }

    # ------------------------------------------------------------------ группы
    def _group_table(self, run: Dict[str, Any], group_key: str) -> List[Dict[str, Any]]:
        """Положение команд группы: серии, карты и сила."""
        teams = [team for team in run["tournament"]["teams"] if team["group"] == group_key]
        rows: Dict[str, Dict[str, Any]] = {
            team["id"]: {"team": team, "wins": 0, "losses": 0, "maps": 0, "maps_lost": 0}
            for team in teams
        }
        for match in run["tournament"]["matches"]:
            if match["phase"] != "group" or match["group"] != group_key:
                continue
            if match["result"] is None:
                continue
            winner = match["result"]["winner"]
            loser = match["result"]["loser"]
            score = match["result"]["score"]
            rows[winner]["wins"] += 1
            rows[loser]["losses"] += 1
            rows[winner]["maps"] += score[winner]
            rows[winner]["maps_lost"] += score[loser]
            rows[loser]["maps"] += score[loser]
            rows[loser]["maps_lost"] += score[winner]
        ordered = sorted(rows.values(), key=lambda row: (
            -row["wins"], -(row["maps"] - row["maps_lost"]),
            -float(row["team"]["strength"]), row["team"]["name"]))
        return ordered

    def _standings(self, run: Dict[str, Any]) -> Dict[str, List[str]]:
        return {group_key: [row["team"]["id"] for row in self._group_table(run, group_key)]
                for group_key in ("A", "B")}

    def _team_losses(self, run: Dict[str, Any], team_id: str) -> int:
        """Сколько серий плей-офф команда проиграла: две — и сетка её не ждёт."""
        losses = 0
        for match in run["tournament"]["matches"]:
            if match["phase"] != "playoff" or match["result"] is None:
                continue
            if match["result"]["loser"] == team_id:
                losses += 1
        return losses

    def _still_playing(self, run: Dict[str, Any], team_id: str) -> bool:
        """Есть ли у команды серия впереди: иначе она выбыла."""
        for match in run["tournament"]["matches"]:
            if match["phase"] != "playoff" or match["result"] is not None:
                continue
            sides = self._resolve_sides(run, match)
            if sides is not None and team_id in (sides[0]["id"], sides[1]["id"]):
                return True
        return False

    def _open_bracket(self, run: Dict[str, Any]) -> None:
        """Группа сыграна: собираем верхнюю и нижнюю сетки по местам."""
        tournament = run["tournament"]
        standings = self._standings(run)
        for key, round_key, plan in BRACKET_PLAN:
            sides: List[Dict[str, Any]] = []
            for source in plan:
                if source[0] == "group":
                    sides.append({"team": standings[source[2]][source[1] - 1]})
                elif source[0] == "winner":
                    sides.append({"winner": source[1]})
                else:
                    sides.append({"loser": source[1]})
            info = ROUND_INFO[round_key]
            tournament["matches"].append({
                "key": key,
                "phase": "playoff",
                "group": None,
                "round": round_key,
                "title": info["title"],
                "best_of": int(info["best_of"]),
                "sides": tuple(sides),
                "result": None,
            })
        tournament["bracket_at"] = time.time()
        mine = self._my_team(run)
        place = next(index + 1 for index, row in enumerate(self._group_table(run, mine["group"]))
                     if row["team"]["id"] == mine["id"])
        self._say(run, f"Группа сыграна: вы на {place} месте — "
                       + ("верхняя сетка" if place <= 2 else "нижняя сетка"))

    def _check_phase(self, run: Dict[str, Any]) -> None:
        """Куда идёт прогон: группа, плей-офф, вылет или титул."""
        matches = run["tournament"]["matches"]
        if all(match["result"] is not None for match in matches if match["phase"] == "group"):
            if not run["tournament"].get("bracket_at"):
                self._open_bracket(run)
        mine = self._my_team(run)
        final = self._find_match(run, "gf-0")
        if final is not None and final["result"] is not None \
                and mine["id"] in (final["result"]["winner"], final["result"]["loser"]):
            run["phase"] = "champion" if final["result"]["winner"] == mine["id"] else "dead"
            return
        # Команда играет, пока у неё есть серия впереди: у верхней сетки право на
        # ошибку есть, а у тех, кто начал с нижней, первое же поражение — вылет.
        if run["tournament"].get("bracket_at") and not self._still_playing(run, mine["id"]):
            run["phase"] = "dead"
            return
        run["phase"] = "playoff" if run["tournament"].get("bracket_at") else "group"

    # ------------------------------------------------------------------- матчи
    def play(self, run_id: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Играет вашу ближайшую серию. Вылет после двух поражений."""
        with self._lock:
            run = self._run(run_id)
            self._owner_check(run, user)
            if run["phase"] == "draft":
                raise DotaDraftError(f"Сначала соберите состав: {SQUAD_SIZE} игроков "
                                     f"и герои на все позиции")
            if run["phase"] in ("dead", "champion"):
                raise DotaDraftError("Прогон закончен — начните новый")
            self._advance(run)
            match, sides = self._pending_match(run)
            if match is None or sides is None:
                raise DotaDraftError("Ваших серий впереди нет")
            self._play_series(run, match, sides)
            self._advance(run)
            run["updated_at"] = time.time()
            self._check_phase(run)
            if run["phase"] == "champion":
                self._say(run, "Титул Streamers Battle 13 взят: гранд-финал выигран!")
            elif run["phase"] == "dead":
                self._say(run, "Гранд-финал проигран — прогон закончен"
                       if match["key"] == "gf-0"
                       else "Поражение в сетке: своих серий больше нет — прогон закончен")
            if run["phase"] in ("dead", "champion"):
                self._finish(run)
            return self._payload(run, user, run["updated_at"])

    # ------------------------------------------------------------------ журнал
    def _say(self, run: Dict[str, Any], message: str) -> None:
        run.setdefault("log", []).append({"at": time.time(), "text": message})
        run["log"] = run["log"][-60:]

    def _finish(self, run: Dict[str, Any]) -> None:
        """Результат прогона уходит в журнал: он виден и игроку, и админу."""
        if self._on_finish is None:
            return
        rating = self.rating(run)
        squad = "; ".join(
            f"{player['nickname']} ({POSITION_LABELS[int(run['heroes'][player['id']]['position'])]},"
            f" {run['heroes'][player['id']]['name']})"
            for player in run["roster"] if player["id"] in run["heroes"]) or "—"
        history = run["history"]
        last = history[-1] if history else None
        record = {
            "game": "dota322",
            "username": run["username"],
            "user_id": run["user_id"],
            "difficulty": run["difficulty"],
            "era": "sb13",
            "champion": run["phase"] == "champion",
            "wins": len([item for item in history if item["won"]]),
            "losses": len([item for item in history if not item["won"]]),
            "stage": (last["round"] if last else "group1"),
            "rating": float(rating["total"]) if rating["filled"] else 0.0,
            "squad": squad,
            "packs": "; ".join(item["opponent"]["name"] for item in history) or "—",
            "score": "; ".join(f"{item['title']} {item['score']}" for item in history),
        }
        try:
            self._on_finish(record)
        except Exception as exc:  # noqa: BLE001
            self._say(run, f"Не удалось записать результат в журнал: {exc}")

    # ------------------------------------------------------------------ статус
    def stats(self) -> Dict[str, Any]:
        with self._lock:
            self._cleanup(time.time())
            return {
                "players": len(self._players),
                "heroes": len(self._heroes),
                "pairs": len(self._pair_ratings),
                "known_positions": self.known_positions(),
                "runs": len(self._runs),
                "positions": self.position_counts(),
            }

    def rounds_catalog(self) -> List[Dict[str, Any]]:
        """Все раунды прогона: группа (три тура) и сетка."""
        catalog = [{"key": f"group{index + 1}", "title": f"Группа, тур {index + 1}",
                    "best_of": GROUP_BEST_OF} for index in range(len(GROUP_ROUNDS))]
        catalog.extend(dict(item) for item in self.rounds)
        return catalog

    def _series_public(self, run: Dict[str, Any], match: Dict[str, Any]) -> Dict[str, Any]:
        """Серия сетки в том виде, в каком её видит страница."""
        by_id = {team["id"]: team for team in run["tournament"]["teams"]}
        names: List[str] = []
        for side in match["sides"]:
            if "team" in side:
                team = by_id.get(side["team"])
                names.append(team["name"] if team else "—")
            elif "winner" in side:
                names.append("победитель пары")
            else:
                names.append("проигравший пары")
        sides = self._resolve_sides(run, match)
        if sides is not None:
            names = [sides[0]["name"], sides[1]["name"]]
        result = match["result"]
        score = ""
        won = None
        mine = bool(sides and any(team["mine"] for team in sides))
        if result is not None:
            if sides is not None:
                score = f"{result['score'][sides[0]['id']]}:{result['score'][sides[1]['id']]}"
                won = result["winner"] == sides[0]["id"]
        return {
            "key": match["key"],
            "round": match["round"],
            "title": match["title"],
            "best_of": int(match["best_of"]),
            "teams": names,
            "score": score,
            "played": result is not None,
            "mine": mine,
            "won": won,
        }

    def _payload(self, run: Dict[str, Any], user: Dict[str, Any], now: float) -> Dict[str, Any]:
        rating = self.rating(run)
        pack = run.get("pack") or {"players": [], "heroes": []}
        tournament = run.get("tournament")
        positions = []
        for position, label in POSITIONS:
            owner = None
            for player in run["roster"]:
                hero = run["heroes"].get(player["id"])
                if hero and int(hero["position"]) == position:
                    owner = player
                    break
            hero = run["heroes"].get(owner["id"]) if owner else None
            positions.append({
                "position": position,
                "label": label,
                "hint": POSITION_HINTS.get(position, ""),
                "player": public_player(owner) if owner else None,
                "hero": public_hero(hero) if hero else None,
                "hero_rating": self.pair_rating(owner, hero) if owner and hero else 0,
            })

        next_match = None
        groups: List[Dict[str, Any]] = []
        bracket: List[Dict[str, Any]] = []
        if tournament:
            match, sides = self._pending_match(run)
            if match is not None and sides is not None:
                rival = sides[1] if sides[0]["mine"] else sides[0]
                next_match = {
                    "key": match["key"],
                    "title": match["title"],
                    "best_of": int(match["best_of"]),
                    "round": match["round"],
                    "opponent": self._opponent_public(rival),
                }
            for group_key in ("A", "B"):
                rows = self._group_table(run, group_key)
                groups.append({
                    "key": group_key,
                    "title": f"Группа {group_key}",
                    "rows": [{
                        "place": index + 1,
                        "name": row["team"]["name"],
                        "mine": bool(row["team"]["mine"]),
                        "wins": row["wins"],
                        "losses": row["losses"],
                        "maps": row["maps"],
                        "maps_lost": row["maps_lost"],
                        "strength": round(float(row["team"]["strength"]), 2),
                        "group_budget": int(row["team"]["budget"]),
                    } for index, row in enumerate(rows)],
                })
            bracket = [self._series_public(run, match)
                       for match in tournament["matches"] if match["phase"] == "playoff"]
            if not bracket:
                bracket = [self._series_public(run, match)
                           for match in tournament["matches"]
                           if match["phase"] == "group"
                           and any(team["mine"] for team in
                                   (self._resolve_sides(run, match) or ()))]

        return {
            "id": run["id"],
            "game": run["game"],
            "title": "322-0",
            "phase": run["phase"],
            "difficulty": run["difficulty"],
            "difficulty_label": DIFFICULTY_LABELS[run["difficulty"]],
            "event": run["event"],
            "budget": run["budget"],
            "spent": self._spent(run),
            "left": run["budget"] - self._spent(run),
            "squad_size": SQUAD_SIZE,
            "picks": int(run.get("picks") or 0),
            "roster": [
                {
                    **public_player(player),
                    "hero": public_hero(run["heroes"][player["id"]])
                    if player["id"] in run["heroes"] else None,
                    "hero_rating": self.pair_rating(player, run["heroes"][player["id"]])
                    if player["id"] in run["heroes"] else 0,
                }
                for player in run["roster"]
            ],
            "positions": positions,
            "rating": rating,
            "ready": self._complete(run),
            "pack": {
                "players": [
                    {**public_player(player),
                     "fits": int(player["cost"]) <= run["budget"] - self._spent(run)}
                    for player in pack.get("players", ())
                ],
                "heroes": [public_hero(hero) for hero in pack.get("heroes", ())],
            },
            "tournament": {
                "phase": run["phase"],
                "groups": groups,
                "bracket": bracket,
                "next": next_match,
                "my_losses": self._team_losses(run, self._my_team(run)["id"]),
                "group_best_of": GROUP_BEST_OF,
                "group_size": GROUP_SIZE,
            } if tournament else None,
            "history": run["history"],
            "log": run.get("log", [])[-15:],
            "positions_catalog": [{"position": position, "label": label,
                                   "hint": POSITION_HINTS.get(position, "")}
                                  for position, label in POSITIONS],
            "rounds": self.rounds_catalog(),
            "rules": {
                "pack_players": PACK_PLAYERS,
                "pack_heroes": PACK_HEROES,
                "mid_position": MID_POSITION,
                "mid_cost_limit": MID_COST_LIMIT,
                "own_position_bonus": OWN_POSITION_BONUS,
                "other_position_penalty": OTHER_POSITION_PENALTY,
                "groups": GROUPS,
                "group_size": GROUP_SIZE,
                "group_best_of": GROUP_BEST_OF,
                "opponent_budget_min": OPPONENT_BUDGET_MIN,
                "opponent_budget_max": OPPONENT_BUDGET_MAX,
            },
            "difficulties": [{"key": key, "label": DIFFICULTY_LABELS[key],
                              "budget": DIFFICULTY_BUDGETS[key]} for key in DIFFICULTIES],
        }


__all__ = [
    "DotaDraft",
    "DotaDraftError",
    "DIFFICULTIES",
    "DIFFICULTY_BUDGETS",
    "DIFFICULTY_LABELS",
    "MAX_RUNS",
    "RUN_TTL_SECONDS",
    "public_hero",
    "public_player",
]
