# -*- coding: utf-8 -*-
"""«87-0» — драфт-рогалик по Counter-Strike.

Замысел тот же, что у 322-0.app для Dota 2: собираешь «состав Франкенштейна» из
реальных команд прошлых турниров и пытаешься пройти фейковый мейджор без
поражений. Отличие в деталях, привычных для CS:

    * пак — это реальный состав на конкретном турнире: пять игроков с ролями
      (AWP, IGL, энтри, сапорт, луркер) и карты его маппула;
    * состав оценивается по базовому рейтингу игроков, попаданию в свою роль,
      сыгранности (кто играл вместе) и своему маппулу;
    * прогон — четыре стадии (групповой Bo1, четвертьфинал и полуфинал Bo3,
      финал Bo5): матчи симулируются по картам и раундам, а между стадиями
      даётся усиление на выбор;
    * поражение заканчивает прогон: это рогалик, результат уходит в журнал.

Данные о составах и ролях — реальные исторические, а оценки AIM/CLUTCH/IMP —
игровые: они расставлены для баланса, это не официальная статистика
(см. backend/csdraft_data.py).
"""
from __future__ import annotations

import itertools
import random
import sys
import threading
import time
import zlib
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

try:  # запуск как модуль: python -m backend.server
    from .csdraft_data import (
        BOOSTS,
        DUOS,
        ERA_LABELS,
        ROLE_LABELS,
        ROLES,
        normalize_pack,
        overall,
        seed_rows,
    )
except ImportError:  # запуск как файл: python backend/server.py
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from csdraft_data import (  # type: ignore
        BOOSTS,
        DUOS,
        ERA_LABELS,
        ROLE_LABELS,
        ROLES,
        normalize_pack,
        overall,
        seed_rows,
    )

# Заброшенный прогон: держим сутки, потому что матчи идут не подряд.
RUN_TTL_SECONDS = 24 * 60 * 60
MAX_RUNS = 300

SQUAD_SIZE = 5
POOL_SIZE = 3

# Сложность — это только количество рероллов, как в 322-0 (Hard/Easy/Smurfing).
DIFFICULTIES: Tuple[str, ...] = ("hard", "easy", "smurf")
DIFFICULTY_REROLLS = {"hard": 0, "easy": 1, "smurf": 2}
DIFFICULTY_LABELS = {"hard": "Хардкор", "easy": "Обычная", "smurf": "Смёрф"}

# Эпохи: легендарные составы против современной сцены.
ERAS = ("legacy", "modern")

# Кто как расставляет игроков по слотам.
ASSIGN_MODES = ("auto", "manual")

# Стадии прогона: сколько карт играется (до победы, как в реальном CS).
STAGES: Tuple[Dict[str, Any], ...] = (
    {"key": "opening", "title": "Групповой этап", "best_of": 1},
    {"key": "quarters", "title": "Четвертьфинал", "best_of": 3},
    {"key": "semis", "title": "Полуфинал", "best_of": 3},
    {"key": "final", "title": "Финал мейджора", "best_of": 5},
)

# Оценка состава: база — средний рейтинг, дальше надбавки и штрафы.
FIT_NATURAL = 4.0          # игрок в своей роли
FIT_ADJACENT = 0.0         # родственная роль (энтри и луркер, AWP и луркер)
FIT_WRONG = -5.0           # совсем не его роль
CHEM_SAME_PACK = 2.5       # играли вместе в этом составе на этом турнире
CHEM_SAME_REGION = 1.0     # из одного региона
CHEM_DUO = 1.5             # известная связка (device + dupreeh и подобные)
MAP_EDGE = 3.0             # на своей карте играется легче

# Розыгрыш карты: до 16 побед, при 15:15 — овертаймы.
ROUNDS_TO_WIN = 16
MAX_ROUNDS = 30
OVERTIME_ROUNDS = 6
OVERTIME_TO_WIN = 4
MAX_OVERTIMES = 3

