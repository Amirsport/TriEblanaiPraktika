# -*- coding: utf-8 -*-
"""Наполнение базы для игры Narutodle: персонажи и их изображения.

Что делает:
    * заливает исходный набор из backend/narutodle_data.py в таблицу
      narutodle_characters (повторный запуск обновляет свойства, а уже
      привязанные картинки и цвета не затирает);
    * раскладывает ваши изображения по персонажам: файлы из папки сшиваются
      с именами, копируются в front/games/narutodle/portraits и прописываются
      в колонку image. Пустая колонка — страница рисует аватар из инициалов;
    * показывает, что сейчас лежит в базе (--list).

Примеры:
    python backend/seed_narutodle.py --db data/greenhouse.sqlite3 --list
    python backend/seed_narutodle.py --dsn "postgresql://greenhouse:пароль@localhost:5432/greenhouse"
    python backend/seed_narutodle.py --dsn "..." --images C:\\photos --map photos.json
    python backend/seed_narutodle.py --dsn "..." --url "Наруто Узумаки=https://example.org/naruto.png"
    python backend/seed_narutodle.py --dsn "..." --clear-image "Наруто Узумаки"

Имя файла сшивается с персонажем без учёта регистра и расширения:
«наруто узумаки.jpg» попадёт в «Наруто Узумаки». Если имена не совпадают,
задайте соответствия файлом --map: {"файл.jpg": "Имя персонажа"}.
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

try:  # запуск как модуль: python -m backend.seed_narutodle
    from .db import open_database
    from .narutodle_data import village_color
    from .narutodle_data import seed_rows
except ImportError:  # запуск как файл: python backend/seed_narutodle.py
    from db import open_database  # type: ignore
    from narutodle_data import seed_rows, village_color  # type: ignore

PORTRAITS_DIR = ROOT / "front" / "games" / "narutodle" / "portraits"
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif", ".svg")
SAFE_NAME = re.compile(r'[\\/:*?"<>|]+')


def normalize(value: str) -> str:
    """Ключ сравнения имён: регистр и лишние пробелы не важны."""
    return " ".join((value or "").split()).casefold()


def human(value: Optional[str]) -> str:
    """Имя персонажа для консоли: пустое значение показываем прочерком."""
    return value if value else "—"


def safe_filename(name: str) -> str:
    """Имя файла без символов, недопустимых в пути и в ссылке."""
    cleaned = SAFE_NAME.sub("_", pathlib.Path(name).name).strip()
    return cleaned or "image.png"


def load_map(path: Optional[str]) -> Dict[str, str]:
    """Соответствия «имя файла -> имя персонажа» из JSON."""
    if not path:
        return {}
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Файл --map должен содержать объект {\"файл\": \"Персонаж\"}")
    return {str(key): str(value) for key, value in data.items()}


def seed(db, dry_run: bool = False) -> List[Dict[str, Any]]:
    """Загружает исходный набор в базу и возвращает то, что получилось."""
    rows = seed_rows()
    if dry_run:
        return rows
    db.narutodle_save_characters(rows)
    return db.narutodle_characters()


def attach_images(db, folder: pathlib.Path, mapping: Dict[str, str],
                  dry_run: bool = False) -> int:
    """Копирует файлы в папку игры и прописывает их персонажам."""
    files = sorted(path for path in folder.rglob("*")
                   if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES)
    if not files:
        print(f"В папке {folder} нет изображений ({', '.join(IMAGE_SUFFIXES)})")
        return 0

    characters = {normalize(item["name"]): item["name"] for item in db.narutodle_characters()}
    mapped = {normalize(key): value for key, value in mapping.items()}
    attached = 0
    for path in files:
        target = mapped.get(normalize(path.name)) or mapped.get(normalize(path.stem))
        if not target:
            target = characters.get(normalize(path.stem))
        if not target:
            print(f"  пропуск: {path.name} — нет персонажа с таким именем "
                  f"(добавьте пару в --map)")
            continue

        file_name = safe_filename(target) + path.suffix.lower()
        destination = PORTRAITS_DIR / file_name
        if not dry_run:
            PORTRAITS_DIR.mkdir(parents=True, exist_ok=True)
            if path.resolve() != destination.resolve():
                shutil.copy2(path, destination)
            db.narutodle_set_image(target, f"portraits/{file_name}")
        print(f"  {human(target)} <- {path.name}  ({destination.name})")
        attached += 1
    return attached


def main() -> int:
    parser = argparse.ArgumentParser(description="Персонажи Narutodle в базе")
    parser.add_argument("--db", type=pathlib.Path, help="файл SQLite")
    parser.add_argument("--dsn", help="строка подключения PostgreSQL")
    parser.add_argument("--images", type=pathlib.Path, help="папка с изображениями")
    parser.add_argument("--map", dest="map_file", help="JSON-файл соответствий имён")
    parser.add_argument("--url", action="append", default=[],
                        help="привязать ссылку: --url \"Персонаж=https://...\"")
    parser.add_argument("--clear-image", action="append", default=[],
                        help="снять картинку и вернуть аватар: --clear-image \"Персонаж\"")
    parser.add_argument("--clear-images", action="store_true",
                        help="снять картинки у всех персонажей")
    parser.add_argument("--list", action="store_true", help="показать, что в базе")
    parser.add_argument("--dry-run", action="store_true",
                        help="ничего не менять, только показать план")
    args = parser.parse_args()

    if not args.db and not args.dsn:
        parser.error("укажите --db для SQLite или --dsn для PostgreSQL")

    db = open_database(args.db, args.dsn)
    db.initialize()

    before = db.narutodle_character_count()
    rows = seed(db, args.dry_run)
    after = db.narutodle_character_count()
    print(f"Персонажей: было {before}, стало {after} "
          f"({len(rows)} строк в источнике){' — холостой прогон' if args.dry_run else ''}")

    if args.clear_images:
        for item in db.narutodle_characters():
            if not args.dry_run:
                db.narutodle_set_image(item["name"], "")
        print("Картинки сняты у всех персонажей")

    for name in args.clear_image:
        if args.dry_run:
            print(f"  сняли бы картинку: {name}")
        elif db.narutodle_set_image(name, ""):
            print(f"  картинка снята: {name}")
        else:
            print(f"  персонаж не найден: {name}")

    for pair in args.url:
        if "=" not in pair:
            print(f"  ожидался формат «Персонаж=ссылка», а получено: {pair}")
            continue
        name, url = (part.strip() for part in pair.split("=", 1))
        if args.dry_run:
            print(f"  привязали бы ссылку: {name} -> {url}")
        elif db.narutodle_set_image(name, url):
            print(f"  ссылка привязана: {name} -> {url}")
        else:
            print(f"  персонаж не найден: {name}")

    if args.images:
        print(f"Изображения из {args.images}:")
        attached = attach_images(db, args.images, load_map(args.map_file), args.dry_run)
        print(f"  привязано файлов: {attached}")

    if args.list or not (args.images or args.url or args.clear_image or args.clear_images):
        items = db.narutodle_characters()
        with_image = sum(1 for item in items if item["image"])
        print(f"\nВ базе {len(items)} персонажей, с картинкой {with_image}, "
              f"аватаров {len(items) - with_image}")
        for item in items:
            mark = item["image"] or "аватар"
            print(f"  {item['name']:<24} {item['village']:<12} {mark}")
        print(f"\nМатчей в журнале: {db.narutodle_match_count()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
