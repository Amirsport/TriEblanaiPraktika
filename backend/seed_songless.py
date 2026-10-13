# -*- coding: utf-8 -*-
"""Наполнение базы для игры «Аниме-сонглесс»: треки и записи к ним.

Что делает:
    * заливает исходный набор из backend/songless_data.py в таблицу
      songless_tracks (повторный запуск обновляет справочные сведения,
      а уже привязанные записи, начало и длину фрагмента не затирает);
    * раскладывает **ваши** аудиофайлы по трекам: файлы из папки сшиваются
      с названиями аниме, копируются в front/games/animesongless/audio и
      прописываются в колонку audio;
    * привязывает ссылки на записи (--url) и правит место фрагмента (--start);
    * показывает, что сейчас в базе и что из этого можно играть (--list).

Записей опенингов в проекте нет и не будет: музыка защищена авторским правом.
Пока у трека нет записи, раунд на нём не строится — играть можно только те
треки, для которых владелец сайта положил файл или указал ссылку.

Примеры:
    python backend/seed_songless.py --dsn "postgresql://greenhouse:пароль@localhost:5432/greenhouse"
    python backend/seed_songless.py --dsn "..." --list
    python backend/seed_songless.py --dsn "..." --audio "C:\\music" --map music.json
    python backend/seed_songless.py --dsn "..." --url "Наруто=https://example.org/op.mp3"
    python backend/seed_songless.py --dsn "..." --start "Наруто=42" --length 10
    python backend/seed_songless.py --dsn "..." --clear-audio "Наруто"

Имя файла сшивается с названием аниме без учёта регистра и расширения:
«наруто.mp3» попадёт в «Наруто». Если имена не совпадают, задайте соответствия
файлом --map: {"файл.mp3": "Название аниме"}.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import sys
from typing import Any, Dict, List, Optional

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:  # запуск как модуль: python -m backend.seed_songless
    from .db import DEFAULT_CLIP_LENGTH, open_database
    from .songless_data import DEFAULT_START, seed_rows
except ImportError:  # запуск как файл: python backend/seed_songless.py
    from db import DEFAULT_CLIP_LENGTH, open_database  # type: ignore
    from songless_data import DEFAULT_START, seed_rows  # type: ignore

AUDIO_DIR = ROOT / "front" / "games" / "animesongless" / "audio"
AUDIO_SUFFIXES = (".mp3", ".m4a", ".aac", ".ogg", ".opus", ".wav", ".flac", ".webm", ".mp4")
SAFE_NAME = re.compile(r'[\\/:*?"<>|]+')


def normalize(value: str) -> str:
    """Ключ сравнения имён: регистр и лишние пробелы не важны."""
    return " ".join((value or "").split()).casefold()


def safe_filename(name: str, suffix: str) -> str:
    """Имя файла без символов, недопустимых в пути и в ссылке."""
    cleaned = SAFE_NAME.sub("_", pathlib.Path(name).name).strip()
    return (cleaned or "track") + suffix


def load_map(path: Optional[str]) -> Dict[str, str]:
    """Соответствия «имя файла -> название аниме» из JSON."""
    if not path:
        return {}
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("--map ожидает объект вида {\"файл.mp3\": \"Название аниме\"}")
    return {normalize(key): str(value) for key, value in data.items()}


def seed(db, dry_run: bool) -> List[Dict[str, Any]]:
    """Заливает справочный набор в базу."""
    rows = seed_rows()
    if not dry_run:
        db.songless_save_tracks(rows)
    return rows


def attach_audio(db, folder: pathlib.Path, mapping: Dict[str, str], dry_run: bool) -> int:
    """Копирует файлы из папки в игру и привязывает их к трекам."""
    if not folder.is_dir():
        print(f"  папка не найдена: {folder}")
        return 0
    tracks = {normalize(track["anime"]): track["anime"] for track in db.songless_tracks()}
    attached = 0
    for path in sorted(folder.iterdir()):
        if not path.is_file() or path.suffix.lower() not in AUDIO_SUFFIXES:
            continue
        target = mapping.get(normalize(path.stem)) or tracks.get(normalize(path.stem))
        if not target:
            print(f"  пропуск: {path.name} — нет аниме с таким названием "
                  f"(добавьте пару в --map)")
            continue
        # Путь внутри папки игры: на странице он склеивается с адресом игры.
        file_name = safe_filename(tracks.get(normalize(target), target), path.suffix.lower())
        destination = AUDIO_DIR / file_name
        if not dry_run:
            AUDIO_DIR.mkdir(parents=True, exist_ok=True)
            if path.resolve() != destination.resolve():
                shutil.copy2(path, destination)
            db.songless_set_audio(target, f"audio/{file_name}")
        print(f"  {target} <- {path.name}  ({destination.name})")
        attached += 1
    return attached


def main() -> int:
    parser = argparse.ArgumentParser(description="Треки «Аниме-сонглесса» в базе")
    parser.add_argument("--db", type=pathlib.Path, help="файл SQLite")
    parser.add_argument("--dsn", help="строка подключения PostgreSQL")
    parser.add_argument("--audio", type=pathlib.Path, help="папка с аудиофайлами")
    parser.add_argument("--map", dest="map_file", help="JSON-файл соответствий имён")
    parser.add_argument("--url", action="append", default=[],
                        help="привязать ссылку: --url \"Аниме=https://...\"")
    parser.add_argument("--start", action="append", default=[],
                        help="с какого места играть фрагмент: --start \"Аниме=42\"")
    parser.add_argument("--length", type=float,
                        help="длина фрагмента в секундах (для всех треков или вместе с --url)")
    parser.add_argument("--clear-audio", action="append", default=[],
                        help="снять запись у трека: --clear-audio \"Аниме\"")
    parser.add_argument("--remove", action="append", default=[],
                        help="убрать трек из набора: --remove \"Аниме\"")
    parser.add_argument("--list", action="store_true", help="показать, что в базе")
    parser.add_argument("--dry-run", action="store_true",
                        help="ничего не менять, только показать план")
    args = parser.parse_args()

    if not args.db and not args.dsn:
        parser.error("укажите --db для SQLite или --dsn для PostgreSQL")

    db = open_database(args.db, args.dsn)
    db.initialize()

    before = db.songless_track_count()
    rows = seed(db, args.dry_run)
    after = db.songless_track_count()
    print(f"Треков: было {before}, стало {after} "
          f"({len(rows)} строк в источнике){' — холостой прогон' if args.dry_run else ''}")

    for pair in args.url:
        if "=" not in pair:
            print(f"  ожидался формат «Аниме=ссылка», а получено: {pair}")
            continue
        name, url = (part.strip() for part in pair.split("=", 1))
        if args.dry_run:
            print(f"  привязали бы запись: {name} -> {url}")
        elif db.songless_set_audio(name, url, clip_length=args.length):
            print(f"  запись привязана: {name} -> {url}")
        else:
            print(f"  аниме не найдено: {name}")

    for pair in args.start:
        if "=" not in pair:
            print(f"  ожидался формат «Аниме=секунды», а получено: {pair}")
            continue
        name, value = (part.strip() for part in pair.split("=", 1))
        try:
            seconds = float(value)
        except ValueError:
            print(f"  не число: {value}")
            continue
        if args.dry_run:
            print(f"  сдвинули бы фрагмент: {name} -> {seconds} с")
        elif db.songless_set_clip(name, clip_start=seconds, clip_length=args.length):
            print(f"  фрагмент начинается с {seconds} с: {name}")
        else:
            print(f"  аниме не найдено: {name}")

    for name in args.clear_audio:
        if args.dry_run:
            print(f"  сняли бы запись: {name}")
        elif db.songless_set_audio(name, ""):
            print(f"  запись снята: {name}")
        else:
            print(f"  аниме не найдено: {name}")

    for name in args.remove:
        if args.dry_run:
            print(f"  убрали бы трек: {name}")
        elif db.songless_delete_track(name):
            print(f"  трек убран из набора: {name}")
        else:
            print(f"  аниме не найдено: {name}")

    if args.audio:
        print(f"Аудио из {args.audio}:")
        attached = attach_audio(db, args.audio, load_map(args.map_file), args.dry_run)
        print(f"  привязано файлов: {attached}")

    if args.length and not args.url and not args.start:
        print(f"Длина фрагмента {args.length} с будет применена только вместе с --url или --start")

    if args.list or not (args.audio or args.url or args.start or args.clear_audio or args.remove):
        show(db)
    return 0


def show(db) -> None:
    """Показывает состав набора: что можно играть, а что ждёт записи."""
    items = db.songless_tracks()
    with_audio = [item for item in items if item["audio"]]
    print(f"\nВ базе {len(items)} треков, с записью {len(with_audio)}, "
          f"без записи {len(items) - len(with_audio)}")
    if len(with_audio) < 4:
        print("  Играть пока нельзя: нужно минимум четыре трека с записью")
    for item in items:
        mark = item["audio"] or "нет записи"
        length = item["clip_length"] or DEFAULT_CLIP_LENGTH
        print(f"  {item['anime']:<34} {item['song']:<30} "
              f"фрагмент с {item['clip_start']:g} с, {length:g} с  {mark}")


if __name__ == "__main__":
    sys.exit(main())
