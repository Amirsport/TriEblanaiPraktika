# -*- coding: utf-8 -*-
"""Наполнение базы для игры «322-0» (драфт по Dota 2, Streamers Battle 13).

Что делает:
    * заливает пул игроков со стоимостями (dotadraft_players) и пул героев с
      позициями и оценками (dotadraft_heroes) из backend/dotadraft_data.py;
      повторный запуск обновляет строки по идентификатору, поэтому и ники,
      и стоимости удобнее править в файле данных и заливать заново;
    * показывает, что уже лежит в базе (--list) и проверяет набор (--check);
    * убирает игрока или героя из пула (--remove, --remove-hero);
    * правит стоимость на месте (--cost dm=90) и оценку героя (--rating invoker=95).

Журнал прогонов «322-0» живёт в общей таблице csdraft_runs с game = 'dota322',
поэтому этот скрипт его не трогает.

Примеры:
    python backend/seed_dotadraft.py --db data/greenhouse.sqlite3
    python backend/seed_dotadraft.py --db data/greenhouse.sqlite3 --list
    python backend/seed_dotadraft.py --dsn "postgresql://greenhouse:пароль@localhost:5432/greenhouse"
    python backend/seed_dotadraft.py --db data/greenhouse.sqlite3 --cost dm=90
    python backend/seed_dotadraft.py --db data/greenhouse.sqlite3 --remove-hero magnus

Стоимости игроков — из таблицы владельца сайта. Оценки героев — игровые, они
влияют только на силу состава. Ники, Dota 2 и её герои — исторические названия
и товарные знаки их владельцев; игра некоммерческая.
"""
from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Any, Dict, List

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:  # запуск как модуль: python -m backend.seed_dotadraft
    from .db import open_database
    from .dotadraft_data import (
        BUDGET,
        POSITION_LABELS,
        SQUAD_SIZE,
        hero_rows,
        player_rows,
        validate_heroes,
        validate_players,
    )
except ImportError:  # запуск как файл: python backend/seed_dotadraft.py
    from db import open_database  # type: ignore
    from dotadraft_data import (  # type: ignore
        BUDGET,
        POSITION_LABELS,
        SQUAD_SIZE,
        hero_rows,
        player_rows,
        validate_heroes,
        validate_players,
    )


def seed(db, dry_run: bool) -> Dict[str, List[Dict[str, Any]]]:
    """Заливает пул игроков и пул героев в базу."""
    players = player_rows()
    heroes = hero_rows()
    if not dry_run:
        db.dotadraft_save_players(players)
        db.dotadraft_save_heroes(heroes)
    return {"players": players, "heroes": heroes}


def show(db) -> None:
    """Что сейчас в базе: игроки по стоимости и герои по позициям."""
    players = db.dotadraft_players()
    heroes = db.dotadraft_heroes()
    per_position: Dict[int, int] = {}
    for hero in heroes:
        per_position[int(hero["position"])] = per_position.get(int(hero["position"]), 0) + 1
    print(f"\nВ базе {len(players)} игроков и {len(heroes)} героев")
    positions = ", ".join(f"{POSITION_LABELS[position]}: {per_position.get(position, 0)}"
                          for position in sorted(POSITION_LABELS))
    print(f"Герои по позициям — {positions}")
    top = sorted(players, key=lambda player: (-int(player["cost"]), player["id"]))
    print("\nИгроки (первые 40 по стоимости):")
    for player in top[:40]:
        print(f"  {int(player['cost']):>3}  {player['nickname']}  ({player['id']})")
    print("\nГерои:")
    for hero in sorted(heroes, key=lambda item: (int(item["position"]), -int(item["rating"]))):
        print(f"  {int(hero['position'])}  {int(hero['rating']):>3}  "
              f"{hero['name']} / {hero['name_en']}  ({hero['id']})")


def check(source: Dict[str, List[Dict[str, Any]]], db) -> List[str]:
    """Проблемы набора в файле данных и в базе."""
    problems = validate_players(source["players"]) + validate_heroes(source["heroes"])
    if db.dotadraft_player_count():
        problems += [f"в базе: {item}" for item in
                     validate_players(db.dotadraft_players()) +
                     validate_heroes(db.dotadraft_heroes())]
    positions = {int(hero["position"]) for hero in source["heroes"]}
    missing = sorted(set(POSITION_LABELS) - positions)
    if missing:
        problems.append("нет героев для позиций: " +
                        ", ".join(POSITION_LABELS[position] for position in missing))
    affordable = sum(1 for player in source["players"] if int(player["cost"]) <= BUDGET)
    if affordable < SQUAD_SIZE:
        problems.append(f"в бюджет {BUDGET} проходит всего {affordable} игроков — "
                        f"состав из {SQUAD_SIZE} не собрать")
    return problems


