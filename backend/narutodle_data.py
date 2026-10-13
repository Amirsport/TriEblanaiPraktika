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
    {"key": "debut", "label": "Первое появление"},
    {"key": "status", "label": "Статус"},
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

KLASSIKA = "Классика"
SHIPPUDEN = "Шиппуден"
BORUTO = "Боруто"

NO_CLAN = "нет клана"
NO_KEKKEI = "нет"
NO_BEAST = "нет"

ALIVE = "жив"
DEAD = "погиб"

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
          "jinchuriki", "debut", "status")

# name, gender, village, clan, nature, kekkei, jinchuriki, debut, status
ROWS: List[tuple] = [
    # --- Коноха: команда 7 и наставники
    ("Наруто Узумаки", MALE, KONOHA, "Узумаки", ["Ветер"], NO_KEKKEI, "Девятихвостый", KLASSIKA, ALIVE),
    ("Саске Учиха", MALE, KONOHA, "Учиха", ["Огонь", "Молния"], "Шаринган", NO_BEAST, KLASSIKA, ALIVE),
    ("Сакура Харуно", FEMALE, KONOHA, NO_CLAN, ["Земля", "Вода"], NO_KEKKEI, NO_BEAST, KLASSIKA, ALIVE),
    ("Какаши Хатаке", MALE, KONOHA, NO_CLAN, ["Молния"], "Шаринган", NO_BEAST, KLASSIKA, ALIVE),
    ("Ямато", MALE, KONOHA, NO_CLAN, ["Земля", "Вода"], "Деревянный выпуск", NO_BEAST, KLASSIKA, ALIVE),
    ("Сай", MALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, ALIVE),
    ("Кабуто Якуши", MALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, ALIVE),

    # --- Коноха: сверстники и выпуск
    ("Хината Хьюга", FEMALE, KONOHA, "Хьюга", [UNKNOWN], "Бьякуган", NO_BEAST, KLASSIKA, ALIVE),
    ("Неджи Хьюга", MALE, KONOHA, "Хьюга", [UNKNOWN], "Бьякуган", NO_BEAST, KLASSIKA, DEAD),
    ("Ханаби Хьюга", FEMALE, KONOHA, "Хьюга", [UNKNOWN], "Бьякуган", NO_BEAST, KLASSIKA, ALIVE),
    ("Хиаши Хьюга", MALE, KONOHA, "Хьюга", [UNKNOWN], "Бьякуган", NO_BEAST, KLASSIKA, ALIVE),
    ("Рок Ли", MALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, ALIVE),
    ("Тентен", FEMALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, ALIVE),
    ("Майто Гай", MALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, ALIVE),
    ("Шикамару Нара", MALE, KONOHA, "Нара", [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, ALIVE),
    ("Тёджи Акимичи", MALE, KONOHA, "Акимичи", [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, ALIVE),
    ("Ино Яманака", FEMALE, KONOHA, "Яманака", [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, ALIVE),
    ("Киба Инузука", MALE, KONOHA, "Инузука", [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, ALIVE),
    ("Шино Абураме", MALE, KONOHA, "Абураме", [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, ALIVE),

    # --- Коноха: кланы и старшее поколение
    ("Шикаку Нара", MALE, KONOHA, "Нара", [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, DEAD),
    ("Тёдза Акимичи", MALE, KONOHA, "Акимичи", [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, ALIVE),
    ("Иноичи Яманака", MALE, KONOHA, "Яманака", [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, ALIVE),
    ("Цуме Инузука", FEMALE, KONOHA, "Инузука", [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, ALIVE),
    ("Шиби Абураме", MALE, KONOHA, "Абураме", [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, ALIVE),
    ("Хирузен Сарутоби", MALE, KONOHA, "Сарутоби", ["Огонь", "Земля"], NO_KEKKEI, NO_BEAST, KLASSIKA, DEAD),
    ("Асума Сарутоби", MALE, KONOHA, "Сарутоби", [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, DEAD),
    ("Конахамару Сарутоби", MALE, KONOHA, "Сарутоби", [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, ALIVE),
    ("Куренай Юхи", FEMALE, KONOHA, "Юхи", [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, ALIVE),
    ("Шизуне", FEMALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, ALIVE),
    ("Митараши Анко", FEMALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, ALIVE),
    ("Умино Ирука", MALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, ALIVE),
    ("Джирайя", MALE, KONOHA, NO_CLAN, ["Огонь"], NO_KEKKEI, NO_BEAST, KLASSIKA, DEAD),
    ("Цунаде", FEMALE, KONOHA, "Сенджу", [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, ALIVE),
    ("Орочимару", MALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, ALIVE),
    ("Минато Намиказе", MALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, DEAD),
    ("Хатаке Сакумо", MALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, DEAD),
    ("Гекко Хаяте", MALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, DEAD),
    ("Дан Като", FEMALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, DEAD),
    ("Рин Нохара", FEMALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, "Трёххвостый", KLASSIKA, DEAD),
    ("Шимура Данзо", MALE, KONOHA, "Шимура", ["Ветер"], "Шаринган", NO_BEAST, KLASSIKA, DEAD),

    # --- Коноха: Сенджу, Учиха, Узумаки
    ("Хаширама Сенджу", MALE, KONOHA, "Сенджу", ["Земля", "Вода"], "Деревянный выпуск", NO_BEAST, KLASSIKA, DEAD),
    ("Тобирама Сенджу", MALE, KONOHA, "Сенджу", ["Вода"], NO_KEKKEI, NO_BEAST, KLASSIKA, DEAD),
    ("Итачи Учиха", MALE, KONOHA, "Учиха", ["Огонь", "Вода"], "Шаринган", NO_BEAST, KLASSIKA, DEAD),
    ("Мадара Учиха", MALE, KONOHA, "Учиха", ["Огонь"], "Риннеган", NO_BEAST, KLASSIKA, DEAD),
    ("Изуна Учиха", MALE, KONOHA, "Учиха", ["Огонь"], "Шаринган", NO_BEAST, KLASSIKA, DEAD),
    ("Обито Учиха", MALE, KONOHA, "Учиха", ["Огонь"], "Шаринган", NO_BEAST, KLASSIKA, DEAD),
    ("Шисуи Учиха", MALE, KONOHA, "Учиха", ["Огонь"], "Шаринган", NO_BEAST, KLASSIKA, DEAD),
    ("Фугаку Учиха", MALE, KONOHA, "Учиха", ["Огонь"], "Шаринган", NO_BEAST, KLASSIKA, DEAD),
    ("Микото Учиха", FEMALE, KONOHA, "Учиха", [UNKNOWN], "Шаринган", NO_BEAST, KLASSIKA, DEAD),
    ("Кушина Узумаки", FEMALE, UZUSHIO, "Узумаки", [UNKNOWN], NO_KEKKEI, "Девятихвостый", KLASSIKA, DEAD),
    ("Мито Узумаки", FEMALE, UZUSHIO, "Узумаки", [UNKNOWN], NO_KEKKEI, "Девятихвостый", KLASSIKA, DEAD),

    # --- Суна
    ("Гаара", MALE, SUNA, NO_CLAN, ["Земля", "Ветер"], NO_KEKKEI, "Однохвостый", KLASSIKA, ALIVE),
    ("Темари", FEMALE, SUNA, NO_CLAN, ["Ветер"], NO_KEKKEI, NO_BEAST, KLASSIKA, ALIVE),
    ("Канкуро", MALE, SUNA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, ALIVE),
    ("Баки", MALE, SUNA, NO_CLAN, ["Ветер"], NO_KEKKEI, NO_BEAST, KLASSIKA, ALIVE),
    ("Раса", MALE, SUNA, NO_CLAN, ["Земля"], "Магнитный выпуск", NO_BEAST, KLASSIKA, DEAD),
    ("Карура", FEMALE, SUNA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, DEAD),
    ("Чиё", FEMALE, SUNA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, SHIPPUDEN, DEAD),
    ("Сасори", MALE, SUNA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, SHIPPUDEN, DEAD),

    # --- Кири
    ("Забуза Момоти", MALE, KIRI, NO_CLAN, ["Вода"], NO_KEKKEI, NO_BEAST, KLASSIKA, DEAD),
    ("Хаку", MALE, KIRI, NO_CLAN, ["Вода", "Ветер"], "Ледяной выпуск", NO_BEAST, KLASSIKA, DEAD),
    ("Кисаме Хосигаки", MALE, KIRI, "Хосигаки", ["Вода"], NO_KEKKEI, NO_BEAST, KLASSIKA, DEAD),
    ("Кимимаро Кагуя", MALE, KIRI, "Кагуя", [UNKNOWN], "Шикоцумьяку", NO_BEAST, KLASSIKA, DEAD),
    ("Мэй Тэруми", FEMALE, KIRI, NO_CLAN, ["Вода", "Огонь"], "Кипящий выпуск", NO_BEAST, SHIPPUDEN, ALIVE),
    ("Ао", MALE, KIRI, NO_CLAN, ["Вода"], "Бьякуган", NO_BEAST, SHIPPUDEN, ALIVE),
    ("Тёдзиро", MALE, KIRI, NO_CLAN, ["Вода"], NO_KEKKEI, NO_BEAST, SHIPPUDEN, ALIVE),
    ("Суйгецу Хозуки", MALE, KIRI, "Хозуки", ["Вода"], NO_KEKKEI, NO_BEAST, SHIPPUDEN, ALIVE),
    ("Мангетсу Хозуки", MALE, KIRI, "Хозуки", ["Вода"], NO_KEKKEI, NO_BEAST, SHIPPUDEN, ALIVE),
    ("Ягура Каратачи", MALE, KIRI, NO_CLAN, [UNKNOWN], NO_KEKKEI, "Трёххвостый", SHIPPUDEN, DEAD),
    ("Утаката", MALE, KIRI, NO_CLAN, [UNKNOWN], NO_KEKKEI, "Шестихвостый", SHIPPUDEN, DEAD),

    # --- Кумо
    ("Киллер Би", MALE, KUMO, NO_CLAN, ["Молния"], NO_KEKKEI, "Восьмихвостый", SHIPPUDEN, ALIVE),
    ("Эй", MALE, KUMO, NO_CLAN, ["Молния"], NO_KEKKEI, NO_BEAST, SHIPPUDEN, ALIVE),
    ("Югито Нии", FEMALE, KUMO, NO_CLAN, [UNKNOWN], NO_KEKKEI, "Двухвостый", SHIPPUDEN, DEAD),
    ("Мабуи", MALE, KUMO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, SHIPPUDEN, ALIVE),
    ("Омои", MALE, KUMO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, SHIPPUDEN, ALIVE),
    ("Каруи", FEMALE, KUMO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, SHIPPUDEN, ALIVE),

    # --- Ива
    ("Дейдара", MALE, IWA, NO_CLAN, ["Земля"], "Взрывной выпуск", NO_BEAST, SHIPPUDEN, DEAD),
    ("Ооноки", MALE, IWA, NO_CLAN, ["Земля"], NO_KEKKEI, NO_BEAST, SHIPPUDEN, ALIVE),
    ("Куротсучи", FEMALE, IWA, NO_CLAN, ["Земля", "Огонь"], "Лавовый выпуск", NO_BEAST, SHIPPUDEN, ALIVE),
    ("Роши", MALE, IWA, NO_CLAN, ["Земля"], NO_KEKKEI, "Четырёххвостый", SHIPPUDEN, DEAD),
    ("Хан", MALE, IWA, NO_CLAN, [UNKNOWN], NO_KEKKEI, "Пятихвостый", SHIPPUDEN, DEAD),

    # --- Ото: подручные Орочимару
    ("Таюя", FEMALE, OTO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, ALIVE),
    ("Дзюго", MALE, OTO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, SHIPPUDEN, ALIVE),
    ("Карин", FEMALE, KUSA, "Узумаки", [UNKNOWN], NO_KEKKEI, NO_BEAST, SHIPPUDEN, ALIVE),
    ("Кидомару", MALE, OTO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, DEAD),
    ("Сакон", MALE, OTO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, DEAD),
    ("Джиробо", MALE, OTO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, DEAD),
    ("Заку Абуми", MALE, OTO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, ALIVE),
    ("Досу Кинута", MALE, OTO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, ALIVE),

    # --- Аме, Таки, прочие
    ("Нагато", MALE, AME, "Узумаки", [UNKNOWN], "Риннеган", NO_BEAST, KLASSIKA, DEAD),
    ("Конан", FEMALE, AME, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, DEAD),
    ("Яхико", MALE, AME, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, DEAD),
    ("Какузу", MALE, TAKI, NO_CLAN, ["Земля"], NO_KEKKEI, NO_BEAST, SHIPPUDEN, DEAD),
    ("Фу", FEMALE, TAKI, NO_CLAN, [UNKNOWN], NO_KEKKEI, "Семихвостый", SHIPPUDEN, DEAD),
    ("Хидан", MALE, UNKNOWN, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, SHIPPUDEN, UNKNOWN),
    ("Зецу", MALE, NO_VILLAGE, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KLASSIKA, UNKNOWN),

    # --- Ооцуцуки и поколение Боруто
    ("Кагуя Ооцуцуки", FEMALE, NO_VILLAGE, "Ооцуцуки", [UNKNOWN], "Бьякуган", NO_BEAST, SHIPPUDEN, UNKNOWN),
    ("Хагаромо Ооцуцуки", MALE, NO_VILLAGE, "Ооцуцуки", [UNKNOWN], "Риннеган", "Десятихвостый", SHIPPUDEN, UNKNOWN),
    ("Хамура Ооцуцуки", MALE, NO_VILLAGE, "Ооцуцуки", [UNKNOWN], "Бьякуган", NO_BEAST, SHIPPUDEN, UNKNOWN),
    ("Момошики Ооцуцуки", MALE, NO_VILLAGE, "Ооцуцуки", [UNKNOWN], "Бьякуган", NO_BEAST, BORUTO, DEAD),
    ("Урашики Ооцуцуки", MALE, NO_VILLAGE, "Ооцуцуки", [UNKNOWN], NO_KEKKEI, NO_BEAST, BORUTO, DEAD),
    ("Ишики Ооцуцуки", MALE, NO_VILLAGE, "Ооцуцуки", [UNKNOWN], NO_KEKKEI, NO_BEAST, BORUTO, DEAD),
    ("Каваки", MALE, NO_VILLAGE, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, BORUTO, ALIVE),
    ("Боруто Узумаки", MALE, KONOHA, "Узумаки", ["Ветер", "Молния"], NO_KEKKEI, NO_BEAST, BORUTO, ALIVE),
    ("Сарада Учиха", FEMALE, KONOHA, "Учиха", ["Огонь", "Молния"], "Шаринган", NO_BEAST, BORUTO, ALIVE),
    ("Мицуки", MALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, BORUTO, ALIVE),
    ("Химавари Узумаки", FEMALE, KONOHA, "Узумаки", [UNKNOWN], "Бьякуган", NO_BEAST, BORUTO, ALIVE),
    ("Чёчо Акимичи", FEMALE, KONOHA, "Акимичи", [UNKNOWN], NO_KEKKEI, NO_BEAST, BORUTO, ALIVE),
    ("Шикадай Нара", MALE, KONOHA, "Нара", [UNKNOWN], NO_KEKKEI, NO_BEAST, BORUTO, ALIVE),
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
    "ATTRIBUTES",
    "CHARACTERS",
    "FIELDS",
    "ROWS",
    "UNKNOWN",
    "VILLAGE_COLORS",
    "attribute_list",
    "character_names",
    "find_character",
    "public_character",
    "seed_rows",
    "village_color",
]
