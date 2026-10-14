# -*- coding: utf-8 -*-
"""Данные для дуэли «Narutodle»: персонажи, графы сравнения и цвета аватаров.

Этот файл — исходный набор для первичного заполнения базы: при запуске сервер
проверяет таблицу `narutodle_characters` и, если она пуста, заливает данные
отсюда (см. backend/seed_narutodle.py). Дальше источник правды — база:
персонажей можно править и добавлять прямо в ней, а изображения — привязывать
к строкам.

Таблица персонажей читается сверху вниз по FIELDS; неизвестные или спорные
значения помечаются UNKNOWN и по этой графе догадка считается несовпавшей
(кроме случая, когда неизвестно у обоих). Тексты не переписывались ни из каких
источников — это короткие справочные значения: деревня, клан, стихии и так далее.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

UNKNOWN = "неизвестно"

# Графы сравнения: подпись показывается в шапке таблицы попыток.
ATTRIBUTES: List[Dict[str, Any]] = [
    {"key": "gender", "label": "Пол"},
    {"key": "village", "label": "Деревня"},
    {"key": "clan", "label": "Клан"},
    {"key": "nature", "label": "Стихии", "multi": True},
    {"key": "kekkei", "label": "Кеккей генкай"},
    {"key": "jinchuriki", "label": "Джинчурики"},
    {"key": "debut", "label": "Первая арка"},
]

MALE = "мужской"
FEMALE = "женский"

KONOHA = "Коноха"
SUNA = "Суна"
KIRI = "Кири"
KUMO = "Кумо"
IWA = "Ива"
OTO = "Ото"
AME = "Аме"
TAKI = "Таки"
KUSA = "Куса"
UZUSHIO = "Узушио"
NO_VILLAGE = "нет деревни"

# Арки сюжета по порядку. «Первая арка» — это место персонажа в истории, а не
# серия («Классика»/«Шиппуден»): границы взяты по манге — Naruto главы 1–699 и
# Boruto: Naruto Next Generations. Списком ARCS проверяются данные.
WAVES = "Страна Волн"
CHUNIN = "Экзамен на чунина"
KONOHA_CRUSH = "Вторжение в Коноху"
TSUNADE = "Поиск Цунаде"
RETRIEVAL = "Погоня за Саске"
KAZEKAGE = "Спасение Гаары"
REUNION = "Воссоединение с Саске"
AKATSUKI = "Хидан и Какудзу"
ITACHI = "Погоня за Итачи"
PAIN = "Вторжение Пейна"
KAGE = "Совет пяти Каге"
WAR = "Четвёртая мировая война"
KAGUYA = "Финал: Кагуя"
BORUTO = "Боруто"

ARCS: List[str] = [
    WAVES, CHUNIN, KONOHA_CRUSH, TSUNADE, RETRIEVAL, KAZEKAGE, REUNION,
    AKATSUKI, ITACHI, PAIN, KAGE, WAR, KAGUYA, BORUTO,
]

NO_CLAN = "нет клана"
NO_KEKKEI = "нет"
NO_BEAST = "нет"

# Цвет аватара — по родной деревне. Аватар рисует страница игры: инициалы
# на цветном квадрате; свою картинку можно подставить в поле image.
VILLAGE_COLORS: Dict[str, str] = {
    KONOHA: "#3f7d3a",
    SUNA: "#c2912c",
    KIRI: "#2f7fa8",
    KUMO: "#b0661f",
    IWA: "#6b6f74",
    OTO: "#7a4b9a",
    AME: "#4b6b8a",
    TAKI: "#2f8f7a",
    KUSA: "#6f8f2f",
    UZUSHIO: "#b8455f",
    NO_VILLAGE: "#6d5a8f",
    UNKNOWN: "#7a6a5f",
}
DEFAULT_COLOR = "#8a5a3c"

FIELDS = ("name", "gender", "village", "clan", "nature", "kekkei",
          "jinchuriki", "debut")

# Портрет персонажа отдаётся отдельным адресом: в каталоге — только ссылка.
PORTRAIT_PATH = "/api/games/narutodle/portrait/%s"

# name, gender, village, clan, nature, kekkei, jinchuriki, debut (арка)
ROWS: List[tuple] = [
    # --- Коноха: команда 7 и наставники
    ("Наруто Узумаки", MALE, KONOHA, "Узумаки", ["Ветер"], NO_KEKKEI, "Девятихвостый", WAVES),
    ("Саске Учиха", MALE, KONOHA, "Учиха", ["Огонь", "Молния"], "Шаринган", NO_BEAST, WAVES),
    ("Сакура Харуно", FEMALE, KONOHA, NO_CLAN, ["Земля", "Вода"], NO_KEKKEI, NO_BEAST, WAVES),
    ("Какаши Хатаке", MALE, KONOHA, NO_CLAN, ["Молния"], "Шаринган", NO_BEAST, WAVES),
    ("Ямато", MALE, KONOHA, NO_CLAN, ["Земля", "Вода"], "Деревянный выпуск", NO_BEAST, REUNION),
    ("Сай", MALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, REUNION),
    ("Кабуто Якуши", MALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),

    # --- Коноха: сверстники и выпуск
    ("Хината Хьюга", FEMALE, KONOHA, "Хьюга", [UNKNOWN], "Бьякуган", NO_BEAST, CHUNIN),
    ("Неджи Хьюга", MALE, KONOHA, "Хьюга", [UNKNOWN], "Бьякуган", NO_BEAST, CHUNIN),
    ("Ханаби Хьюга", FEMALE, KONOHA, "Хьюга", [UNKNOWN], "Бьякуган", NO_BEAST, CHUNIN),
    ("Хиаши Хьюга", MALE, KONOHA, "Хьюга", [UNKNOWN], "Бьякуган", NO_BEAST, CHUNIN),
    ("Рок Ли", MALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Тентен", FEMALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Майто Гай", MALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Шикамару Нара", MALE, KONOHA, "Нара", [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Тёджи Акимичи", MALE, KONOHA, "Акимичи", [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Ино Яманака", FEMALE, KONOHA, "Яманака", [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Киба Инузука", MALE, KONOHA, "Инузука", [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Шино Абураме", MALE, KONOHA, "Абураме", [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),

    # --- Коноха: кланы и старшее поколение
    ("Шикаку Нара", MALE, KONOHA, "Нара", [UNKNOWN], NO_KEKKEI, NO_BEAST, KONOHA_CRUSH),
    ("Тёдза Акимичи", MALE, KONOHA, "Акимичи", [UNKNOWN], NO_KEKKEI, NO_BEAST, KONOHA_CRUSH),
    ("Иноичи Яманака", MALE, KONOHA, "Яманака", [UNKNOWN], NO_KEKKEI, NO_BEAST, KONOHA_CRUSH),
    ("Цуме Инузука", FEMALE, KONOHA, "Инузука", [UNKNOWN], NO_KEKKEI, NO_BEAST, KONOHA_CRUSH),
    ("Шиби Абураме", MALE, KONOHA, "Абураме", [UNKNOWN], NO_KEKKEI, NO_BEAST, KONOHA_CRUSH),
    ("Хирузен Сарутоби", MALE, KONOHA, "Сарутоби", ["Огонь", "Земля"], NO_KEKKEI, NO_BEAST, WAVES),
    ("Асума Сарутоби", MALE, KONOHA, "Сарутоби", [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Конахамару Сарутоби", MALE, KONOHA, "Сарутоби", [UNKNOWN], NO_KEKKEI, NO_BEAST, WAVES),
    ("Куренай Юхи", FEMALE, KONOHA, "Юхи", [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Шизуне", FEMALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, TSUNADE),
    ("Митараши Анко", FEMALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Умино Ирука", MALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, WAVES),
    ("Джирайя", MALE, KONOHA, NO_CLAN, ["Огонь"], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Цунаде", FEMALE, KONOHA, "Сенджу", [UNKNOWN], NO_KEKKEI, NO_BEAST, TSUNADE),
    ("Орочимару", MALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Минато Намиказе", MALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, RETRIEVAL),
    ("Хатаке Сакумо", MALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, PAIN),
    ("Гекко Хаяте", MALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Дан Като", FEMALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, TSUNADE),
    ("Рин Нохара", FEMALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, "Трёххвостый", RETRIEVAL),
    ("Шимура Данзо", MALE, KONOHA, "Шимура", ["Ветер"], "Шаринган", NO_BEAST, REUNION),

    # --- Коноха: Сенджу, Учиха, Узумаки
    ("Хаширама Сенджу", MALE, KONOHA, "Сенджу", ["Земля", "Вода"], "Деревянный выпуск", NO_BEAST, KONOHA_CRUSH),
    ("Тобирама Сенджу", MALE, KONOHA, "Сенджу", ["Вода"], NO_KEKKEI, NO_BEAST, KONOHA_CRUSH),
    ("Итачи Учиха", MALE, KONOHA, "Учиха", ["Огонь", "Вода"], "Шаринган", NO_BEAST, TSUNADE),
    ("Мадара Учиха", MALE, KONOHA, "Учиха", ["Огонь"], "Риннеган", NO_BEAST, PAIN),
    ("Изуна Учиха", MALE, KONOHA, "Учиха", ["Огонь"], "Шаринган", NO_BEAST, ITACHI),
    ("Обито Учиха", MALE, KONOHA, "Учиха", ["Огонь"], "Шаринган", NO_BEAST, RETRIEVAL),
    ("Шисуи Учиха", MALE, KONOHA, "Учиха", ["Огонь"], "Шаринган", NO_BEAST, KAGE),
    ("Фугаку Учиха", MALE, KONOHA, "Учиха", ["Огонь"], "Шаринган", NO_BEAST, TSUNADE),
    ("Микото Учиха", FEMALE, KONOHA, "Учиха", [UNKNOWN], "Шаринган", NO_BEAST, TSUNADE),
    ("Кушина Узумаки", FEMALE, UZUSHIO, "Узумаки", [UNKNOWN], NO_KEKKEI, "Девятихвостый", PAIN),
    ("Мито Узумаки", FEMALE, UZUSHIO, "Узумаки", [UNKNOWN], NO_KEKKEI, "Девятихвостый", WAR),

    # --- Суна
    ("Гаара", MALE, SUNA, NO_CLAN, ["Земля", "Ветер"], NO_KEKKEI, "Однохвостый", CHUNIN),
    ("Темари", FEMALE, SUNA, NO_CLAN, ["Ветер"], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Канкуро", MALE, SUNA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Баки", MALE, SUNA, NO_CLAN, ["Ветер"], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Раса", MALE, SUNA, NO_CLAN, ["Земля"], "Магнитный выпуск", NO_BEAST, CHUNIN),
    ("Карура", FEMALE, SUNA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, WAR),
    ("Чиё", FEMALE, SUNA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KAZEKAGE),
    ("Сасори", MALE, SUNA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KAZEKAGE),

    # --- Кири
    ("Забуза Момоти", MALE, KIRI, NO_CLAN, ["Вода"], NO_KEKKEI, NO_BEAST, WAVES),
    ("Хаку", MALE, KIRI, NO_CLAN, ["Вода", "Ветер"], "Ледяной выпуск", NO_BEAST, WAVES),
    ("Кисаме Хосигаки", MALE, KIRI, "Хосигаки", ["Вода"], NO_KEKKEI, NO_BEAST, TSUNADE),
    ("Кимимаро Кагуя", MALE, KIRI, "Кагуя", [UNKNOWN], "Шикоцумьяку", NO_BEAST, RETRIEVAL),
    ("Мэй Тэруми", FEMALE, KIRI, NO_CLAN, ["Вода", "Огонь"], "Кипящий выпуск", NO_BEAST, KAGE),
    ("Ао", MALE, KIRI, NO_CLAN, ["Вода"], "Бьякуган", NO_BEAST, KAGE),
    ("Тёдзиро", MALE, KIRI, NO_CLAN, ["Вода"], NO_KEKKEI, NO_BEAST, KAGE),
    ("Суйгецу Хозуки", MALE, KIRI, "Хозуки", ["Вода"], NO_KEKKEI, NO_BEAST, ITACHI),
    ("Мангетсу Хозуки", MALE, KIRI, "Хозуки", ["Вода"], NO_KEKKEI, NO_BEAST, WAR),
    ("Ягура Каратачи", MALE, KIRI, NO_CLAN, [UNKNOWN], NO_KEKKEI, "Трёххвостый", KAGE),
    ("Утаката", MALE, KIRI, NO_CLAN, [UNKNOWN], NO_KEKKEI, "Шестихвостый", WAR),

    # --- Кумо
    ("Киллер Би", MALE, KUMO, NO_CLAN, ["Молния"], NO_KEKKEI, "Восьмихвостый", ITACHI),
    ("Эй", MALE, KUMO, NO_CLAN, ["Молния"], NO_KEKKEI, NO_BEAST, PAIN),
    ("Югито Нии", FEMALE, KUMO, NO_CLAN, [UNKNOWN], NO_KEKKEI, "Двухвостый", AKATSUKI),
    ("Мабуи", MALE, KUMO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, PAIN),
    ("Омои", MALE, KUMO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, PAIN),
    ("Каруи", FEMALE, KUMO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, PAIN),

    # --- Ива
    ("Дейдара", MALE, IWA, NO_CLAN, ["Земля"], "Взрывной выпуск", NO_BEAST, KAZEKAGE),
    ("Ооноки", MALE, IWA, NO_CLAN, ["Земля"], NO_KEKKEI, NO_BEAST, KAGE),
    ("Куротсучи", FEMALE, IWA, NO_CLAN, ["Земля", "Огонь"], "Лавовый выпуск", NO_BEAST, KAGE),
    ("Роши", MALE, IWA, NO_CLAN, ["Земля"], NO_KEKKEI, "Четырёххвостый", ITACHI),
    ("Хан", MALE, IWA, NO_CLAN, [UNKNOWN], NO_KEKKEI, "Пятихвостый", WAR),

    # --- Ото: подручные Орочимару
    ("Таюя", FEMALE, OTO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Дзюго", MALE, OTO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, ITACHI),
    ("Карин", FEMALE, KUSA, "Узумаки", [UNKNOWN], NO_KEKKEI, NO_BEAST, ITACHI),
    ("Кидомару", MALE, OTO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Сакон", MALE, OTO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Джиробо", MALE, OTO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Заку Абуми", MALE, OTO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Досу Кинута", MALE, OTO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),

    # --- Аме, Таки, прочие
    ("Нагато", MALE, AME, "Узумаки", [UNKNOWN], "Риннеган", NO_BEAST, PAIN),
    ("Конан", FEMALE, AME, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, ITACHI),
    ("Яхико", MALE, AME, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, PAIN),
    ("Какузу", MALE, TAKI, NO_CLAN, ["Земля"], NO_KEKKEI, NO_BEAST, AKATSUKI),
    ("Фу", FEMALE, TAKI, NO_CLAN, [UNKNOWN], NO_KEKKEI, "Семихвостый", WAR),
    ("Хидан", MALE, UNKNOWN, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, AKATSUKI),
    ("Зецу", MALE, NO_VILLAGE, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, RETRIEVAL),

    # --- Ооцуцуки и поколение Боруто
    ("Кагуя Ооцуцуки", FEMALE, NO_VILLAGE, "Ооцуцуки", [UNKNOWN], "Бьякуган", NO_BEAST, KAGUYA),
    ("Хагаромо Ооцуцуки", MALE, NO_VILLAGE, "Ооцуцуки", [UNKNOWN], "Риннеган", "Десятихвостый", WAR),
    ("Хамура Ооцуцуки", MALE, NO_VILLAGE, "Ооцуцуки", [UNKNOWN], "Бьякуган", NO_BEAST, WAR),
    ("Момошики Ооцуцуки", MALE, NO_VILLAGE, "Ооцуцуки", [UNKNOWN], "Бьякуган", NO_BEAST, BORUTO),
    ("Урашики Ооцуцуки", MALE, NO_VILLAGE, "Ооцуцуки", [UNKNOWN], NO_KEKKEI, NO_BEAST, BORUTO),
    ("Ишики Ооцуцуки", MALE, NO_VILLAGE, "Ооцуцуки", [UNKNOWN], NO_KEKKEI, NO_BEAST, BORUTO),
    ("Каваки", MALE, NO_VILLAGE, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, BORUTO),
    ("Боруто Узумаки", MALE, KONOHA, "Узумаки", ["Ветер", "Молния"], NO_KEKKEI, NO_BEAST, BORUTO),
    ("Сарада Учиха", FEMALE, KONOHA, "Учиха", ["Огонь", "Молния"], "Шаринган", NO_BEAST, BORUTO),
    ("Мицуки", MALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, BORUTO),
    ("Химавари Узумаки", FEMALE, KONOHA, "Узумаки", [UNKNOWN], "Бьякуган", NO_BEAST, BORUTO),
    ("Чёчо Акимичи", FEMALE, KONOHA, "Акимичи", [UNKNOWN], NO_KEKKEI, NO_BEAST, BORUTO),
    ("Шикадай Нара", MALE, KONOHA, "Нара", [UNKNOWN], NO_KEKKEI, NO_BEAST, BORUTO),
]

CHARACTERS: List[Dict[str, Any]] = [dict(zip(FIELDS, row)) for row in ROWS]

# Поиск по имени: регистр и лишние пробелы не важны.
INDEX = {character["name"].casefold(): character for character in CHARACTERS}


def find_character(name: str) -> Optional[Dict[str, Any]]:
    """Возвращает персонажа по названию или None, если такого в наборе нет."""
    return INDEX.get((name or "").strip().casefold())


def character_names() -> List[str]:
    """Названия для подсказки в поле ввода — без скрытых свойств."""
    return [character["name"] for character in CHARACTERS]


def village_color(village: str) -> str:
    """Цвет аватара для деревни; для незнакомых названий — нейтральный."""
    return VILLAGE_COLORS.get(village, DEFAULT_COLOR)


def public_character(character: Dict[str, Any]) -> Dict[str, Any]:
    """Персонаж для отправки клиенту (после конца раунда)."""
    return {key: character[key] for key in FIELDS}


def portrait_ref(character: Dict[str, Any]) -> str:
    """Куда странице взять портрет персонажа.

    Картинка может лежать прямо в базе строкой `data:image/...` — тогда в ответе
    стоит ссылка на отдельный адрес API: сам base64 в каталоге весит мегабайты,
    и через туннель страница не успевала его получить. Если в базе путь или
    ссылка, отдаём как есть — файл кладёт владелец сайта.
    """
    image = str(character.get("image") or "")
    if not image:
        return ""
    if image.startswith("data:"):
        return PORTRAIT_PATH % character.get("id")
    return image


def attribute_list() -> List[Dict[str, Any]]:
    """Описание граф сравнения — страница строит по нему шапку таблицы."""
    return [dict(attribute) for attribute in ATTRIBUTES]


def seed_rows() -> List[Dict[str, Any]]:
    """Строки для первичного заполнения таблицы narutodle_characters."""
    return [
        {**character, "color": village_color(character["village"]), "image": ""}
        for character in CHARACTERS
    ]


__all__ = [
    "ARCS",
    "ATTRIBUTES",
    "CHARACTERS",
    "FIELDS",
    "PORTRAIT_PATH",
    "ROWS",
    "UNKNOWN",
    "VILLAGE_COLORS",
    "attribute_list",
    "character_names",
    "find_character",
    "portrait_ref",
    "public_character",
    "seed_rows",
    "village_color",
]
