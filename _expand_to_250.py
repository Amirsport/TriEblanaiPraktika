# -*- coding: utf-8 -*-
"""Доводит набор сонглесса до 250 треков: все OP с animethemes.moe."""
import ast
import hashlib
import io
import json
import os
import re
import socket
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psycopg
import socks
from PIL import Image

socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 10808, rdns=True)
socket.socket = socks.socksocket
API = "https://api.animethemes.moe"
UA = "AmrGames/1.0 (personal, non-commercial)"
OUT = Path("front/games/animesongless/covers")
OUT.mkdir(parents=True, exist_ok=True)
TARGET = 250

EXTRA = [
    ("Провожающая в последний путь Фрирен", "Frieren: Beyond Journey's End"),
    ("Семья шпиона", "Spy x Family"),
    ("Синяя тюрьма", "Blue Lock"),
    ("Моя звёздная дочь", "Oshi no Ko"),
    ("Дандадан", "Dandadan"),
    ("Адский рай", "Hell's Paradise"),
    ("Поднятие уровня в одиночку", "Solo Leveling"),
    ("Кайдзю №8", "Kaiju No. 8"),
    ("Мэшл", "Mashle"),
    ("Сага о Винланде", "Vinland Saga"),
    ("Блич", "Bleach"),
    ("Наруто", "Naruto"),
    ("Ван-Пис", "One Piece"),
    ("Гинтама", "Gintama"),
    ("Токийский гуль", "Tokyo Ghoul"),
]


def load_map() -> Dict[str, str]:
    source = Path("_sync_themes_manual.py").read_text(encoding="utf-8")
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "MAP":
            return ast.literal_eval(node.value)
    return {}


def read_url(url: str, timeout: int = 40) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def find(query: str) -> Optional[Dict[str, Any]]:
    params = urllib.parse.urlencode({
        "q": query, "limit": 8,
        "include": "images,animethemes.song,animethemes.animethemeentries.videos",
    })
    items = json.loads(read_url(f"{API}/anime?{params}").decode("utf-8")).get("anime") or []
    wanted = re.sub(r"[^a-z0-9]", "", query.casefold())
    for item in items:
        slug = re.sub(r"[^a-z0-9]", "", str(item.get("slug") or "").casefold())
        if slug == wanted:
            return item
    for item in items:
        slug = re.sub(r"[^a-z0-9]", "", str(item.get("slug") or "").casefold())
        if wanted and (wanted == slug or wanted in slug or slug in wanted):
            return item
    return items[0] if items else None


def theme_rows(item: Dict[str, Any]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for theme in item.get("animethemes") or []:
        if theme.get("type") != "OP":
            continue
        video = ""
        for entry in theme.get("animethemeentries") or []:
            for item_video in entry.get("videos") or []:
                if item_video.get("link"):
                    video = str(item_video["link"])
                    break
            if video:
                break
        if not video:
            continue
        song_data = theme.get("song") or {}
        artists = ", ".join(str(value.get("name") or "")
                            for value in song_data.get("artists") or []
                            if value.get("name"))
        rows.append({
            "slug": str(theme.get("slug") or "OP"),
            "song": str(song_data.get("title") or theme.get("slug") or "OP"),
            "artist": artists,
            "video": video,
        })
    return rows


def cover_of(item: Dict[str, Any]) -> str:
    images = item.get("images") or []
    for facet in ("Small Cover", "Large Cover"):
        for image in images:
            if image.get("facet") == facet:
                return str(image.get("link") or "")
    return ""


def save_cover(anime: str, url: str) -> str:
    digest = hashlib.sha1(anime.encode("utf-8")).hexdigest()[:16]
    suffix = Path(urllib.parse.urlparse(url).path).suffix.lower() or ".jpg"
    path = OUT / f"{digest}{suffix}"
    if not path.exists() and url:
        raw = read_url(url)
        if suffix in (".avif", ".webp"):
            path.write_bytes(raw)
        else:
            image = Image.open(io.BytesIO(raw)).convert("RGB")
            image.thumbnail((320, 440))
            image.save(path, "JPEG", quality=84, optimize=True)
    return f"covers/{path.name}" if path.exists() else ""


def fetch(pair: Tuple[str, str]):
    anime, query = pair
    try:
        item = find(query)
        if not item:
            return anime, None, []
        return anime, item, theme_rows(item)
    except Exception as exc:  # noqa: BLE001
        return anime, {"error": str(exc)}, []


pairs = sorted({**load_map(), **dict(EXTRA)}.items())
dsn = os.environ["DSN"]
with psycopg.connect(dsn) as conn:
    existing_rows = conn.execute(
        "SELECT anime, song, cover FROM songless_tracks"
    ).fetchall()
    existing = {(str(row[0]), str(row[1])) for row in existing_rows}
    covers = {str(row[0]): str(row[2]) for row in existing_rows if row[2]}
    total = len(existing_rows)
    print("start", total, flush=True)
    pool = ThreadPoolExecutor(max_workers=8)
    futures = [pool.submit(fetch, pair) for pair in pairs]
    for future in as_completed(futures):
        if total >= TARGET:
            pool.shutdown(wait=False, cancel_futures=True)
            break
        anime, item, themes = future.result()
        if not item or (isinstance(item, dict) and item.get("error")):
            print(anime, "не найден", flush=True)
            continue
        cover = covers.get(anime) or ""
        if not cover:
            try:
                cover = save_cover(anime, cover_of(item))
                covers[anime] = cover
            except Exception as exc:  # noqa: BLE001
                print(anime, "обложка:", exc, flush=True)
        for theme in themes:
            if total >= TARGET:
                break
            key = (anime, theme["song"])
            if key in existing:
                continue
            track_key = "a" + hashlib.sha1(
                (anime + "|" + theme["slug"]).encode("utf-8")).hexdigest()[:15]
            conn.execute(
                "INSERT INTO songless_tracks (track_key, anime, song, artist, year, "
                "audio, cover, video, clip_start, clip_length, updated_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, 8, now()) "
                "ON CONFLICT (track_key) DO NOTHING",
                (track_key, anime, theme["song"], theme["artist"],
                 str(item.get("year") or ""), theme["video"], cover, theme["video"]),
            )
            existing.add(key)
            total += 1
        conn.commit()
        print(anime, "->", total, flush=True)
    pool.shutdown(wait=False, cancel_futures=True)
print("total", total)