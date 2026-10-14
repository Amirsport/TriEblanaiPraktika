# -*- coding: utf-8 -*-
"""Наполнение базы для игры «87-0»: составы прошлых турниров по Counter-Strike.

Что делает:
    * заливает исходный набор из backend/csdraft_data.py в таблицу csdraft_packs
      (повторный запуск обновляет пак по его идентификатору: состав, карты,
      место и эпоху можно поправить в файле данных и залить заново);
    * показывает, что уже лежит в базе (--list) и что советует игра (--check);
    * убирает пак из базы (--remove), если состав оказался неточным.

Повторный запуск без изменений в файле данных ничего не портит: строки паков
обновляются на месте, журнал прогонов (csdraft_runs) не трогается.

Примеры:
    python backend/seed_csdraft.py --db data/greenhouse.sqlite3
    python backend/seed_csdraft.py --dsn "postgresql://greenhouse:пароль@localhost:5432/greenhouse"
    python backend/seed_csdraft.py --dsn "..." --list
    python backend/seed_csdraft.py --dsn "..." --remove nip-dh-winter-2013
    python backend/seed_csdraft.py --db data/greenhouse.sqlite3 --dry-run

Оценки AIM/CLUTCH/IMP — игровые, а не официальная статистика; ники, команды и
турниры — исторические факты и принадлежат их владельцам.
"""
from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Any, Dict, List

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:  # запуск как модуль: python -m backend.seed_csdraft
    from .csdraft_data import ERA_LABELS, ROLE_LABELS, seed_rows, validate
    from .db import open_database
except ImportError:  # запуск как файл: python backend/seed_csdraft.py
    from csdraft_data import ERA_LABELS, ROLE_LABELS, seed_rows, validate  # type: ignore
    from db import open_database  # type: ignore


def seed(db, dry_run: bool) -> List[Dict[str, Any]]:
    """Заливает набор паков в базу."""
    rows = seed_rows()
    if not dry_run:
        db.csdraft_save_packs(rows)
    return rows


def show(db) -> None:
    """Что сейчас в базе: по эпохам, командам и игрокам."""
    items = db.csdraft_packs()
    runs = db.csdraft_run_count()
    print(f"\nВ базе {len(items)} составов, прогонов в журнале {runs}")
    for era, label in ERA_LABELS.items():
        part = [item for item in items if item["era"] == era]
        if part:
            print(f"  {label}: {len(part)}")
    extra = sorted({item["era"] for item in items} - set(ERA_LABELS))
    for era in extra:
        print(f"  неизвестная эпоха «{era}»: "
              f"{len([item for item in items if item['era'] == era])}")
    for item in items:
        players = ", ".join(
            f"{player['name']} ({ROLE_LABELS.get(player['role'], player['role'])})"
            for player in item["players"])
        title = item["event"] + (f", {item['place']}" if item["place"] else "")
        print(f"  {item['id']:<26} {item['team']:<14} {title} ({item['year']})")
        print(f"    карты: {', '.join(item['maps'])}")
        print(f"    состав: {players}")


def check(packs: List[Dict[str, Any]]) -> List[str]:
    """Проблемы набора: неполные составы, неизвестные роли, повтор игрока.

    Совпадение ролей внутри пака — не ошибка: в жизни двое игроков и правда
    делили одно амплуа, а в драфте из-за этого приходится брать кого-то не
    в свою роль. Ошибка — один и тот же игрок дважды в одном составе.
    """
    problems = list(validate(packs))
    for pack in packs:
        names = [player["name"].casefold() for player in pack["players"]]
        if len(set(names)) != len(names):
            problems.append(f"{pack['id']}: один игрок указан дважды")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Составы «87-0» в базе")
    parser.add_argument("--db", type=pathlib.Path, help="файл SQLite")
    parser.add_argument("--dsn", help="строка подключения PostgreSQL")
    parser.add_argument("--list", action="store_true", help="показать, что в базе")
    parser.add_argument("--check", action="store_true",
                        help="проверить набор в файле данных и то, что лежит в базе")
    parser.add_argument("--remove", action="append", default=[],
                        help="убрать состав из базы: --remove nip-dh-winter-2013")
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
        print(f"Проверка набора в файле данных: составов {len(source)}, "
              f"проблем {len(problems)}")
        for problem in problems:
            print(f"  {problem}")
        if db.csdraft_pack_count():
            stored = db.csdraft_packs()
            stored_problems = check(stored)
            print(f"Проверка базы: составов {len(stored)}, проблем {len(stored_problems)}")
            for problem in stored_problems:
                print(f"  {problem}")
        if problems:
            return 1

    before = db.csdraft_pack_count()
    rows = seed(db, args.dry_run)
    after = db.csdraft_pack_count()
    print(f"Составов: было {before}, стало {after} "
          f"({len(rows)} строк в источнике){' — холостой прогон' if args.dry_run else ''}")

    for pack_id in args.remove:
        if args.dry_run:
            print(f"  убрали бы состав: {pack_id}")
        elif db.csdraft_delete_pack(pack_id):
            print(f"  состав убран: {pack_id}")
        else:
            print(f"  состав не найден: {pack_id}")

    if args.list:
        show(db)
    return 0


if __name__ == "__main__":
    sys.exit(main())
