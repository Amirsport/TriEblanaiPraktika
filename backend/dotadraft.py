# -*- coding: utf-8 -*-
"""«322-0» — драфт по Dota 2 на бюджет: Streamers Battle 13.

Правила игры:
    * пул — игроки Streamers Battle 13, у каждого в таблице своя стоимость
      (от 10 до 95 очков);
    * состав — пять игроков, и сумма их стоимости не должна выйти за бюджет
      (в хардкоре это 300 очков, как договаривались);
    * каждому игроку выбирается герой, а позиция героя (1–5) становится
      позицией игрока: пять героев обязаны закрыть все пять позиций;
    * затем прогон по сетке: группа, четвертьфинал, полуфинал, финал
      (Bo1/Bo3/Bo3/Bo5), между стадиями — усиление на выбор. Поражение
      заканчивает прогон.

Соперники собираются из того же пула: на каждой стадии игра выдаёт случайный
состав с бюджетом по силе стадии — то есть у соперника тоже свои игроки
и свои герои, и его сила считается той же формулой, что и ваша.

Стоимости игроков — из таблицы владельца сайта; оценки героев — игровые
(см. backend/dotadraft_data.py). Ники участников, Dota 2 и её герои —
исторические названия и товарные знаки их владельцев; игра некоммерческая.
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
        BOOSTS,
        DIFFICULTIES,
        DIFFICULTY_BUDGETS,
        DIFFICULTY_LABELS,
        DIFFICULTY_OPPONENT_SHIFT,
        HERO_WEIGHT,
        PLAYER_WEIGHT,
        POSITIONS,
        POSITION_HINTS,
        POSITION_LABELS,
        SQUAD_SIZE,
        STAGES,
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
        BOOSTS,
        DIFFICULTIES,
        DIFFICULTY_BUDGETS,
        DIFFICULTY_LABELS,
        DIFFICULTY_OPPONENT_SHIFT,
        HERO_WEIGHT,
        PLAYER_WEIGHT,
        POSITIONS,
        POSITION_HINTS,
        POSITION_LABELS,
        SQUAD_SIZE,
        STAGES,
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

# Сложность — это только бюджет, рероллов в этом режиме нет.
DIFFICULTY_REROLLS: Dict[str, int] = {key: 0 for key in DIFFICULTIES}


class DotaDraftError(ValueError):
    """Ошибка правил игры: превращается в ответ 400 с понятным текстом."""


def public_player(player: Dict[str, Any]) -> Dict[str, Any]:
    """Игрок в том виде, в каком его видит страница."""
    return {
        "id": str(player["id"]),
        "nickname": str(player["nickname"]),
        "cost": int(player["cost"]),
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
    """Прогоны «322-0»: сборка состава в бюджет и выбор героев."""

    def __init__(self, players: Optional[Sequence[Dict[str, Any]]] = None,
                 heroes: Optional[Sequence[Dict[str, Any]]] = None,
                 rng: Optional[random.Random] = None,
                 players_provider: Optional[Callable[[], List[Dict[str, Any]]]] = None,
                 heroes_provider: Optional[Callable[[], List[Dict[str, Any]]]] = None,
                 on_finish: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        self._lock = threading.Lock()
        self._runs: Dict[str, Dict[str, Any]] = {}
        self._rng = rng or random.Random()
        self._players_provider = players_provider
        self._heroes_provider = heroes_provider
        self._on_finish = on_finish
        self._players: List[Dict[str, Any]] = []
        self._heroes: List[Dict[str, Any]] = []
        # Стадии держим на движке: их показывают и страница, и API.
        self.stages: List[Dict[str, Any]] = [dict(stage) for stage in STAGES]
        self.reload_pool(players, heroes)

    # ------------------------------------------------------------------ данные
    def reload_pool(self, players: Optional[Sequence[Dict[str, Any]]] = None,
                    heroes: Optional[Sequence[Dict[str, Any]]] = None) -> int:
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
        if players is None:
            players = player_rows()
        if heroes is None:
            heroes = hero_rows()
        self._players = [self._normalize_player(row) for row in players if row.get("nickname")]
        self._heroes = [self._normalize_hero(row) for row in heroes if row.get("name")]
        return len(self._players)

    @staticmethod
    def _normalize_player(row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": str(row.get("id") or ""),
            "nickname": str(row.get("nickname") or ""),
            "cost": int(row.get("cost") or 0),
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

    def position_counts(self) -> Dict[int, int]:
        counts = {position: 0 for position, _ in POSITIONS}
        for hero in self._heroes:
            counts[hero["position"]] = counts.get(hero["position"], 0) + 1
        return counts

    def ready(self) -> bool:
        """Играть можно, когда на каждой позиции есть хотя бы один герой."""
        if len(self._players) < SQUAD_SIZE * 6:
            return False
        return all(count >= 1 for count in self.position_counts().values())

    def problems(self) -> List[str]:
        """Что не так с пулом: пустые поля, повторы, мало героев на позицию."""
        return validate_players(self._players) + validate_heroes(self._heroes)

    def pool(self) -> Dict[str, Any]:
        """Весь пул для страницы: игроки и герои."""
        return {
            "players": [public_player(player) for player in self._players],
            "heroes": [public_hero(hero) for hero in self._heroes],
        }

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
                "stage": 0,
                "history": [],
                "wins": 0,
                "losses": 0,
                "boosts": [],
                "reward": [],
                "seed": self._rng.getrandbits(32),
                "log": [],
            }
            self._runs[run["id"]] = run
            self._say(run, f"Старт прогона: {DIFFICULTY_LABELS[difficulty]}, "
                           f"бюджет {run['budget']} очков на {SQUAD_SIZE} игроков")
            return self._payload(run, user, now)

    # ------------------------------------------------------------------- состав
    def take(self, run_id: str, user: Dict[str, Any], player_id: str) -> Dict[str, Any]:
        """Покупает игрока в состав, если он проходит по бюджету."""
        with self._lock:
            run = self._run(run_id)
            self._owner_check(run, user)
            if run["phase"] != "draft":
                raise DotaDraftError("Состав уже собран: сначала закончите прогон")
            player = self._player(player_id)
            if any(item["id"] == player["id"] for item in run["roster"]):
                raise DotaDraftError(f"{player['nickname']} уже в составе")
            if len(run["roster"]) >= SQUAD_SIZE:
                raise DotaDraftError(f"В составе уже {SQUAD_SIZE} игроков")
            if self._spent(run) + player["cost"] > run["budget"]:
                left = run["budget"] - self._spent(run)
                raise DotaDraftError(
                    f"{player['nickname']} стоит {player['cost']}, а в бюджете осталось {left}")
            run["roster"].append(dict(player))
            self._say(run, f"Куплен {player['nickname']} за {player['cost']} "
                           f"(осталось {run['budget'] - self._spent(run)})")
            run["updated_at"] = time.time()
            self._refresh_phase(run)
            return self._payload(run, user, run["updated_at"])

    def drop(self, run_id: str, user: Dict[str, Any], player_id: str) -> Dict[str, Any]:
        """Убирает игрока из состава вместе с его героем."""
        with self._lock:
            run = self._run(run_id)
            self._owner_check(run, user)
            if run["phase"] != "draft":
                raise DotaDraftError("Состав уже собран: сначала закончите прогон")
            wanted = str(player_id or "").strip().lower()
            found = next((item for item in run["roster"]
                          if item["id"].lower() == wanted
                          or item["nickname"].lower() == wanted), None)
            if not found:
                raise DotaDraftError("Такого игрока нет в составе")
            run["roster"] = [item for item in run["roster"] if item["id"] != found["id"]]
            run["heroes"].pop(found["id"], None)
            self._say(run, f"{found['nickname']} убран из состава")
            run["updated_at"] = time.time()
            self._refresh_phase(run)
            return self._payload(run, user, run["updated_at"])

    def hero(self, run_id: str, user: Dict[str, Any], player_id: str,
             hero_id: Optional[str]) -> Dict[str, Any]:
        """Выдаёт героя игроку; пустой герой — снимает выбор."""
        with self._lock:
            run = self._run(run_id)
            self._owner_check(run, user)
            if run["phase"] != "draft":
                raise DotaDraftError("Состав уже собран: сначала закончите прогон")
            wanted = str(player_id or "").strip().lower()
            player = next((item for item in run["roster"]
                           if item["id"].lower() == wanted
                           or item["nickname"].lower() == wanted), None)
            if not player:
                raise DotaDraftError("Сначала купите этого игрока в состав")
            if hero_id in (None, "", "-"):
                if run["heroes"].pop(player["id"], None):
                    self._say(run, f"У {player['nickname']} освободилась позиция")
                run["updated_at"] = time.time()
                self._refresh_phase(run)
                return self._payload(run, user, run["updated_at"])
            hero = self._hero(hero_id)
            for other_id, taken in run["heroes"].items():
                if taken["id"] == hero["id"] and other_id != player["id"]:
                    other = next((item for item in run["roster"] if item["id"] == other_id), None)
                    name = other["nickname"] if other else "другой игрок"
                    raise DotaDraftError(
                        f"Герой {hero['name']} уже занят: за него играет {name}")
                if taken["position"] == hero["position"] and other_id != player["id"]:
                    other = next((item for item in run["roster"] if item["id"] == other_id), None)
                    name = other["nickname"] if other else "другой игрок"
                    raise DotaDraftError(
                        f"Позиция {hero['position']} ({POSITION_LABELS[hero['position']]}) "
                        f"уже занята: там {name}")
            run["heroes"][player["id"]] = dict(hero)
            self._say(run, f"{player['nickname']} играет на {hero['name']} "
                           f"({POSITION_LABELS[hero['position']]})")
            run["updated_at"] = time.time()
            self._refresh_phase(run)
            return self._payload(run, user, run["updated_at"])

    def auto_heroes(self, run_id: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Доставляет героев тем, кто остался без них: сильнейшие на свободные позиции.

        Ручной выбор не затирается: занятые позиции и уже выданные герои
        остаются у своих игроков, а свободные закрываются лучшими в пуле.
        """
        with self._lock:
            run = self._run(run_id)
            self._owner_check(run, user)
            if run["phase"] != "draft":
                raise DotaDraftError("Состав уже собран: сначала закончите прогон")
            if len(run["roster"]) != SQUAD_SIZE:
                raise DotaDraftError(f"Сначала соберите состав из {SQUAD_SIZE} игроков")
            kept = {player_id: dict(hero) for player_id, hero in run["heroes"].items()}
            taken_positions = {int(hero["position"]) for hero in kept.values()}
            # По одному лучшему герою на каждую свободную позицию: иначе позиции повторятся.
            best_heroes: List[Dict[str, Any]] = []
            for position, _ in POSITIONS:
                if position in taken_positions:
                    continue
                candidates = [hero for hero in self._heroes if hero["position"] == position]
                if not candidates:
                    raise DotaDraftError(f"Для позиции {position} "
                                         f"({POSITION_LABELS[position]}) в пуле нет героев")
                best_heroes.append(dict(max(candidates,
                                            key=lambda hero: (hero["rating"], hero["name"]))))
            # Дорогому игроку — герой посильнее.
            best_heroes.sort(key=lambda hero: (-hero["rating"], hero["name"]))
            waiting = sorted((player for player in run["roster"] if player["id"] not in kept),
                             key=lambda item: (-item["cost"], item["id"]))
            run["heroes"] = kept
            for player, hero in zip(waiting, best_heroes):
                run["heroes"][player["id"]] = hero
            if waiting:
                self._say(run, f"Герои доставлены автоматически: {len(waiting)} "
                               f"из {SQUAD_SIZE} игроков")
            else:
                self._say(run, "Герои уже расставлены: свободных игроков нет")
            run["updated_at"] = time.time()
            self._refresh_phase(run)
            return self._payload(run, user, run["updated_at"])

    def _spent(self, run: Dict[str, Any]) -> int:
        return sum(int(item["cost"]) for item in run["roster"])

    def _refresh_phase(self, run: Dict[str, Any]) -> None:
        run["phase"] = "ready" if self._complete(run) else "draft"

    def _complete(self, run: Dict[str, Any]) -> bool:
        """Состав собран: пять игроков и пять героев на все пять позиций."""
        if len(run["roster"]) != SQUAD_SIZE:
            return False
        if len(run["heroes"]) != SQUAD_SIZE:
            return False
        positions = {hero["position"] for hero in run["heroes"].values()}
        return len(positions) == SQUAD_SIZE

    # ------------------------------------------------------------------ оценки
    def rating(self, run: Dict[str, Any]) -> Dict[str, Any]:
        """Разложение силы состава: игроки и герои, связки, усиления."""
        pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        for player in run["roster"]:
            hero = run["heroes"].get(player["id"])
            if hero:
                pairs.append((player, hero))
        base = 0.0
        for player, hero in pairs:
            base += PLAYER_WEIGHT * float(player["cost"]) + HERO_WEIGHT * float(hero["rating"])
        base = base / len(pairs) if pairs else 0.0

        pair_bonus = 0.0
        for player, hero in pairs:
            if int(player["cost"]) >= STAR_COST and int(hero["rating"]) >= STRONG_HERO:
                pair_bonus += STAR_PAIR
            elif int(player["cost"]) >= STAR_COST and int(hero["rating"]) <= WEAK_HERO:
                pair_bonus += STAR_CARRY_WEAK_HERO

        position_boosts: Dict[int, float] = {}
        flat = 0.0
        hero_boost = 0.0
        for boost in run.get("boosts", ()):
            if boost.get("position"):
                position = int(boost["position"])
                position_boosts[position] = position_boosts.get(position, 0.0) + float(boost["value"])
            elif boost.get("heroes"):
                hero_boost += float(boost["value"] or 0)
            else:
                flat += float(boost.get("value") or 0)

        pair_boosts = 0.0
        for player, hero in pairs:
            position = int(hero["position"])
            pair_boosts += position_boosts.get(position, 0.0)
        # Усиление «свежая мета» поднимает всех героев, а они весят HERO_WEIGHT.
        flat += HERO_WEIGHT * hero_boost

        total = base + pair_bonus + pair_boosts + flat
        return {
            "base": round(base, 2),
            "pairs": round(pair_bonus, 2),
            "position_boosts": round(pair_boosts, 2),
            "boosts": round(flat, 2),
            "total": round(total, 2),
            "filled": len(pairs),
        }

    def _strength(self, run: Dict[str, Any]) -> float:
        return self.rating(run)["total"]

    # ------------------------------------------------------------------- матчи
    def play(self, run_id: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Играет текущую стадию. Поражение завершает прогон."""
        with self._lock:
            run = self._run(run_id)
            self._owner_check(run, user)
            if not self._complete(run):
                raise DotaDraftError(f"Сначала соберите состав: {SQUAD_SIZE} игроков "
                                     f"и герои на все позиции")
            if run.get("reward"):
                raise DotaDraftError("Сначала выберите усиление")
            if run["phase"] in ("dead", "champion"):
                raise DotaDraftError("Прогон закончен — начните новый")
            if run["phase"] == "ready":
                run["phase"] = "running"
                self._say(run, "Турнир начался: четыре стадии до титула")
            run["stage"] = min(run["stage"], len(STAGES) - 1)
            stage = STAGES[run["stage"]]
            opponent = self._draw_opponent(run, stage)
            match = self._simulate(run, opponent, stage)
            match["stage"] = stage["key"]
            match["stage_title"] = stage["title"]
            match["stage_index"] = run["stage"]
            run["history"].append(match)
            if match["won"]:
                run["wins"] += 1
                self._say(run, f"{stage['title']}: победа над {opponent['label']} "
                               f"{match['score']}")
            else:
                run["losses"] += 1
                run["phase"] = "dead"
                self._say(run, f"{stage['title']}: поражение от {opponent['label']} "
                               f"{match['score']} — прогон закончен")
            if match["won"] and run["stage"] == len(STAGES) - 1:
                run["phase"] = "champion"
                self._say(run, "Титул Streamers Battle 13 взят без поражений!")
            elif match["won"]:
                run["reward"] = self._offer_boosts(run)
                self._say(run, "Усиление на выбор: три карты")
            run["updated_at"] = time.time()
            if run["phase"] in ("dead", "champion"):
                self._finish(run)
            return self._payload(run, user, run["updated_at"])

    def boost(self, run_id: str, user: Dict[str, Any], index: int) -> Dict[str, Any]:
        with self._lock:
            run = self._run(run_id)
            self._owner_check(run, user)
            if not run.get("reward"):
                raise DotaDraftError("Усиление сейчас не предлагается")
            try:
                chosen = run["reward"][int(index)]
            except (IndexError, TypeError, ValueError):
                raise DotaDraftError("Такой карты усиления нет") from None
            run["boosts"].append(chosen)
            run["reward"] = []
            run["stage"] += 1
            self._say(run, f"Усиление: {chosen['title']}. "
                           f"Дальше — {STAGES[min(run['stage'], len(STAGES) - 1)]['title']}")
            run["updated_at"] = time.time()
            return self._payload(run, user, run["updated_at"])

    def _offer_boosts(self, run: Dict[str, Any]) -> List[Dict[str, Any]]:
        taken = {boost["id"] for boost in run.get("boosts", ())}
        available = [boost for boost in BOOSTS if boost["id"] not in taken]
        if not available:
            available = list(BOOSTS)
        return [dict(boost) for boost in self._rng.sample(available, min(3, len(available)))]

    def _draw_opponent(self, run: Dict[str, Any], stage: Dict[str, Any]) -> Dict[str, Any]:
        """Соперник: случайный состав из того же пула под бюджет стадии."""
        mine = {item["id"] for item in run["roster"]}
        pool = [player for player in self._players if player["id"] not in mine]
        target = int(stage.get("opponent_cost") or 300) + int(
            DIFFICULTY_OPPONENT_SHIFT.get(run["difficulty"], 0))
        # Перебор случайных пятёрок: берём ту, что ближе всего к бюджету стадии.
        roster: List[Dict[str, Any]] = []
        spent = 0
        best_gap = None
        for _ in range(400):
            if len(pool) < SQUAD_SIZE:
                break
            candidate = self._rng.sample(pool, SQUAD_SIZE)
            total = sum(player["cost"] for player in candidate)
            gap = abs(total - target)
            if best_gap is None or gap < best_gap:
                best_gap = gap
                roster = candidate
                spent = total
                if gap == 0:
                    break
        roster = [dict(player) for player in roster]
        # Герои — из верхней половины позиции: соперник не должен проседать случайно.
        heroes: Dict[str, Dict[str, Any]] = {}
        positions = [position for position, _ in POSITIONS]
        self._rng.shuffle(positions)
        for player, position in zip(roster, positions):
            candidates = sorted((hero for hero in self._heroes
                                 if hero["position"] == position),
                                key=lambda hero: (-hero["rating"], hero["name"]))
            if candidates:
                top = candidates[:max(1, len(candidates) // 2)]
                heroes[player["id"]] = dict(self._rng.choice(top))
        label = "микс " + ", ".join(player["nickname"] for player in roster)
        return {"label": label, "roster": roster, "heroes": heroes, "budget": spent}

    def _simulate(self, run: Dict[str, Any], opponent: Dict[str, Any],
                  stage: Dict[str, Any]) -> Dict[str, Any]:
        """Серия игр до победы: Bo1 в группе, Bo3 в плей-офф, Bo5 в финале."""
        rng = random.Random(run["seed"] + run["stage"] * 7919
                            + sum(ord(char) for char in opponent["label"]))
        need = stage["best_of"] // 2 + 1
        ours = self._strength(run)
        theirs = self._strength(opponent)
        chance = 1.0 / (1.0 + 10 ** ((theirs - ours) / STRENGTH_SCALE))
        team_score = 0
        opp_score = 0
        games: List[Dict[str, Any]] = []
        guard = 0
        while team_score < need and opp_score < need and guard < stage["best_of"]:
            guard += 1
            won = rng.random() < chance
            team_score += 1 if won else 0
            opp_score += 0 if won else 1
            games.append({"game": len(games) + 1, "won": won})
        return {
            "opponent": {
                "label": opponent["label"],
                "budget": int(opponent.get("budget") or 0),
                "roster": [public_player(player) for player in opponent["roster"]],
                "heroes": [public_hero(hero) for hero in opponent["heroes"].values()],
                "strength": round(theirs, 2),
            },
            "best_of": stage["best_of"],
            "team_score": team_score,
            "opp_score": opp_score,
            "score": f"{team_score}:{opp_score}",
            "our_strength": round(ours, 2),
            "games": games,
            "won": team_score > opp_score,
        }

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
        record = {
            "game": "dota322",
            "username": run["username"],
            "user_id": run["user_id"],
            "difficulty": run["difficulty"],
            "era": "sb13",
            "champion": run["phase"] == "champion",
            "wins": run["wins"],
            "losses": run["losses"],
            "stage": STAGES[run["stage"]]["key"],
            "rating": float(rating["total"]) if rating["filled"] else 0.0,
            "squad": squad,
            "packs": "; ".join(item["opponent"]["label"].split(" ", 1)[-1]
                               for item in run["history"]) or "—",
            "score": "; ".join(f"{item['stage_title']} {item['score']}"
                               for item in run["history"]),
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
                "runs": len(self._runs),
                "positions": self.position_counts(),
            }

    def _payload(self, run: Dict[str, Any], user: Dict[str, Any], now: float) -> Dict[str, Any]:
        rating = self.rating(run)
        stage = STAGES[min(run["stage"], len(STAGES) - 1)]
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
                "boost": round(sum(float(boost["value"]) for boost in run.get("boosts", ())
                                   if boost.get("position") == position), 2),
            })
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
            "roster": [
                {
                    **public_player(player),
                    "hero": public_hero(run["heroes"][player["id"]])
                    if player["id"] in run["heroes"] else None,
                }
                for player in run["roster"]
            ],
            "positions": positions,
            "rating": rating,
            "ready": self._complete(run),
            "stage": {
                "index": min(run["stage"], len(STAGES) - 1),
                "key": stage["key"],
                "title": stage["title"],
                "best_of": stage["best_of"],
                "total": len(STAGES),
                "opponent_cost": stage.get("opponent_cost"),
            },
            "history": run["history"],
            "reward": run.get("reward", []),
            "boosts": [{"id": boost["id"], "title": boost["title"]} for boost in run["boosts"]],
            "log": run.get("log", [])[-15:],
            "positions_catalog": [{"position": position, "label": label,
                                   "hint": POSITION_HINTS.get(position, "")}
                                  for position, label in POSITIONS],
            "stages": [{"key": item["key"], "title": item["title"], "best_of": item["best_of"]}
                       for item in STAGES],
            "difficulties": [{"key": key, "label": DIFFICULTY_LABELS[key],
                              "budget": DIFFICULTY_BUDGETS[key]} for key in DIFFICULTIES],
        }


__all__ = [
    "DotaDraft",
    "DotaDraftError",
    "DIFFICULTIES",
    "DIFFICULTY_BUDGETS",
    "DIFFICULTY_LABELS",
    "DIFFICULTY_REROLLS",
    "MAX_RUNS",
    "RUN_TTL_SECONDS",
    "STAGES",
    "public_hero",
    "public_player",
]