# Чем больше «шкала», тем меньше одна и та же разница в рейтинге значит.
STRENGTH_SCALE = 12.0
PACK_OFFERS = 3            # сколько бустов предлагать после стадии


class CsdraftError(ValueError):
    """Ошибка правил игры: превращается в ответ 400 с понятным текстом."""


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def public_pack(pack: Dict[str, Any]) -> Dict[str, Any]:
    """Пак в том виде, в каком его видит страница."""
    return {
        "id": pack["id"],
        "team": pack["team"],
        "event": pack["event"],
        "year": int(pack["year"]),
        "place": pack.get("place", ""),
        "major": bool(pack.get("major")),
        "region": pack.get("region", ""),
        "era": pack.get("era", "legacy"),
        "maps": list(pack.get("maps", ())),
        "players": [
            {
                "name": player["name"],
                "role": player["role"],
                "role_label": ROLE_LABELS.get(player["role"], player["role"]),
                "aim": float(player["aim"]),
                "clutch": float(player["clutch"]),
                "impact": float(player["impact"]),
                "ovr": float(player["ovr"]),
            }
            for player in pack.get("players", ())
        ],
    }


class Csdraft:
    """Прогоны «87-0»: драфт состава и симуляция мейджора."""

    def __init__(self, packs: Optional[Sequence[Dict[str, Any]]] = None,
                 rng: Optional[random.Random] = None,
                 provider: Optional[Callable[[], List[Dict[str, Any]]]] = None,
                 on_finish: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        self._lock = threading.Lock()
        self._runs: Dict[str, Dict[str, Any]] = {}
        self._rng = rng or random.Random()
        self._provider = provider
        self._on_finish = on_finish
        self._packs: List[Dict[str, Any]] = []
        self.reload_packs(packs)

    # ------------------------------------------------------------------ данные
    def reload_packs(self, packs: Optional[Sequence[Dict[str, Any]]] = None) -> int:
        """Перечитывает паки: обычно из базы, при первом запуске — из набора в коде."""
        if packs is None and self._provider is not None:
            try:
                packs = self._provider()
            except Exception:  # noqa: BLE001
                packs = None
        if packs is None:
            packs = seed_rows()
        self._packs = [normalize_pack(pack) for pack in packs if pack.get("players")]
        return len(self._packs)

    def refresh(self) -> int:
        """Перечитать паки перед новым прогоном: правки в базе видны сразу."""
        return self.reload_packs()

    def pack_count(self) -> int:
        return len(self._packs)

    def era_counts(self) -> Dict[str, int]:
        counts = {era: 0 for era in ERAS}
        for pack in self._packs:
            counts[str(pack.get("era", "legacy"))] = counts.get(str(pack.get("era", "legacy")), 0) + 1
        return counts

    def ready(self, era: Optional[str] = None) -> bool:
        """Играть можно, если паков хватает: минимум четыре на эпоху прогона."""
        if era and era not in ERAS:
            return False
        if era:
            return len(self._eligible(era)) >= 4
        return len(self._packs) >= 4

    def _eligible(self, era: str) -> List[Dict[str, Any]]:
        chosen = [pack for pack in self._packs if str(pack.get("era", "legacy")) == era]
        return chosen or list(self._packs)

    def _pack(self, pack_id: str) -> Dict[str, Any]:
        for pack in self._packs:
            if pack["id"] == pack_id:
                return pack
        raise CsdraftError("Такого состава нет в наборе")

    # ---------------------------------------------------------------- служебное
    def _cleanup(self, now: float) -> None:
        for run_id, run in list(self._runs.items()):
            if now - run.get("updated_at", now) > RUN_TTL_SECONDS:
                self._runs.pop(run_id, None)

    def _new_run_id(self) -> str:
        while True:
            run_id = "%08x" % self._rng.getrandbits(32)
            if run_id not in self._runs:
                return run_id

    def _run(self, run_id: str) -> Dict[str, Any]:
        run = self._runs.get(str(run_id or "").strip())
        if not run:
            raise CsdraftError("Прогон не найден: возможно, он устарел")
        return run

    def state(self, run_id: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Текущее состояние прогона: этим страница обновляет экран."""
        run = self._run(run_id)
        self._owner_check(run, user)
        return self._payload(run, user, time.time())

    @staticmethod
    def _owner_check(run: Dict[str, Any], user: Dict[str, Any]) -> None:
        if user.get("role") == "admin":
            return
        if int(run["user_id"]) != int(user.get("id") or 0):
            raise CsdraftError("Это чужой прогон")

    def _used_packs(self, run: Dict[str, Any]) -> set:
        used = {run["pack"]["id"]} if run.get("pack") else set()
        used.update(pack for pack in run.get("seen_packs", ()))
        return used

    def _draw_pack(self, run: Dict[str, Any]) -> Dict[str, Any]:
        """Случайный пак под эпоху прогона, которого в этом прогоне ещё не было."""
        pool = self._eligible(run["era"])
        if not pool:
            raise CsdraftError("Набор составов пуст")
        used = self._used_packs(run)
        free = [pack for pack in pool if pack["id"] not in used]
        if not free:
            free = list(pool)
        return self._rng.choice(free)

    # ------------------------------------------------------------------ оценки
    def _assigned_role(self, run: Dict[str, Any], player: Dict[str, Any],
                       role: Optional[str] = None) -> str:
        """Куда поставить игрока: в свою роль, иначе в лучшую свободную."""
        if role:
            return role
        squad = run["squad"]
        if not squad.get(player["role"]):
            return player["role"]
        free = [slot for slot in ROLES if not squad.get(slot)]
        if not free:
            raise CsdraftError("В составе уже заняты все пять ролей")
        return min(free, key=lambda slot: (-self._fit(player["role"], slot), slot))

    @staticmethod
    def _fit(natural: str, slot: str) -> float:
        """Насколько игрок подходит слоту: своя роль, родственная или чужая."""
        if natural == slot:
            return FIT_NATURAL
        neighbours = {
            "awp": {"lurker"},
            "lurker": {"awp", "entry"},
            "entry": {"lurker", "support"},
            "support": {"entry", "igl"},
            "igl": {"support"},
        }
        return FIT_ADJACENT if slot in neighbours.get(natural, set()) else FIT_WRONG

    def _duo_bonus(self, names: Sequence[str]) -> float:
        bonus = 0.0
        lowered = {name.lower() for name in names}
        for first, second in DUOS:
            if first.lower() in lowered and second.lower() in lowered:
                bonus += CHEM_DUO
        return bonus

    def rating(self, run: Dict[str, Any]) -> Dict[str, Any]:
        """Разложение силы состава: база, роли, сыгранность, бусты."""
        squad = run["squad"]
        filled = [player for player in squad.values() if player]
        base = sum(float(player["ovr"]) for player in filled) / len(filled) if filled else 0.0

        fit = 0.0
        for slot, player in squad.items():
            if player:
                fit += self._fit(player["role"], slot)

        packs = [player["pack"] for player in filled]
        chem = 0.0
        for index, first in enumerate(filled):
            for second in filled[index + 1:]:
                if first["pack"] == second["pack"]:
                    chem += CHEM_SAME_PACK
                elif first["region"] and first["region"] == second["region"]:
                    chem += CHEM_SAME_REGION
        chem += self._duo_bonus([player["name"] for player in filled])

        boost_roles: Dict[str, float] = {}
        flat = 0.0
        for boost in run.get("boosts", ()):
            if boost.get("role"):
                boost_roles[boost["role"]] = boost_roles.get(boost["role"], 0.0) + float(boost["value"])
            else:
                flat += float(boost.get("value") or 0)
        for slot, player in squad.items():
            if player:
                flat += boost_roles.get(slot, 0.0) + boost_roles.get(player["name"].lower(), 0.0)

        total = base + fit + chem + flat
        return {
            "base": round(base, 2),
            "fit": round(fit, 2),
            "chemistry": round(chem, 2),
            "boosts": round(flat, 2),
            "total": round(total, 2),
            "filled": len(filled),
            "same_packs": len(packs) - len(set(packs)),
        }

    def _strength(self, run: Dict[str, Any], map_name: Optional[str] = None) -> float:
        value = self.rating(run)["total"]
        if map_name and map_name in run.get("pool", ()):
            value += MAP_EDGE
        return value

    # ------------------------------------------------------------------- старт
    def start(self, user: Dict[str, Any], difficulty: str = "hard",
              era: str = "legacy", assign: str = "auto") -> Dict[str, Any]:
        if difficulty not in DIFFICULTY_REROLLS:
            raise CsdraftError("Неизвестная сложность")
        if era not in ERAS:
            raise CsdraftError("Неизвестная эпоха")
        if assign not in ASSIGN_MODES:
            raise CsdraftError("Неизвестный способ расстановки")
        self.refresh()
        if not self.ready(era):
            raise CsdraftError("Пока нет составов для игры: база пуста")

        now = time.time()
        with self._lock:
            self._cleanup(now)
            if len(self._runs) >= MAX_RUNS:
                oldest = min(self._runs, key=lambda key: self._runs[key]["updated_at"])
                self._runs.pop(oldest, None)
            run: Dict[str, Any] = {
                "id": self._new_run_id(),
                "user_id": int(user.get("id") or 0),
                "username": user.get("username") or "",
                "created_at": now,
                "updated_at": now,
                "difficulty": difficulty,
                "era": era,
                "assign": assign,
                "rerolls": DIFFICULTY_REROLLS[difficulty],
                "squad": {role: None for role in ROLES},
                "pool": [],
                "boosts": [],
                "seen_packs": [],
                "stage": 0,
                "history": [],
                "wins": 0,
                "losses": 0,
                "status": "draft",
                "reward": [],
                "seed": self._rng.getrandbits(32),
                "pack": {},
                "log": [],
            }
            run["pack"] = self._draw_pack(run)
            self._runs[run["id"]] = run
            self._say(run, f"Старт прогона: {DIFFICULTY_LABELS[difficulty]}, "
                           f"{ERA_LABELS.get(era, era)}, рероллов {run['rerolls']}")
            return self._payload(run, user, now)

    # -------------------------------------------------------------------- драфт
    def take(self, run_id: str, user: Dict[str, Any], player_name: str,
             role: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            run = self._run(run_id)
            self._owner_check(run, user)
            if run["status"] != "draft":
                raise CsdraftError("Драфт уже закончен: состав собран")
            pack = run["pack"]
            packet = next((item for item in pack["players"]
                           if item["name"].lower() == str(player_name or "").strip().lower()), None)
            if packet is None:
                raise CsdraftError("Такого игрока нет в предложенном составе")
            if any(player and player["name"].lower() == packet["name"].lower()
                   for player in run["squad"].values()):
                raise CsdraftError(f"{packet['name']} уже в составе")

            slot = self._assigned_role(run, packet, role)
            if slot not in ROLES:
                raise CsdraftError("Неизвестная роль")
            if run["squad"].get(slot):
                raise CsdraftError(f"Роль {ROLE_LABELS[slot]} уже занята")

            run["squad"][slot] = {
                "name": packet["name"],
                "role": packet["role"],
                "ovr": float(packet["ovr"]),
                "pack": pack["id"],
                "region": pack.get("region", ""),
                "era": pack.get("era", "legacy"),
            }
            place = f" на {ROLE_LABELS[slot]}" if packet["role"] != slot else ""
            self._say(run, f"В состав взят {packet['name']}{place} ({pack['team']}, {pack['event']})")
            run["updated_at"] = time.time()
            if all(run["squad"].values()):
                run["status"] = "ready"
                self._say(run, "Состав собран — можно начинать мейджор")
            return self._payload(run, user, run["updated_at"])

    def take_map(self, run_id: str, user: Dict[str, Any], map_name: str) -> Dict[str, Any]:
        with self._lock:
            run = self._run(run_id)
            self._owner_check(run, user)
            if run["status"] not in ("draft", "ready", "running"):
                raise CsdraftError("Прогон уже закончен")
            name = str(map_name or "").strip()
            if name not in run["pack"].get("maps", ()):
                raise CsdraftError("Такой карты нет в маппуле этого состава")
            if name in run["pool"]:
                raise CsdraftError(f"{name} уже в вашем маппуле")
            limit = POOL_SIZE + sum(1 for boost in run["boosts"] if boost.get("extra_map"))
            if len(run["pool"]) >= limit:
                raise CsdraftError("Маппул заполнен: карты можно менять только бустами")
            run["pool"].append(name)
            self._say(run, f"В маппул добавлена карта {name}")
            run["updated_at"] = time.time()
            return self._payload(run, user, run["updated_at"])

    def skip_pack(self, run_id: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Следующий состав: обычный шаг вперёд, реролл не тратится."""
        return self._next_pack(run_id, user, paid=False)

    def reroll(self, run_id: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Реролл: новый состав вместо предложенного, тратит попытку."""
        return self._next_pack(run_id, user, paid=True)

    def _next_pack(self, run_id: str, user: Dict[str, Any], paid: bool) -> Dict[str, Any]:
        with self._lock:
            run = self._run(run_id)
            self._owner_check(run, user)
            if run["status"] not in ("draft", "ready") and not paid:
                raise CsdraftError("Состав уже собран: следующий пак не нужен")
            if paid and run["rerolls"] <= 0:
                raise CsdraftError("Рероллы закончились")
            if run.get("pack"):
                run["seen_packs"].append(run["pack"]["id"])
            run["pack"] = self._draw_pack(run)
            if paid:
                run["rerolls"] -= 1
                self._say(run, f"Реролл: новый состав {run['pack']['team']} "
                               f"({run['pack']['event']}), осталось {run['rerolls']}")
            else:
                self._say(run, f"Следующий состав: {run['pack']['team']} ({run['pack']['event']})")
            run["updated_at"] = time.time()
            return self._payload(run, user, run["updated_at"])

    def set_assign(self, run_id: str, user: Dict[str, Any], mode: str) -> Dict[str, Any]:
        """Способ расстановки: вручную или автоматически по лучшему попаданию."""
        with self._lock:
            run = self._run(run_id)
            self._owner_check(run, user)
            if mode not in ASSIGN_MODES:
                raise CsdraftError("Неизвестный способ расстановки")
            run["assign"] = mode
            run["updated_at"] = time.time()
            self._say(run, "Расстановка: " + ("вручную" if mode == "manual" else "автоматически"))
            return self._payload(run, user, run["updated_at"])

    def auto_assign(self, run_id: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Пересобрать состав по ролям: каждому игроку — лучший свободный слот."""
        with self._lock:
            run = self._run(run_id)
            self._owner_check(run, user)
            if run["status"] not in ("draft", "ready"):
                raise CsdraftError("Состав уже играет")
            players = [player for player in run["squad"].values() if player]
            if not players:
                raise CsdraftError("В составе пока нет игроков")
            best: Optional[Tuple[float, List[Any]]] = None
            # Перебираем все способы разложить игроков по свободным слотам
            # (для пяти игроков это 120 вариантов) и берём лучший по попаданию.
            for slots in itertools.permutations(ROLES, len(players)):
                score = sum(self._fit(player["role"], slot) for player, slot in zip(players, slots))
                if best is None or score > best[0]:
                    best = (score, list(slots))
            assert best is not None
            placed = dict(zip([player["name"] for player in players], best[1]))
            run["squad"] = {role: None for role in ROLES}
            for player in players:
                run["squad"][placed[player["name"]]] = player
            self._say(run, "Роли расставлены автоматически")
            run["updated_at"] = time.time()
            return self._payload(run, user, run["updated_at"])

    # ------------------------------------------------------------------- матчи
    def play(self, run_id: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Играть текущую стадию. Поражение завершает прогон."""
        with self._lock:
            run = self._run(run_id)
            self._owner_check(run, user)
            if not all(run["squad"].values()):
                raise CsdraftError("Сначала соберите состав: нужны все пять ролей")
            if run.get("reward"):
                raise CsdraftError("Сначала выберите усиление")
            if run["status"] in ("dead", "champion"):
                raise CsdraftError("Прогон закончен — начните новый")
            if run["status"] == "ready":
                run["status"] = "running"
                self._say(run, "Мейджор начался: четыре стадии до титула")
            run["stage"] = min(run["stage"], len(STAGES) - 1)
            stage = STAGES[run["stage"]]
            opponent = self._draw_pack({**run, "pack": None})
            match = self._simulate(run, opponent, stage)
            match["stage"] = stage["key"]
            match["stage_title"] = stage["title"]
            match["stage_index"] = run["stage"]
            run["history"].append(match)
            if match["won"]:
                run["wins"] += 1
                self._say(run, f"{stage['title']}: победа над {opponent['team']} "
                               f"{match['score']} ({match['maps']})")
            else:
                run["losses"] += 1
                run["status"] = "dead"
                self._say(run, f"{stage['title']}: поражение от {opponent['team']} "
                               f"{match['score']} ({match['maps']}) — прогон закончен")

            if match["won"] and run["stage"] == len(STAGES) - 1:
                run["status"] = "champion"
                self._say(run, "Титул мейджора взят без поражений — идеальный прогон!")
            elif match["won"]:
                run["reward"] = self._offer_boosts(run)
                self._say(run, "Усиление на выбор: три карты бустов")
            run["updated_at"] = time.time()
            if run["status"] in ("dead", "champion"):
                self._finish(run)
            return self._payload(run, user, run["updated_at"])

    def boost(self, run_id: str, user: Dict[str, Any], index: int) -> Dict[str, Any]:
        with self._lock:
            run = self._run(run_id)
            self._owner_check(run, user)
            if not run.get("reward"):
                raise CsdraftError("Усиление сейчас не предлагается")
            try:
                chosen = run["reward"][int(index)]
            except (IndexError, TypeError, ValueError):
                raise CsdraftError("Такой карты усиления нет") from None
            run["boosts"].append(chosen)
            if chosen.get("reroll"):
                run["rerolls"] += int(chosen["reroll"])
            run["reward"] = []
            run["stage"] += 1
            self._say(run, f"Усиление: {chosen['title']}. "
                           f"Дальше — {STAGES[min(run['stage'], len(STAGES) - 1)]['title']}")
            run["updated_at"] = time.time()
            return self._payload(run, user, run["updated_at"])

    def _offer_boosts(self, run: Dict[str, Any]) -> List[Dict[str, Any]]:
        taken = {boost["id"] for boost in run.get("boosts", ())}
        available = [boost for boost in BOOSTS if boost["id"] not in taken or boost.get("repeatable")]
        if not available:
            available = list(BOOSTS)
        return [dict(boost) for boost in self._rng.sample(available, min(PACK_OFFERS, len(available)))]

    def _simulate(self, run: Dict[str, Any], opponent: Dict[str, Any],
                  stage: Dict[str, Any]) -> Dict[str, Any]:
        """Матч: играем карты до победы, как в реальном формате Bo1/Bo3/Bo5."""
        rng = random.Random(run["seed"] + run["stage"] * 7919 + zlib.crc32(opponent["id"].encode("utf-8")))
        need = stage["best_of"] // 2 + 1

        maps_choice = self._maps_for_match(run, opponent, rng)
        team_score = 0
        opp_score = 0
        log: List[Dict[str, Any]] = []
        for map_name in maps_choice:
            if team_score >= need or opp_score >= need:
                break
            ours = self._strength(run, map_name)
            theirs = _pack_strength(opponent)
            their_maps = set(opponent.get("maps", ()))
            if map_name in their_maps:
                theirs += MAP_EDGE
            us, them, overtime = _simulate_map(ours, theirs, rng)
            won = us > them
            team_score += 1 if won else 0
            opp_score += 0 if won else 1
            log.append({
                "map": map_name,
                "ours": us,
                "theirs": them,
                "won": won,
                "overtime": overtime,
                "ours_map": map_name in run.get("pool", ()),
                "theirs_map": map_name in their_maps,
            })
        return {
            "opponent": {
                "id": opponent["id"],
                "team": opponent["team"],
                "event": opponent["event"],
                "year": int(opponent["year"]),
                "place": opponent.get("place", ""),
                "region": opponent.get("region", ""),
                "maps": list(opponent.get("maps", ())),
                "players": [player["name"] for player in opponent["players"]],
            },
            "best_of": stage["best_of"],
            "team_score": team_score,
            "opp_score": opp_score,
            "score": f"{team_score}:{opp_score}",
            "maps": ", ".join(f"{row['map']} {row['ours']}:{row['theirs']}" for row in log),
            "log": log,
            "won": team_score > opp_score,
        }

    def _maps_for_match(self, run: Dict[str, Any], opponent: Dict[str, Any],
                        rng: random.Random) -> List[str]:
        """Карты матча: сначала свои и соперника, потом остальные из набора."""
        chosen: List[str] = []
        for name in list(run.get("pool", ())) + list(opponent.get("maps", ())):
            if name not in chosen:
                chosen.append(name)
        rest: List[str] = []
        for pack in self._packs:
            for name in pack.get("maps", ()):
                if name not in chosen and name not in rest:
                    rest.append(name)
        rng.shuffle(rest)
        while len(chosen) < 5 and rest:
            chosen.append(rest.pop())
        rng.shuffle(chosen)
        return chosen[:5]

    # ------------------------------------------------------------------ журнал
    def _say(self, run: Dict[str, Any], message: str) -> None:
        run.setdefault("log", []).append({"at": time.time(), "text": message})
        run["log"] = run["log"][-60:]

    def _finish(self, run: Dict[str, Any]) -> None:
        """Результат прогона уходит в журнал: он виден и игроку, и админу."""
        if self._on_finish is None:
            return
        rating = self.rating(run)
        record = {
            "username": run["username"],
            "user_id": run["user_id"],
            "difficulty": run["difficulty"],
            "era": run["era"],
            "champion": run["status"] == "champion",
            "wins": run["wins"],
            "losses": run["losses"],
            "stage": STAGES[run["stage"]]["key"],
            "rating": float(rating["total"]) if rating["filled"] else 0.0,
            "squad": "; ".join(
                f"{player['name']} ({ROLE_LABELS[slot]})"
                for slot, player in run["squad"].items() if player) or "—",
            "packs": "; ".join(dict.fromkeys(
                player["pack"] for player in run["squad"].values() if player)) or "—",
            "score": "; ".join(f"{item['stage_title']} {item['score']}" for item in run["history"]),
        }
        try:
            self._on_finish(record)
        except Exception as exc:  # noqa: BLE001
            self._say(run, f"Не удалось записать результат в журнал: {exc}")

    # ------------------------------------------------------------------ статус
    def stats(self) -> Dict[str, Any]:
        return {
            "packs": len(self._packs),
            "eras": self.era_counts(),
            "runs": len(self._runs),
        }

    def _payload(self, run: Dict[str, Any], user: Dict[str, Any], now: float) -> Dict[str, Any]:
        rating = self.rating(run)
        stage = STAGES[min(run["stage"], len(STAGES) - 1)]
        return {
            "id": run["id"],
            "status": run["status"],
            "difficulty": run["difficulty"],
            "difficulty_label": DIFFICULTY_LABELS[run["difficulty"]],
            "era": run["era"],
            "era_label": ERA_LABELS.get(run["era"], run["era"]),
            "assign": run["assign"],
            "rerolls": run["rerolls"],
            "pack": public_pack(run["pack"]) if run.get("pack") else None,
            "squad": {
                slot: ({
                    "name": player["name"],
                    "role": player["role"],
                    "role_label": ROLE_LABELS.get(player["role"], player["role"]),
                    "slot_label": ROLE_LABELS[slot],
                    "ovr": player["ovr"],
                    "pack": player["pack"],
                    "fit": self._fit(player["role"], slot),
                } if player else None)
                for slot, player in run["squad"].items()
            },
            "pool": list(run["pool"]),
            "pool_limit": POOL_SIZE + sum(1 for boost in run["boosts"] if boost.get("extra_map")),
            "boosts": [{"id": boost["id"], "title": boost["title"]} for boost in run["boosts"]],
            "rating": rating,
            "stage": {
                "index": min(run["stage"], len(STAGES) - 1),
                "key": stage["key"],
                "title": stage["title"],
                "best_of": stage["best_of"],
                "total": len(STAGES),
            },
            "history": run["history"],
            "reward": run.get("reward", []),
            "ready": all(run["squad"].values()),
            "log": run.get("log", [])[-15:],
            "roles": [{"key": role, "label": ROLE_LABELS[role]} for role in ROLES],
        }


def _pack_strength(pack: Dict[str, Any]) -> float:
    """Сила соперника: средний рейтинг игроков его состава.

    Пак может прийти и без посчитанного рейтинга (например, прямо из набора
    данных), поэтому считаем его из трёх оценок.
    """
    players = pack.get("players") or []
    if not players:
        return 60.0
    values = [float(player.get("ovr") or overall(player)) for player in players]
    return sum(values) / len(values)


def _simulate_map(ours: float, theirs: float, rng: random.Random) -> Tuple[int, int, bool]:
    """Один матч на карте: до 16 побед, при 15:15 — овертаймы.

    Вероятность раунда берётся логистической функцией от разницы силы: разница
    в 12 очков даёт примерно три четверти раундов одной стороне.
    """
    chance = 1.0 / (1.0 + 10 ** ((theirs - ours) / STRENGTH_SCALE))
    us = 0
    them = 0
    rounds = 0
    while us < ROUNDS_TO_WIN and them < ROUNDS_TO_WIN and rounds < MAX_ROUNDS:
        rounds += 1
        if rng.random() < chance:
            us += 1
        else:
            them += 1
    if us == them:  # 15:15 — овертайм по шесть раундов до четырёх побед
        for _ in range(MAX_OVERTIMES):
            overtime_us = 0
            overtime_them = 0
            for _ in range(OVERTIME_ROUNDS):
                if rng.random() < chance:
                    overtime_us += 1
                else:
                    overtime_them += 1
            us += overtime_us
            them += overtime_them
            if overtime_us >= OVERTIME_TO_WIN or overtime_them >= OVERTIME_TO_WIN:
                break
        if us == them:  # совсем упёрлись — решает один раунд
            if rng.random() < chance:
                us += 1
            else:
                them += 1
        return us, them, True
    return us, them, False


__all__ = [
    "Csdraft",
    "CsdraftError",
    "ROLES",
    "ROLE_LABELS",
    "STAGES",
    "DIFFICULTIES",
    "DIFFICULTY_REROLLS",
    "DIFFICULTY_LABELS",
    "ERAS",
    "ASSIGN_MODES",
    "SQUAD_SIZE",
    "POOL_SIZE",
    "public_pack",
]
