# -*- coding: utf-8 -*-
"""Достижения AmrGames: что нужно сделать и что за это дают.

Достижения считаются по тому, что уже записано в базе, — отдельного журнала
событий не нужно. Метрики собирает сервер (см. `server.py`, `game_metrics`):

    narutodle_played   партии в Narutodle (любая роль в матче)
    narutodle_wins     победы в Narutodle
    songguess_runs     заходы в «Угадай песню»
    songguess_best     лучший счёт за один заход
    songguess_correct  сколько песен угадано всего
    draft_runs         прогоны драфтов (CS, Dota 2, Valorant, Rocket League)
    draft_champions    сколько турниров выиграно
    raporder_played    партии в «Рэп-хронологии»
    raporder_wins      победы в «Рэп-хронологии»
    narutodle_team_carry    победы в командах без единой своей догадки
    narutodle_madara_first  Мадара, угаданный с первой попытки
    songless_played    заходы и партии в «Аниме-сонглесс»
    songless_correct   сколько опенингов угадано
    songless_perfect   заходы без единой ошибки
    songless_fast      ответы быстрее двух секунд
    songless_guesses   сколько разных аниме угадано за всё время
    games_touched      в скольких играх есть хоть одна запись (из четырёх)
    total_games        все партии и заходы вместе

Награда — это статус рядом с ником или предмет кастомизации: ободок и
оформление карточки. Часть предметов доступна всем, а «Легенда», «Золото» и
«Прожектор» открываются только за достижения (см. GATED_FRAMES и GATED_CARDS).

Идентификаторы статусов должны совпадать с тем, что рисует страница профиля
(front/games/profile/index.html) и шапка (pill.js).
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Sequence, Set, Tuple

try:  # запуск как модуль: python -m backend.server
    from .auth import CARDS, FRAMES
except ImportError:  # запуск как файл: python backend/server.py
    from auth import CARDS, FRAMES  # type: ignore

# Статус рядом с ником: подпись, значок и цвет плашки.
STATUSES: Dict[str, Dict[str, str]] = {
    "genin": {"title": "Генин", "icon": "🍥", "color": "#f59e0b"},
    "chunin": {"title": "Тюнин", "icon": "🥋", "color": "#d97706"},
    "jonin": {"title": "Джонин", "icon": "🗡️", "color": "#0ea5e9"},
    "hokage": {"title": "Хокаге", "icon": "👑", "color": "#f43f5e"},
    "listener": {"title": "Меломан", "icon": "🎧", "color": "#a855f7"},
    "maestro": {"title": "Маэстро", "icon": "🎼", "color": "#8b5cf6"},
    "drafter": {"title": "Драфтер", "icon": "🎯", "color": "#22c55e"},
    "beatmaker": {"title": "Битмейкер", "icon": "🎤", "color": "#eab308"},
    "goldchain": {"title": "Золотая цепь", "icon": "⛓️", "color": "#d4af37"},
    "sennin": {"title": "Сеннин", "icon": "🐸", "color": "#16a34a"},
    "virtuoso": {"title": "Виртуоз", "icon": "🎻", "color": "#6366f1"},
    "dynasty": {"title": "Династия", "icon": "🏛️", "color": "#b45309"},
    "academy": {"title": "Академия", "icon": "📘", "color": "#0ea5e9"},
    "duelist": {"title": "Дуэлянт", "icon": "🥊", "color": "#ef4444"},
    "racer": {"title": "Гонщик", "icon": "🏃", "color": "#f97316"},
    "teammate": {"title": "Товарищ", "icon": "🤝", "color": "#14b8a6"},
    "flash": {"title": "Молния", "icon": "⚡", "color": "#facc15"},
    "stubborn": {"title": "Несгибаемый", "icon": "🔁", "color": "#94a3b8"},
    # «Аниме-сонглесс»: за достижения в угадывании опенингов.
    "animefan": {"title": "Анимешник", "icon": "🎌", "color": "#0ea5e9"},
    "openingexpert": {"title": "Знаток опенингов", "icon": "🎵", "color": "#8b5cf6"},
    "perfectear": {"title": "Идеальный слух", "icon": "👂", "color": "#22c55e"},
    "speedlisten": {"title": "Скоростной слух", "icon": "⚡", "color": "#f59e0b"},
    "collector": {"title": "Коллекционер", "icon": "📀", "color": "#a855f7"},
    # Секретный титул за все песни Re:Zero. На плашке — эмблема Субару.
    "subaruknight": {
        "title": "Самопровозглашённый рыцарь",
        "icon": "🛡️",
        "icon_url": "/games/profile/emblems/subaru.svg",
        "color": "#f97316",
    },
    # Скрытые титулы: в достижениях видно название, условие не раскрывается.
    # У «SiZeTovich» на плашке — флаг Израиля.
    "sizetovich": {
        "title": "SiZeTovich",
        "icon": "🎒",
        "icon_url": "/games/profile/emblems/israel.svg",
        "color": "#a3e635",
    },
    "madarovich": {"title": "Мадарович", "icon": "🌀", "color": "#dc2626"},
    # Титул администратора: открыт только роли admin, достижения не нужны.
    "owner": {"title": "Основатель", "icon": "🛠️", "color": "#b8121b", "adminOnly": "1"},
}

# Титулы, которые ставит только администратор.
ADMIN_STATUSES: Tuple[str, ...] = ("owner",)

# Достижения: условие — метрика не меньше goal. Награда: status и/или frame/card.
ACHIEVEMENTS: Sequence[Dict[str, Any]] = (
    {
        "id": "narutodle_first", "game": "narutodle", "icon": "🍥",
        "title": "Первый шаг ниндзя",
        "description": "Сыграть первую партию в Narutodle",
        "metric": "narutodle_played", "goal": 1,
        "reward": {"status": "genin"},
    },
    {
        "id": "narutodle_ten", "game": "narutodle", "icon": "🥋",
        "title": "Десять дуэлей",
        "description": "Сыграть десять партий в Narutodle",
        "metric": "narutodle_played", "goal": 10,
        "reward": {"status": "chunin"},
    },
    {
        "id": "narutodle_five_wins", "game": "narutodle", "icon": "🗡️",
        "title": "Пять побед",
        "description": "Выиграть пять партий в Narutodle",
        "metric": "narutodle_wins", "goal": 5,
        "reward": {"status": "jonin"},
    },
    {
        "id": "narutodle_hokage", "game": "narutodle", "icon": "👑",
        "title": "Хокаге",
        "description": "Выиграть пятнадцать партий в Narutodle",
        "metric": "narutodle_wins", "goal": 15,
        "reward": {"status": "hokage"},
    },
    {
        "id": "narutodle_academy", "game": "narutodle", "icon": "📘",
        "title": "Академия ниндзя",
        "description": "Сыграть пять партий в Narutodle",
        "metric": "narutodle_played", "goal": 5,
        "reward": {"status": "academy"},
    },
    {
        "id": "narutodle_duel_10", "game": "narutodle", "icon": "🥊",
        "title": "Дуэлянт",
        "description": "Провести десять партий в режиме «Дуэль»",
        "metric": "narutodle_duel", "goal": 10,
        "reward": {"status": "duelist"},
    },
    {
        "id": "narutodle_race_10", "game": "narutodle", "icon": "🏃",
        "title": "Гонщик",
        "description": "Провести десять партий в режиме «Гонка»",
        "metric": "narutodle_race", "goal": 10,
        "reward": {"status": "racer"},
    },
    {
        "id": "narutodle_teams_10", "game": "narutodle", "icon": "🤝",
        "title": "Командный игрок",
        "description": "Провести десять партий в режиме «Команды»",
        "metric": "narutodle_teams", "goal": 10,
        "reward": {"status": "teammate"},
    },
    {
        "id": "narutodle_fast_5", "game": "narutodle", "icon": "⚡",
        "title": "Молния",
        "description": "Выиграть пять партий не больше чем за три попытки",
        "metric": "narutodle_fast_wins", "goal": 5,
        "reward": {"status": "flash"},
    },
    {
        "id": "narutodle_losses_10", "game": "narutodle", "icon": "🔁",
        "title": "Несгибаемый",
        "description": "Проиграть десять партий и не уйти из комнаты",
        "metric": "narutodle_losses", "goal": 10,
        "reward": {"status": "stubborn"},
    },
    {
        "id": "narutodle_team_carry", "game": "narutodle", "icon": "🎒",
        "title": "SiZeTovich",
        "description": "Выиграть командный матч, не угадав ни одного персонажа",
        "metric": "narutodle_team_carry", "goal": 1,
        "reward": {"status": "sizetovich"},
        # Скрытое достижение: название видно, условие в профиле не показываем.
        "secret": True,
    },
    {
        "id": "narutodle_madara_first", "game": "narutodle", "icon": "🌀",
        "title": "Мадарович",
        "description": "Угадать Мадару Учиху с первой попытки",
        "metric": "narutodle_madara_first", "goal": 1,
        "reward": {"status": "madarovich"},
        "secret": True,
    },
    {
        "id": "songless_first", "game": "songless", "icon": "🎌",
        "title": "Первый опенинг",
        "description": "Сыграть первый заход в «Аниме-сонглесс»",
        "metric": "songless_played", "goal": 1,
        "reward": {"status": "animefan"},
    },
    {
        "id": "songless_correct_50", "game": "songless", "icon": "🎵",
        "title": "Знаток опенингов",
        "description": "Угадать пятьдесят опенингов",
        "metric": "songless_correct", "goal": 50,
        "reward": {"status": "openingexpert"},
    },
    {
        "id": "songless_perfect", "game": "songless", "icon": "👂",
        "title": "Идеальный слух",
        "description": "Пройти заход без единой ошибки",
        "metric": "songless_perfect", "goal": 1,
        "reward": {"status": "perfectear"},
    },
    {
        "id": "songless_fast_10", "game": "songless", "icon": "⚡",
        "title": "Скоростной слух",
        "description": "Десять раз ответить быстрее чем за две секунды",
        "metric": "songless_fast", "goal": 10,
        "reward": {"status": "speedlisten"},
    },
    {
        "id": "songless_collect_25", "game": "songless", "icon": "📀",
        "title": "Коллекционер опенингов",
        "description": "Угадать двадцать пять разных аниме",
        "metric": "songless_guesses", "goal": 25,
        "reward": {"status": "collector"},
    },
    {
        "id": "songless_rezero_all", "game": "songless", "icon": "🛡️",
        "title": "Самопровозглашённый рыцарь",
        "description": "Угадать все песни из Re:Zero в «Аниме-сонглессе»",
        # В наборе шесть опенингов Re:Zero: Redo, Paradisus-Paradoxum, Realize,
        # Long shot, Reweave и Recollect. Добавите новый — поднимите и goal.
        "metric": "songless_rezero", "goal": 6,
        "reward": {"status": "subaruknight"},
        "secret": True,
    },
    {
        "id": "narutodle_chars_25", "game": "narutodle", "icon": "🍃",
        "title": "Знаток Конохи",
        "description": "Угадать двадцать пять разных персонажей",
        "metric": "narutodle_chars", "goal": 25,
        "reward": {"frame": "konoha"},
    },
    {
        "id": "narutodle_chars_50", "game": "narutodle", "icon": "📜",
        "title": "Архивариус",
        "description": "Угадать пятьдесят разных персонажей",
        "metric": "narutodle_chars", "goal": 50,
        "reward": {"card": "scroll"},
    },
    {
        "id": "songguess_first", "game": "songguess", "icon": "🎧",
        "title": "Первый мотив",
        "description": "Пройти первый заход в «Угадай песню»",
        "metric": "songguess_runs", "goal": 1,
        "reward": {"status": "listener"},
    },
    {
        "id": "songguess_maestro", "game": "songguess", "icon": "🎼",
        "title": "Абсолютный слух",
        "description": "Набрать 600 очков за один заход «Угадай песню»",
        "metric": "songguess_best", "goal": 600,
        "reward": {"status": "maestro"},
    },
    {
        "id": "draft_first", "game": "csdraft", "icon": "🎯",
        "title": "Первый пик",
        "description": "Пройти первый драфт: CS, Dota 2, Valorant или Rocket League",
        "metric": "draft_runs", "goal": 1,
        "reward": {"status": "drafter"},
    },
    {
        "id": "draft_champion", "game": "csdraft", "icon": "🏆",
        "title": "Чемпион",
        "description": "Выиграть турнир в любом драфте",
        "metric": "draft_champions", "goal": 1,
        "reward": {"card": "gold"},
    },
    {
        "id": "raporder_first", "game": "raporder", "icon": "🎤",
        "title": "Первый трек",
        "description": "Сыграть первую партию в «Рэп-хронологии»",
        "metric": "raporder_played", "goal": 1,
        "reward": {"status": "beatmaker"},
    },
    {
        "id": "raporder_wins", "game": "raporder", "icon": "⛓️",
        "title": "Золотая цепь",
        "description": "Выиграть пять партий в «Рэп-хронологии»",
        "metric": "raporder_wins", "goal": 5,
        "reward": {"status": "goldchain"},
    },
    {
        "id": "all_games", "game": "all", "icon": "🌿",
        "title": "Везде по разу",
        "description": "Сыграть хотя бы по партии в каждой из четырёх игр",
        "metric": "games_touched", "goal": 4,
        "reward": {"frame": "legend"},
    },
    {
        "id": "veteran", "game": "all", "icon": "🔥",
        "title": "Ветеран AmrGames",
        "description": "Сорок партий и заходов во всех играх вместе",
        "metric": "total_games", "goal": 40,
        "reward": {"card": "spotlight"},
    },
    {
        "id": "narutodle_wins_30", "game": "narutodle", "icon": "🐸",
        "title": "Сеннин",
        "description": "Выиграть тридцать партий в Narutodle",
        "metric": "narutodle_wins", "goal": 30,
        "reward": {"status": "sennin"},
    },
    {
        "id": "songguess_correct_100", "game": "songguess", "icon": "🎻",
        "title": "Золотой слух",
        "description": "Угадать сто песен в «Угадай песню»",
        "metric": "songguess_correct", "goal": 100,
        "reward": {"status": "virtuoso"},
    },
    {
        "id": "draft_champions_5", "game": "csdraft", "icon": "🏛️",
        "title": "Династия",
        "description": "Выиграть пять турниров в драфтах",
        "metric": "draft_champions", "goal": 5,
        "reward": {"status": "dynasty", "card": "crown"},
    },
)

# Предметы, которые нельзя поставить без достижения.
GATED_FRAMES: Dict[str, str] = {
    "legend": "all_games",
    "konoha": "narutodle_chars_25",
}
GATED_CARDS: Dict[str, str] = {
    "gold": "draft_champion",
    "spotlight": "veteran",
    "crown": "draft_champions_5",
    "scroll": "narutodle_chars_50",
}


def by_id(achievement_id: str) -> Dict[str, Any]:
    """Достижение по идентификатору (или пустой словарь)."""
    for item in ACHIEVEMENTS:
        if item["id"] == achievement_id:
            return dict(item)
    return {}


def rewards_status(achievement_ids: Iterable[str]) -> Set[str]:
    """Какие статусы открыты набором достижений."""
    ids = set(achievement_ids)
    return {str(item["reward"]["status"]) for item in ACHIEVEMENTS
            if "status" in item["reward"] and item["id"] in ids}


def unlocked_frames(achievement_ids: Iterable[str]) -> List[str]:
    """Ободки, доступные игроку: обычные всем, «Легенда» — за достижение."""
    ids = set(achievement_ids)
    free = [frame for frame in FRAMES if frame and frame not in GATED_FRAMES]
    extra = [frame for frame, need in GATED_FRAMES.items() if need in ids]
    return free + sorted(extra)


def unlocked_cards(achievement_ids: Iterable[str]) -> List[str]:
    """Оформления карточки, доступные игроку."""
    ids = set(achievement_ids)
    free = [card for card in CARDS if card and card not in GATED_CARDS]
    extra = [card for card, need in GATED_CARDS.items() if need in ids]
    return free + sorted(extra)


def progress(metrics: Dict[str, int], unlocked: Iterable[str]) -> List[Dict[str, Any]]:
    """Состояние всех достижений: сколько сделано, открыто ли и когда.

    У скрытых достижений наружу уходит только название и награда: условие,
    метрику и прогресс не показываем, иначе секрет перестаёт быть секретом.
    """
    unlocked_map = {str(key): value for key, value in dict(unlocked).items()}
    result: List[Dict[str, Any]] = []
    for item in ACHIEVEMENTS:
        metric = str(item["metric"])
        goal = int(item["goal"])
        done = int(metrics.get(metric) or 0)
        secret = bool(item.get("secret"))
        row = {
            "id": item["id"],
            "game": item["game"],
            "icon": item["icon"],
            "title": item["title"],
            "description": item["description"],
            "metric": metric,
            "goal": goal,
            "progress": min(done, goal),
            "done": done >= goal,
            "unlocked": item["id"] in unlocked_map,
            "unlocked_at": unlocked_map.get(item["id"]),
            "reward": dict(item["reward"]),
            "secret": secret,
        }
        if secret:
            row["description"] = ""
            row["metric"] = ""
            row["goal"] = 0
            row["progress"] = 0
        result.append(row)
    return result


def validate_status(value: object, allowed: Iterable[str], role: str = "user") -> str:
    """Статус рядом с ником: пусто, открытый достижением или админский титул."""
    text = str(value or "").strip().lower()
    if not text:
        return ""
    if text not in STATUSES:
        raise ValueError("Неизвестный статус")
    if text in ADMIN_STATUSES:
        # Титул «Основатель» не выдаётся достижениями — только ролью.
        if role != "admin":
            raise ValueError("Этот титул доступен только администратору")
        return text
    if text not in set(allowed):
        raise ValueError("Этот статус ещё не открыт")
    return text


def check_item(value: object, unlocked: Iterable[str], title: str) -> str:
    """Предмет кастомизации: обычный доступен всем, закрытый — за достижение."""
    text = str(value or "").strip().lower()
    if not text:
        return ""
    if text not in set(unlocked):
        raise ValueError(f"{title} открывается за достижение")
    return text


__all__ = [
    "ACHIEVEMENTS",
    "ADMIN_STATUSES",
    "GATED_CARDS",
    "GATED_FRAMES",
    "STATUSES",
    "by_id",
    "check_item",
    "progress",
    "rewards_status",
    "unlocked_cards",
    "unlocked_frames",
    "validate_status",
]