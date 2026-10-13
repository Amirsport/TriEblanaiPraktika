# -*- coding: utf-8 -*-
"""Данные для дуэли «Narutodle».

Здесь только факты о персонажах (деревня, клан, стихии и т. д.) — тот набор,
по которому игрок сравнивает свою догадку с загадкой. Тексты не переписывались
ни из каких источников: это короткие справочные значения.

Набор сознательно небольшой и легко правится: одна строка — один персонаж.
Если значение неизвестно или спорно, ставится UNKNOWN, и по этой графе догадка
считается несовпавшей (кроме случая, когда неизвестно у обоих).
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

# Деревни и страны — короткие общеупотребительные названия.
KONOHA = "Коноха"
SUNA = "Суна"
KIRI = "Кири"
KUMO = "Кумо"
IWA = "Ива"
OTO = "Ото"
AME = "Аме"
TAKI = "Таки"

KLASSIKA = "Классика"
SHIPPUDEN = "Шиппуден"
BORUTO = "Боруто"

NO_CLAN = "нет клана"
NO_KEKKEI = "нет"
NO_BEAST = "нет"

CHARACTERS: List[Dict[str, Any]] = [
    # --- Коноха: команда 7 и наставники
    {"name": "Наруто Узумаки", "gender": MALE, "village": KONOHA, "clan": "Узумаки",
     "nature": ["Ветер"], "kekkei": NO_KEKKEI, "jinchuriki": "Девятихвостый",
     "debut": KLASSIKA, "status": "жив"},
    {"name": "Саске Учиха", "gender": MALE, "village": KONOHA, "clan": "Учиха",
     "nature": ["Огонь", "Молния"], "kekkei": "Шаринган", "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "жив"},
    {"name": "Сакура Харуно", "gender": FEMALE, "village": KONOHA, "clan": NO_CLAN,
     "nature": ["Земля", "Вода"], "kekkei": NO_KEKKEI, "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "жив"},
    {"name": "Какаши Хатаке", "gender": MALE, "village": KONOHA, "clan": NO_CLAN,
     "nature": ["Молния"], "kekkei": "Шаринган", "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "жив"},
    {"name": "Ямато", "gender": MALE, "village": KONOHA, "clan": NO_CLAN,
     "nature": ["Земля", "Вода"], "kekkei": "Деревянный выпуск", "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "жив"},

    # --- Коноха: команда 8, 10 и сверстники
    {"name": "Хината Хьюга", "gender": FEMALE, "village": KONOHA, "clan": "Хьюга",
     "nature": [UNKNOWN], "kekkei": "Бьякуган", "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "жив"},
    {"name": "Неджи Хьюга", "gender": MALE, "village": KONOHA, "clan": "Хьюга",
     "nature": [UNKNOWN], "kekkei": "Бьякуган", "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "погиб"},
    {"name": "Рок Ли", "gender": MALE, "village": KONOHA, "clan": NO_CLAN,
     "nature": [UNKNOWN], "kekkei": NO_KEKKEI, "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "жив"},
    {"name": "Тентен", "gender": FEMALE, "village": KONOHA, "clan": NO_CLAN,
     "nature": [UNKNOWN], "kekkei": NO_KEKKEI, "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "жив"},
    {"name": "Шикамару Нара", "gender": MALE, "village": KONOHA, "clan": "Нара",
     "nature": [UNKNOWN], "kekkei": NO_KEKKEI, "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "жив"},
    {"name": "Тёджи Акимичи", "gender": MALE, "village": KONOHA, "clan": "Акимичи",
     "nature": [UNKNOWN], "kekkei": NO_KEKKEI, "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "жив"},
    {"name": "Ино Яманака", "gender": FEMALE, "village": KONOHA, "clan": "Яманака",
     "nature": [UNKNOWN], "kekkei": NO_KEKKEI, "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "жив"},
    {"name": "Киба Инузука", "gender": MALE, "village": KONOHA, "clan": "Инузука",
     "nature": [UNKNOWN], "kekkei": NO_KEKKEI, "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "жив"},
    {"name": "Шино Абураме", "gender": MALE, "village": KONOHA, "clan": "Абураме",
     "nature": [UNKNOWN], "kekkei": NO_KEKKEI, "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "жив"},
    {"name": "Сай", "gender": MALE, "village": KONOHA, "clan": NO_CLAN,
     "nature": [UNKNOWN], "kekkei": NO_KEKKEI, "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "жив"},

    # --- Коноха: старшее поколение
    {"name": "Хирузен Сарутоби", "gender": MALE, "village": KONOHA, "clan": "Сарутоби",
     "nature": ["Огонь", "Земля"], "kekkei": NO_KEKKEI, "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "погиб"},
    {"name": "Асума Сарутоби", "gender": MALE, "village": KONOHA, "clan": "Сарутоби",
     "nature": [UNKNOWN], "kekkei": NO_KEKKEI, "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "погиб"},
    {"name": "Конахамару Сарутоби", "gender": MALE, "village": KONOHA, "clan": "Сарутоби",
     "nature": [UNKNOWN], "kekkei": NO_KEKKEI, "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "жив"},
    {"name": "Минато Намиказе", "gender": MALE, "village": KONOHA, "clan": NO_CLAN,
     "nature": [UNKNOWN], "kekkei": NO_KEKKEI, "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "погиб"},
    {"name": "Кушина Узумаки", "gender": FEMALE, "village": KONOHA, "clan": "Узумаки",
     "nature": [UNKNOWN], "kekkei": NO_KEKKEI, "jinchuriki": "Девятихвостый",
     "debut": KLASSIKA, "status": "погибла"},
    {"name": "Цунаде", "gender": FEMALE, "village": KONOHA, "clan": "Сенджу",
     "nature": [UNKNOWN], "kekkei": NO_KEKKEI, "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "жив"},
    {"name": "Джирайя", "gender": MALE, "village": KONOHA, "clan": NO_CLAN,
     "nature": ["Огонь"], "kekkei": NO_KEKKEI, "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "погиб"},
    {"name": "Орочимару", "gender": MALE, "village": KONOHA, "clan": NO_CLAN,
     "nature": [UNKNOWN], "kekkei": NO_KEKKEI, "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "жив"},
    {"name": "Майто Гай", "gender": MALE, "village": KONOHA, "clan": NO_CLAN,
     "nature": [UNKNOWN], "kekkei": NO_KEKKEI, "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "жив"},
    {"name": "Куренай Юхи", "gender": FEMALE, "village": KONOHA, "clan": "Юхи",
     "nature": [UNKNOWN], "kekkei": NO_KEKKEI, "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "жив"},

    # --- Учиха
    {"name": "Итачи Учиха", "gender": MALE, "village": KONOHA, "clan": "Учиха",
     "nature": ["Огонь", "Вода"], "kekkei": "Шаринган", "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "погиб"},
    {"name": "Мадара Учиха", "gender": MALE, "village": KONOHA, "clan": "Учиха",
     "nature": ["Огонь"], "kekkei": "Риннеган", "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "погиб"},
    {"name": "Обито Учиха", "gender": MALE, "village": KONOHA, "clan": "Учиха",
     "nature": ["Огонь"], "kekkei": "Шаринган", "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "погиб"},

    # --- Суна
    {"name": "Гаара", "gender": MALE, "village": SUNA, "clan": NO_CLAN,
     "nature": ["Земля", "Ветер"], "kekkei": NO_KEKKEI, "jinchuriki": "Однохвостый",
     "debut": KLASSIKA, "status": "жив"},
    {"name": "Темари", "gender": FEMALE, "village": SUNA, "clan": NO_CLAN,
     "nature": ["Ветер"], "kekkei": NO_KEKKEI, "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "жив"},
    {"name": "Канкуро", "gender": MALE, "village": SUNA, "clan": NO_CLAN,
     "nature": [UNKNOWN], "kekkei": NO_KEKKEI, "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "жив"},
    {"name": "Чиё", "gender": FEMALE, "village": SUNA, "clan": NO_CLAN,
     "nature": [UNKNOWN], "kekkei": NO_KEKKEI, "jinchuriki": NO_BEAST,
     "debut": SHIPPUDEN, "status": "погибла"},
    {"name": "Сасори", "gender": MALE, "village": SUNA, "clan": NO_CLAN,
     "nature": [UNKNOWN], "kekkei": NO_KEKKEI, "jinchuriki": NO_BEAST,
     "debut": SHIPPUDEN, "status": "погиб"},

    # --- Кири
    {"name": "Забуза Момоти", "gender": MALE, "village": KIRI, "clan": NO_CLAN,
     "nature": ["Вода"], "kekkei": NO_KEKKEI, "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "погиб"},
    {"name": "Хаку", "gender": MALE, "village": KIRI, "clan": NO_CLAN,
     "nature": ["Вода", "Ветер"], "kekkei": "Ледяной выпуск", "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "погиб"},
    {"name": "Кисаме Хосигаки", "gender": MALE, "village": KIRI, "clan": "Хосигаки",
     "nature": ["Вода"], "kekkei": NO_KEKKEI, "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "погиб"},
    {"name": "Мэй Тэруми", "gender": FEMALE, "village": KIRI, "clan": NO_CLAN,
     "nature": ["Вода", "Огонь"], "kekkei": "Кипящий выпуск", "jinchuriki": NO_BEAST,
     "debut": SHIPPUDEN, "status": "жив"},

    # --- Кумо, Ива, Аме, Таки
    {"name": "Киллер Би", "gender": MALE, "village": KUMO, "clan": NO_CLAN,
     "nature": ["Молния"], "kekkei": NO_KEKKEI, "jinchuriki": "Восьмихвостый",
     "debut": SHIPPUDEN, "status": "жив"},
    {"name": "Эй", "gender": MALE, "village": KUMO, "clan": NO_CLAN,
     "nature": ["Молния"], "kekkei": NO_KEKKEI, "jinchuriki": NO_BEAST,
     "debut": SHIPPUDEN, "status": "жив"},
    {"name": "Дейдара", "gender": MALE, "village": IWA, "clan": NO_CLAN,
     "nature": ["Земля"], "kekkei": "Взрывной выпуск", "jinchuriki": NO_BEAST,
     "debut": SHIPPUDEN, "status": "погиб"},
    {"name": "Какузу", "gender": MALE, "village": TAKI, "clan": NO_CLAN,
     "nature": ["Земля"], "kekkei": NO_KEKKEI, "jinchuriki": NO_BEAST,
     "debut": SHIPPUDEN, "status": "погиб"},
    {"name": "Нагато", "gender": MALE, "village": AME, "clan": "Узумаки",
     "nature": [UNKNOWN], "kekkei": "Риннеган", "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "погиб"},
    {"name": "Конан", "gender": FEMALE, "village": AME, "clan": NO_CLAN,
     "nature": [UNKNOWN], "kekkei": NO_KEKKEI, "jinchuriki": NO_BEAST,
     "debut": KLASSIKA, "status": "погибла"},

    # --- Боруто
    {"name": "Боруто Узумаки", "gender": MALE, "village": KONOHA, "clan": "Узумаки",
     "nature": ["Ветер", "Молния"], "kekkei": NO_KEKKEI, "jinchuriki": NO_BEAST,
     "debut": BORUTO, "status": "жив"},
    {"name": "Сарада Учиха", "gender": FEMALE, "village": KONOHA, "clan": "Учиха",
     "nature": ["Огонь", "Молния"], "kekkei": "Шаринган", "jinchuriki": NO_BEAST,
     "debut": BORUTO, "status": "жив"},
    {"name": "Мицуки", "gender": MALE, "village": KONOHA, "clan": NO_CLAN,
     "nature": [UNKNOWN], "kekkei": NO_KEKKEI, "jinchuriki": NO_BEAST,
     "debut": BORUTO, "status": "жив"},
]

# Индекс по имени — догадки сравниваются по точному названию, но пробелы
# и регистр не важны: «наРУТО узумаки» найдётся.
INDEX = {character["name"].casefold(): character for character in CHARACTERS}


def find_character(name: str) -> Optional[Dict[str, Any]]:
    """Возвращает персонажа по названию или None, если такого в наборе нет."""
    return INDEX.get((name or "").strip().casefold())


def character_names() -> List[str]:
    """Названия для подсказки в поле ввода — без скрытых свойств."""
    return [character["name"] for character in CHARACTERS]


def public_character(character: Dict[str, Any]) -> Dict[str, Any]:
    """Персонаж в виде, пригодном для отправки клиенту (после конца раунда)."""
    return {key: character[key] for key in ("name", "gender", "village", "clan",
                                            "nature", "kekkei", "jinchuriki",
                                            "debut", "status")}


def attribute_list() -> List[Dict[str, Any]]:
    """Описание граф сравнения — страница строит по нему шапку таблицы."""
    return [dict(attribute) for attribute in ATTRIBUTES]


__all__ = [
    "ATTRIBUTES",
    "CHARACTERS",
    "UNKNOWN",
    "attribute_list",
    "character_names",
    "find_character",
    "public_character",
]
