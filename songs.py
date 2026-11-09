#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Фрагменты песен для игр «Угадай песню» и «Аниме-сонглесс» — сразу в базу.

Что делает:
    * берёт песни из базы (`songguess_tracks` и `songless_tracks`), а на пустой
      базе сначала заливает исходный набор;
    * находит для каждой песни ваш аудиофайл — по названию, исполнителю,
      идентификатору или по таблице соответствий `--map`;
    * вырезает фрагмент через ffmpeg и кладёт MP3-байты в таблицу `audio_clips`;
    * ставит в колонку `audio` маркер `db:clip`, чтобы сервер отдавал запись
      из базы, а игра считала песню доступной.

На диск ничего не сохраняется. Скачивать музыку из интернета скрипт не умеет:
используйте только те записи, на которые у вас есть права.

Примеры:
    python songs.py
    python songs.py --only songguess --audio "C:\\music"
    python songs.py --audio authorized_audio --force
    python songs.py --db data/greenhouse.sqlite3 --dry-run
    python songs.py --dsn "postgresql://greenhouse:пароль@localhost:5432/greenhouse"
    python songs.py --map music.json --limit 5

Для нарезки нужен ffmpeg: либо установленный в системе, либо пакет
imageio-ffmpeg (см. requirements-songs.txt).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.db import AUDIO_IN_DB, open_database
from backend.songguess_data import DEFAULT_CLIP as SONGGUESS_CLIP
from backend.songguess_data import seed_rows as songguess_seed_rows
from backend.songless_data import DEFAULT_CLIP as SONGLESS_CLIP
from backend.songless_data import seed_rows as songless_seed_rows

GAMES = ("songguess", "songless")
AUDIO_SUFFIXES = {
    ".mp3", ".m4a", ".aac", ".ogg", ".opus", ".wav", ".flac", ".webm", ".mp4",
}
DEFAULT_AUDIO_DIR = ROOT / "authorized_audio"
DEFAULT_DSN_FILE = ROOT / "data" / "dsn.txt"
DEFAULT_CLIP = {"songguess": SONGGUESS_CLIP, "songless": SONGLESS_CLIP}


def normalize(value: Any) -> str:
    """Ключ сравнения имён: регистр и лишние пробелы не важны."""
    return " ".join(str(value or "").split()).casefold()


def track_key(game: str, track: Dict[str, Any]) -> str:
    """Ключ записи в audio_clips: id песни или ключ трека аниме."""
    if game == "songless":
        return str(track.get("track_key") or track.get("anime") or "")
    return str(track.get("id") or "")


def track_variants(game: str, track: Dict[str, Any]) -> List[str]:
    """Как может называться файл с этой песней (в порядке приоритета)."""
    if game == "songless":
        title = str(track.get("song") or "")
        artist = str(track.get("artist") or "")
        keys = [track.get("anime"), title]
    else:
        title = str(track.get("title") or "")
        artist = str(track.get("artist") or "")
        keys = [track.get("id"), title]

    keys += [
        f"{artist} - {title}",
        f"{title} - {artist}",
        f"{artist} — {title}",
        f"{title} — {artist}",
    ]
    result: List[str] = []
    for key in keys:
        value = normalize(key)
        if value and value not in result:
            result.append(value)
    return result


def load_map(path: Optional[str]) -> Dict[str, str]:
    """Соответствия «файл -> песня» из JSON (как в seed_songguess.py)."""
    if not path:
        return {}
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"--map: не получилось прочитать {path}: {exc}") from None
    if not isinstance(data, dict):
        raise SystemExit(
            '--map ожидает объект вида {"файл.mp3": "anime-again"}'
        )
    return {normalize(key): str(value) for key, value in data.items()}


def scan_audio(folders: Sequence[Path]) -> List[Path]:
    """Все поддерживаемые аудиофайлы из указанных папок (или отдельные файлы)."""
    files: List[Path] = []
    for folder in folders:
        if folder.is_file():
            if folder.suffix.lower() in AUDIO_SUFFIXES:
                files.append(folder)
            continue
        if not folder.is_dir():
            print(f"  папка не найдена: {folder}")
            continue
        for path in sorted(folder.rglob("*")):
            if path.is_file() and path.suffix.lower() in AUDIO_SUFFIXES:
                files.append(path)
    return files


