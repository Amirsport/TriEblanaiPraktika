# -*- coding: utf-8 -*-
"""Собирает фотографии игроков и карт с Liquipedia для игры «87-0».

Скрипт разработческий: он раскладывает готовые превью в
`front/games/csdraft/img/` — страница игры берёт их оттуда по имени файла
(имя игрока или карты, приведённое к нижнему регистру с дефисами).

Как устроен сбор:

    * список игроков и карт берётся прямо из данных игры;
    * для каждого игрока ищется страница в Liquipedia (подписи из разделов
      участников мейджоров лежат в кэше `_fetch_major_rosters.py`, остальные
      имена находятся по названию страницы);
    * вики-текст страниц приходит пачками по 50 штук: из карточки читается поле
      `image` — именно эту фотографию показывает Liquipedia;
    * ссылки на превью приходят вторым пакетным запросом, скачанное
      уменьшается до нужной ширины и сохраняется в JPEG;
    * карты берутся со страниц карт Liquipedia (`Mirage/cs2`, `Dust2/cs2` и так
      далее) — там лежат игровые снимки.

Запуск (из корня проекта):

    .\\.venv\\Scripts\\python.exe _fetch_player_images.py

Уже сохранённое не трогается, поэтому повторный запуск докачивает только
недостающее. Фотографии принадлежат их авторам и взяты с Liquipedia
(CC-BY-SA 3.0) для обозначения игроков; любой файл можно удалить, тогда игра
покажет заготовку с инициалами.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from io import BytesIO
from typing import Dict, List, Optional, Sequence, Tuple

from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(ROOT, "front", "games", "csdraft", "img")
API = "https://liquipedia.net/counterstrike/api.php"
UA = "GreenhouseCraft/1.0 (personal non-commercial project; contact: site owner)"
CACHE_DIR = os.path.join(os.environ.get("TEMP") or os.environ.get("TMP") or ".", "liqcache")
PAUSE = 6.0
BATCH = 50
# Размер превью в игре и размер, который запрашивается у Liquipedia (с запасом
# на резкость при уменьшении).
PLAYER_WIDTH = 320
PLAYER_SOURCE = 720
MAP_WIDTH = 960
MAP_SOURCE = 1600
JPEG_QUALITY = 88

# Как карта называется в игре и где искать её снимок: страницы проверяются
# по порядку, пока не найдётся подходящая картинка.
MAP_PAGES: Dict[str, Tuple[str, ...]] = {
    "Mirage": ("Mirage/cs2",),
    "Inferno": ("Inferno/cs2",),
    "Nuke": ("Nuke/cs2",),
    "Dust2": ("Dust II/cs2", "Dust2/cs2", "Dust2/csgo", "Dust2"),
    "Train": ("Train/cs2",),
    "Cache": ("Cache/cs2", "Cache/csgo"),
    "Overpass": ("Overpass/cs2",),
    "Cobblestone": ("Cobblestone/csgo",),
    "Vertigo": ("Vertigo/cs2",),
    "Ancient": ("Ancient/cs2",),
    "Anubis": ("Anubis/cs2",),
}

# Файлы, которые фотографиями игрока или карты не являются: флаги, иконки,
# логотипы команд, значки турниров и служебная графика.
NOT_A_PHOTO = re.compile(r"(_hd\.png$|allmode|icon|logo|gameicon|\.svg$|non_hd|flag"
                         r"|trophy|stats|chart|bracket|timeline)", re.I)


def slug(text: str) -> str:
    """Имя файла для игрока или карты (то же правило, что и в странице игры)."""
    return re.sub(r"^-+|-+$", "", re.sub(r"[^a-z0-9]+", "-", str(text).lower()))


def api(params: Dict[str, str]) -> Dict[str, object]:
    """Запрос к API Liquipedia: кэш на диске и повторы при ограничении частоты."""
    query = urllib.parse.urlencode(params)
    digest = hashlib.sha1(query.encode("utf-8")).hexdigest()[:16]
    path = os.path.join(CACHE_DIR, f"query-{digest}.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    request = urllib.request.Request(f"{API}?{query}", headers={
        "User-Agent": UA, "Accept": "application/json", "Accept-Encoding": "gzip"})
    payload = b""
    for attempt in range(6):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                payload = response.read()
                if response.headers.get("Content-Encoding") == "gzip":
                    payload = gzip.decompress(payload)
            break
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == 5:
                raise
            wait = 45 * (attempt + 1)
            print(f"лимит запросов, пауза {wait} с", flush=True)
            time.sleep(wait)
    data: Dict[str, object] = json.loads(payload.decode("utf-8"))
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False)
    time.sleep(PAUSE)
    return data


def page_files(titles: Sequence[str]) -> Dict[str, List[str]]:
    """Файлы страниц: {название страницы: [файлы]} — по 50 страниц за запрос.

    Годится для страниц карт: там картинок мало и нужен снимок с самой страницы.
    """
    result: Dict[str, List[str]] = {}
    for start in range(0, len(titles), BATCH):
        portion = list(titles[start:start + BATCH])
        data = api({"action": "query", "format": "json", "prop": "images", "imlimit": "500",
                    "redirects": "1", "titles": "|".join(portion)})
        query = data.get("query") or {}
        pages = query.get("pages") or {}  # type: ignore[union-attr]
        for page in pages.values():  # type: ignore[union-attr]
            files = [str(item["title"]) for item in (page.get("images") or [])]
            result[str(page.get("title"))] = files
        for redirect in query.get("redirects") or []:  # type: ignore[union-attr]
            target = redirect.get("to")
            if target and str(target) in result:
                result[str(redirect["from"])] = result[str(target)]
        print(f"  страниц карт: {min(start + BATCH, len(titles))}/{len(titles)}", flush=True)
    return result


def page_infobox_image(titles: Sequence[str]) -> Dict[str, str]:
    """Фотография из карточки страницы: {название страницы: имя файла}.

    Вики-текст берётся пачками по 50 страниц, из карточки читается поле
    `image` — там лежит именно та фотография, что показывает Liquipedia.
    """
    result: Dict[str, str] = {}
    for start in range(0, len(titles), BATCH):
        portion = list(titles[start:start + BATCH])
        data = api({"action": "query", "format": "json", "prop": "revisions",
                    "rvprop": "content", "rvslots": "main", "redirects": "1",
                    "titles": "|".join(portion)})
        query = data.get("query") or {}
        pages = query.get("pages") or {}  # type: ignore[union-attr]
        found: Dict[str, str] = {}
        for page in pages.values():  # type: ignore[union-attr]
            revisions = page.get("revisions") or []
            content = ""
            if revisions:
                content = str((revisions[0].get("slots") or {}).get("main", {}).get("*") or "")
            match = re.search(r"\|\s*image\s*=\s*([^\n|}]+)", content)
            if match:
                found[str(page.get("title"))] = match.group(1).strip()
        result.update(found)
        for redirect in query.get("redirects") or []:  # type: ignore[union-attr]
            target = redirect.get("to")
            if target and str(target) in found:
                result[str(redirect["from"])] = found[str(target)]
        print(f"  страниц игроков: {min(start + BATCH, len(titles))}/{len(titles)}, "
              f"с фото: {len(result)}", flush=True)
    return result


def file_urls(files: Sequence[str], width: int) -> Dict[str, str]:
    """Ссылки на превью файлов: {файл: адрес} — по 50 файлов за запрос."""
    result: Dict[str, str] = {}
    for start in range(0, len(files), BATCH):
        portion = list(files[start:start + BATCH])
        data = api({"action": "query", "format": "json", "prop": "imageinfo",
                    "iiprop": "url", "iiurlwidth": str(width), "titles": "|".join(portion)})
        for page in ((data.get("query") or {}).get("pages") or {}).values():  # type: ignore[union-attr]
            info = (page.get("imageinfo") or [{}])[0]
            url = info.get("thumburl") or info.get("url")
            if url and not page.get("missing"):
                result[str(page.get("title"))] = str(url)
        print(f"  ссылок собрано: {min(start + BATCH, len(files))}/{len(files)}", flush=True)
    return result


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "image/*", "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = response.read()
        if response.headers.get("Content-Encoding") == "gzip":
            payload = gzip.decompress(payload)
    return payload


def save_image(url: str, folder: str, key: str, width: int) -> bool:
    """Скачивает картинку и сохраняет превью нужной ширины."""
    path = os.path.join(OUT_DIR, folder, f"{key}.jpg")
    if os.path.exists(path):
        return True
    try:
        payload = download(url)
    except Exception as error:  # сеть: игра покажет заготовку вместо фото
        print(f"    {key}: не скачалось ({error})", flush=True)
        return False
    try:
        image = Image.open(BytesIO(payload))
        image.load()
    except Exception as error:
        print(f"    {key}: не открылось ({error})", flush=True)
        return False
    if image.mode in ("RGBA", "LA", "P"):
        canvas = Image.new("RGB", image.size, (255, 255, 255))
        canvas.paste(image, mask=image.split()[-1])
        image = canvas
    else:
        image = image.convert("RGB")
    if image.width > width:
        image = image.resize((width, max(1, round(image.height * width / image.width))),
                             Image.LANCZOS)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    image.save(path, "JPEG", quality=JPEG_QUALITY, optimize=True)
    return True


def map_photo(files: Sequence[str]) -> Optional[str]:
    """Снимок карты: первый подходящий файл страницы."""
    for name in files:
        text = str(name)
        if not NOT_A_PHOTO.search(text):
            return text
    return None


def game_names() -> Tuple[List[str], List[str]]:
    """Игроки и карты, которые встречаются в данных игры."""
    sys.path.insert(0, os.path.join(ROOT, "backend"))
    import csdraft_data as data  # noqa: PLC0415

    rows = data.packs()
    players = sorted({str(player["name"]) for row in rows for player in row["players"]})
    maps = sorted({str(name) for row in rows for name in row["maps"]})
    return players, maps


def page_titles_from_cache(players: Sequence[str]) -> Dict[str, str]:
    """Адреса страниц игроков из кэша разделов участников (без запросов к API)."""
    mapping: Dict[str, str] = {}
    if not os.path.isdir(CACHE_DIR):
        return mapping
    link = re.compile(r'href="/counterstrike/([^"/]+)"\s+title="([^"]+)"')
    for name in os.listdir(CACHE_DIR):
        if not name.startswith("text-"):
            continue
        with open(os.path.join(CACHE_DIR, name), encoding="utf-8") as handle:
            html = handle.read()
        for page, title in link.findall(html):
            mapping.setdefault(re.sub(r"\s*\([^)]*\)$", "", title), urllib.parse.unquote(page))
    return {player: mapping[player] for player in players if player in mapping}


def collect(players: List[str], maps: List[str]) -> Tuple[int, int]:
    print("\nкарты:")
    candidates = [title for name in maps for title in MAP_PAGES.get(name, (name,))]
    map_files = page_files(candidates)
    chosen_maps: Dict[str, str] = {}
    for name in maps:
        for title in MAP_PAGES.get(name, (name,)):
            photo = map_photo(map_files.get(title, []))
            if photo:
                chosen_maps[name] = photo
                break
    map_urls = file_urls(sorted(set(chosen_maps.values())), MAP_SOURCE)
    saved_maps = 0
    for name, title in chosen_maps.items():
        url = map_urls.get(title)
        if url and save_image(url, "maps", slug(name), MAP_WIDTH):
            saved_maps += 1
    print(f"карт сохранено: {saved_maps} из {len(maps)}")

    print("\nигроки:")
    pages = page_titles_from_cache(players)
    titles = [pages.get(player, player) for player in players]
    photos = page_infobox_image(titles)
    chosen: Dict[str, str] = {}
    for player, title in zip(players, titles):
        file = photos.get(title)
        if file:
            chosen[player] = file if file.startswith("File:") else f"File:{file}"
    print(f"фотографий нашлось: {len(chosen)} из {len(players)}")
    urls = file_urls(sorted(set(chosen.values())), PLAYER_SOURCE)
    saved = 0
    for player, file in chosen.items():
        url = urls.get(file)
        if url and save_image(url, "players", slug(player), PLAYER_WIDTH):
            saved += 1
    print(f"фотографий сохранено: {saved} из {len(players)}")
    return saved_maps, saved


def main() -> int:
    players, maps = game_names()
    print(f"игроков в данных: {len(players)}, карт: {len(maps)}")
    collect(players, maps)
    print(f"\nпапка: {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
