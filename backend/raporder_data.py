# -*- coding: utf-8 -*-
"""Треки русского рэпа для игры «Рэп-хронология»: исполнитель, название, год.

Игра — про порядок: треки надо расставить от самого старого к самому новому,
поэтому в наборе важны только исполнитель, название и год выпуска.

Что здесь есть и чего нет:
    * текстов песен и аудио нет и не будет: игра не про слова и не про звук,
      а про хронологию, поэтому набор — это факты (кто, что, когда);
    * исполнитель, название и год — факты из открытых источников и принадлежат
      их авторам и правообладателям; игра некоммерческая;
    * годы стоит перепроверять: часть дат проставлена по памяти и может
      отличаться от официальной (например, год альбома вместо года сингла
      или год переиздания). Набор правится прямо в базе — см.
      backend/seed_raporder.py, там же видно, что именно лежит в наборе.

Формат записи: (id, исполнитель, название, год).
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

# Сколько треков в раунде и сколько раундов в партии.
TRACKS_PER_ROUND = 5
ROUNDS_PER_GAME = 5
DUEL_ROUNDS = 3

# Треки: id латиницей, потому что id используется в адресах API.
TRACKS: Tuple[Tuple[str, str, str, int], ...] = (
    ("malchishnik-seks", "Мальчишник", "Секс без перерыва", 1993),
    ("bad-balance-gorod", "Bad Balance", "Город", 1998),
    ("detsl-vecherinka", "Децл", "Вечеринка", 2000),
    ("kasta-vokrug-shum", "Каста", "Вокруг шум", 2001),
    ("kasta-skrepya-serjtse", "Каста", "Скрепя сердце", 2002),
    ("serega-chernyy-bumer", "Серёга", "Чёрный бумер", 2004),
    ("krovostok-reka", "Кровосток", "Река", 2004),
    ("smoki-mo-plany", "Смоки Мо", "Планы", 2005),
    ("timati-v-klube", "Тимати", "В клубе", 2006),
    ("krovostok-biologiya", "Кровосток", "Биология", 2006),
    ("ak47-volki", "АК-47", "Волки", 2007),
    ("centr-gorod-dorog", "Centr", "Город дорог", 2008),
    ("krovostok-kurtets", "Кровосток", "Куртец", 2008),
    ("basta-sansara", "Баста", "Сансара", 2009),
    ("noizemc-ustroy-destroy", "Noize MC", "Устрой дестрой", 2010),
    ("oxxxymiron-kto-ubil-marka", "Oxxxymiron", "Кто убил Марка?", 2011),
    ("kravts-obmani-menya", "Кравц", "Обмани меня", 2012),
    ("skriptonit-tantsuy-sama", "Скриптонит", "Танцуй сама", 2013),
    ("kaspiyskiy-gruz-tabak", "Каспийский Груз", "Табак", 2014),
    ("oxxxymiron-gorod-pod-podoshvoy", "Oxxxymiron", "Город под подошвой", 2015),
    ("hasky-panelka", "Хаски", "Панелька", 2016),
    ("griby-taet-led", "Грибы", "Тает лёд", 2017),
    ("face-yumorist", "Фейс", "Юморист", 2017),
    ("eldzhey-rozovoe-vino", "Элджей", "Розовое вино", 2017),
    ("miyagi-i-got-love", "MiyaGi & Эндшпиль", "I Got Love", 2017),
    ("bigbabytape-gimme-the-loot", "Big Baby Tape", "Gimme the Loot", 2018),
    ("timabelorusskih-mokrye-krossy", "Тима Белорусских", "Мокрые кроссы", 2018),
    ("morgenshtern-novyy-merin", "Моргенштерн", "Новый Мерин", 2019),
    ("morgenshtern-cadillac", "Моргенштерн", "Cadillac", 2020),
    ("oxxxymiron-oyda", "Oxxxymiron", "Ойда", 2022),
)


def _item(row: Tuple[str, str, str, int]) -> Dict[str, Any]:
    """Строка набора в виде словаря."""
    track_id, artist, title, year = row
    return {
        "id": str(track_id),
        "artist": str(artist),
        "title": str(title),
        "year": int(year),
    }


def tracks() -> List[Dict[str, Any]]:
    """Набор треков для движка и проверок."""
    return [_item(row) for row in TRACKS]


def seed_rows() -> List[Dict[str, Any]]:
    """Строки для базы: тот же набор, готова к записи."""
    return [_item(row) for row in TRACKS]


def validate(rows: Any = None) -> List[str]:
    """Проверка набора: уникальные id, заполненные поля и правдоподобный год."""
    problems: List[str] = []
    seen = set()
    for track in (list(rows) if rows is not None else tracks()):
        track_id = str(track.get("id") or "")
        if not track_id:
            problems.append("трек без идентификатора")
            continue
        if track_id in seen:
            problems.append(f"повторяющийся идентификатор: {track_id}")
        seen.add(track_id)
        for field, label in (("artist", "исполнителя"), ("title", "названия")):
            if not str(track.get(field) or "").strip():
                problems.append(f"{track_id}: нет {label}")
        try:
            year = int(track.get("year") or 0)
        except (TypeError, ValueError):
            problems.append(f"{track_id}: год не число")
            continue
        if not 1980 <= year <= 2030:
            problems.append(f"{track_id}: год вне разумных границ ({year})")
    if len({int(track["year"]) for track in (list(rows) if rows is not None else tracks())}) < \
            TRACKS_PER_ROUND:
        problems.append("разных годов меньше, чем треков в раунде: раунд не собрать")
    return problems


__all__ = [
    "TRACKS",
    "TRACKS_PER_ROUND",
    "ROUNDS_PER_GAME",
    "DUEL_ROUNDS",
    "tracks",
    "seed_rows",
    "validate",
]