def build_index(files: Sequence[Path]) -> Dict[str, List[Path]]:
    index: Dict[str, List[Path]] = {}
    for path in files:
        for key in (normalize(path.stem), normalize(path.name)):
            index.setdefault(key, []).append(path)
    return index


def find_source(game: str, track: Dict[str, Any], files: Sequence[Path],
                index: Dict[str, List[Path]], mapping: Dict[str, str]) -> Optional[Path]:
    """Ищет файл песни: сначала по --map, потом по точному имени, потом по вхождению."""
    variants = track_variants(game, track)

    for path in files:
        mapped = mapping.get(normalize(path.stem)) or mapping.get(normalize(path.name))
        if mapped and normalize(mapped) in variants:
            return path

    for key in variants:
        matches = index.get(key)
        if matches:
            return matches[0]

    title = normalize(track.get("song") or track.get("title"))
    if len(title) >= 4:
        found = [path for path in files if title in normalize(path.stem)]
        if len(found) == 1:
            return found[0]
    return None


def clip_bounds(game: str, track: Dict[str, Any]) -> Tuple[float, float]:
    """Начало и длина фрагмента из базы (с разумными значениями по умолчанию)."""
    start = max(0.0, float(track.get("clip_start") or 0))
    length = float(track.get("clip_length") or 0)
    if length <= 0:
        length = DEFAULT_CLIP[game]
    return start, max(0.5, length)


