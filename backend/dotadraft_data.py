# -*- coding: utf-8 -*-
"""Данные игры «322-0»: пул игроков Streamers Battle 13 и герои Dota 2.

Игра — про сборку команды в бюджет: у каждого игрока в таблице есть
стоимость и своя позиция, состав из пяти игроков должен уложиться в
отведённые очки, а каждому игроку выбирается герой.

Что здесь есть:
    * PLAYERS — игроки Streamers Battle 13 с их стоимостью (из таблицы
      владельца сайта; ники — исторические и принадлежат участникам);
    * PLAYER_POSITIONS — своя позиция игрока (1–5) там, где она известна;
    * HEROES — подборка героев Dota 2: русское имя, английское имя, привычная
      позиция (1–5) и оценка силы. Оценки — **игровые**, это не официальная
      статистика и не баланс Valve: они расставлены так, чтобы герои различались
      по силе и по позициям. Позиция — типичная для героя, а не единственная
      возможная;
    * PLAYER_HERO_RATINGS — оценки героев под конкретного игрока (по его матчам
      на Dotabuff). Пока пары нет, берётся обычная оценка героя.

Пул, героев и оценки пар игра берёт из базы (`dotadraft_players`,
`dotadraft_heroes` и `dotadraft_player_heroes`), а этот файл — исходник для её
наполнения (см. backend/seed_dotadraft.py).
Dota 2 и её герои — товарные знаки Valve; игра некоммерческая и не связана
с Valve.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

# Бюджет состава в очках стоимости и размер состава.
BUDGET = 300
SQUAD_SIZE = 5

# Пак драфта: пять игроков и пять героев. Из пака берут ровно одно — игрока
# либо героя, — после чего пак меняется целиком.
PACK_PLAYERS = 5
PACK_HEROES = 5

# Мид — особая позиция: туда берут только игрока дешевле этого порога.
MID_POSITION = 2
MID_COST_LIMIT = 75

# Своя позиция игрока (столбец position в пуле): игра на своей позиции даёт
# надбавку, игра на чужой — заметный минус. Ноль значит «позиция неизвестна»:
# тогда нет ни надбавки, ни минуса.
OWN_POSITION_BONUS = 5.0
OTHER_POSITION_PENALTY = -10.0

# Позиции в Dota: номер → как её называют.
POSITIONS: Tuple[Tuple[int, str], ...] = (
    (1, "Керри"),
    (2, "Мидер"),
    (3, "Офлейнер"),
    (4, "Четвёрка"),
    (5, "Пятёрка"),
)
POSITION_LABELS: Dict[int, str] = dict(POSITIONS)
POSITION_HINTS: Dict[int, str] = {
    1: "сейф-лейн, фарм и урон в лейте",
    2: "центр, темп и размен на карте",
    3: "сложная линия, инициация и живучесть",
    4: "роумер и второй саппорт, темп и станы",
    5: "пятёрка, вижн и прикрытие керри",
}

# Сложность — это бюджет состава: 300, 305 или 310 очков.
DIFFICULTY_BUDGETS: Dict[str, int] = {"hard": 300, "easy": 305, "smurf": 310}
DIFFICULTY_LABELS: Dict[str, str] = {
    "hard": "Хардкор (300)",
    "easy": "Обычная (305)",
    "smurf": "Смёрф (310)",
}
DIFFICULTIES: Tuple[str, ...] = ("hard", "easy", "smurf")

# Турнир: две группы по четыре команды, внутри группы круговая Bo3. Места 1–2
# в группе уходят в верхнюю сетку — там поражение опускает в нижнюю, — а места
# 3–4 начинают с нижней сетки и вылетают после первого поражения в ней. Финал
# нижней сетки и гранд-финал играются Bo5, гранд-финал решающий.
GROUPS = 2
GROUP_SIZE = 4
GROUP_BEST_OF = 3

# Бюджеты чужих составов: у соперников он чуть выше и разный от команды к команде.
OPPONENT_BUDGET_MIN = 300
OPPONENT_BUDGET_MAX = 315

# Раунды плей-офф: ключи те же, что у серий в движке (backend/dotadraft.py).
BRACKET_ROUNDS: Tuple[Dict[str, Any], ...] = (
    {"key": "ub1", "title": "Верхняя сетка, полуфинал", "best_of": 3},
    {"key": "ub2", "title": "Верхняя сетка, финал", "best_of": 3},
    {"key": "lb1", "title": "Нижняя сетка, первый раунд", "best_of": 3},
    {"key": "lb2", "title": "Нижняя сетка, второй раунд", "best_of": 3},
    {"key": "lb3", "title": "Нижняя сетка, полуфинал", "best_of": 3},
    {"key": "lb4", "title": "Финал нижней сетки", "best_of": 5},
    {"key": "gf", "title": "Гранд-финал", "best_of": 5},
)

# Оценка состава: стоимость игрока весит больше, герой — меньше.
PLAYER_WEIGHT = 0.62
HERO_WEIGHT = 0.38

# Надбавки и штрафы за связку «игрок + герой».
STAR_PAIR = 4.0            # и звёздный игрок, и сильный герой
STAR_CARRY_WEAK_HERO = -3.0  # дорогой игрок на слабом герое
STAR_COST = 85             # с какой стоимости игрок считается звездой
STRONG_HERO = 88           # с какой оценки герой считается сильным
WEAK_HERO = 80             # ниже этой оценки герой считается слабым

# Розыгрыш одной игры серии: до победы одной из сторон.
STRENGTH_SCALE = 12.0

# Игроки Streamers Battle 13: (ник, стоимость). Источник — таблица владельца
# сайта; ники сведены к одной строке (пробелы и переводы строк убраны).
PLAYERS: Tuple[Tuple[str, int], ...] = (
    ("DM", 95),
    ("Satanic", 95),
    ("ChodΣX", 91),
    ("mangekyou", 91),
    ("Rincyq", 91),
    ("DarkLord", 90),
    ("Munkushi~", 90),
    ("ssnovv1", 90),
    ("Immersion", 89),
    ("re1bl", 88),
    ("Xakoda", 88),
    ("daxak", 87),
    ("Koma", 87),
    ("nesfeer", 87),
    ("Retsu", 87),
    ("Smiling Knight", 87),
    ("waveformn", 87),
    ("Kiyotaka", 86),
    ("alberkaaaa", 85),
    ("fn", 85),
    ("iseedeadpeople", 85),
    ("Kolya_kaban86", 85),
    ("Egxrdemxn", 84),
    ("iLTW", 84),
    ("Miposhka", 84),
    ("Ramzes", 84),
    ("arteezybastark", 83),
    ("Miyao", 83),
    ("Dyrachyo", 82),
    ("Lens", 82),
    ("Limitless", 82),
    ("Rostislav_999", 80),
    ("Stariy_bog", 80),
    ("WoE", 80),
    ("zipzzzap", 80),
    ("Alohadance", 79),
    ("Cooman", 79),
    ("Kyzko", 79),
    ("Mariachi", 79),
    ("Petushara", 79),
    ("rodjer", 79),
    ("Shishak", 79),
    ("Dizzying", 78),
    ("hina", 78),
    ("Krylat", 78),
    ("Mary_day", 78),
    ("Xanni(Sadovnik)", 78),
    ("xsvampire", 78),
    ("Afterlife", 77),
    ("Avice", 77),
    ("Groom", 77),
    ("Lagoona", 77),
    ("Lowkez", 77),
    ("DkFogas", 76),
    ("Fng", 76),
    ("Rinlar", 76),
    ("Sunlight", 76),
    ("UnderShock", 76),
    ("GGwplanay", 75),
    ("Alagon", 74),
    ("Blindzone", 74),
    ("Solo", 74),
    ("EarthQ", 73),
    ("zxcursed", 72),
    ("633", 70),
    ("Afoninje", 70),
    ("Cenra", 70),
    ("Ez25", 70),
    ("Leviamur", 70),
    ("mrxsmurf", 70),
    ("Unique", 70),
    ("ya_sulen", 70),
    ("judah_xx", 69),
    ("9Pasha", 68),
    ("BLackarchangel", 68),
    ("Haero_x", 68),
    ("reira", 68),
    ("sQreen", 68),
    ("absolut3", 66),
    ("akumaqqe", 66),
    ("Mantis", 66),
    ("Saneking", 66),
    ("Nix", 65),
    ("Qsnake", 65),
    ("Shachlo", 65),
    ("Vovapain", 65),
    ("Hollow Maiden", 64),
    ("hollowmaiden_", 64),
    ("RoMaLL1Ka", 63),
    ("4ce", 61),
    ("chechiga", 61),
    ("goodoq", 60),
    ("Kudes", 60),
    ("macintow", 60),
    ("Just_ns", 57),
    ("Amor", 56),
    ("Dread", 56),
    ("Lesn4ok", 56),
    ("BowBowBow", 55),
    ("TpaBoMaH", 55),
    ("fruktozka", 54),
    ("shattered_doto", 50),
    ("Влад ( брат Ростика )", 50),
    ("eternals", 49),
    ("Serega Pirat", 49),
    ("Grayne", 48),
    ("tankzor", 48),
    ("ybicanoobov", 48),
    ("Goodwin", 45),
    ("RavshanN", 44),
    ("rostikfacekid", 44),
    ("Stray228", 44),
    ("Cake", 42),
    ("good mma", 41),
    ("Inmate", 41),
    ("ddeni", 36),
    ("Ubica", 36),
    ("Sasavot", 35),
    ("By_owl", 33),
    ("Lukawa", 33),
    ("Vasilisa", 33),
    ("Zloba", 33),
    ("LenaGol0vach", 30),
    ("Ян Непомнящий", 30),
    ("misolo3", 28),
    ("Stintik", 28),
    ("iLame", 25),
    ("Korb3n", 25),
    ("Voskresenskii", 25),
    ("zhenya_dota2", 25),
    ("perdeda88", 23),
    ("VoodooSh", 23),
    ("babich", 20),
    ("balod9l", 20),
    ("Recrent", 18),
    ("Cheatbanned", 15),
    ("Ct0m", 15),
    ("Нексюша", 13),
    ("Бебур", 10),
    ("Мелхарукос", 10),
)

# Своя позиция игрока (1–5) — столбец position в пуле. Расставлено там, где
# роль игрока известна; кто не указан, у того позиция считается неизвестной
# (0). Такой игрок не получает ни надбавки за свою позицию, ни минуса за чужую.
# Владелец сайта дополняет словарь, в том числе прямо в базе.
PLAYER_POSITIONS: Dict[str, int] = {
    "Satanic": 1,
    "Ramzes": 1,
    "Dyrachyo": 1,
    "Cooman": 1,
    "iLTW": 2,
    "Afoninje": 2,
    "zxcursed": 2,
    "9Pasha": 3,
    "Afterlife": 3,
    "Alohadance": 4,
    "rodjer": 4,
    "Miposhka": 5,
    "Solo": 5,
    "Fng": 5,
    "Just_ns": 5,
    "Dread": 5,
}

# Герои: (русское имя, английское имя, позиция, оценка).
HEROES: Tuple[Tuple[str, str, int, int], ...] = (
    # Позиция 1 — керри
    ("Антимаг", "Anti-Mage", 1, 86),
    ("Джаггернаут", "Juggernaut", 1, 90),
    ("Фантомка", "Phantom Assassin", 1, 88),
    ("Войд", "Faceless Void", 1, 91),
    ("Спектра", "Spectre", 1, 87),
    ("Террорблейд", "Terrorblade", 1, 89),
    ("Луна", "Luna", 1, 85),
    ("Медуза", "Medusa", 1, 84),
    ("Сларк", "Slark", 1, 84),
    ("Морфлинг", "Morphling", 1, 86),
    ("Король-призрак", "Wraith King", 1, 83),
    ("Свен", "Sven", 1, 85),
    ("Пожиратель", "Lifestealer", 1, 84),
    ("Дровка", "Drow Ranger", 1, 83),
    ("Гирокоптер", "Gyrocopter", 1, 86),
    ("Урса", "Ursa", 1, 85),
    ("Манки Кинг", "Monkey King", 1, 84),
    ("Нага", "Naga Siren", 1, 81),
    # Позиция 2 — мид
    ("Инвокер", "Invoker", 2, 92),
    ("Шторм", "Storm Spirit", 2, 89),
    ("Пак", "Puck", 2, 89),
    ("Квопа", "Queen of Pain", 2, 88),
    ("Эмбер", "Ember Spirit", 2, 88),
    ("Войд Спирит", "Void Spirit", 2, 90),
    ("ТА", "Templar Assassin", 2, 87),
    ("Шадоу Финд", "Shadow Fiend", 2, 87),
    ("Лина", "Lina", 2, 86),
    ("Кунка", "Kunkka", 2, 86),
    ("Снайпер", "Sniper", 2, 85),
    ("Тини", "Tiny", 2, 85),
    ("ОД", "Outworld Destroyer", 2, 85),
    ("Пангольер", "Pangolier", 2, 85),
    ("Вайпер", "Viper", 2, 84),
    ("Алхимик", "Alchemist", 2, 84),
    ("Зевс", "Zeus", 2, 84),
    ("Тинкер", "Tinker", 2, 84),
    ("Хускар", "Huskar", 2, 83),
    ("Лешрак", "Leshrac", 2, 83),
    ("Дез Пропет", "Death Prophet", 2, 83),
    ("Виндрейнджер", "Windranger", 2, 83),
    ("Пугна", "Pugna", 2, 82),
    ("Мипо", "Meepo", 2, 80),
    # Позиция 3 — офлейн
    ("Магнус", "Magnus", 3, 93),
    ("Марс", "Mars", 3, 92),
    ("Тайдхантер", "Tidehunter", 3, 90),
    ("Дум", "Doom", 3, 89),
    ("Бистмастер", "Beastmaster", 3, 88),
    ("Сэнд Кинг", "Sand King", 3, 88),
    ("Дарк Сир", "Dark Seer", 3, 87),
    ("Андерлорд", "Underlord", 3, 86),
    ("Центавр", "Centaur Warrunner", 3, 86),
    ("Энигма", "Enigma", 3, 86),
    ("Бристлбэк", "Bristleback", 3, 85),
    ("Акс", "Axe", 3, 85),
    ("Брюмастер", "Brewmaster", 3, 85),
    ("Тимберсо", "Timbersaw", 3, 84),
    ("Легионка", "Legion Commander", 3, 84),
    ("Слардар", "Slardar", 3, 84),
    ("Праймал", "Primal Beast", 3, 84),
    ("Ночной", "Night Stalker", 3, 83),
    ("Донбрейкер", "Dawnbreaker", 3, 83),
    ("Клокверк", "Clockwerk", 3, 83),
    ("Абаддон", "Abaddon", 3, 82),
    ("Элдер Титан", "Elder Titan", 3, 82),
    # Позиция 4 — четвёрка
    ("Рубик", "Rubick", 4, 92),
    ("Эрс Спирит", "Earth Spirit", 4, 90),
    ("Пудж", "Pudge", 4, 88),
    ("Туск", "Tusk", 4, 87),
    ("Снэпфайр", "Snapfire", 4, 87),
    ("Мирана", "Mirana", 4, 86),
    ("Худвинк", "Hoodwink", 4, 86),
    ("Марси", "Marci", 4, 86),
    ("Гримстроук", "Grimstroke", 4, 85),
    ("Никс", "Nyx Assassin", 4, 85),
    ("Феникс", "Phoenix", 4, 85),
    ("Баунти", "Bounty Hunter", 4, 84),
    ("Спирит Брейкер", "Spirit Breaker", 4, 84),
    ("Дизраптор", "Disruptor", 4, 84),
    ("Шадоу Демон", "Shadow Demon", 4, 83),
    ("Венга", "Vengeful Spirit", 4, 83),
    ("Энчантресса", "Enchantress", 4, 82),
    ("Визаж", "Visage", 4, 82),
    ("Рики", "Riki", 4, 82),
    ("Скайрат", "Skywrath Mage", 4, 82),
    ("Течис", "Techies", 4, 80),
    # Позиция 5 — пятёрка
    ("Ио", "Io", 5, 87),
    ("Чен", "Chen", 5, 86),
    ("Шаман", "Shadow Shaman", 5, 86),
    ("Лич", "Lich", 5, 85),
    ("Варлок", "Warlock", 5, 85),
    ("Дазл", "Dazzle", 5, 85),
    ("ВД", "Witch Doctor", 5, 84),
    ("Оракл", "Oracle", 5, 84),
    ("Анданнг", "Undying", 5, 84),
    ("ЦМ", "Crystal Maiden", 5, 83),
    ("Трент", "Treant Protector", 5, 83),
    ("АА", "Ancient Apparition", 5, 83),
    ("Котл", "Keeper of the Light", 5, 82),
    ("Бейн", "Bane", 5, 82),
    ("Сайленсер", "Silencer", 5, 82),
    ("Джакиро", "Jakiro", 5, 81),
    ("Огр", "Ogre Magi", 5, 80),
    ("Виверна", "Winter Wyvern", 5, 81),
)

# Оценки героев под конкретного игрока: (ник игрока, английское имя героя,
# оценка). Так оценка героя зависит от того, насколько игрок на нём играет —
# источник владельца сайта, матчи игрока на герое на Dotabuff. Пустой набор
# значит «пар нет»: тогда используется обычная оценка героя из HEROES.
PLAYER_HERO_RATINGS: Tuple[Tuple[str, str, int], ...] = ()


def slug(text: str) -> str:
    """Идентификатор из ника или имени: латиница/цифры, остальное — дефис."""
    table = str.maketrans({
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh",
        "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
        "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "ts",
        "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu",
        "я": "ya", "σ": "s",
    })
    lowered = str(text).lower().translate(table)
    keep = [char if (char.isalnum() and char.isascii()) else "-" for char in lowered]
    slug_text = "".join(keep)
    while "--" in slug_text:
        slug_text = slug_text.replace("--", "-")
    return slug_text.strip("-") or "player"


def player_rows() -> List[Dict[str, Any]]:
    """Пул игроков: идентификатор, ник, стоимость и своя позиция."""
    rows: List[Dict[str, Any]] = []
    used: Dict[str, int] = {}
    for nickname, cost in PLAYERS:
        base = slug(nickname)
        index = used.get(base, 0) + 1
        used[base] = index
        rows.append({
            "id": base if index == 1 else f"{base}-{index}",
            "nickname": str(nickname),
            "cost": int(cost),
            "position": int(PLAYER_POSITIONS.get(str(nickname), 0)),
        })
    return rows


def hero_rows() -> List[Dict[str, Any]]:
    """Подборка героев: идентификатор, имена, позиция и оценка."""
    rows: List[Dict[str, Any]] = []
    used: Dict[str, int] = {}
    for name, name_en, position, rating in HEROES:
        base = slug(name_en)
        index = used.get(base, 0) + 1
        used[base] = index
        rows.append({
            "id": base if index == 1 else f"{base}-{index}",
            "name": str(name),
            "name_en": str(name_en),
            "position": int(position),
            "rating": int(rating),
        })
    return rows


def validate_players(rows: Any = None) -> List[str]:
    """Проверка пула: уникальные id, заполненные ники, стоимость и позиция."""
    problems: List[str] = []
    seen = set()
    for row in (list(rows) if rows is not None else player_rows()):
        player_id = str(row.get("id") or "")
        if not player_id:
            problems.append("игрок без идентификатора")
            continue
        if player_id in seen:
            problems.append(f"повторяющийся идентификатор игрока: {player_id}")
        seen.add(player_id)
        if not str(row.get("nickname") or "").strip():
            problems.append(f"{player_id}: нет ника")
        try:
            cost = int(row.get("cost") or 0)
        except (TypeError, ValueError):
            problems.append(f"{player_id}: стоимость не число")
            continue
        if not 1 <= cost <= 200:
            problems.append(f"{player_id}: странная стоимость ({cost})")
        try:
            position = int(row.get("position") or 0)
        except (TypeError, ValueError):
            problems.append(f"{player_id}: позиция не число")
            continue
        if position and position not in {value for value, _ in POSITIONS}:
            problems.append(f"{player_id}: неизвестная своя позиция ({position})")
    return problems


def validate_heroes(rows: Any = None) -> List[str]:
    """Проверка героев: уникальные id, известная позиция, оценка в границах."""
    problems: List[str] = []
    seen = set()
    positions = {position for position, _ in POSITIONS}
    for row in (list(rows) if rows is not None else hero_rows()):
        hero_id = str(row.get("id") or "")
        if not hero_id:
            problems.append("герой без идентификатора")
            continue
        if hero_id in seen:
            problems.append(f"повторяющийся идентификатор героя: {hero_id}")
        seen.add(hero_id)
        for field, label in (("name", "русского имени"), ("name_en", "английского имени")):
            if not str(row.get(field) or "").strip():
                problems.append(f"{hero_id}: нет {label}")
        try:
            position = int(row.get("position") or 0)
        except (TypeError, ValueError):
            problems.append(f"{hero_id}: позиция не число")
            continue
        if position not in positions:
            problems.append(f"{hero_id}: неизвестная позиция ({position})")
        try:
            rating = int(row.get("rating") or 0)
        except (TypeError, ValueError):
            problems.append(f"{hero_id}: оценка не число")
            continue
        if not 40 <= rating <= 100:
            problems.append(f"{hero_id}: оценка вне границ ({rating})")
    return problems


def player_hero_rows() -> List[Dict[str, Any]]:
    """Оценки героев под игроков: пара «игрок + герой» и её оценка."""
    players = {row["nickname"]: row["id"] for row in player_rows()}
    heroes = {row["name_en"]: row["id"] for row in hero_rows()}
    rows: List[Dict[str, Any]] = []
    for nickname, hero_name, rating in PLAYER_HERO_RATINGS:
        player_id = players.get(str(nickname))
        hero_id = heroes.get(str(hero_name))
        if not player_id or not hero_id:
            continue
        rows.append({
            "player_id": player_id,
            "hero_id": hero_id,
            "rating": int(rating),
        })
    return rows


def validate_player_heroes(rows: Any = None) -> List[str]:
    """Проверка пар: ники и герои должны быть из своих наборов."""
    problems: List[str] = []
    players = {row["nickname"] for row in player_rows()}
    heroes = {row["name_en"] for row in hero_rows()}
    for row in (list(rows) if rows is not None else player_hero_rows()):
        nickname = str(row.get("nickname") or "")
        hero_name = str(row.get("hero_name") or "")
        if rows is None and (nickname not in players or hero_name not in heroes):
            problems.append(f"пара не из пула: {nickname} + {hero_name}")
    return problems


def validate() -> List[str]:
    """Проверка всего набора сразу."""
    problems = validate_players() + validate_heroes() + validate_player_heroes()
    for position in (position for position, _ in POSITIONS):
        count = len([1 for hero in hero_rows() if hero["position"] == position])
        if count < 3:
            problems.append(f"позиция {position}: героев мало ({count})")
    return problems


__all__ = [
    "BRACKET_ROUNDS",
    "BUDGET",
    "DIFFICULTIES",
    "DIFFICULTY_BUDGETS",
    "DIFFICULTY_LABELS",
    "GROUPS",
    "GROUP_BEST_OF",
    "GROUP_SIZE",
    "HEROES",
    "HERO_WEIGHT",
    "MID_COST_LIMIT",
    "MID_POSITION",
    "OPPONENT_BUDGET_MAX",
    "OPPONENT_BUDGET_MIN",
    "OTHER_POSITION_PENALTY",
    "OWN_POSITION_BONUS",
    "PACK_HEROES",
    "PACK_PLAYERS",
    "PLAYERS",
    "PLAYER_HERO_RATINGS",
    "PLAYER_POSITIONS",
    "PLAYER_WEIGHT",
    "POSITIONS",
    "POSITION_HINTS",
    "POSITION_LABELS",
    "SQUAD_SIZE",
    "STAR_CARRY_WEAK_HERO",
    "STAR_COST",
    "STAR_PAIR",
    "STRENGTH_SCALE",
    "STRONG_HERO",
    "WEAK_HERO",
    "hero_rows",
    "player_hero_rows",
    "player_rows",
    "slug",
    "validate",
]
