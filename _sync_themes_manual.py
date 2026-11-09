# -*- coding: utf-8 -*-
"""Ручная карта русских названий на animethemes: обложки и видео опенингов."""
import hashlib
import io
import json
import re
import socket
import sys
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Optional

import socks
from PIL import Image

socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 10808, rdns=True)
socket.socket = socks.socksocket
API = "https://api.animethemes.moe"
UA = "AmrGames/1.0 (personal, non-commercial)"
OUT = Path("front/games/animesongless/covers")
OUT.mkdir(parents=True, exist_ok=True)

MAP = {
    "Наруто": "Naruto",
    "Наруто: Ураганные хроники": "Naruto Shippuuden",
    "Ван-Пис": "One Piece",
    "Блич": "Bleach",
    "Тетрадь смерти": "Death Note",
    "Атака титанов": "Shingeki no Kyojin",
    "Стальной алхимик: Братство": "Fullmetal Alchemist: Brotherhood",
    "Код Гиас: Восставший Лелуш": "Code Geass: Hangyaku no Lelouch",
    "Токийский гуль": "Tokyo Ghoul",
    "Паразит: учение о жизни": "Kiseijuu: Sei no Kakuritsu",
    "Охотник × Охотник": "Hunter x Hunter",
    "Хвост феи": "Fairy Tail",
    "Евангелион": "Neon Genesis Evangelion",
    "Мастера меча онлайн": "Sword Art Online",
    "Клинок, рассекающий демонов": "Kimetsu no Yaiba",
    "Магическая битва": "Jujutsu Kaisen",
    "Моя геройская академия": "Boku no Hero Academia",
    "Re:Zero. Жизнь с нуля в альтернативном мире": "Re:Zero kara Hajimeru Isekai Seikatsu",
    "Врата Штейна": "Steins;Gate",
    "Девочка-волшебница Мадока": "Mahou Shoujo Madoka Magica",
    "Ковбой Бибоп": "Cowboy Bebop",
    "Самурай Чамплу": "Samurai Champloo",
    "Великий из бродячих псов": "Bungou Stray Dogs",
    "Токийские мстители": "Tokyo Revengers",
    "Человек-бензопила": "Chainsaw Man",
    "Ванпанчмен": "One Punch Man",
    "Гуррен-Лаганн": "Tengen Toppa Gurren Lagann",
    "Сейлор Мун": "Bishoujo Senshi Sailor Moon",
    "Покемон": "Pokemon",
    "Драконий жемчуг Z": "Dragon Ball Z",
    "Драконий жемчуг": "Dragon Ball",
    "Слэм-данк": "Slam Dunk",
    "Сейнт Сейя": "Saint Seiya",
    "Приключения Диджимонов": "Digimon Adventure",
    "Ю-Ги-О!": "Yuugiou Duel Monsters",
    "Торадора!": "Toradora!",
    "Кланнад": "Clannad",
    "Меланхолия Харухи Судзумии": "Suzumiya Haruhi no Yuuutsu",
    "Ангельские ритмы!": "Angel Beats!",
    "Дневник будущего": "Mirai Nikki",
    "Волчица и пряности": "Ookami to Koushinryou",
    "Клеймор": "Claymore",
    "Эльфийская песнь": "Elfen Lied",
    "Хеллсинг": "Hellsing",
    "Триган": "Trigun",
    "Самурай Икс": "Rurouni Kenshin",
    "Нана": "Nana",
    "Хост-клуб Оранской школы": "Ouran High School Host Club",
    "Дюрарара!!": "Durarara!!",
    "Судьба/Ноль": "Fate/Zero",
    "Некий магический индекс": "Toaru Majutsu no Index",
    "К-он!": "K-On!",
    "Лаки Стар": "Lucky Star",
    "Моб Психо 100": "Mob Psycho 100",
    "Доктор Стоун": "Dr. Stone",
    "Волейбол!!": "Haikyuu!!",
    "Баскетбол Куроко": "Kuroko no Basket",
    "Крутой учитель Онидзука": "Great Teacher Onizuka",
    "Бездомный бог": "Noragami",
    "Эксперименты Лэйн": "Serial Experiments Lain",
    "Кагуя: в любви как на войне": "Kaguya-sama wa Kokurasetai",
    "Класс убийц": "Ansatsu Kyoushitsu",
    "Синий экзорцист": "Ao no Exorcist",
    "Берсерк": "Berserk",
    "Кобаяши из дома с драконами": "Kobayashi-san Chi no Maid Dragon",
    "Тебе, любимая": "Kimi ni Todoke",
    "Моногатари": "Bakemonogatari",
    "Первый шаг": "Hajime no Ippo",
    "Kill la Kill": "Kill la Kill",
    "Психопаспорт": "Psycho-Pass",
    "Пожиратель душ": "Soul Eater",
}


def read_url(url: str, timeout: int = 30) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1 + attempt)


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


def parse(item: Dict[str, Any]) -> Dict[str, str]:
    cover = ""
    images = item.get("images") or []
    for facet in ("Small Cover", "Large Cover"):
        for image in images:
            if image.get("facet") == facet:
                cover = str(image.get("link") or "")
                break
        if cover:
            break
    video = song = artist = ""
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
            "name": str(item.get("name") or "")}


def save_cover(anime: str, url: str) -> str:
    digest = hashlib.sha1(anime.encode("utf-8")).hexdigest()[:16]
    suffix = Path(urllib.parse.urlparse(url).path).suffix.lower() or ".jpg"
    path = OUT / f"{digest}{suffix}"
    if not path.exists():
        raw = read_url(url)
        if suffix in (".avif", ".webp"):
            path.write_bytes(raw)
        else:
            image = Image.open(io.BytesIO(raw)).convert("RGB")
            image.thumbnail((320, 440))
            image.save(path, "JPEG", quality=84, optimize=True)
    return f"covers/{path.name}"


def one(anime: str, query: str):
    try:
        item = find(query)
        if not item:
            return anime, None
        data = parse(item)
        data["cover"] = save_cover(anime, data["cover"]) if data.get("cover") else ""
        return anime, data
    except Exception as exc:  # noqa: BLE001
        return anime, {"error": str(exc)}


meta: Dict[str, Dict[str, str]] = {}
with ThreadPoolExecutor(max_workers=6) as pool:
    futures = [pool.submit(one, anime, query) for anime, query in MAP.items()]
    for index, future in enumerate(as_completed(futures), 1):
        anime, found = future.result()
        if not found:
            print(f"[{index}/{len(MAP)}] {anime}: не найдено", flush=True)
            continue
        if found.get("error"):
            print(f"[{index}/{len(MAP)}] {anime}: {found['error']}", flush=True)
            continue
        meta[anime] = found
        Path("_themes_meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[{index}/{len(MAP)}] {anime} -> {found.get('name')}", flush=True)
print("matched", len(meta), "of", len(MAP))