def _resolve_binary(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    path = Path(value)
    if path.is_file():
        return str(path.resolve())
    return shutil.which(value)


def find_ffmpeg(explicit: Optional[str]) -> Optional[str]:
    """ffmpeg из аргумента, переменной окружения, PATH или imageio-ffmpeg."""
    for value in (explicit, os.environ.get("FFMPEG_BINARY"), "ffmpeg"):
        found = _resolve_binary(value)
        if found:
            return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # пакет не установлен или бинарник недоступен
        return None


def cut_clip(ffmpeg: str, source: Path, start: float, length: float) -> bytes:
    """Вырезает фрагмент и возвращает MP3-байты (тишина дополнит короткий трек)."""
    command = [
        ffmpeg,
        "-nostdin",
        "-hide_banner",
        "-loglevel", "error",
        "-ss", f"{start:.3f}",
        "-i", str(source),
        "-vn",
        "-af", "apad",
        "-t", f"{length:.3f}",
        "-acodec", "libmp3lame",
        "-b:a", "192k",
        "-f", "mp3",
        "pipe:1",
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0 or not result.stdout:
        details = result.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(details.splitlines()[-1] if details else "ffmpeg не вернул данные")
    return result.stdout


def store_clip(db, game: str, track: Dict[str, Any], data: bytes,
               length: float, source: Path) -> None:
    """Кладёт байты в audio_clips и помечает песню как играбельную."""
    key = track_key(game, track)
    db.audio_clip_save(game, key, data, "audio/mpeg", int(round(length * 1000)),
                       source.name)
    if game == "songless":
        db.songless_set_audio(str(track.get("anime") or ""), AUDIO_IN_DB,
                              clip_start=0, clip_length=length, track_key=key)
    else:
        db.songguess_set_audio(str(track.get("id") or ""), AUDIO_IN_DB,
                               clip_start=0, clip_length=length)


def load_tracks(db, only: str) -> List[Tuple[str, Dict[str, Any]]]:
    """Песни выбранных игр; пустые таблицы наполняются исходным набором."""
    result: List[Tuple[str, Dict[str, Any]]] = []
    if only in ("all", "songguess"):
        if not db.songguess_track_count():
            db.songguess_save_tracks(songguess_seed_rows())
        result += [("songguess", track) for track in db.songguess_tracks()]
    if only in ("all", "songless"):
        if not db.songless_track_count():
            db.songless_save_tracks(songless_seed_rows())
        result += [("songless", track) for track in db.songless_tracks()]
    return result


def open_target(args: argparse.Namespace):
    """SQLite из --db либо PostgreSQL из --dsn, GREENHOUSE_DSN или data/dsn.txt."""
    if args.db:
        return open_database(Path(args.db))
    dsn = args.dsn or os.environ.get("GREENHOUSE_DSN")
    if not dsn and DEFAULT_DSN_FILE.is_file():
        dsn = DEFAULT_DSN_FILE.read_text(encoding="utf-8-sig").strip()
    if not dsn:
        raise SystemExit(
            "Укажите --dsn (PostgreSQL) или --db (файл SQLite). "
            f"Файл {DEFAULT_DSN_FILE} не найден."
        )
    return open_database(None, dsn)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Фрагменты песен сразу в базу: «Угадай песню» и «Аниме-сонглесс»",
    )
    parser.add_argument("--only", choices=("all", "songguess", "songless"),
                        default="all", help="какую игру наполнять (по умолчанию all)")
    parser.add_argument("--audio", action="append",
                        help="папка с аудиофайлами (можно несколько); "
                             f"по умолчанию {DEFAULT_AUDIO_DIR.name}")
    parser.add_argument("--map", dest="map_file",
                        help='JSON соответствий: {"файл.mp3": "anime-again"}')
    parser.add_argument("--db", help="файл SQLite вместо PostgreSQL")
    parser.add_argument("--dsn", help="строка подключения PostgreSQL")
    parser.add_argument("--ffmpeg", help="путь к ffmpeg (иначе ищется сам)")
    parser.add_argument("--limit", type=int, help="обработать не больше N песен")
    parser.add_argument("--force", action="store_true",
                        help="перезаписывать записи, которые уже есть в базе")
    parser.add_argument("--dry-run", action="store_true",
                        help="показать план, ничего не сохраняя")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    args = build_parser().parse_args(argv)
    mapping = load_map(args.map_file)
    folders = [Path(item) for item in (args.audio or [DEFAULT_AUDIO_DIR])]

    db = open_target(args)
    db.initialize()

    tracks = load_tracks(db, args.only)
    if args.limit is not None:
        tracks = tracks[:max(0, args.limit)]
    if not tracks:
        print("В базе нет песен для обработки.")
        return 1

    files = scan_audio(folders)
    if not files:
        print("Не найдено ни одного аудиофайла. Положите свои записи в "
              f"{DEFAULT_AUDIO_DIR} или укажите папку через --audio.")
        return 2
    print(f"Песен: {len(tracks)}, аудиофайлов: {len(files)}")

    ffmpeg = find_ffmpeg(args.ffmpeg)
    if not ffmpeg and not args.dry_run:
        print("Не найден ffmpeg — без него mp3 не нарезать.\n"
              "Установите его в систему или выполните:\n"
              f"  {sys.executable} -m pip install -r requirements-songs.txt")
        return 2

    index = build_index(files)
    existing = {game: set(db.audio_clip_keys(game)) for game in GAMES}

    saved = skipped = missing = planned = errors = 0
    for number, (game, track) in enumerate(tracks, 1):
        label = (track.get("title") or track.get("song") or "")
        artist = track.get("artist") or ""
        prefix = f"[{number}/{len(tracks)}] {game:<9} {artist} — {label}".rstrip(" —")
        print(prefix)

        key = track_key(game, track)
        if not key:
            print("  пропуск: у песни нет ключа")
            errors += 1
            continue
        if key in existing[game] and not args.force:
            print("  уже в базе (--force, чтобы перезаписать)")
            skipped += 1
            continue

        current = str(track.get("audio") or "").strip()
        if current and current != AUDIO_IN_DB and not args.force:
            print("  уже есть своя запись (--force, чтобы заменить)")
            skipped += 1
            continue

        source = find_source(game, track, files, index, mapping)
        if source is None:
            print("  нет подходящего аудиофайла")
            missing += 1
            continue

        start, length = clip_bounds(game, track)
        if args.dry_run:
            print(f"  взяли бы {source.name}: {length:g} с с {start:g} с")
            planned += 1
            continue

        try:
            data = cut_clip(ffmpeg or "ffmpeg", source, start, length)
            store_clip(db, game, track, data, length, source)
        except Exception as exc:  # noqa: BLE001 — одна песня не должна ронять всё
            print(f"  ошибка: {exc}")
            errors += 1
            continue

        existing[game].add(key)
        print(f"  сохранено из {source.name}: {length:g} с, "
              f"{len(data) / 1024:.0f} КБ")
        saved += 1

    print("\nГотово.")
    print(f"  сохранено в базу: {saved}")
    if skipped:
        print(f"  уже было: {skipped}")
    if missing:
        print(f"  без файла: {missing}")
    if planned:
        print(f"  в плане (--dry-run): {planned}")
    if errors:
        print(f"  с ошибками: {errors}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

