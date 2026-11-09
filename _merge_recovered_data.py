# -*- coding: utf-8 -*-
"""Возврат данных из резервной копии в живую базу «умной теплицы».

Зачем нужен. Восстановление дампа на VPS идёт через `pg_dump --clean --if-exists`,
то есть заливает таблицы целиком (DROP → CREATE → COPY) и затирает то, что было
в базе. Если такой дамп снят не с сервера, а с устаревшей локальной базы, данные
сервера теряются. Здесь наоборот: из старой копии **добирается** то, чего в
живой базе сейчас нет, а существующее не трогается.

Что делает:
    * подключается к живой базе (`--live-dsn`) и к базе со старой копией
      (`--recovered-dsn`, например `greenhouse_recovered`, куда залит дамп);
    * пользователей сопоставляет **по логину**, а не по id — поэтому номера
      могут быть разными, а дубли не появляются;
    * добавляет отсутствующих пользователей вместе с профилями (аватары
      переносятся как байты), состоянием панели, партиями Narutodle и
      журналами прогонов игр; ссылки на пользователей пересчитывает на новые id;
    * по умолчанию ничего не пишет — только показывает, что добавит
      (--apply включает запись).

Примеры:
    # что добавится (без записи)
    python _merge_recovered_data.py --recovered-dsn "postgresql://greenhouse:пароль@localhost:5432/greenhouse_recovered"

    # применить
    python _merge_recovered_data.py --recovered-dsn "..." --apply

Живая строка подключения берётся из --live-dsn, переменной GREENHOUSE_DSN или
файла data/dsn.txt.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parent
DEFAULT_DSN_FILE = ROOT / "data" / "dsn.txt"

# Таблицы, которые переносим. Для каждой — колонки, ссылающиеся на пользователя,
# и признак, по которому отличаем уже существующую запись (чтобы повторный
# запуск не удваивал историю).
USER_LINKS = {
    "user_profiles": ("user_id",),
    "user_states": ("user_id",),
    "narutodle_matches": ("player1_id", "player2_id", "winner_id"),
    "songguess_runs": ("user_id",),
    "csdraft_runs": ("user_id",),
    "raporder_matches": ("player1_id", "player2_id", "winner_id"),
}

# Как понять, что такая запись уже есть в живой базе (для таблиц-журналов).
DEDUPE = {
    "narutodle_matches": ("played_at", "player1_name", "player2_name", "target", "round_number"),
    "songguess_runs": ("played_at", "username", "rounds", "score"),
    "csdraft_runs": ("played_at", "username", "rounds_placeholder"),
    "raporder_matches": ("played_at", "player1_name", "player2_name", "rounds"),
}
DEDUPE["csdraft_runs"] = ("played_at", "username", "wins", "losses", "stage")


def read_live_dsn(explicit: Optional[str]) -> str:
    """Строка подключения к живой базе: аргумент, переменная или data/dsn.txt."""
    if explicit:
        return explicit.strip()
    from_env = (os.environ.get("GREENHOUSE_DSN") or "").strip()
    if from_env:
        return from_env
    if DEFAULT_DSN_FILE.is_file():
        value = DEFAULT_DSN_FILE.read_text(encoding="utf-8-sig").strip()
        if value:
            return value
    raise SystemExit("Укажите --live-dsn, переменную GREENHOUSE_DSN или файл data/dsn.txt")


def columns(conn: Any, table: str) -> List[str]:
    """Порядок колонок таблицы — так строки переносятся без ручных списков."""
    rows = conn.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = %s ORDER BY ordinal_position",
        (table,),
    ).fetchall()
    return [row["column_name"] for row in rows]


def fetch_all(conn: Any, table: str) -> List[Dict[str, Any]]:
    """Все строки таблицы (колонки берём из самой таблицы)."""
    names = columns(conn, table)
    rows = conn.execute(f"SELECT {', '.join(names)} FROM {table}").fetchall()
    return [dict(row) for row in rows]


def remap_ids(value: Any, id_map: Dict[int, Optional[int]]) -> Any:
    """Пересчитывает список идентификаторов вида «3,17,42» на новые номера."""
    if value is None or str(value).strip() == "":
        return value
    parts: List[str] = []
    for item in str(value).split(","):
        piece = item.strip()
        if piece.isdigit():
            new_id = id_map.get(int(piece))
            parts.append(str(new_id) if new_id is not None else piece)
        elif piece:
            parts.append(piece)
    return ",".join(parts)


def merge_users(live: Any, recovered: Any, apply_changes: bool,
                report: List[str]) -> Tuple[Dict[int, Optional[int]], List[str]]:
    """Добавляет отсутствующих пользователей; возвращает карту id и их логины."""
    rec_users = fetch_all(recovered, "users")
    live_ids = {row["username"]: row["id"] for row in fetch_all(live, "users")}

    id_map: Dict[int, Optional[int]] = {}
    added_names: List[str] = []
    for user in rec_users:
        name = str(user["username"])
        if name in live_ids:
            id_map[int(user["id"])] = int(live_ids[name])
            continue
        new_id: Optional[int] = None
        if apply_changes:
            row = live.execute(
                "INSERT INTO users (username, password_hash, role, created_at) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                (name, user["password_hash"], user["role"], user["created_at"]),
            ).fetchone()
            new_id = int(row["id"])
            live_ids[name] = new_id
        id_map[int(user["id"])] = new_id
        added_names.append(name)

    report.append(f"users: добавлено {len(added_names)}, уже было {len(rec_users) - len(added_names)}")
    return id_map, added_names


def merge_table(live: Any, recovered: Any, table: str,
                id_map: Dict[int, Optional[int]], apply_changes: bool,
                report: List[str]) -> None:
    """Переносит строки таблицы, пересчитывая ссылки на пользователей по карте."""
    links = USER_LINKS[table]
    names = [name for name in columns(live, table) if name != "id"]
    keys = DEDUPE.get(table)

    seen = set()
    if keys:
        for row in fetch_all(live, table):
            seen.add(tuple(str(row.get(key)) for key in keys))

    added = existing = orphan = 0
    for row in fetch_all(recovered, table):
        data = dict(row)
        safe = True
        for link in links:
            old = data.get(link)
            if old is None:
                continue
            new = id_map.get(int(old))
            if new is None:  # пользователя нет ни в старой базе, ни в новой
                safe = False
            data[link] = new
        if "player_ids" in data:
            data["player_ids"] = remap_ids(data["player_ids"], id_map)
        if not safe:
            orphan += 1
            continue

        if keys:
            key = tuple(str(data.get(name)) for name in keys)
            if key in seen:
                existing += 1
                continue
            seen.add(key)
        else:
            found = live.execute(
                f"SELECT 1 FROM {table} WHERE user_id = %s", (data.get("user_id"),)
            ).fetchone()
            if found:
                existing += 1
                continue

        added += 1
        if apply_changes:
            placeholders = ", ".join(["%s"] * len(names))
            live.execute(
                f"INSERT INTO {table} ({', '.join(names)}) VALUES ({placeholders})",
                tuple(data.get(name) for name in names),
            )

    report.append(f"{table}: добавлено {added}, уже было {existing}, без пользователя {orphan}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Возврат данных из резервной копии в живую базу теплицы",
    )
    parser.add_argument("--live-dsn", help="живая база (иначе GREENHOUSE_DSN или data/dsn.txt)")
    parser.add_argument("--recovered-dsn", required=True,
                        help="база с залитой старой копией, например …/greenhouse_recovered")
    parser.add_argument("--apply", action="store_true",
                        help="действительно записать; без него — только показать план")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    args = build_parser().parse_args(argv)
    live_dsn = read_live_dsn(args.live_dsn)

    try:
        import psycopg  # noqa: PLC0415
        from psycopg.rows import dict_row  # noqa: PLC0415
    except ImportError:
        print("Нужен psycopg:\n"
              f"  {sys.executable} -m pip install -r requirements-fetch.txt")
        return 2

    report: List[str] = []
    report.append("РЕЖИМ: запись включена (--apply)" if args.apply
                  else "РЕЖИМ: холостой прогон — ничего не пишется (добавьте --apply)")

    with psycopg.connect(live_dsn, row_factory=dict_row) as live, \
            psycopg.connect(args.recovered_dsn, row_factory=dict_row) as recovered:
        id_map, added_names = merge_users(live, recovered, args.apply, report)
        if added_names:
            report.append("  новые логины: " + ", ".join(sorted(added_names)))
        for table in USER_LINKS:
            merge_table(live, recovered, table, id_map, args.apply, report)
        if args.apply:
            live.commit()
        else:
            live.rollback()

    print("\n".join(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())