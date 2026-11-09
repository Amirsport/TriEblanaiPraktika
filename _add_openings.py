# -*- coding: utf-8 -*-
"""Новые опенинги из newops.txt: треки с местом, с которого играть отрывок.

Что делает: добавляет строки в `songless_tracks` — название аниме, название
опенинга и `clip_start` (время из списка). Сами записи скрипт **не** трогает:
аудио владелец сайта кладёт отдельно (`songs.py` / `seed_songless.py --audio`),
а `clip_start` только задаёт место фрагмента. Пока у трека нет записи, раунд на
нём не строится, поэтому добавление ничему не мешает.

Примеры:
    # только SQL (его же можно скормить psql на сервере)
    python _add_openings.py --sql data/new_openings.sql

    # применить к базе, до которой есть прямой доступ
    python _add_openings.py --dsn "postgresql://greenhouse:пароль@localhost:5432/greenhouse"

Повторный запуск безопасен: строки обновляются по `track_key`, поэтому правки
названий и времени просто перезаписываются. Уже привязанные записи, начало и
длина фрагмента не затираются.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import sys
from typing import Dict, List, Tuple

ROOT = pathlib.Path(__file__).resolve().parent

# (аниме, опенинг, start в секундах, как было в списке владельца).
# Названия аниме — как в остальном наборе (см. backend/songless_catalog.json).
# Где название опенинга в списке не указано, поле пустое: его можно дописать
# одной строкой в базе, когда владелец добавит запись.
OPENINGS: Tuple[Tuple[str, str, float, str], ...] = (
    ("Рейтинг королей", "Hadaka no Yuusha", 40.0, "рейтинг королей op 2"),
    ("Невероятные приключения ДжоДжо", "Sono Chi no Sadame", 0.0, "JoJo op 1"),
    ("Невероятные приключения ДжоДжо", "Bloody Stream", 0.0, "JoJo op2"),
    ("Невероятные приключения ДжоДжо", "Stand Proud", 0.0, "JoJo op3"),
    ("Невероятные приключения ДжоДжо", "End of THE WORLD", 0.0, "JoJo op4"),
    ("Невероятные приключения ДжоДжо: Стальной шарик", "", 0.0, "JoJo SBR op1"),
    ("Класс превосходства", "", 58.0, "CoTe op1"),
    ("Класс превосходства", "", 0.0, "CoTe op2"),
    ("Класс превосходства", "", 0.0, "CoTe op3"),
    ("Класс превосходства", "", 50.0, "CoTe op4"),
    ("Шангри-Ла: Фронтир", "", 45.0, "Shangri-La Frontier"),
    ("Шангри-Ла: Фронтир", "", 0.0, "Shangri-La op1"),
    ("Шангри-Ла: Фронтир", "", 50.0, "Shangri-La op2"),
    ("Шангри-Ла: Фронтир", "", 0.0, "Shangri-La op3"),
    ("Wind Breaker", "", 40.0, "Windbreaker op1"),
    ("Семья шпиона", "SOUVENIR", 35.0, "Spy×Family op2"),
    ("Семья шпиона", "Kura Kura", 45.0, "Spy×Family op3"),
    ("Реинкарнация безработного", "spiral", 35.0, "Mushoku Tensei S2 op1"),
    ("Чёрный клевер", "", 40.0, "Black Clover op14"),
    ("Моя геройская академия", "ODD FUTURE", 0.0, "MHA ODD FUTURE"),
    ("Моя геройская академия", "Merry-Go-Round", 60.0, "MHA Merry-Go-Round"),
    ("Моя геройская академия", "Curtain Call", 55.0, "MHA «カーテンコール»"),
    ("Моя геройская академия", "Bokura no", 40.0, "MHA «ぼくらの»"),
    ("Магическая битва", "", 0.0, "JJK op5"),
    ("Магическая битва", "", 40.0, "JJK op3"),
    ("Магическая битва", "", 0.0, "JJK op4"),
    ("Мэшл", "Bling-Bang-Bang-Born", 0.0, "Mashle op2"),
    ("Атака титанов", "", 0.0, "Attack on Titan op3"),
    ("Атака титанов", "", 0.0, "Attack on Titan op4"),
    ("Атака титанов", "", 0.0, "Attack on Titan op6"),
    ("Атака титанов", "", 0.0, "Attack on Titan op7"),
    ("Witch Watch", "", 45.0, "Witch Watch op1"),
    ("Zom 100: Список дел мертвеца", "Song of the Dead", 45.0, "Zom 100 op1"),
    ("Ya Boy Kongming!", "Chikichiki Banban", 0.0, "Ya Boy Kongming!"),
    ("Киберпанк: Бегущие по краю", "This Fffire", 55.0, "Cyberpunk: Edgerunners op1"),
    ("Доктор Стоун", "CASANOVA POSSE", 35.0, "Dr.STONE SCIENCE FUTURE"),
    ("Аля иногда кокетничает по-русски", "", 45.0, "Alya Sometimes Hides Her Feelings"),
    ("Скип и Лофер", "Mellow", 50.0, "Skip and Loafer «メロウ»"),
    ("Зов ночи", "Daten", 0.0, "Call of the Night op1"),
    ("Зов ночи", "", 65.0, "Call of the Night op2"),
    ("Человек-бензопила", "", 0.0, "Chainsaw Man op2"),
    ("Оверлорд", "GO CRY GO", 0.0, "Overlord op2"),
    ("Оверлорд", "VORACITY", 0.0, "Overlord op3"),
    ("Оверлорд", "Hollow Hunger", 0.0, "Overlord op4"),
    ("Урусэи Яцура", "Aiue", 30.0, "Urusei Yatsura «アイウエ»"),
    ("Отряд красивых детективов", "Shake & Shake", 40.0, "Bishounen Tanteidan"),
    ("Хоримия", "Iro Kousui", 0.0, "Horimiya op"),
    ("Слишком много проигравших героинь", "", 40.0, "Makeine"),
    ("Ниндзя Камуи", "", 55.0, "Ninja Kamui op1"),
    ("Kill Blue", "", 45.0, "Kill Blue op1"),
    ("Моя подруга-олениха Нокотан", "Shikairo Days", 0.0, "My Deer Friend Nokotan op1"),
    ("Oshi no Ko", "", 0.0, "Oshi no Ko op2"),
    ("Oshi no Ko", "", 30.0, "Oshi no Ko op3"),
)


def track_key(anime: str, song: str, label: str, start: float) -> str:
    """Ключ трека: «a» + хвост sha1, как у остальных строк набора.

    Ключ не зависит от порядка строк списка: он считается от названий и метки,
    поэтому повторный запуск обновляет те же строки, а не плодит дубликаты.
    """
    seed = "|".join((anime, song, label, f"{start:.1f}"))
    return "a" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:15]


def rows() -> List[Dict[str, object]]:
    """Строки для вставки: ключ, аниме, опенинг и место фрагмента."""
    prepared: List[Dict[str, object]] = []
    for anime, song, start, label in OPENINGS:
        prepared.append({
            "track_key": track_key(anime, song, label, start),
            "anime": anime,
            "song": song,
            "clip_start": float(start),
            "label": label,
        })
    return prepared


def sql_text() -> str:
    """SQL для psql: вставка с обновлением названий и места фрагмента."""
    lines = [
        "-- Новые опенинги: только справочные сведения и место фрагмента.",
        "-- Повторный запуск обновляет те же строки по track_key.",
        "BEGIN;",
    ]
    for row in rows():
        anime = str(row["anime"]).replace("'", "''")
        song = str(row["song"]).replace("'", "''")
        key = str(row["track_key"]).replace("'", "''")
        start = float(row["clip_start"])
        lines.append(
            f"INSERT INTO songless_tracks (track_key, anime, song, clip_start, updated_at) "
            f"VALUES ('{key}', '{anime}', '{song}', {start}, now()) "
            f"ON CONFLICT (track_key) DO UPDATE SET anime = EXCLUDED.anime, "
            f"song = EXCLUDED.song, clip_start = EXCLUDED.clip_start, "
            f"updated_at = EXCLUDED.updated_at;"
        )
    lines.append(
        "SELECT count(*) AS new_tracks FROM songless_tracks WHERE track_key IN ("
        + ", ".join("'" + str(row["track_key"]) + "'" for row in rows()) + ");"
    )
    lines.append("COMMIT;")
    return "\n".join(lines) + "\n"


def apply_to_dsn(dsn: str) -> None:
    """Применяет список к базе, доступной напрямую (через backend.db)."""
    sys.path.insert(0, str(ROOT))
    from backend.db import open_database  # импорт здесь: нужен только для --dsn

    db = open_database(dsn=dsn)
    db.initialize()
    saved = db.songless_save_tracks([
        {"track_key": row["track_key"], "anime": row["anime"], "song": row["song"],
         "clip_start": row["clip_start"]}
        for row in rows()
    ])
    print(f"обновлено строк: {saved}")
    print(f"всего треков в базе: {db.songless_track_count()}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Новые опенинги в songless_tracks")
    parser.add_argument("--sql", default="", help="файл, куда записать SQL")
    parser.add_argument("--dsn", default=os.environ.get("GREENHOUSE_DSN", ""),
                        help="строка подключения, если база доступна напрямую")
    parser.add_argument("--list", action="store_true", help="показать список и выйти")
    args = parser.parse_args()

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    if args.list:
        for row in rows():
            print(f"  {row['anime']} — {row['song'] or '(без названия)'} "
                  f"| start {row['clip_start']:.0f} c | {row['label']}")
        print(f"всего строк: {len(rows())}")
        return 0

    if args.sql:
        target = pathlib.Path(args.sql)
        if not target.is_absolute():
            target = ROOT / target
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(sql_text(), encoding="utf-8")
        print(f"SQL записан: {target} (строк {len(rows())})")

    if args.dsn:
        apply_to_dsn(args.dsn)

    if not args.sql and not args.dsn:
        print(sql_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())