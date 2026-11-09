# -*- coding: utf-8 -*-
"""Наполнение базы для игры «322-0» (драфт по Dota 2, Streamers Battle 13).

Что делает:
    * заливает пул игроков со стоимостями и позициями (dotadraft_players),
      пул героев с позициями и оценками (dotadraft_heroes) и оценки героев под
      игроков (dotadraft_player_heroes) из backend/dotadraft_data.py;
      повторный запуск обновляет строки по идентификатору, поэтому и ники,
      и стоимости удобнее править в файле данных и заливать заново;
    * показывает, что уже лежит в базе (--list) и проверяет набор (--check);
    * убирает игрока или героя из пула (--remove, --remove-hero);
    * правит стоимость на месте (--cost dm=90), свою позицию игрока
      (--position dm=1) и оценку героя (--rating invoker=95);
    * ведёт оценки пар «игрок + герой» по матчам игрока на герое:
      --pair satanic=anti-mage=88 и --remove-pair satanic=anti-mage.

Позиция игрока — это его роль (1 керри … 5 пятёрка), 0 значит «неизвестна»:
такой игрок не получает ни надбавки за свою позицию, ни минуса за чужую.
Оценка пары (герой под игрока) — из матчей игрока на Dotabuff; пока пары нет,
движок берёт обычную оценку героя.

Журнал прогонов «322-0» живёт в общей таблице csdraft_runs с game = 'dota322',
поэтому этот скрипт его не трогает.

Примеры:
    python backend/seed_dotadraft.py --db data/greenhouse.sqlite3
    python backend/seed_dotadraft.py --db data/greenhouse.sqlite3 --list
    python backend/seed_dotadraft.py --dsn "postgresql://greenhouse:пароль@localhost:5432/greenhouse"
    python backend/seed_dotadraft.py --db data/greenhouse.sqlite3 --cost dm=90
    python backend/seed_dotadraft.py --db data/greenhouse.sqlite3 --position dm=1
    python backend/seed_dotadraft.py --db data/greenhouse.sqlite3 --pair satanic=anti-mage=88
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
        MID_COST_LIMIT,
        POSITION_LABELS,
        SQUAD_SIZE,
        hero_rows,
        player_hero_rows,
        player_rows,
        validate_heroes,
        validate_player_heroes,
        validate_players,
    )
except ImportError:  # запуск как файл: python backend/seed_dotadraft.py
    from db import open_database  # type: ignore
    from dotadraft_data import (  # type: ignore
        BUDGET,
        MID_COST_LIMIT,
        POSITION_LABELS,
        SQUAD_SIZE,
        hero_rows,
        player_hero_rows,
        player_rows,
        validate_heroes,
        validate_player_heroes,
        validate_players,
    )


def seed(db, dry_run: bool) -> Dict[str, List[Dict[str, Any]]]:
    """Заливает пул игроков, пул героев и оценки пар в базу."""
    players = player_rows()
    heroes = hero_rows()
    pairs = player_hero_rows()
    if not dry_run:
        db.dotadraft_save_players(players)
        db.dotadraft_save_heroes(heroes)
        if pairs:
            db.dotadraft_save_player_hero_ratings(pairs)
    return {"players": players, "heroes": heroes, "pairs": pairs}


def show(db) -> None:
    """Что сейчас в базе: игроки по стоимости, герои по позициям и пары."""
    players = db.dotadraft_players()
    heroes = db.dotadraft_heroes()
    pairs = db.dotadraft_player_hero_ratings()
    per_position: Dict[int, int] = {}
    for hero in heroes:
        per_position[int(hero["position"])] = per_position.get(int(hero["position"]), 0) + 1
    known = [player for player in players if int(player.get("position") or 0)]
    print(f"\nВ базе {len(players)} игроков и {len(heroes)} героев, "
          f"оценок пар: {len(pairs)}")
    print(f"Своя позиция известна у {len(known)} игроков")
    positions = ", ".join(f"{POSITION_LABELS[position]}: {per_position.get(position, 0)}"
                          for position in sorted(POSITION_LABELS))
    print(f"Герои по позициям — {positions}")
    top = sorted(players, key=lambda player: (-int(player["cost"]), player["id"]))
    print("\nИгроки (первые 40 по стоимости):")
    for player in top[:40]:
        own = int(player.get("position") or 0)
        mark = POSITION_LABELS.get(own, "—") if own else "—"
        print(f"  {int(player['cost']):>3}  {player['nickname']}  ({player['id']})  {mark}")
    print("\nГерои:")
    for hero in sorted(heroes, key=lambda item: (int(item["position"]), -int(item["rating"]))):
        print(f"  {int(hero['position'])}  {int(hero['rating']):>3}  "
              f"{hero['name']} / {hero['name_en']}  ({hero['id']})")
    if pairs:
        print("\nОценки героев под игроков:")
        for pair in pairs:
            print(f"  {pair['player_id']} + {pair['hero_id']}: {int(pair['rating'])}")


def check(source: Dict[str, List[Dict[str, Any]]], db) -> List[str]:
    """Проблемы набора в файле данных и в базе."""
    problems = (validate_players(source["players"]) + validate_heroes(source["heroes"])
                + validate_player_heroes(source.get("pairs") or []))
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
    cheap = sum(1 for player in source["players"]
                if int(player["cost"]) < MID_COST_LIMIT)
    if cheap < 8:
        problems.append(f"на мид (дешевле {MID_COST_LIMIT} очков) проходит "
                        f"всего {cheap} игроков — на восемь команд этого мало")
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


def apply_positions(db, pairs: List[str], dry_run: bool) -> int:
    """Меняет свою позицию игрока: --position dm=1 (можно несколько раз)."""
    changed = 0
    for pair in pairs:
        if "=" not in pair:
            print(f"  непонятная правка позиции: {pair} (нужно dm=1)")
            continue
        player_id, _, raw = pair.rpartition("=")
        try:
            position = int(raw)
        except ValueError:
            print(f"  позиция не число: {pair}")
            continue
        if position not in POSITION_LABELS and position != 0:
            print(f"  неизвестная позиция: {position} (нужно 0–{max(POSITION_LABELS)})")
            continue
        current = [player for player in db.dotadraft_players()
                   if player["id"] == player_id
                   or player["nickname"].lower() == player_id.lower()]
        if not current:
            print(f"  игрок не найден: {player_id}")
            continue
        player = current[0]
        if dry_run:
            print(f"  поменяли бы позицию: {player['nickname']} → "
                  f"{POSITION_LABELS.get(position, 'неизвестна')}")
        else:
            db.dotadraft_set_player_position(player["id"], position)
            print(f"  позиция поправлена: {player['nickname']} → "
                  f"{POSITION_LABELS.get(position, 'неизвестна')}")
        changed += 1
    return changed


def apply_pairs(db, pairs: List[str], dry_run: bool) -> int:
    """Ведёт оценку пары: --pair satanic=anti-mage=88 (можно несколько раз)."""
    changed = 0
    for pair in pairs:
        parts = pair.split("=")
        if len(parts) != 3:
            print(f"  непонятная пара: {pair} (нужно satanic=anti-mage=88)")
            continue
        player_id, hero_id, raw = (part.strip() for part in parts)
        try:
            rating = int(raw)
        except ValueError:
            print(f"  оценка не число: {pair}")
            continue
        player = find_player(db, player_id)
        hero = find_hero(db, hero_id)
        if not player:
            print(f"  игрок не найден: {player_id}")
            continue
        if not hero:
            print(f"  герой не найден: {hero_id}")
            continue
        if dry_run:
            print(f"  записали бы пару: {player['nickname']} + {hero['name']} → {rating}")
        else:
            db.dotadraft_save_player_hero_ratings([{
                "player_id": player["id"], "hero_id": hero["id"], "rating": rating,
            }])
            print(f"  пара записана: {player['nickname']} + {hero['name']} → {rating}")
        changed += 1
    return changed


def remove_pairs(db, pairs: List[str], dry_run: bool) -> int:
    """Убирает оценку пары: --remove-pair satanic=anti-mage."""
    changed = 0
    for pair in pairs:
        parts = pair.split("=")
        if len(parts) != 2:
            print(f"  непонятная пара: {pair} (нужно satanic=anti-mage)")
            continue
        player_id, hero_id = (part.strip() for part in parts)
        player = find_player(db, player_id)
        hero = find_hero(db, hero_id)
        if not player or not hero:
            print(f"  пара не найдена: {pair}")
            continue
        if dry_run:
            print(f"  убрали бы пару: {player['nickname']} + {hero['name']}")
        elif db.dotadraft_delete_player_hero(player["id"], hero["id"]):
            print(f"  пара убрана: {player['nickname']} + {hero['name']}")
        else:
            print(f"  пары и не было: {player['nickname']} + {hero['name']}")
        changed += 1
    return changed


def find_player(db, player_id: str):
    """Игрок базы по идентификатору или нику."""
    wanted = str(player_id or "").strip().lower()
    for player in db.dotadraft_players():
        if player["id"].lower() == wanted or player["nickname"].lower() == wanted:
            return player
    return None


def find_hero(db, hero_id: str):
    """Герой базы по идентификатору, русскому или английскому имени."""
    wanted = str(hero_id or "").strip().lower()
    for hero in db.dotadraft_heroes():
        if hero["id"].lower() == wanted or hero["name"].lower() == wanted \
                or hero["name_en"].lower() == wanted:
            return hero
    return None


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
    parser.add_argument("--position", action="append", default=[],
                        help="поправить свою позицию игрока: --position dm=1")
    parser.add_argument("--rating", action="append", default=[],
                        help="поправить оценку героя: --rating invoker=95")
    parser.add_argument("--pair", action="append", default=[],
                        help="оценка героя под игрока: --pair satanic=anti-mage=88")
    parser.add_argument("--remove-pair", action="append", default=[],
                        help="убрать оценку пары: --remove-pair satanic=anti-mage")
    parser.add_argument("--dry-run", action="store_true",
                        help="ничего не менять, только показать план")
    args = parser.parse_args()

    if not args.db and not args.dsn:
        parser.error("укажите --db для SQLite или --dsn для PostgreSQL")

    db = open_database(args.db, args.dsn)
    db.initialize()

    source = {"players": player_rows(), "heroes": hero_rows(), "pairs": player_hero_rows()}
    if args.check:
        problems = check(source, db)
        print(f"Проверка набора: игроков {len(source['players'])}, "
              f"героев {len(source['heroes'])}, пар {len(source['pairs'])}, "
              f"проблем {len(problems)}")
        for problem in problems:
            print(f"  {problem}")
        if problems:
            return 1

    before = (db.dotadraft_player_count(), db.dotadraft_hero_count(),
              db.dotadraft_player_hero_count())
    rows = seed(db, args.dry_run)
    after = (db.dotadraft_player_count(), db.dotadraft_hero_count(),
             db.dotadraft_player_hero_count())
    note = "холостой прогон" if args.dry_run else (
        f"в источнике {len(rows['players'])} игроков, {len(rows['heroes'])} героев "
        f"и {len(rows['pairs'])} пар")
    print(f"Игроков: было {before[0]}, стало {after[0]}; "
          f"героев: было {before[1]}, стало {after[1]}; "
          f"пар: было {before[2]}, стало {after[2]} ({note})")

    if args.cost:
        print(f"Правок стоимости: {apply_costs(db, args.cost, args.dry_run)}")
    if args.position:
        print(f"Правок позиции: {apply_positions(db, args.position, args.dry_run)}")
    if args.rating:
        print(f"Правок оценки: {apply_ratings(db, args.rating, args.dry_run)}")
    if args.pair:
        print(f"Записанных пар: {apply_pairs(db, args.pair, args.dry_run)}")
    if args.remove_pair:
        print(f"Убранных пар: {remove_pairs(db, args.remove_pair, args.dry_run)}")

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
