# -*- coding: utf-8 -*-
"""Реестр игр-драфтов: у каждой игры свои роли, арены, стадии и правила матчей.

Движок один (backend/csdraft.py), а всё, что отличает одну игру от другой,
собрано здесь: состав ролей, набор арен (в CS это карты), эпохи, стадии прогона,
усиления, известные связки и правила розыгрыша одной арены.

Данные о составах — реальные исторические: команда, турнир, год, место и игроки
с ролями. Оценки AIM/CLUTCH/IMP — игровые, они расставлены для баланса, а не
являются официальной статистикой. Ники игроков, названия команд и турниров —
исторические факты и принадлежат их владельцам; игры некоммерческие и не связаны
с издателями игр.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

try:  # запуск как модуль: python -m backend.server
    from .csdraft_data import (
        BOOSTS as CS_BOOSTS,
        DUOS as CS_DUOS,
        ERA_LABELS as CS_ERA_LABELS,
        PACKS as CS_PACKS,
        ROLE_LABELS as CS_ROLE_LABELS,
        ROLES as CS_ROLES,
        STAT_WEIGHTS as CS_STAT_WEIGHTS,
        packs as cs_packs,
    )
    from .draft_games_data import RL_PACKS, VALORANT_PACKS
except ImportError:  # запуск как файл: python backend/server.py
    from csdraft_data import (  # type: ignore
        BOOSTS as CS_BOOSTS,
        DUOS as CS_DUOS,
        ERA_LABELS as CS_ERA_LABELS,
        PACKS as CS_PACKS,
        ROLE_LABELS as CS_ROLE_LABELS,
        ROLES as CS_ROLES,
        STAT_WEIGHTS as CS_STAT_WEIGHTS,
        packs as cs_packs,
    )
    from draft_games_data import RL_PACKS, VALORANT_PACKS  # type: ignore

# Стадии прогона одинаковы по смыслу (группа, четвертьфинал, полуфинал, финал),
# но форматы разные — как в реальных турнирах этих игр.
CS_STAGES: Tuple[Dict[str, Any], ...] = (
    {"key": "opening", "title": "Групповой этап", "best_of": 1},
    {"key": "quarters", "title": "Четвертьфинал", "best_of": 3},
    {"key": "semis", "title": "Полуфинал", "best_of": 3},
    {"key": "final", "title": "Финал мейджора", "best_of": 5},
)

VALORANT_STAGES: Tuple[Dict[str, Any], ...] = (
    {"key": "opening", "title": "Групповой этап", "best_of": 1},
    {"key": "quarters", "title": "Четвертьфинал", "best_of": 3},
    {"key": "semis", "title": "Полуфинал", "best_of": 3},
    {"key": "final", "title": "Финал Champions", "best_of": 5},
)

RL_STAGES: Tuple[Dict[str, Any], ...] = (
    {"key": "opening", "title": "Групповой этап", "best_of": 5},
    {"key": "quarters", "title": "Четвертьфинал", "best_of": 5},
    {"key": "semis", "title": "Полуфинал", "best_of": 7},
    {"key": "final", "title": "Финал Worlds", "best_of": 7},
)

# Родственные роли: игрок не в своей роли получает штраф, но у соседних ролей
# он меньше — например, AWP-шер может закрыть луркера.
CS_ADJACENCY: Dict[str, Tuple[str, ...]] = {
    "awp": ("lurker",),
    "lurker": ("awp", "entry"),
    "entry": ("lurker", "support"),
    "support": ("entry", "igl"),
    "igl": ("support",),
}

VALORANT_ADJACENCY: Dict[str, Tuple[str, ...]] = {
    "duelist": ("flex",),
    "flex": ("duelist", "initiator"),
    "initiator": ("flex", "controller"),
    "controller": ("initiator", "sentinel"),
    "sentinel": ("controller", "flex"),
}

RL_ADJACENCY: Dict[str, Tuple[str, ...]] = {
    "striker": ("midfield",),
    "midfield": ("striker", "keeper"),
    "keeper": ("midfield",),
}

VALORANT_ROLES: Tuple[str, ...] = ("duelist", "initiator", "controller", "sentinel", "flex")
VALORANT_ROLE_LABELS: Dict[str, str] = {
    "duelist": "Дуэлист",
    "initiator": "Инициатор",
    "controller": "Контроллер",
    "sentinel": "Часовой",
    "flex": "Флекс",
}

RL_ROLES: Tuple[str, ...] = ("striker", "midfield", "keeper")
RL_ROLE_LABELS: Dict[str, str] = {
    "striker": "Атакующий",
    "midfield": "Полузащитник",
    "keeper": "Защитник",
}

VALORANT_BOOSTS: Tuple[Dict[str, Any], ...] = (
    {"id": "duelist-charge", "title": "Смелый вход: +4 к дуэлисту", "value": 4.0, "role": "duelist"},
    {"id": "initiator-flash", "title": "Постановка флешек: +4 к инициатору", "value": 4.0, "role": "initiator"},
    {"id": "controller-smoke", "title": "Смоки и стены: +4 к контроллеру", "value": 4.0, "role": "controller"},
    {"id": "sentinel-traps", "title": "Ловушки на флангах: +4 к часовому", "value": 4.0, "role": "sentinel"},
    {"id": "flex-swap", "title": "Смена агента: +4 к флексу", "value": 4.0, "role": "flex"},
    {"id": "chem-camp", "title": "Сбор: +3 к сыгранности", "value": 3.0},
    {"id": "coach", "title": "Тренер на буткемпе: +5 к составу", "value": 5.0},
    {"id": "clutch-mind", "title": "Хладнокровие: +3 к составу", "value": 3.0},
    {"id": "map-pool", "title": "Заготовка: +1 карта в маппул", "value": 0.0, "extra_map": True},
    {"id": "reroll", "title": "Просмотр рынка: +1 реролл", "value": 0.0, "reroll": 1},
)

VALORANT_DUOS: Tuple[Tuple[str, str], ...] = (
    ("aspas", "Less"),
    ("Sacy", "saadhak"),
    ("yay", "crashies"),
    ("Demon1", "Ethan"),
    ("Boostio", "C0M"),
    ("Boaster", "Derke"),
    ("Chronicle", "Alfajer"),
    ("f0rsakeN", "Jinggg"),
    ("Jinggg", "d4v41"),
    ("TenZ", "zekken"),
    ("ZmjjKK", "CHICHOO"),
    ("Boo", "MiniBoo"),
    ("Meteor", "t3xture"),
    ("cNed", "starxo"),
    ("nAts", "Chronicle"),
    ("ardiis", "Suygetsu"),
)

RL_BOOSTS: Tuple[Dict[str, Any], ...] = (
    {"id": "striker-air", "title": "Игра в воздухе: +4 к атакующему", "value": 4.0, "role": "striker"},
    {"id": "midfield-pass", "title": "Пас на выход: +4 к полузащитнику", "value": 4.0, "role": "midfield"},
    {"id": "keeper-save", "title": "Сейв на линии: +4 к защитнику", "value": 4.0, "role": "keeper"},
    {"id": "chem-camp", "title": "Сбор: +3 к сыгранности", "value": 3.0},
    {"id": "coach", "title": "Тренер на буткемпе: +5 к составу", "value": 5.0},
    {"id": "kickoff", "title": "Отработанный кикофф: +3 к составу", "value": 3.0},
    {"id": "map-pool", "title": "Заготовка: +1 арена в пул", "value": 0.0, "extra_map": True},
    {"id": "reroll", "title": "Просмотр рынка: +1 реролл", "value": 0.0, "reroll": 1},
)

RL_DUOS: Tuple[Tuple[str, str], ...] = (
    ("Kaydop", "ViolentPanda"),
    ("Kaydop", "Turbopolsa"),
    ("ViolentPanda", "Turbopolsa"),
    ("SquishyMuffinz", "Gimmick"),
    ("SquishyMuffinz", "Torment"),
    ("Gimmick", "Torment"),
    ("GarrettG", "Jstn"),
    ("GarrettG", "Turbopolsa"),
    ("Fairy Peak", "Kaydop"),
    ("M0nkey M00n", "Extra"),
    ("M0nkey M00n", "Marc_by_8"),
    ("Extra", "Marc_by_8"),
    ("JKnaps", "Chicago"),
    ("Chicago", "Atomic"),
    ("JKnaps", "Atomic"),
    ("Vatira", "Joyo"),
    ("Joyo", "rise."),
    ("Vatira", "rise."),
    ("zen", "Alpha54"),
    ("zen", "Radosin"),
    ("Alpha54", "Radosin"),
    ("Extra", "Rise"),
    ("Rise", "M0nkey M00n"),
)

# --- Конфигурации игр -------------------------------------------------------

CS_GAME: Dict[str, Any] = {
    "key": "cs",
    "title": "87-0",
    "tagline": "Драфт по Counter-Strike: собери состав мечты и возьми мейджор",
    "help": [
        "Паки — это реальные составы прошлых турниров: пять игроков с ролями и карты "
        "того маппула.",
        "Забирайте игроков в пять слотов ролей и карты в свой маппул: за попадание в роль "
        "и сыгранность состав получает надбавку, а на своих картах играть легче.",
        "Потом прогон по сетке мейджора: поражение заканчивает прогон.",
    ],
    "roles": CS_ROLES,
    "role_labels": CS_ROLE_LABELS,
    "adjacency": CS_ADJACENCY,
    "pool_size": 3,
    "pool_label": "Свой маппул",
    "pool_hint": "на этих картах состав играет лучше",
    "pool_item_hint": "их можно забрать в свой пул",
    "boot_title": "Начать мейджор",
    "tournament": "мейджор",
    "tournament_cap": "Мейджор",
    "texts": {
        "no_map": "Такой карты нет в маппуле этого состава",
        "pool_taken": "{name} уже в вашем маппуле",
        "pool_full": "Маппул заполнен: карты можно менять только бустами",
        "pool_added": "В маппул добавлена карта {name}",
        "started": "Мейджор начался: четыре стадии до титула",
        "champion": "Титул мейджора взят без поражений — идеальный прогон!",
    },
    "stages": CS_STAGES,
    "boosts": CS_BOOSTS,
    "duos": CS_DUOS,
    "era_labels": CS_ERA_LABELS,
    "match": {
        "arena": "карта",
        "arena_cap": "Карты маппула",
        "score": "раунды",
        "rounds_to_win": 16,
        "max_rounds": 30,
        "overtime_rounds": 6,
        "overtime_to_win": 4,
        "max_overtimes": 3,
        "strength_scale": 12.0,
        "map_edge": 3.0,
    },
    "packs": cs_packs(),
}

VALORANT_GAME: Dict[str, Any] = {
    "key": "valorant",
    "title": "13-0",
    "tagline": "Драфт по Valorant: собери состав из звёзд VCT и возьми Champions",
    "help": [
        "Паки — это реальные составы команд VCT: пять игроков и карты их маппула.",
        "Роли здесь как в Valorant: дуэлист, инициатор, контроллер, часовой и флекс. "
        "Карта играется до 13 побед, при 12:12 — овертаймы.",
        "Между стадиями пула выбирается усиление, поражение заканчивает прогон.",
    ],
    "roles": VALORANT_ROLES,
    "role_labels": VALORANT_ROLE_LABELS,
    "adjacency": VALORANT_ADJACENCY,
    "pool_size": 3,
    "pool_label": "Свой маппул",
    "pool_hint": "на своих картах играется легче",
    "pool_item_hint": "их можно забрать в свой пул",
    "boot_title": "Начать Champions",
    "tournament": "Champions",
    "tournament_cap": "Champions",
    "texts": {
        "no_map": "Такой карты нет в маппуле этого состава",
        "pool_taken": "{name} уже в вашем маппуле",
        "pool_full": "Маппул заполнен: расширить его можно только усилением",
        "pool_added": "В маппул добавлена карта {name}",
        "started": "Champions начался: четыре стадии до титула",
        "champion": "Титул Champions взят без поражений — идеальный прогон!",
    },
    "stages": VALORANT_STAGES,
    "boosts": VALORANT_BOOSTS,
    "duos": VALORANT_DUOS,
    "era_labels": {"legacy": "Первый VCT (2021–2022)", "modern": "Франшиза (2023–2024)"},
    "match": {
        "arena": "карта",
        "arena_cap": "Карты маппула",
        "score": "раунды",
        "rounds_to_win": 13,
        "max_rounds": 24,
        "overtime_rounds": 2,
        "overtime_to_win": 2,
        "max_overtimes": 3,
        "strength_scale": 12.0,
        "map_edge": 3.0,
    },
    "packs": VALORANT_PACKS,
}

RL_GAME: Dict[str, Any] = {
    "key": "rl",
    "title": "4-0",
    "tagline": "Драфт по Rocket League: собери тройку из истории RLCS и возьми Worlds",
    "help": [
        "Паки — это реальные составы команд RLCS: тройка игроков и арены их пула.",
        "Роли — атакующий, полузащитник и защитник; серии играются до победы в Bo5 и Bo7, "
        "а игра (арена) — до трёх голов.",
        "Поражение в серии заканчивает прогон, между стадиями даётся усиление.",
    ],
    "roles": RL_ROLES,
    "role_labels": RL_ROLE_LABELS,
    "adjacency": RL_ADJACENCY,
    "pool_size": 3,
    "pool_label": "Свой пул арен",
    "pool_hint": "на своих аренах играется легче",
    "pool_item_hint": "их можно забрать в свой пул",
    "boot_title": "Начать Worlds",
    "tournament": "Worlds",
    "tournament_cap": "Worlds",
    "texts": {
        "no_map": "Такой арены нет в пуле этого состава",
        "pool_taken": "{name} уже в вашем пуле арен",
        "pool_full": "Пул арен заполнен: расширить его можно только усилением",
        "pool_added": "В пул добавлена арена {name}",
        "started": "Worlds начался: четыре стадии до титула",
        "champion": "Титул Worlds взят без поражений — идеальный прогон!",
    },
    "stages": RL_STAGES,
    "boosts": RL_BOOSTS,
    "duos": RL_DUOS,
    "era_labels": {"legacy": "Легенды RLCS (2017–2019)", "modern": "Новое время (2021–2025)"},
    "match": {
        "arena": "арена",
        "arena_cap": "Арены пула",
        "score": "голы",
        "rounds_to_win": 3,
        "max_rounds": 8,
        "overtime_rounds": 2,
        "overtime_to_win": 2,
        "max_overtimes": 3,
        "strength_scale": 10.0,
        "map_edge": 2.5,
    },
    "packs": RL_PACKS,
}

GAMES: Dict[str, Dict[str, Any]] = {
    "cs": CS_GAME,
    "valorant": VALORANT_GAME,
    "rl": RL_GAME,
}

# Порядок игр на странице выбора.
GAME_KEYS: Tuple[str, ...] = ("cs", "valorant", "rl")

# Общие части: оценки и веса одинаковы во всех играх, меняются только подписи.
STAT_KEYS: Tuple[str, ...] = ("aim", "clutch", "impact")
STAT_LABELS: Dict[str, str] = {"aim": "AIM", "clutch": "CLUTCH", "impact": "IMP"}
STAT_WEIGHTS: Dict[str, float] = dict(CS_STAT_WEIGHTS)


def game_config(key: Optional[str]) -> Dict[str, Any]:
    """Конфигурация игры по ключу: неизвестный ключ — понятная ошибка."""
    name = str(key or "cs").strip().lower()
    if name not in GAMES:
        raise KeyError(f"Неизвестная игра: {key}")
    return GAMES[name]


def game_block(key: str) -> Dict[str, Any]:
    """Публичная часть конфигурации для страницы: без данных и служебных полей."""
    cfg = game_config(key)
    return {
        "key": cfg["key"],
        "title": cfg["title"],
        "tagline": cfg["tagline"],
        "help": list(cfg["help"]),
        "tournament": cfg["tournament"],
        "pool_label": cfg["pool_label"],
        "pool_hint": cfg["pool_hint"],
        "pool_item_hint": cfg["pool_item_hint"],
        "boot_title": cfg["boot_title"],
        "roles": [{"key": role, "label": cfg["role_labels"][role]} for role in cfg["roles"]],
        "era_labels": dict(cfg["era_labels"]),
        "stages": [{"key": stage["key"], "title": stage["title"], "best_of": stage["best_of"]}
                   for stage in cfg["stages"]],
        "match": {
            "arena": cfg["match"]["arena"],
            "arena_cap": cfg["match"]["arena_cap"],
            "score": cfg["match"]["score"],
            "rounds_to_win": cfg["match"]["rounds_to_win"],
        },
    }


def games_block() -> List[Dict[str, Any]]:
    """Список игр для страницы выбора: ключ, название и подпись."""
    return [{"key": key, "title": GAMES[key]["title"], "tagline": GAMES[key]["tagline"]}
            for key in GAME_KEYS]


def seed_rows_for(key: str) -> List[Dict[str, Any]]:
    """Паки игры для записи в базу (без посчитанных рейтингов).

    У CS идентификаторы паков исторические и уже лежат в базах без префикса,
    поэтому для CS берётся набор из backend/csdraft_data.py как есть, а паки
    других игр получают префикс с ключом игры, чтобы не совпасть между собой.
    """
    cfg = game_config(key)
    if cfg["key"] == "cs":
        return [
            {
                "id": pack["id"],
                "game": "cs",
                "team": pack["team"],
                "event": pack["event"],
                "year": pack["year"],
                "place": pack.get("place", ""),
                "major": pack.get("major", False),
                "region": pack.get("region", ""),
                "era": pack.get("era", "legacy"),
                "maps": list(pack.get("maps", ())),
                "players": [dict(player) for player in pack.get("players", ())],
            }
            for pack in cs_packs()
        ]
    rows: List[Dict[str, Any]] = []
    for pack in cfg["packs"]:
        players = []
        for player in pack.get("players", ()):
            if isinstance(player, dict):
                item = dict(player)
            else:
                name, role, aim, clutch, impact = player
                item = {"name": name, "role": role, "aim": aim, "clutch": clutch, "impact": impact}
            players.append({
                "name": str(item["name"]),
                "role": str(item["role"]),
                "aim": float(item.get("aim") or 0),
                "clutch": float(item.get("clutch") or 0),
                "impact": float(item.get("impact") or 0),
            })
        rows.append({
            "id": f"{cfg['key']}:{pack['id']}",
            "game": str(cfg["key"]),
            "team": str(pack["team"]),
            "event": str(pack["event"]),
            "year": int(pack["year"]),
            "place": str(pack.get("place") or ""),
            "major": bool(pack.get("major")),
            "region": str(pack.get("region") or ""),
            "era": str(pack.get("era") or "legacy"),
            "maps": "; ".join(str(name) for name in pack.get("maps", ())),
            "players": players,
        })
    return rows


__all__ = [
    "GAMES",
    "GAME_KEYS",
    "STAT_KEYS",
    "STAT_LABELS",
    "STAT_WEIGHTS",
    "game_config",
    "game_block",
    "games_block",
    "seed_rows_for",
]
