# -*- coding: utf-8 -*-
"""Перенос данных теплицы из SQLite в PostgreSQL.

Запуск:
    python backend/migrate_to_postgres.py --dsn postgresql://greenhouse:пароль@localhost:5432/greenhouse
    python backend/migrate_to_postgres.py --dsn ... --from data/greenhouse.sqlite3
    python backend/migrate_to_postgres.py --dsn ... --replace

Схема в PostgreSQL создаётся автоматически (backend/schema_postgres.sql), затем
копируются таблицы zones, readings, zone_devices, settings, state, logs.
Повторный запуск безопасен: строки обновляются по первичному ключу, дубликатов нет.
Ключ --replace предварительно очищает таблицы в PostgreSQL.
Чтобы перенести новую таблицу, добавьте её в schema_postgres.sql и в TRANSFERS.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:  # запуск как модуль: python -m backend.migrate_to_postgres
    from .db_postgres import BOOL_COLUMNS, TIME_COLUMNS, TRANSFERS, PostgresDatabase, parse_iso
except ImportError:  # запуск как файл: python backend/migrate_to_postgres.py
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from db_postgres import BOOL_COLUMNS, TIME_COLUMNS, TRANSFERS, PostgresDatabase, parse_iso  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SQLITE = ROOT / "data" / "greenhouse.sqlite3"

TRUNCATE = "TRUNCATE zones, readings, zone_devices, settings, state, logs RESTART IDENTITY CASCADE"

# После копирования с явными id нужно сдвинуть последовательности BIGSERIAL.
SEQUENCE_FIXES = ("readings", "logs")


def _convert(column: str, value: Any) -> Any:
    if value is None:
        return None
    if column in BOOL_COLUMNS:
        return bool(value)
    if column in TIME_COLUMNS:
        return parse_iso(value)
    return value


def _read_sqlite(path: Path, table: str, columns: Tuple[str, ...], limit: int | None) -> List[Tuple[Any, ...]]:
    query = f"SELECT {', '.join(columns)} FROM {table}"
    if limit:
        query += " ORDER BY id DESC LIMIT ?"
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as source:
        source.row_factory = sqlite3.Row
        try:
            rows = source.execute(query, (limit,) if limit else ()).fetchall()
        except sqlite3.Error as exc:
            raise RuntimeError(f"Не удалось прочитать таблицу {table} из {path}: {exc}") from exc
    return [tuple(_convert(column, row[column]) for column in columns) for row in rows]


def _copy_table(pg: PostgresDatabase, table: str, columns: Tuple[str, ...], conflict: Tuple[str, ...],
                rows: List[Tuple[Any, ...]]) -> int:
    if not rows:
        return 0
    marks = ", ".join(["%s"] * len(columns))
    updates = [c for c in columns if c not in conflict and c != "id"]
    action = "DO UPDATE SET " + ", ".join(f"{c} = EXCLUDED.{c}" for c in updates) if updates else "DO NOTHING"
    sql = (f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({marks}) "
           f"ON CONFLICT ({', '.join(conflict)}) {action}")
    with pg.connect() as db:
        with db.cursor() as cur:
            cur.executemany(sql, rows)
    return len(rows)


def migrate(sqlite_path: Path, dsn: str, replace: bool,
            history_limit: int | None) -> Tuple[Dict[str, int], Dict[str, int]]:
    if not sqlite_path.exists():
        raise FileNotFoundError(f"Файл SQLite не найден: {sqlite_path}")

    pg = PostgresDatabase(dsn)
    pg.initialize()

    if replace:
        with pg.connect() as db:
            db.execute(TRUNCATE)
        pg.initialize()  # возвращаем базовые строки (участки, настройки, состояние)

    copied: Dict[str, int] = {}
    for table, columns, conflict in TRANSFERS:
        limit = history_limit if table == "readings" else None
        rows = _read_sqlite(sqlite_path, table, columns, limit)
        copied[table] = _copy_table(pg, table, columns, conflict, rows)

    with pg.connect() as db:
        for table in SEQUENCE_FIXES:
            db.execute(
                f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                f"GREATEST(COALESCE(MAX(id), 1), 1), COUNT(*) > 0) FROM {table}"
            )
        totals = {table: db.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
                  for table, _, _ in TRANSFERS}
    return copied, totals


def main() -> None:
    parser = argparse.ArgumentParser(description="Перенос данных теплицы из SQLite в PostgreSQL")
    parser.add_argument("--dsn", default=os.environ.get("GREENHOUSE_DSN"),
                        help="строка подключения PostgreSQL (или переменная GREENHOUSE_DSN)")
    parser.add_argument("--from", dest="source", type=Path, default=DEFAULT_SQLITE,
                        help=f"файл SQLite (по умолчанию {DEFAULT_SQLITE})")
    parser.add_argument("--replace", action="store_true",
                        help="очистить таблицы в PostgreSQL перед переносом")
    parser.add_argument("--history-limit", type=int, default=None,
                        help="перенести только N последних показаний на участок")
    args = parser.parse_args()

    if not args.dsn:
        parser.error("не задан --dsn (или переменная окружения GREENHOUSE_DSN)")

    copied, totals = migrate(args.source, args.dsn, args.replace, args.history_limit)
    print(f"Источник: {args.source}")
    print("Перенесено строк из SQLite:")
    for name, count in copied.items():
        print(f"  {name}: {count}")
    print("Сейчас в PostgreSQL:")
    for name, count in totals.items():
        print(f"  {name}: {count}")
    print("Готово. База видна в pgAdmin: Servers → PostgreSQL 17 → база из DSN.")


if __name__ == "__main__":
    main()
