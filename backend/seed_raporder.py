# -*- coding: utf-8 -*-
"""Наполнение базы для игры «Рэп-хронология»: исполнитель, название, год.

Что делает:
    * заливает исходный набор из backend/raporder_data.py в таблицу
      raporder_tracks (повторный запуск обновляет трек по его идентификатору:
      год, исполнителя и название можно поправить в файле данных и залить
      заново — именно так удобнее всего править годы);
    * показывает, что уже лежит в базе (--list) и что советует игра (--check);
    * убирает трек из базы (--remove), если он оказался неточным или лишним;
    * умеет задать год одного трека на месте (--year id=2010).

Повторный запуск без изменений в файле данных ничего не портит: строки
обновляются на месте, журнал партий (raporder_matches) не трогается.

Примеры:
    python backend/seed_raporder.py --db data/greenhouse.sqlite3
    python backend/seed_raporder.py --db data/greenhouse.sqlite3 --list
    python backend/seed_raporder.py --dsn "postgresql://greenhouse:пароль@localhost:5432/greenhouse"
    python backend/seed_raporder.py --dsn "..." --year krovostok-reka=2005
    python backend/seed_raporder.py --db data/greenhouse.sqlite3 --remove lipovyy-trek

Текстов песен в наборе нет и не будет: игра про хронологию, а не про слова.
Исполнитель, название и год — факты из открытых источников и принадлежат их
авторам и правообладателям; годы стоит перепроверять.
"""
from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Any, Dict, List

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:  # запуск как модуль: python -m backend.seed_raporder
    from .db import open_database
    from .raporder_data import TRACKS_PER_ROUND, seed_rows, validate
except ImportError:  # запуск как файл: python backend/seed_raporder.py
    from db import open_database  # type: ignore
    from raporder_data import TRACKS_PER_ROUND, seed_rows, validate  # type: ignore


def seed(db, dry_run: bool) -> List[Dict[str, Any]]:
    """Заливает набор треков в базу."""
    rows = seed_rows()
    if not dry_run:
        db.raporder_save_tracks(rows)
    return rows


def show(db) -> None:
    """Что сейчас в базе: годы, исполнители и названия."""
    items = db.raporder_tracks()
    matches = db.raporder_match_count()
    years = {int(item["year"]) for item in items}
    print(f"\nВ базе {len(items)} треков, разных годов {len(years)}, партий {matches}")
    for item in sorted(items, key=lambda track: (int(track["year"]), track["id"])):
        print(f"  {item['year']:<6} {item['artist']:<20} {item['title']}  ({item['id']})")


def check(tracks: List[Dict[str, Any]]) -> List[str]:
    """Проблемы набора: пустые поля, повтор идентификатора, мало разных годов."""
    return validate(tracks)


def apply_years(db, pairs: List[str], dry_run: bool) -> int:
    """Меняет год у указанных треков: --year id=2010 (можно несколько раз)."""
    changed = 0
    for pair in pairs:
        if "=" not in pair:
            print(f"  непонятная правка года: {pair} (нужно id=2010)")
            continue
        track_id, _, raw = pair.rpartition("=")
        try:
            year = int(raw)
        except ValueError:
            print(f"  год не число: {pair}")
            continue
        current = [track for track in db.raporder_tracks() if track["id"] == track_id]
        if not current:
            print(f"  трек не найден: {track_id}")
            continue
        track = dict(current[0])
        track["year"] = year
        if dry_run:
            print(f"  поменяли бы год: {track_id} → {year}")
        else:
            db.raporder_save_tracks([track])
            print(f"  год поправлен: {track_id} → {year} "
                  f"({track['artist']} — «{track['title']}»)")
        changed += 1
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Треки «Рэп-хронологии» в базе")
    parser.add_argument("--db", type=pathlib.Path, help="файл SQLite")
    parser.add_argument("--dsn", help="строка подключения PostgreSQL")
    parser.add_argument("--list", action="store_true", help="показать, что в базе")
    parser.add_argument("--check", action="store_true",
                        help="проверить набор в файле данных и то, что лежит в базе")
    parser.add_argument("--remove", action="append", default=[],
                        help="убрать трек из базы: --remove krovostok-reka")
    parser.add_argument("--year", action="append", default=[],
                        help="поправить год: --year krovostok-reka=2005")
    parser.add_argument("--dry-run", action="store_true",
                        help="ничего не менять, только показать план")
    args = parser.parse_args()

    if not args.db and not args.dsn:
        parser.error("укажите --db для SQLite или --dsn для PostgreSQL")

    db = open_database(args.db, args.dsn)
    db.initialize()

    if args.check:
        source = seed_rows()
        problems = check(source)
        print(f"Проверка набора в файле данных: треков {len(source)}, проблем {len(problems)}")
        for problem in problems:
            print(f"  {problem}")
        if db.raporder_track_count():
            stored = db.raporder_tracks()
            stored_problems = check(stored)
            print(f"Проверка базы: треков {len(stored)}, проблем {len(stored_problems)}")
            for problem in stored_problems:
                print(f"  {problem}")
        if problems:
            return 1

    before = db.raporder_track_count()
    rows = seed(db, args.dry_run)
    after = db.raporder_track_count()
    print(f"Треков: было {before}, стало {after} "
          f"({len(rows)} строк в источнике){' — холостой прогон' if args.dry_run else ''}")

    if args.year:
        changed = apply_years(db, args.year, args.dry_run)
        print(f"Правок года: {changed}")

    for track_id in args.remove:
        if args.dry_run:
            print(f"  убрали бы трек: {track_id}")
        elif db.raporder_delete_track(track_id):
            print(f"  трек убран: {track_id}")
        else:
            print(f"  трек не найден: {track_id}")

    if args.list:
        show(db)

    years = len({int(item["year"]) for item in db.raporder_tracks()})
    if years < TRACKS_PER_ROUND:
        print(f"Внимание: в базе всего {years} разных годов, а раунду нужно "
              f"{TRACKS_PER_ROUND} — игра не начнётся")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
