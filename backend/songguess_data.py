# -*- coding: utf-8 -*-
"""Данные для игры «Угадай песню за 10 секунд»: песни по темам.

Этот файл — исходный набор для первичного заполнения таблицы `songguess_tracks`:
сервер проверяет её при запуске и, если она пуста, заливает данные отсюда
(см. backend/seed_songguess.py). Дальше источник правды — база.

Темы (категории) задаются в `CATEGORIES`: сейчас это аниме, русский рэп и
хип-хоп. Наборы по аниме и русскому рэпу **не дублируются**, а берутся из уже
существующих файлов данных ([`backend/songless_data.py`](songless_data.py) и
[`backend/raporder_data.py`](raporder_data.py)) — так одна и та же песня не
расползается по двум спискам. Новую тему достаточно добавить в `CATEGORIES`
и положить её строки в `ROWS_BY_CATEGORY`.

Здесь **только справочные сведения** — название, исполнитель, год и (для аниме)
название сериала. Текстов песен и записей нет и быть не может: музыка защищена
авторским правом, поэтому аудио добавляет владелец сайта — своими файлами в
`front/games/songguess/audio/` или ссылками на файлы (см. README и
`backend/seed_songguess.py --audio` / `--url`). Пока у песни нет записи, раунд
на ней не строится.

Фрагмент короткий: игра быстрая, поэтому по умолчанию слушаем `SLICE_SECONDS`
секунд с начала припева (`clip_start`), а на ответ даётся `DIFFICULTIES`.
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

try:  # запуск как модуль: python -m backend.server
    from .raporder_data import TRACKS as RAP_TRACKS
    from .songless_data import ROWS as ANIME_ROWS
except ImportError:  # запуск как файл: python backend/server.py
    from raporder_data import TRACKS as RAP_TRACKS  # type: ignore
    from songless_data import ROWS as ANIME_ROWS  # type: ignore

# Сколько вариантов ответа показывать (один верный и три «обманки»).
OPTION_COUNT = 4

# Раундов в заходе: угадал — идём дальше, промахнулся — раунд потерян.
ROUNDS_PER_GAME = 5

# Сколько секунд слушаем фрагмент и сколько показываем разбор раунда.
SLICE_SECONDS = 5.0
REVEAL_SECONDS = 5.0

DEFAULT_START = 0.0
DEFAULT_CLIP = 10.0

# Сложность — это и есть «X секунд»: сколько времени даётся на ответ.
DIFFICULTIES: Tuple[Tuple[str, str, float], ...] = (
    ("blitz", "Блиц (5 секунд)", 5.0),
    ("normal", "Обычная (10 секунд)", 10.0),
    ("calm", "Спокойная (15 секунд)", 15.0),
)
DIFFICULTY_SECONDS: Dict[str, float] = {key: seconds for key, _, seconds in DIFFICULTIES}
DIFFICULTY_LABELS: Dict[str, str] = {key: label for key, label, _ in DIFFICULTIES}

# Очки: базовые за верный ответ плюс добавка за скорость.
BASE_POINTS = 100
SPEED_POINTS = 100

FIELDS = ("id", "category", "title", "artist", "year", "source", "audio",
          "clip_start", "clip_length")

# Темы игры: ключ латиницей (попадает в адреса API), подпись и подсказка.
CATEGORIES: Tuple[Dict[str, str], ...] = (
    {"key": "anime", "label": "Аниме", "hint": "опенинги и эндинги"},
    {"key": "rusrap", "label": "Русский рэп", "hint": "рэп на русском"},
    {"key": "hiphop", "label": "Хип-хоп", "hint": "зарубежный хип-хоп"},
)
CATEGORY_LABELS: Dict[str, str] = {item["key"]: item["label"] for item in CATEGORIES}

# Хип-хоп: название, исполнитель, год. Проверялось по открытым источникам,
# но годы стоит перепроверять: часть песен выходила синглами и в альбомах
# разных лет.
HIPHOP_ROWS: Tuple[Tuple[str, str, str], ...] = (
    ("The Message", "Grandmaster Flash and the Furious Five", "1982"),
    ("Walk This Way", "Run-D.M.C. и Aerosmith", "1986"),
    ("Fight the Power", "Public Enemy", "1989"),
    ("C.R.E.A.M.", "Wu-Tang Clan", "1993"),
    ("N.Y. State of Mind", "Nas", "1994"),
    ("Juicy", "The Notorious B.I.G.", "1994"),
    ("California Love", "2Pac", "1995"),
    ("Still D.R.E.", "Dr. Dre и Snoop Dogg", "1999"),
    ("My Name Is", "Eminem", "1999"),
    ("Party Up (Up in Here)", "DMX", "1999"),
    ("Stan", "Eminem", "2000"),
    ("Ms. Jackson", "OutKast", "2000"),
    ("Get Ur Freak On", "Missy Elliott", "2001"),
    ("Lose Yourself", "Eminem", "2002"),
    ("In da Club", "50 Cent", "2003"),
    ("99 Problems", "Jay-Z", "2003"),
    ("Drop It Like It's Hot", "Snoop Dogg", "2004"),
    ("Stronger", "Kanye West", "2007"),
    ("A Milli", "Lil Wayne", "2008"),
    ("Empire State of Mind", "Jay-Z и Alicia Keys", "2009"),
    ("Alright", "Kendrick Lamar", "2015"),
    ("HUMBLE.", "Kendrick Lamar", "2017"),
    ("Bodak Yellow", "Cardi B", "2017"),
    ("God's Plan", "Drake", "2018"),
    ("SICKO MODE", "Travis Scott", "2018"),
)


def slug(text: str) -> str:
    """Идентификатор из названия: латиница и цифры, остальное — дефис."""
    table = str.maketrans({
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh",
        "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
        "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "ts",
        "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu",
        "я": "ya",
    })
    lowered = str(text).lower().translate(table)
    keep = [char if (char.isalnum() and char.isascii()) else "-" for char in lowered]
    slug_text = "".join(keep)
    while "--" in slug_text:
        slug_text = slug_text.replace("--", "-")
    return slug_text.strip("-") or "song"


def _rows_by_category() -> Dict[str, List[Tuple[str, str, str, str]]]:
    """Строки тем: название, исполнитель, год и пояснение (для аниме — сериал)."""
    anime = [(song, artist, str(year), anime) for anime, song, artist, year in ANIME_ROWS]
    rap = [(title, artist, str(year), "") for _, artist, title, year in RAP_TRACKS]
    hiphop = [(title, artist, year, "") for title, artist, year in HIPHOP_ROWS]
    return {"anime": anime, "rusrap": rap, "hiphop": hiphop}


ROWS_BY_CATEGORY: Dict[str, List[Tuple[str, str, str, str]]] = _rows_by_category()


def _build_tracks() -> List[Dict[str, Any]]:
    """Плоский список песен: у каждой свой идентификатор внутри темы."""
    tracks: List[Dict[str, Any]] = []
    for category in CATEGORIES:
        key = category["key"]
        used: Dict[str, int] = {}
        for title, artist, year, source in ROWS_BY_CATEGORY.get(key, ()):
            base = slug(title)
            index = used.get(base, 0) + 1
            used[base] = index
            tracks.append({
                "id": f"{key}-{base}" if index == 1 else f"{key}-{base}-{index}",
                "category": key,
                "title": str(title),
                "artist": str(artist),
                "year": str(year),
                "source": str(source or ""),
                "audio": "",
                "clip_start": DEFAULT_START,
                "clip_length": DEFAULT_CLIP,
            })
    return tracks


TRACKS: List[Dict[str, Any]] = _build_tracks()


def category_keys() -> List[str]:
    """Ключи тем в том порядке, в каком их показываем."""
    return [item["key"] for item in CATEGORIES]


def category_blocks() -> List[Dict[str, Any]]:
    """Темы с подписями и числом песен — для API и страницы."""
    blocks: List[Dict[str, Any]] = []
    for item in CATEGORIES:
        own = [track for track in TRACKS if track["category"] == item["key"]]
        blocks.append({
            "key": item["key"],
            "label": item["label"],
            "hint": item["hint"],
            "songs": len(own),
            "titles": len({str(track["title"]).casefold() for track in own}),
        })
    return blocks


def playable(track: Dict[str, Any]) -> bool:
    """Играть можно только песню, у которой есть запись."""
    return bool(str(track.get("audio") or "").strip())


def public_track(track: Dict[str, Any]) -> Dict[str, Any]:
    """Песня для отправки клиенту после раунда."""
    return {key: track.get(key, "") for key in FIELDS}


def find_track(track_id: str) -> Dict[str, Any] | None:
    """Песня по идентификатору: регистр не важен."""
    wanted = str(track_id or "").strip().casefold()
    for track in TRACKS:
        if str(track["id"]).casefold() == wanted:
            return track
    return None


def seed_rows() -> List[Dict[str, Any]]:
    """Строки для первичного заполнения таблицы songguess_tracks."""
    return [dict(track) for track in TRACKS]


def validate(rows: Sequence[Dict[str, Any]] | None = None) -> List[str]:
    """Проверка набора: уникальные id, заполненные поля, известная тема.

    Набор годен к игре, только если в теме хватает разных названий на все
    варианты ответа: иначе «обманку» взять негде.
    """
    problems: List[str] = []
    items = [dict(row) for row in rows] if rows is not None else [dict(t) for t in TRACKS]
    seen = set()
    titles: Dict[str, set] = {}
    for item in items:
        track_id = str(item.get("id") or "")
        if not track_id:
            problems.append("песня без идентификатора")
            continue
        if track_id in seen:
            problems.append(f"повторяющийся идентификатор: {track_id}")
        seen.add(track_id)
        category = str(item.get("category") or "")
        if category not in CATEGORY_LABELS:
            problems.append(f"{track_id}: неизвестная тема «{category}»")
        title = str(item.get("title") or "").strip()
        if not title:
            problems.append(f"{track_id}: нет названия")
        if not str(item.get("artist") or "").strip():
            problems.append(f"{track_id}: нет исполнителя")
        year = str(item.get("year") or "")
        if not year.isdigit() or not (1900 <= int(year) <= 2100):
            problems.append(f"{track_id}: непонятный год «{year}»")
        titles.setdefault(category, set()).add(title.casefold())
    for key, label in CATEGORY_LABELS.items():
        count = len(titles.get(key, ()))
        if count < OPTION_COUNT:
            problems.append(f"в теме «{label}» всего {count} разных названий, "
                            f"а для раунда нужно {OPTION_COUNT}")
    return problems


__all__ = [
    "BASE_POINTS",
    "CATEGORIES",
    "CATEGORY_LABELS",
    "DEFAULT_CLIP",
    "DEFAULT_START",
    "DIFFICULTIES",
    "DIFFICULTY_LABELS",
    "DIFFICULTY_SECONDS",
    "FIELDS",
    "HIPHOP_ROWS",
    "OPTION_COUNT",
    "REVEAL_SECONDS",
    "ROUNDS_PER_GAME",
    "ROWS_BY_CATEGORY",
    "SLICE_SECONDS",
    "SPEED_POINTS",
    "TRACKS",
    "category_blocks",
    "category_keys",
    "find_track",
    "playable",
    "public_track",
    "seed_rows",
    "slug",
    "validate",
]
