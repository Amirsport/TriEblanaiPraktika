# -*- coding: utf-8 -*-
"""Доводит набор «Аниме-сонглесса» до 500 опенингов через AnimeThemes API.

Популярные аниме берутся из Kitsu, темы и записи — из AnimeThemes.moe.
Скрипт идемпотентен: уже известные пары «аниме + песня» пропускаются.

Пример:
    $env:DSN = "postgresql://greenhouse:пароль@localhost:5432/greenhouse"
    python _expand_to_500.py --dry-run
    python _expand_to_500.py --target 500
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import socks
except ImportError:  # прокси необязателен
    socks = None

import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "backend" / "songless_catalog.json"
API = "https://api.animethemes.moe"
KITSU = "https://kitsu.io/api/edge/anime"
UA = "AmrGames/1.0 (personal, non-commercial)"
DEFAULT_TARGET = 500
CURL_PROXY = ""


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").casefold())


def anime_name_map() -> Dict[str, str]:
    """Английские/ромадзи-названия -> русские подписи из _sync_themes_manual.py."""
    source = ROOT / "_sync_themes_manual.py"
    try:
        tree = ast.parse(source.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return {}
    result: Dict[str, str] = {}
    for node in tree.body:
        if (isinstance(node, ast.Assign)
                and getattr(node.targets[0], "id", "") == "MAP"):
            try:
                data = ast.literal_eval(node.value)
            except (ValueError, SyntaxError):
                break
            if isinstance(data, dict):
                result.update({normalize(str(en)): str(ru) for ru, en in data.items()})
            break
    return result


def configure_proxy(value: Optional[str]) -> None:
    global CURL_PROXY
    if not value:
        return
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "socks5":
        raise SystemExit("Поддерживается только socks5://host:port")
    CURL_PROXY = value.replace("socks5://", "socks5h://", 1)
    if socks is None:
        return
    socks.set_default_proxy(socks.SOCKS5, parsed.hostname or "127.0.0.1",
                            parsed.port or 1080, rdns=True)
    socket.socket = socks.socksocket


def read_url(url: str, timeout: int = 60) -> bytes:
    try:
        command = "curl.exe" if os.name == "nt" else "curl"
        curl_args = [command, "--ssl-no-revoke", "-sS", "--max-time",
                     str(min(timeout, 30)), "-A", UA]
        if CURL_PROXY:
            curl_args.extend(["--proxy", CURL_PROXY])
        curl_args.append(url)
        result = subprocess.run(curl_args, capture_output=True)
        if result.returncode == 0 and result.stdout:
            return result.stdout
    except FileNotFoundError:
        pass
    try:
        import requests

        session = requests.Session()
        response = session.get(url, headers={"User-Agent": UA}, timeout=timeout,
                                verify=False)
        response.raise_for_status()
        return response.content
    except ImportError:
        pass
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1 + attempt)


def get_json(url: str) -> Dict[str, Any]:
    return json.loads(read_url(url).decode("utf-8"))


def anime_cover(item: Dict[str, Any]) -> str:
    for facet in ("Large Cover", "Small Cover"):
        for image in item.get("images") or []:
            if image.get("facet") == facet and image.get("link"):
                return str(image["link"])
    return ""


def find_anime(title: str) -> Optional[Dict[str, Any]]:
    """Ищет аниме по точному названию, затем обычным поиском."""
    include = "images,animethemes.song.artists,animethemes.animethemeentries.videos"
    url = API + "/anime?" + urllib.parse.urlencode({
        "filter[name]": title, "include": include, "page[size]": 5,
    })
    items = get_json(url).get("anime") or []
    wanted = normalize(title)
    for item in items:
        if normalize(str(item.get("name") or "")) == wanted:
            return item
    for item in items:
        if wanted and wanted in normalize(str(item.get("name") or "")):
            return item
    url = API + "/anime?" + urllib.parse.urlencode({
        "q": title, "include": include, "limit": 5,
    })
    items = get_json(url).get("anime") or []
    return items[0] if items else None


def theme_rows(item: Dict[str, Any]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for theme in item.get("animethemes") or []:
        if theme.get("type") != "OP":
            continue
        video = ""
        for entry in theme.get("animethemeentries") or []:
            for candidate in entry.get("videos") or []:
                if candidate.get("link"):
                    video = str(candidate["link"])
                    break
            if video:
                break
        if not video:
            continue
        song = theme.get("song") or {}
        artists = ", ".join(str(value.get("name") or "")
                            for value in song.get("artists") or []
                            if value.get("name"))
        rows.append({
            "slug": str(theme.get("slug") or ""),
            "song": str(song.get("title") or theme.get("slug") or "OP"),
            "artist": artists,
            "video": video,
        })
    return rows


POPULAR_FALLBACK = (
    "Attack on Titan", "Demon Slayer: Kimetsu no Yaiba", "My Hero Academia",
    "Jujutsu Kaisen", "One Punch Man", "Tokyo Ghoul", "Sword Art Online",
    "Death Note", "Fullmetal Alchemist: Brotherhood", "Code Geass: Hangyaku no Lelouch",
    "Steins;Gate", "Re:Zero kara Hajimeru Isekai Seikatsu",
    "Kono Subarashii Sekai ni Shukufuku wo!", "Overlord", "No Game No Life",
    "Blue Lock", "Spy x Family", "Chainsaw Man", "Mob Psycho 100", "Vinland Saga",
    "Made in Abyss", "Yakusoku no Neverland", "Dr. Stone", "Enen no Shouboutai",
    "Black Clover", "Haikyuu!!", "Kuroko no Basket", "Slam Dunk",
    "Shokugeki no Souma", "Toradora!", "Clannad", "Shigatsu wa Kimi no Uso",
    "Ano Hi Mita Hana no Namae wo Bokutachi wa Mada Shiranai.", "Angel Beats!",
    "Charlotte", "Horimiya", "Kaguya-sama wa Kokurasetai", "Oshi no Ko",
    "Bocchi the Rock!", "Komi-san wa, Comyushou desu.", "Kanojo, Okarishimasu",
    "Gotoubun no Hanayome", "Sono Bisque Doll wa Koi wo Suru", "Blue Box",
    "Dandadan", "Kaijuu 8-gou", "Ore dake Level Up na Ken", "Mashle",
    "Jigokuraku", "Sousou no Frieren", "Kusuriya no Hitorigoto", "Dungeon Meshi",
    "Sakamoto Days", "Cowboy Bebop", "Samurai Champloo",
    "Neon Genesis Evangelion", "Bishoujo Senshi Sailor Moon", "Cardcaptor Sakura",
    "Digimon Adventure", "Pokemon", "Yuugiou Duel Monsters", "Gintama",
    "Detective Conan", "Tensei shitara Slime Datta Ken",
    "Tate no Yuusha no Nariagari", "Mushoku Tensei", "Youjo Senki", "Log Horizon",
    "Noragami", "Akame ga Kill!", "Tokyo Revengers", "Bungou Stray Dogs",
    "Nanatsu no Taizai", "Black Butler", "Ao no Exorcist", "Soul Eater",
    "Durarara!!", "Psycho-Pass", "Fate/Zero", "Mahou Shoujo Madoka Magica",
    "K-On!", "Lucky Star", "Ouran High School Host Club", "Kimi ni Todoke",
    "Nana", "Fruits Basket", "Akatsuki no Yona", "Berserk", "Claymore",
    "Hellsing", "Trigun", "Tengen Toppa Gurren Lagann", "Kill la Kill",
    "Erased", "Mirai Nikki", "Another", "Guilty Crown", "Darling in the Franxx",
    "Doraemon", "Crayon Shin-chan", "Sazae-san", "Chibi Maruko-chan",
    "Anpanman", "Nintama Rantarou", "Oshiri Tantei", "Yo-kai Watch",
    "Beyblade Burst", "Inazuma Eleven", "Duel Masters", "Cardfight!! Vanguard",
    "Future Card Buddyfight", "PriPara", "Aikatsu!", "Love Live! School Idol Project",
    "The Idolmaster", "BanG Dream!", "Uma Musume Pretty Derby", "Zombieland Saga",
    "Boruto: Naruto Next Generations", "Dragon Ball Super", "Saint Seiya",
    "Captain Tsubasa", "Major", "Ace of Diamond", "Yowamushi Pedal", "Free!",
    "Eyeshield 21", "Beelzebub", "Katekyo Hitman Reborn!", "D.Gray-man", "Toriko",
    "Medaka Box", "Nurarihyon no Mago", "Bakuman", "Nisekoi", "Blue Box",
    "Sakamoto Days", "Dungeon Meshi", "Delicious in Dungeon", "Komi Can't Communicate",
    "Rent-a-Girlfriend", "The Quintessential Quintuplets", "My Dress-Up Darling",
    "Kaguya-sama: Love is War", "Oshi no Ko", "Frieren: Beyond Journey's End",
    "The Apothecary Diaries", "Dandadan", "Kaiju No. 8", "Solo Leveling",
    "Mashle: Magic and Muscles", "Hell's Paradise", "Blue Lock", "Spy x Family",
    "Chainsaw Man", "Mob Psycho 100", "Vinland Saga", "Made in Abyss",
    "The Promised Neverland", "Dr. Stone", "Fire Force", "Black Clover",
    "Haikyuu!!", "Kuroko's Basketball", "Food Wars! Shokugeki no Soma",
    "Bleach: Sennen Kessen-hen", "Dragon Ball Daima", "Urusei Yatsura (2022)",
    "Rurouni Kenshin (2023)", "Ranma 1/2 (2024)",
    "Fate/stay night: Unlimited Blade Works", "Gintama'",
    "Bungo Stray Dogs 2", "Mob Psycho 100 II",
    "Attack on Titan: The Final Season",
    "Demon Slayer: Kimetsu no Yaiba - Entertainment District Arc",
    "My Hero Academia 2nd Season", "Sword Art Online II", "Tokyo Ghoul:re",
    "One Punch Man 2nd Season", "Dr. Stone: Stone Wars",
)


def fetch_item(title: str):
    """Поиск одного аниме для параллельной загрузки."""
    try:
        return title, find_anime(title), None
    except Exception as exc:  # noqa: BLE001
        return title, None, exc


def kitsutitles(max_pages: int = 30) -> List[str]:
    """Популярные аниме: Kitsu, а если он недоступен — встроенный список."""
    if max_pages <= 0:
        return list(reversed(POPULAR_FALLBACK))
    titles: List[str] = []
    try:
        for page in range(max_pages):
            url = KITSU + "?" + urllib.parse.urlencode({
                "sort": "-userCount", "page[limit]": 20, "page[offset]": page * 20,
            })
            data = get_json(url)
            items = data.get("data") or []
            for item in items:
                attributes = item.get("attributes") or {}
                names = attributes.get("titles") or {}
                title = (names.get("en_jp") or names.get("en")
                         or attributes.get("canonicalTitle"))
                if title and str(title) not in titles:
                    titles.append(str(title))
            if len(items) < 20:
                break
            time.sleep(0.2)
    except Exception as exc:  # noqa: BLE001
        print(f"Kitsu недоступен ({exc}), беру встроенный список", flush=True)
        return list(POPULAR_FALLBACK)
    if len(titles) < 20:
        titles.extend(item for item in POPULAR_FALLBACK if item not in titles)
    return titles


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description="Расширение набора сонглесса")
    parser.add_argument("--dsn", default=os.environ.get("DSN", ""))
    parser.add_argument("--target", type=int, default=DEFAULT_TARGET)
    parser.add_argument("--proxy", default=os.environ.get("ANIMETHEMES_PROXY", ""))
    parser.add_argument("--pages", type=int, default=30,
                        help="сколько страниц Kitsu просмотреть")
    parser.add_argument("--limit", type=int, default=0,
                        help="сколько названий обработать (0 — все)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fetch-only", action="store_true",
                        help="не трогать базу, только обновить catalog JSON")
    parser.add_argument("--out", default="", help="куда записать каталог в --fetch-only")
    args = parser.parse_args()
    if not args.dsn and not args.fetch_only:
        raise SystemExit("Укажите --dsn, переменную DSN или --fetch-only")

    configure_proxy(args.proxy or None)
    if args.fetch_only:
        catalog_rows = json.loads(CATALOG.read_text(encoding="utf-8"))
        existing = {(str(row.get("anime") or ""), str(row.get("song") or ""))
                    for row in catalog_rows}
        covers = {str(row.get("anime") or ""): str(row.get("cover") or "")
                  for row in catalog_rows if row.get("cover")}
        current_rows = list(catalog_rows)
        total = len(current_rows)
        print(f"Начало: {total} треков (catalog JSON)", flush=True)
        conn_ctx = contextlib.nullcontext(None)
    else:
        conn_ctx = psycopg.connect(args.dsn, row_factory=dict_row)
    with conn_ctx as conn:
        if not args.fetch_only:
            existing_rows = conn.execute(
                "SELECT anime, song, cover FROM songless_tracks ORDER BY id"
            ).fetchall()
            existing = {(str(row["anime"]), str(row["song"])) for row in existing_rows}
            covers = {str(row["anime"]): str(row["cover"])
                      for row in existing_rows if row["cover"]}
            total = len(existing_rows)
            print(f"Начало: {total} треков", flush=True)

        added = 0
        new_rows: List[Dict[str, Any]] = []
        if not args.fetch_only:
            current_rows = []
        titles = kitsutitles(args.pages)
        if args.limit:
            titles = titles[:max(1, args.limit)]
        name_map = anime_name_map()
        print(f"Kitsu: {len(titles)} популярных названий", flush=True)
        with ThreadPoolExecutor(max_workers=12) as pool:
            found = {title: (item, error) for title, item, error
                     in pool.map(fetch_item, titles)}
        for index, title in enumerate(titles, start=1):
            if total >= args.target:
                break
            item, error = found.get(title, (None, None))
            if error is not None:
                print(f"{index}. {title}: поиск не удался ({error})", flush=True)
                continue
            if not item:
                print(f"{index}. {title}: нет в AnimeThemes", flush=True)
                continue
            anime = name_map.get(normalize(str(item.get("name") or title))) or str(item.get("name") or title)
            themes = theme_rows(item)
            if not themes:
                print(f"{index}. {title}: нет OP", flush=True)
                continue
            cover = covers.get(anime) or anime_cover(item)
            if cover:
                covers[anime] = cover
            for theme in themes:
                if total >= args.target:
                    break
                key = (anime, theme["song"])
                if key in existing:
                    continue
                track_key = "a" + hashlib.sha1(
                    (anime + "|" + theme["slug"] + "|" + theme["song"]).encode("utf-8")
                ).hexdigest()[:15]
                print(f"  + {anime} — {theme['song']}", flush=True)
                row_data = {
                    "track_key": track_key, "anime": anime, "song": theme["song"],
                    "artist": theme["artist"], "year": str(item.get("year") or ""),
                    "audio": theme["video"], "cover": cover, "video": theme["video"],
                    "clip_start": 0.0, "clip_length": 8.0,
                }
                if not args.dry_run:
                    if args.fetch_only:
                        new_rows.append(row_data)
                    else:
                        conn.execute(
                            "INSERT INTO songless_tracks (track_key, anime, song, artist, year, "
                            "audio, cover, video, clip_start, clip_length, updated_at) "
                            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, 8, now()) "
                            "ON CONFLICT (track_key) DO NOTHING",
                            (track_key, anime, theme["song"], theme["artist"],
                             str(item.get("year") or ""), theme["video"], cover,
                             theme["video"]),
                        )
                existing.add(key)
                total += 1
                added += 1
            if not args.dry_run and not args.fetch_only:
                conn.commit()
            print(f"{index}. {anime}: {len(themes)} OP, всего {total}", flush=True)
            time.sleep(0.2)

        if not args.dry_run:
            if args.fetch_only:
                rows = current_rows + new_rows
                target = Path(args.out) if args.out else CATALOG
                target.write_text(
                    json.dumps(rows, ensure_ascii=False, indent=1) + "\n",
                    encoding="utf-8",
                )
                print(f"Каталог обновлён: {len(rows)} треков -> {target}", flush=True)
            else:
                rows = conn.execute(
                    "SELECT track_key, anime, song, artist, year, audio, cover, video, "
                    "clip_start, clip_length FROM songless_tracks ORDER BY id"
                ).fetchall()
                for row in rows:
                    if str(row.get("audio") or "") == "db:clip":
                        row["audio"] = str(row.get("video") or "")
                    row["clip_start"] = float(row.get("clip_start") or 0)
                    row["clip_length"] = float(row.get("clip_length") or 8)
                CATALOG.write_text(
                    json.dumps([dict(row) for row in rows], ensure_ascii=False, indent=1) + "\n",
                    encoding="utf-8",
                )
                print(f"Каталог обновлён: {len(rows)} треков", flush=True)
        print(f"Добавлено: {added}, итого: {total}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())