# -*- coding: utf-8 -*-
"""Локальная копия справочника опенингов с рабочего сервера: только названия.

Что переносится: ключ трека, название аниме и название опенинга
(колонки track_key, anime, song таблицы songless_tracks). Записи, обложки,
ссылки на видео, исполнитель и год **не** копируются: самих записей в
репозитории нет, а служебные поля владелец настраивает под свою версию трека.

Зачем: набор из 500+ опенингов живёт на VPS, а локальной базе для разработки
достаточно справочника — без 158 МБ MP3 в таблице audio_clips.

Примеры:
    python _copy_songless_names.py
    python _copy_songless_names.py --dsn "postgresql://greenhouse:пароль@localhost:5432/greenhouse"
    python _copy_songless_names.py --ssh root@203.0.113.10 --key C:\\Users\\me\\.ssh\\id_rsa
    python _copy_songless_names.py --csv data\\songless_vps_names.csv --list

Повторный запуск безопасен: строки обновляются по track_key (уникальный ключ
трека), уже привязанные записи и оформление трека не затрагиваются.
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import pathlib
import subprocess
import sys
from datetime import datetime, timezone
from typing import Dict, List

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

try:  # запуск как модуль: python -m _copy_songless_names
    from backend.db import open_database
except ImportError:  # запуск как файл
    from backend.db import open_database  # type: ignore

DEFAULT_CSV = ROOT / "data" / "songless_vps_names.csv"
DEFAULT_SSH = "root@195.208.3.38"
DEFAULT_KEY = pathlib.Path.home() / ".ssh" / "id_rsa"
REMOTE_SQL = ("\\copy (select track_key, anime, song from songless_tracks order by id) "
              "to stdout with (format csv)")


def default_dsn() -> str:
    """Строка подключения: --dsn, GREENHOUSE_DSN или data/dsn.txt."""
    dsn_file = ROOT / "data" / "dsn.txt"
    if dsn_file.exists():
        return dsn_file.read_text(encoding="utf-8").strip()
    return ""


def fetch_names(ssh_target: str, key: pathlib.Path, database: str) -> List[Dict[str, str]]:
    """Забирает справочник с сервера одним запросом psql в CSV."""
    remote = f"sudo -u postgres psql -X -q -d {database} -c '{REMOTE_SQL}'"
    command = ["ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20",
               "-i", str(key), ssh_target, remote]
    result = subprocess.run(command, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise SystemExit(f"ssh/psql завершились с кодом {result.returncode}: "
                         f"{(result.stderr or '').strip()}")
    rows: List[Dict[str, str]] = []
    for record in csv.reader(io.StringIO(result.stdout)):
        if len(record) < 3:
            continue
        track_key, anime, song = (record[0].strip(), record[1].strip(), record[2].strip())
        if not track_key or not anime:
            continue
        rows.append({"track_key": track_key, "anime": anime, "song": song})
    return rows


def save_rows(db, rows: List[Dict[str, str]]) -> int:
    """Обновляет названия у известных треков и добавляет новые."""
    stamp = datetime.now(timezone.utc)
    with db.connect() as connection:
        with connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO songless_tracks (track_key, anime, song, updated_at) "
                "VALUES (%s, %s, %s, %s) "
                "ON CONFLICT (track_key) DO UPDATE SET "
                "anime = EXCLUDED.anime, song = EXCLUDED.song, "
                "updated_at = EXCLUDED.updated_at",
                [(row["track_key"], row["anime"], row["song"], stamp) for row in rows],
            )
    return len(rows)


def report(db, rows: List[Dict[str, str]]) -> None:
    """Что теперь в локальной базе и чего в ней не хватает."""
    server_keys = {row["track_key"] for row in rows}
    local = db.songless_tracks()
    local_keys = {str(track.get("track_key") or track.get("anime")) for track in local}
    extra = sorted(local_keys - server_keys) if server_keys else []
    with_audio = sum(1 for track in local if track.get("audio"))
    anime = len({track.get("anime") for track in local if track.get("anime")})
    print(f"  строк в локальной базе: {len(local)}")
    print(f"  уникальных аниме:       {anime}")
    if server_keys:
        print(f"  получено с сервера:     {len(rows)}")
    print(f"  с записью (audio):      {with_audio}")
    if extra:
        print(f"  есть только локально:   {len(extra)} (перенос их не трогал)")
    print("  примеры:")
    for track in local[:5]:
        print(f"    {track.get('anime')} — {track.get('song') or '(без названия опенинга)'}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Копия справочника опенингов с сервера: только аниме и названия")
    parser.add_argument("--dsn", default=os.environ.get("GREENHOUSE_DSN") or default_dsn(),
                        help="строка подключения к локальной базе")
    parser.add_argument("--ssh", default=DEFAULT_SSH,
                        help="адрес сервера, например root@203.0.113.10")
    parser.add_argument("--key", default=str(DEFAULT_KEY),
                        help="SSH-ключ (по умолчанию ~/.ssh/id_rsa)")
    parser.add_argument("--database", default="greenhouse", help="имя базы на сервере")
    parser.add_argument("--csv", default=str(DEFAULT_CSV),
                        help="куда сохранить выгрузку с сервера")
    parser.add_argument("--from-csv", default="",
                        help="взять данные из файла, не обращаясь к серверу")
    parser.add_argument("--dry-run", action="store_true",
                        help="только показать, что будет перенесено")
    parser.add_argument("--list", action="store_true", help="показать текущий набор и выйти")
    args = parser.parse_args()

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    db = open_database(dsn=args.dsn)
    db.initialize()

    if args.list:
        report(db, [])
        return 0

    if args.from_csv:
        source = pathlib.Path(args.from_csv)
        rows = []
        for record in csv.reader(io.StringIO(source.read_text(encoding="utf-8"))):
            if len(record) >= 3 and record[0].strip() and record[1].strip():
                rows.append({"track_key": record[0].strip(),
                             "anime": record[1].strip(),
                             "song": record[2].strip()})
        print(f"читаю из файла {source}: строк {len(rows)}")
    else:
        print(f"запрашиваю справочник с {args.ssh}...")
        rows = fetch_names(args.ssh, pathlib.Path(args.key), args.database)
        print(f"получено строк: {len(rows)}")
        if not args.dry_run:
            target = pathlib.Path(args.csv)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["track_key", "anime", "song"])
                writer.writerows([[r["track_key"], r["anime"], r["song"]] for r in rows])
            print(f"выгрузка сохранена: {target}")

    if not rows:
        raise SystemExit("нечего переносить: справочник пуст")

    if args.dry_run:
        print("--dry-run: база не менялась, первые строки:")
        for row in rows[:5]:
            print(f"  {row['anime']} — {row['song']}")
        return 0

    saved = save_rows(db, rows)
    print(f"записано строк: {saved}")
    report(db, rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())