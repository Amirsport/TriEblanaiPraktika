# -*- coding: utf-8 -*-
"""Наполнение базы для игры «Угадай песню за 10 секунд»: песни и записи к ним.

Что делает:
    * заливает исходный набор из backend/songguess_data.py в таблицу
      songguess_tracks (повторный запуск обновляет справочные сведения, а уже
      привязанные записи, начало и длину фрагмента не затирает);
    * раскладывает **ваши** аудиофайлы по песням: файлы из папки сшиваются
      с названиями песен, копируются в front/games/songguess/audio и
      прописываются в колонку audio;
    * привязывает ссылки на записи (--url) и правит место фрагмента (--start);
    * показывает, что сейчас в базе и что из этого можно играть (--list).

Записей песен в проекте нет и не будет: музыка защищена авторским правом.
Пока у песни нет записи, раунд на ней не строится — играть можно только те
песни, для которых владелец сайта положил файл или указал ссылку.

Примеры:
    python backend/seed_songguess.py --dsn "postgresql://greenhouse:пароль@localhost:5432/greenhouse"
    python backend/seed_songguess.py --dsn "..." --list
    python backend/seed_songguess.py --dsn "..." --audio "C:\\music"
    python backend/seed_songguess.py --dsn "..." --audio "C:\\music" --category hiphop --map music.json
    python backend/seed_songguess.py --dsn "..." --url "hiphop-lose-yourself=https://example.org/lose.mp3"
    python backend/seed_songguess.py --dsn "..." --start "hiphop-lose-yourself=42" --length 8
    python backend/seed_songguess.py --dsn "..." --clear-audio "hiphop-lose-yourself"

Имя файла сшивается с песней без учёта регистра и расширения: подходят и
«Lose Yourself.mp3», и «Eminem - Lose Yourself.mp3». Если имена не совпадают,
задайте соответствия файлом --map: {"файл.mp3": "hiphop-lose-yourself"} —
ключом может быть имя файла с расширением или без, а значением — идентификатор
или название песни.

Строк с текстами песен здесь нет и не будет — только название, исполнитель,
год и запись, которую слушает игра.
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

try:  # запуск как модуль: python -m backend.seed_songguess
    from .db import DEFAULT_CLIP_LENGTH, open_database
    from .songguess_data import (
        CATEGORY_LABELS,
        DEFAULT_START,
        SLICE_SECONDS,
        category_blocks,
        seed_rows,
        validate,
    )
except ImportError:  # запуск как файл: python backend/seed_songguess.py
    from db import DEFAULT_CLIP_LENGTH, open_database  # type: ignore
    from songguess_data import (  # type: ignore
        CATEGORY_LABELS,
        DEFAULT_START,
        SLICE_SECONDS,
        category_blocks,
        seed_rows,
        validate,
    )

AUDIO_DIR = ROOT / "front" / "games" / "songguess" / "audio"
AUDIO_SUFFIXES = (".mp3", ".m4a", ".aac", ".ogg", ".opus", ".wav", ".flac", ".webm", ".mp4")
SAFE_NAME = re.compile(r'[\\/:*?"<>|]+')


def normalize(value: str) -> str:
    """Ключ сравнения имён: регистр и лишние пробелы не важны."""
    return " ".join((value or "").split()).casefold()


def safe_filename(name: str, suffix: str) -> str:
    """Имя файла без символов, недопустимых в пути и в ссылке."""
    cleaned = SAFE_NAME.sub("_", pathlib.Path(name).name).strip()
    return (cleaned or "song") + suffix


def load_map(path: Optional[str]) -> Dict[str, str]:
    """Соответствия «имя файла -> песня» из JSON.

    Читаем как utf-8-sig: JSON нередко правят в Блокноте или PowerShell, а они
    добавляют метку порядка байтов, из-за которой обычный utf-8 спотыкается.
    """
    if not path:
        return {}
    try:
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"--map: не получилось прочитать {path}: {exc}") from None
    if not isinstance(data, dict):
        raise SystemExit("--map ожидает объект вида {\"файл.mp3\": \"hiphop-lose-yourself\"}")
    return {normalize(key): str(value) for key, value in data.items()}


def track_index(db, category: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """Указатели на песни: по идентификатору, названию и «исполнитель — название»."""
    index: Dict[str, Dict[str, Any]] = {}
    for track in db.songguess_tracks(category):
        keys = {
            str(track["id"]),
            str(track["title"]),
            f"{track['artist']} — {track['title']}",
            f"{track['artist']} - {track['title']}",
            f"{track['title']} — {track['artist']}",
            f"{track['title']} - {track['artist']}",
        }
        for key in keys:
            index.setdefault(normalize(key), track)
    return index


def seed(db, dry_run: bool) -> List[Dict[str, Any]]:
    """Заливает справочный набор в базу."""
    rows = seed_rows()
    if not dry_run:
        db.songguess_save_tracks(rows)
    return rows


def attach_audio(db, folder: pathlib.Path, mapping: Dict[str, str],
                 category: Optional[str], dry_run: bool) -> int:
    """Копирует файлы из папки в игру и привязывает их к песням."""
    if not folder.is_dir():
        print(f"  папка не найдена: {folder}")
        return 0
    index = track_index(db, category)
    attached = 0
    for path in sorted(folder.iterdir()):
        if not path.is_file() or path.suffix.lower() not in AUDIO_SUFFIXES:
            continue
        key = (mapping.get(normalize(path.stem)) or mapping.get(normalize(path.name))
               or path.stem)
        track = index.get(normalize(key))
        if not track:
            print(f"  пропуск: {path.name} — нет песни с таким названием "
                  f"(добавьте пару в --map)")
            continue
        file_name = safe_filename(str(track["id"]), path.suffix.lower())
        destination = AUDIO_DIR / file_name
        if not dry_run:
            AUDIO_DIR.mkdir(parents=True, exist_ok=True)
            if path.resolve() != destination.resolve():
                shutil.copy2(path, destination)
            db.songguess_set_audio(str(track["id"]), f"audio/{file_name}")
        print(f"  {track['artist']} — {track['title']} <- {path.name}  ({destination.name})")
        attached += 1
    return attached


def apply_values(db, pairs: List[str], value_name: str, setter, dry_run: bool) -> int:
    """Правки на месте: --start id=42, --length 8 или --clear-audio id."""
    changed = 0
    index = track_index(db)
    for pair in pairs:
        if "=" not in pair:
            print(f"  непонятная правка {value_name}: {pair} (нужно id=значение)")
            continue
        key, _, raw = pair.rpartition("=")
        track = index.get(normalize(key))
        if not track:
            print(f"  песня не найдена: {key}")
            continue
        try:
            value = float(raw)
        except ValueError:
            print(f"  значение не число: {pair}")
            continue
        if dry_run:
            print(f"  поменяли бы {value_name}: {track['title']} -> {value}")
        else:
            setter(track, value)
            print(f"  {value_name}: {track['artist']} — {track['title']} -> {value}")
        changed += 1
    return changed


def clear_audio(db, keys: List[str], dry_run: bool) -> int:
    """Снимает запись с песни: она остаётся в наборе, но не играется."""
    cleared = 0
    index = track_index(db)
    for key in keys:
        track = index.get(normalize(key))
        if not track:
            print(f"  песня не найдена: {key}")
            continue
        if dry_run:
            print(f"  сняли бы запись: {track['title']}")
        else:
            db.songguess_set_audio(str(track["id"]), "")
            print(f"  запись снята: {track['artist']} — {track['title']}")
        cleared += 1
    return cleared


def show(db) -> None:
    """Что сейчас в базе: темы, песни и у кого есть запись."""
    tracks = db.songguess_tracks()
    playable = [track for track in tracks if str(track["audio"]).strip()]
    print(f"\nВ базе {len(tracks)} песен, с записью {len(playable)}")
    for block in category_blocks():
        own = [track for track in tracks if track["category"] == block["key"]]
        with_audio = [track for track in own if str(track["audio"]).strip()]
        print(f"  {block['label']:<14} песен {len(own):>3}, с записью {len(with_audio):>3}")
    for track in tracks:
        mark = "♪" if str(track["audio"]).strip() else "·"
        print(f"  {mark} {track['category']:<7} {track['artist']} — {track['title']}"
              f" ({track['year']})  [{track['id']}]")


def main() -> int:
    parser = argparse.ArgumentParser(description="Песни «Угадай песню за 10 секунд»")
    parser.add_argument("--db", type=pathlib.Path, help="файл SQLite")
    parser.add_argument("--dsn", help="строка подключения PostgreSQL")
    parser.add_argument("--audio", type=pathlib.Path, help="папка с аудиофайлами")
    parser.add_argument("--category", help="тема для --audio: аниме, рэп или хип-хоп")
    parser.add_argument("--map", dest="map_file", help="JSON-файл соответствий имён")
    parser.add_argument("--url", action="append", default=[],
                        help="ссылка на запись: --url \"hiphop-lose-yourself=https://…\"")
    parser.add_argument("--start", action="append", default=[],
                        help="с какого места звучит фрагмент: --start \"anime-asterisk=42\"")
    parser.add_argument("--length", type=float,
                        help="сколько секунд звучит фрагмент (по умолчанию как в базе)")
    parser.add_argument("--clear-audio", action="append", default=[],
                        help="снять запись: --clear-audio \"hiphop-lose-yourself\"")
    parser.add_argument("--remove", action="append", default=[],
                        help="убрать песню из набора: --remove \"anime-asterisk\"")
    parser.add_argument("--list", action="store_true", help="показать, что в базе")
    parser.add_argument("--check", action="store_true", help="проверить набор и базу")
    parser.add_argument("--dry-run", action="store_true",
                        help="ничего не менять, только показать план")
    args = parser.parse_args()

    if not args.db and not args.dsn:
        parser.error("укажите --db для SQLite или --dsn для PostgreSQL")

    db = open_database(args.db, args.dsn)
    db.initialize()

    if args.category and args.category not in CATEGORY_LABELS:
        parser.error("--category принимает одну из тем: " +
                     ", ".join(CATEGORY_LABELS))

    if args.check:
        source = seed_rows()
        problems = validate(source)
        print(f"Проверка набора: песен {len(source)}, тем {len(CATEGORY_LABELS)}, "
              f"проблем {len(problems)}")
        for problem in problems:
            print(f"  {problem}")
        if db.songguess_track_count():
            stored_problems = validate(db.songguess_tracks())
            print(f"Проверка базы: песен {db.songguess_track_count()}, "
                  f"проблем {len(stored_problems)}")
            for problem in stored_problems:
                print(f"  {problem}")
        if problems:
            return 1

    before = db.songguess_track_count()
    rows = seed(db, args.dry_run)
    after = db.songguess_track_count()
    print(f"Песен: было {before}, стало {after} "
          f"({len(rows)} строк в источнике){' — холостой прогон' if args.dry_run else ''}")

    if args.audio:
        attached = attach_audio(db, args.audio, load_map(args.map_file),
                                args.category, args.dry_run)
        print(f"Записей привязано: {attached}")

    for pair in args.url:
        if "=" not in pair:
            print(f"  непонятная ссылка: {pair} (нужно id=https://…)")
            continue
        key, _, url = pair.partition("=")
        track = track_index(db).get(normalize(key))
        if not track:
            print(f"  песня не найдена: {key}")
            continue
        if args.dry_run:
            print(f"  привязали бы ссылку: {track['title']} -> {url}")
        else:
            db.songguess_set_audio(str(track["id"]), url)
            print(f"  ссылка привязана: {track['artist']} — {track['title']}")

    if args.start or args.length is not None:
        length = args.length
        changed = apply_values(
            db, args.start, "начало фрагмента",
            lambda track, value: db.songguess_set_audio(
                str(track["id"]), str(track["audio"]), value, length),
            args.dry_run)
        print(f"Правок начала: {changed}")
        if args.start and args.length is None and not args.dry_run:
            print("  подсказка: длина фрагмента не менялась,"
                  " а игра слушает не больше %.0f секунд" % SLICE_SECONDS)

    if args.clear_audio:
        print(f"Записей снято: {clear_audio(db, args.clear_audio, args.dry_run)}")

    for key in args.remove:
        index = track_index(db)
        track = index.get(normalize(key))
        if not track:
            print(f"  песня не найдена: {key}")
            continue
        if args.dry_run:
            print(f"  убрали бы песню: {track['title']}")
        elif db.songguess_delete_track(str(track["id"])):
            print(f"  песня убрана: {track['artist']} — {track['title']}")

    if args.list:
        show(db)

    playable = [track for track in db.songguess_tracks() if str(track["audio"]).strip()]
    if len(playable) < 4:
        print(f"Внимание: записей всего {len(playable)}, а для раунда нужно 4 —"
              " игра не начнётся, пока не добавите аудио")
        return 1
    print(f"Играть можно {len(playable)} песен. Начало фрагмента по умолчанию "
          f"{DEFAULT_START:g} с, длина в базе — {DEFAULT_CLIP_LENGTH:g} с "
          f"(игра слушает не больше {SLICE_SECONDS:g} с)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
