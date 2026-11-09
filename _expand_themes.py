# -*- coding: utf-8 -*-
"""Добавляет новые аниме из animethemes.moe в набор «Аниме-сонглесса»."""
import hashlib
import io
import json
import os
import re
import socket
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

import psycopg
import socks
from PIL import Image

socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 10808, rdns=True)
socket.socket = socks.socksocket
API = "https://api.animethemes.moe"
UA = "AmrGames/1.0 (personal, non-commercial)"
OUT = Path("front/games/animesongless/covers")
OUT.mkdir(parents=True, exist_ok=True)

# Поисковое название на animethemes -> подпись в игре.
NEW = [
    ("Frieren: Beyond Journey's End", "Провожающая в последний путь Фрирен"),
    ("Spy x Family", "Семья шпиона"),
    ("Blue Lock", "Синяя тюрьма"),
    ("Oshi no Ko", "Моя звёздная дочь"),
    ("Dandadan", "Дандадан"),
    ("Hell's Paradise", "Адский рай"),
    ("Solo Leveling", "Поднятие уровня в одиночку"),
    ("Kaiju No. 8", "Кайдзю №8"),
    ("Mashle", "Мэшл"),
    ("Vinland Saga", "Сага о Винланде"),
    ("Fire Force", "Пламенная бригада"),
    ("The Promised Neverland", "Обещанный Неверленд"),
    ("Akame ga Kill!", "Убийца Акамэ"),
    ("Erased", "Город, в котором меня нет"),
    ("Black Clover", "Чёрный клевер"),
    ("Horimiya", "Хоримия"),
    ("Food Wars!", "Кулинарные поединки"),
    ("Overlord", "Повелитель"),
    ("Rent-a-Girlfriend", "Девушка на час"),
    ("Konosuba", "Этот замечательный мир!"),
]


def read_url(url: str, timeout: int = 60) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def get_json(url: str) -> Dict[str, Any]:
    return json.loads(read_url(url).decode("utf-8"))


def find_anime(query: str) -> Optional[Dict[str, Any]]:
    params = urllib.parse.urlencode({
        "q": query, "limit": 10,
        "include": "images,animethemes.song,animethemes.animethemeentries.videos",
    })
    items = get_json(f"{API}/anime?{params}").get("anime") or []
    wanted = re.sub(r"[^a-z0-9]", "", query.casefold())
    for item in items:
        slug = re.sub(r"[^a-z0-9]", "", str(item.get("slug") or "").casefold())
        if slug == wanted or wanted in slug:
            return item
    return items[0] if items else None


def details(item: Dict[str, Any]) -> Dict[str, Any]:
    cover = ""
    for image in item.get("images") or []:
        if image.get("facet") == "Large Cover":
            cover = str(image.get("link") or "")
            break
    video = ""
    song = ""
    artist = ""
    for theme in item.get("animethemes") or []:
        if theme.get("type") != "OP":
            continue
        song_data = theme.get("song") or {}
        song = song or str(song_data.get("title") or "")
        if not artist:
            artist = ", ".join(str(value.get("name") or "")
                               for value in song_data.get("artists") or []
                               if value.get("name"))
        for entry in theme.get("animethemeentries") or []:
            for video_item in entry.get("videos") or []:
                if video_item.get("link"):
                    video = str(video_item["link"])
                    break
            if video:
                break
        if video:
            break
    return {"cover": cover, "video": video, "song": song, "artist": artist,
            "year": str(item.get("year") or "")}


def save_cover(name: str, url: str) -> str:
    digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:16]
    path = OUT / f"{digest}.jpg"
    if not path.exists() and url:
        raw = read_url(url)
        image = Image.open(io.BytesIO(raw)).convert("RGB")
        image.thumbnail((320, 440))
        image.save(path, "JPEG", quality=84, optimize=True)
    return f"covers/{path.name}" if path.exists() else ""


dsn = os.environ["DSN"]
added = 0
with psycopg.connect(dsn) as conn:
    for search, name in NEW:
        if conn.execute("select 1 from songless_tracks where anime = %s", (name,)).fetchone():
            print(name, "уже есть")
            continue
        item = find_anime(search)
        if not item:
            print(name, "не найден на animethemes")
            continue
        data = details(item)
        if not data["video"]:
            print(name, "нет видео опенинга")
            continue
        cover = ""
        try:
            cover = save_cover(name, data["cover"])
        except Exception as exc:  # noqa: BLE001
            print(name, "обложка не скачалась:", exc)
        conn.execute(
            "INSERT INTO songless_tracks (track_key, anime, song, artist, year, audio, cover, "
            "video, clip_start, clip_length, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, 8, now()) "
            "ON CONFLICT (track_key) DO NOTHING",
            (name, name, data["song"], data["artist"], data["year"], data["video"],
             cover, data["video"]),
        )
        conn.commit()
        added += 1
        print(name, "<-", item.get("name"), "(cover=%s)" % bool(cover), flush=True)
        time.sleep(0.2)
print("added", added)