def apply_costs(db, pairs: List[str], dry_run: bool) -> int:
    """Меняет стоимость игрока: --cost dm=90 (можно несколько раз)."""
    changed = 0
    for pair in pairs:
        if "=" not in pair:
            print(f"  непонятная правка стоимости: {pair} (нужно dm=90)")
            continue
        player_id, _, raw = pair.rpartition("=")
        try:
            cost = int(raw)
        except ValueError:
            print(f"  стоимость не число: {pair}")
            continue
        current = [player for player in db.dotadraft_players()
                   if player["id"] == player_id or player["nickname"].lower() == player_id.lower()]
        if not current:
            print(f"  игрок не найден: {player_id}")
            continue
        player = dict(current[0])
        player["cost"] = cost
        if dry_run:
            print(f"  поменяли бы стоимость: {player['nickname']} → {cost}")
        else:
            db.dotadraft_save_players([player])
            print(f"  стоимость поправлена: {player['nickname']} → {cost}")
        changed += 1
    return changed


def apply_ratings(db, pairs: List[str], dry_run: bool) -> int:
    """Меняет оценку героя: --rating invoker=95 (можно несколько раз)."""
    changed = 0
    for pair in pairs:
        if "=" not in pair:
            print(f"  непонятная правка оценки: {pair} (нужно invoker=95)")
            continue
        hero_id, _, raw = pair.rpartition("=")
        try:
            rating = int(raw)
        except ValueError:
            print(f"  оценка не число: {pair}")
            continue
        current = [hero for hero in db.dotadraft_heroes()
                   if hero["id"] == hero_id or hero["name_en"].lower() == hero_id.lower()]
        if not current:
            print(f"  герой не найден: {hero_id}")
            continue
        hero = dict(current[0])
        hero["rating"] = rating
        if dry_run:
            print(f"  поменяли бы оценку: {hero['name']} → {rating}")
        else:
            db.dotadraft_save_heroes([hero])
            print(f"  оценка поправлена: {hero['name']} → {rating}")
        changed += 1
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Пул «322-0» (Dota 2) в базе")
    parser.add_argument("--db", type=pathlib.Path, help="файл SQLite")
    parser.add_argument("--dsn", help="строка подключения PostgreSQL")
    parser.add_argument("--list", action="store_true", help="показать, что в базе")
    parser.add_argument("--check", action="store_true", help="проверить набор и базу")
    parser.add_argument("--remove", action="append", default=[],
                        help="убрать игрока из пула: --remove dm")
    parser.add_argument("--remove-hero", action="append", default=[],
                        help="убрать героя из пула: --remove-hero magnus")
    parser.add_argument("--cost", action="append", default=[],
                        help="поправить стоимость игрока: --cost dm=90")
    parser.add_argument("--rating", action="append", default=[],
                        help="поправить оценку героя: --rating invoker=95")
    parser.add_argument("--dry-run", action="store_true",
                        help="ничего не менять, только показать план")
    args = parser.parse_args()

    if not args.db and not args.dsn:
        parser.error("укажите --db для SQLite или --dsn для PostgreSQL")

    db = open_database(args.db, args.dsn)
    db.initialize()

    source = {"players": player_rows(), "heroes": hero_rows()}
    if args.check:
        problems = check(source, db)
        print(f"Проверка набора: игроков {len(source['players'])}, "
              f"героев {len(source['heroes'])}, проблем {len(problems)}")
        for problem in problems:
            print(f"  {problem}")
        if problems:
            return 1

    before = (db.dotadraft_player_count(), db.dotadraft_hero_count())
    rows = seed(db, args.dry_run)
    after = (db.dotadraft_player_count(), db.dotadraft_hero_count())
    note = "холостой прогон" if args.dry_run else (
        f"в источнике {len(rows['players'])} игроков и {len(rows['heroes'])} героев")
    print(f"Игроков: было {before[0]}, стало {after[0]}; "
          f"героев: было {before[1]}, стало {after[1]} ({note})")

    if args.cost:
        print(f"Правок стоимости: {apply_costs(db, args.cost, args.dry_run)}")
    if args.rating:
        print(f"Правок оценки: {apply_ratings(db, args.rating, args.dry_run)}")

    for player_id in args.remove:
        if args.dry_run:
            print(f"  убрали бы игрока: {player_id}")
        elif db.dotadraft_delete_player(player_id):
            print(f"  игрок убран: {player_id}")
        else:
            print(f"  игрок не найден: {player_id}")
    for hero_id in args.remove_hero:
        if args.dry_run:
            print(f"  убрали бы героя: {hero_id}")
        elif db.dotadraft_delete_hero(hero_id):
            print(f"  герой убран: {hero_id}")
        else:
            print(f"  герой не найден: {hero_id}")

    if args.list:
        show(db)

    players = db.dotadraft_player_count()
    heroes = db.dotadraft_hero_count()
    if players < SQUAD_SIZE or heroes < SQUAD_SIZE:
        print(f"Внимание: пул неполный (игроков {players}, героев {heroes}) — "
              f"игра не начнётся")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
