# -*- coding: utf-8 -*-
"""Обложки и ссылки на записи для новых опенингов (запускается на сервере).

Что делает:
    * для каждой новой строки `songless_tracks` подбирает ссылку на запись
      опенинга на CDN animethemes (`https://v.animethemes.moe/<Slug>-OP<N>.webm`),
      проверяя варианты запросом Range — API animethemes с сервера закрыт
      Cloudflare, а CDN открыт;
    * берёт обложку аниме из AniList (GraphQL), уменьшает её через ffmpeg и
      кладёт в `front/games/animesongless/covers`;
    * прописывает в базу `video` и `cover`.

Фрагменты после этого режет уже сервис `_srv_extend_clips.py`: он берёт треки с
заполненным `video`, вырезает `clip_start .. +20.5 с` и кладёт MP3 в
`audio_clips` — трек становится играбельным.

    /opt/greenhouse/.venv/bin/python _fill_openings_media.py --dry-run
    /opt/greenhouse/.venv/bin/python _fill_openings_media.py --apply
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, "/opt/greenhouse")

from backend.db import open_database  # noqa: E402

import _add_openings  # noqa: E402 — список новых опенингов и их ключи

COVERS = Path("/opt/greenhouse/front/games/animesongless/covers")
CDN = "https://v.animethemes.moe"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
FFMPEG = "/usr/bin/ffmpeg"
COVER_WIDTH = 320
# Пауза между запросами к CDN: без неё он отвечает 503 (ограничение частоты).
PAUSE = 8.0

# label -> (поиск в AniList, варианты (слаг animethemes, номер OP) по порядку)
MEDIA: Dict[str, Tuple[str, Tuple[Tuple[str, int], ...]]] = {
    "рейтинг королей op 2": ("Ousama Ranking", (("OusamaRanking", 2),)),
    "JoJo op 1": ("JoJo no Kimyou na Bouken (TV)", (("JoJoNoKimyouNaBouken", 1),)),
    "JoJo op2": ("JoJo no Kimyou na Bouken (TV)", (("JoJoNoKimyouNaBouken", 2),)),
    "JoJo op3": ("JoJo no Kimyou na Bouken: Stardust Crusaders",
                 (("JoJoNoKimyouNaBoukenStardustCrusaders", 1),)),
    "JoJo op4": ("JoJo no Kimyou na Bouken: Stardust Crusaders Egypt Hen",
                 (("JoJoNoKimyouNaBoukenStardustCrusadersEgyptHen", 1),)),
    "JoJo SBR op1": ("JoJo no Kimyou na Bouken: Steel Ball Run",
                     (("JoJoNoKimyouNaBoukenSteelBallRun", 1),)),
    "CoTe op1": ("Youkoso Jitsuryoku Shijou Shugi no Kyoushitsu e",
                 (("YoukosoJitsuryokuShijouShugiNoKyoushitsuE", 1),)),
    "CoTe op2": ("Youkoso Jitsuryoku Shijou Shugi no Kyoushitsu e 2nd Season",
                 (("YoukosoJitsuryokuShijouShugiNoKyoushitsuE2ndSeason", 1),)),
    "CoTe op3": ("Youkoso Jitsuryoku Shijou Shugi no Kyoushitsu e 3rd Season",
                 (("YoukosoJitsuryokuShijouShugiNoKyoushitsuE3rdSeason", 1),)),
    "CoTe op4": ("Youkoso Jitsuryoku Shijou Shugi no Kyoushitsu e 4th Season",
                 (("YoukosoJitsuryokuShijouShugiNoKyoushitsuE4thSeason", 1),)),
    "Shangri-La Frontier": ("Shangri-La Frontier",
                            (("ShangriLaFrontier", 1), ("ShangriLaFrontier2ndSeason", 1))),
    "Shangri-La op1": ("Shangri-La Frontier", (("ShangriLaFrontier", 1),)),
    "Shangri-La op2": ("Shangri-La Frontier", (("ShangriLaFrontier", 2),)),
    "Shangri-La op3": ("Shangri-La Frontier Season 2",
                       (("ShangriLaFrontier2ndSeason", 1), ("ShangriLaFrontier2ndSeason", 2))),
    "Windbreaker op1": ("Wind Breaker", (("WindBreaker", 1),)),
    "Spy×Family op2": ("Spy x Family", (("SpyXFamily", 2), ("SpyXFamilyS2", 1))),
    "Spy×Family op3": ("Spy x Family Season 3",
                       (("SpyXFamilyS3", 1), ("SpyXFamily", 3), ("SpyXFamilyS2", 2))),
    "Mushoku Tensei S2 op1": ("Mushoku Tensei: Isekai Ittara Honki Dasu Season 2",
                              (("MushokuTenseiIsekaiIttaraHonkiDasu2ndSeason", 1),
                               ("MushokuTenseiIsekaiIttaraHonkiDasu", 3))),
    "Black Clover op14": ("Black Clover", (("BlackClover", 14), ("BlackClover", 13))),
    "MHA ODD FUTURE": ("Boku no Hero Academia 3", (("BokuNoHeroAcademiaS3", 2),)),
    "MHA Merry-Go-Round": ("Boku no Hero Academia 5", (("BokuNoHeroAcademiaS5", 1),)),
    "MHA «カーテンコール»": ("Boku no Hero Academia 7",
                            (("BokuNoHeroAcademiaS7", 2), ("BokuNoHeroAcademiaS7", 1))),
    "MHA «ぼくらの»": ("Boku no Hero Academia 6",
                      (("BokuNoHeroAcademiaS6", 2), ("BokuNoHeroAcademiaS6", 1))),
    "JJK op5": ("Jujutsu Kaisen: Shimetsu Kaiyuu",
                (("JujutsuKaisenShimetsuKaiyuuHen", 1), ("JujutsuKaisen", 5))),
    "JJK op3": ("Jujutsu Kaisen 2nd Season", (("JujutsuKaisen2ndSeason", 1),)),
    "JJK op4": ("Jujutsu Kaisen 2nd Season", (("JujutsuKaisen2ndSeason", 2),)),
    "Mashle op2": ("Mashle: Magic and Muscles", (("MashleMagicAndMuscles", 2),)),
    "Attack on Titan op3": ("Shingeki no Kyojin Season 2", (("ShingekiNoKyojinS2", 1),)),
    "Attack on Titan op4": ("Shingeki no Kyojin Season 3", (("ShingekiNoKyojinS3", 1),)),
    "Attack on Titan op6": ("Shingeki no Kyojin: The Final Season",
                            (("ShingekiNoKyojinS4", 1), ("ShingekiNoKyojinTheFinalSeason", 1))),
    "Attack on Titan op7": ("Shingeki no Kyojin: The Final Season Part 2",
                            (("ShingekiNoKyojinS4KanketsuHenKouhen", 1),
                             ("ShingekiNoKyojinS4Part2", 1))),
    "Witch Watch op1": ("Witch Watch", (("WitchWatch", 1),)),
    "Zom 100 op1": ("Zom 100: Zombie ni Naru made ni Shitai 100 no Koto",
                    (("Zom100ZombiNiNaruMadeNiShitai100NoKoto", 1),)),
    "Ya Boy Kongming!": ("Paripi Koumei", (("ParipiKoumei", 1),)),
    "Cyberpunk: Edgerunners op1": ("Cyberpunk: Edgerunners", (("CyberpunkEdgerunners", 1),)),
    "Dr.STONE SCIENCE FUTURE": ("Dr. Stone: Science Future", (("DrStoneScienceFuture", 1),)),
    "Alya Sometimes Hides Her Feelings": (
        "Alya Sometimes Hides Her Feelings in Russian",
        (("TokidokiBosottoRussiaGoDeDereruTonariNoAryaSan", 1),)),
    "Skip and Loafer «メロウ»": ("Skip to Loafer", (("SkipToLoafer", 1),)),
    "Call of the Night op1": ("Yofukashi no Uta", (("YofukashiNoUta", 1),)),
    "Call of the Night op2": ("Yofukashi no Uta", (("YofukashiNoUta", 2),)),
    "Chainsaw Man op2": ("Chainsaw Man", (("ChainsawMan", 2), ("ChainsawManRezeHen", 1))),
    "Overlord op2": ("Overlord II", (("OverlordII", 1), ("OverlordS2", 1))),
    "Overlord op3": ("Overlord III", (("OverlordIII", 1), ("OverlordS3", 1))),
    "Overlord op4": ("Overlord IV", (("OverlordIV", 1), ("OverlordS4", 1))),
    "Urusei Yatsura «アイウエ»": ("Urusei Yatsura (2022)",
                                 (("UruseiYatsura2022", 1), ("UruseiYatsura", 1))),
    "Bishounen Tanteidan": ("Bishounen Tanteidan", (("BishounenTanteidan", 1),)),
    "Horimiya op": ("Horimiya", (("Horimiya", 1),)),
    "Makeine": ("Make Heroine ga Oosugiru!", (("MakeHeroineGaOosugiru", 1),)),
    "Ninja Kamui op1": ("Ninja Kamui", (("NinjaKamui", 1),)),
    "Kill Blue op1": ("Kill Blue", (("KillBlue", 1),)),
    "My Deer Friend Nokotan op1": ("Shikanoko Nokonoko Koshitantan",
                                   (("ShikanokoNokonokoKoshitantan", 1),)),
    "Oshi no Ko op2": ("Oshi no Ko", (("OshiNoKo", 2), ("OshiNoKo", 3))),
    "Oshi no Ko op3": ("Oshi no Ko", (("OshiNoKo", 3), ("OshiNoKo", 2))),
}

# Варианты имени файла на CDN: у записей бывают пометки качества и источника.
SUFFIXES = ("", "-NCBD1080", "-NCDVD480")

HEADERS = {"User-Agent": UA, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"}


def http(url: str, headers: Optional[Dict[str, str]] = None,
         data: Optional[bytes] = None, timeout: int = 15,
         limit: int = 8000) -> Tuple[int, bytes, Dict[str, str]]:
    """Запрос с кодом ответа, телом и заголовками (ошибки не бросает)."""
    request = urllib.request.Request(url, headers=headers or HEADERS, data=data)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read(limit), dict(response.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, b"", {}
    except Exception as exc:  # noqa: BLE001
        return 0, str(exc).encode("utf-8", "replace"), {}


# Сколько раз подряд CDN ответил 503: чем больше, тем дольше пауза.
_busy = 0


def resolve_video(slug: str, op: int,
                  suffixes: Tuple[str, ...] = SUFFIXES) -> Optional[str]:
    """Первая существующая ссылка на запись: имя файла с пометкой или без.

    CDN ограничивает частоту запросов (503), поэтому между проверками пауза, а
    503 — повод подождать и повторить, а не «файла нет»: 404 значит именно
    отсутствие файла. Серия 503 подряд увеличивает паузу до пяти минут.
    """
    global _busy
    for suffix in suffixes:
        url = f"{CDN}/{slug}-OP{op}{suffix}.webm"
        for _attempt in range(3):
            status, _body, headers = http(url, {**HEADERS, "Range": "bytes=0-200"}, timeout=15)
            if status in (200, 206) and "webm" in headers.get("Content-Type", ""):
                _busy = 0
                time.sleep(PAUSE)
                return url
            if status == 404:
                _busy = 0
                break
            _busy += 1
            time.sleep(min(60 * _busy, 300) if status == 503 else 10)
        time.sleep(PAUSE)
    return None


def anilist_cover(query: str) -> Optional[str]:
    """Ссылка на постер аниме из AniList."""
    payload = json.dumps({
        "query": ("query ($search: String) { Media(search: $search, type: ANIME) "
                  "{ title { romaji } coverImage { extraLarge large } } }"),
        "variables": {"search": query},
    }).encode("utf-8")
    status, body, _ = http("https://graphql.anilist.co",
                           {**HEADERS, "Content-Type": "application/json"},
                           data=payload, timeout=20)
    if status != 200 or not body:
        return None
    try:
        media = json.loads(body.decode("utf-8")).get("data", {}).get("Media") or {}
    except ValueError:
        return None
    image = media.get("coverImage") or {}
    return str(image.get("extraLarge") or image.get("large") or "") or None


def download(url: str, target: Path, timeout: int = 60) -> int:
    """Скачивает файл целиком (картинки бывают больше лимита одного чтения)."""
    import shutil

    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        with target.open("wb") as handle:
            shutil.copyfileobj(response, handle)
    return target.stat().st_size


def save_cover(anime: str, url: str) -> str:
    """Скачивает обложку, уменьшает через ffmpeg и кладёт в папку игры."""
    digest = hashlib.sha1(anime.encode("utf-8")).hexdigest()[:16]
    target = COVERS / f"{digest}.jpg"
    if target.exists() and target.stat().st_size > 4000:
        return f"covers/{target.name}"
    temp = COVERS / f"{digest}.src"
    try:
        size = download(url, temp)
    except Exception:  # noqa: BLE001 — сеть/404: обложки просто не будет
        temp.unlink(missing_ok=True)
        return ""
    if size < 2000:
        temp.unlink(missing_ok=True)
        return ""
    result = subprocess.run(
        [FFMPEG, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(temp), "-vf", f"scale={COVER_WIDTH}:-2", "-q:v", "4", str(target)],
        capture_output=True, text=True, timeout=60)
    temp.unlink(missing_ok=True)
    if result.returncode != 0 or not target.exists() or target.stat().st_size < 4000:
        target.unlink(missing_ok=True)
        return ""
    return f"covers/{target.name}"


def read_dsn() -> str:
    """Строка подключения из окружения сервера (как у _srv_extend_clips.py)."""
    env = Path("/etc/greenhouse.env").read_text(encoding="utf-8")
    for line in env.splitlines():
        if line.startswith("GREENHOUSE_DSN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("в /etc/greenhouse.env нет GREENHOUSE_DSN")


def main() -> int:
    parser = argparse.ArgumentParser(description="обложки и записи для новых опенингов")
    parser.add_argument("--apply", action="store_true", help="записать в базу")
    parser.add_argument("--only", action="append", default=[], help="только эти метки")
    parser.add_argument("--no-covers", action="store_true", help="не трогать обложки")
    parser.add_argument("--covers-only", action="store_true", help="только обложки")
    parser.add_argument("--fast", action="store_true",
                        help="проверять только имена без пометок (меньше запросов)")
    args = parser.parse_args()

    COVERS.mkdir(parents=True, exist_ok=True)
    db = open_database(None, read_dsn())
    existing = {str(track.get("track_key") or ""): track for track in db.songless_tracks()}
    videos = covers = 0
    known_anime: Dict[str, str] = {}

    for row in _add_openings.rows():
        label = str(row["label"])
        if args.only and label not in args.only:
            continue
        plan = MEDIA.get(label)
        if not plan:
            print(f"НЕТ ПЛАНА  {label}", flush=True)
            continue
        query, variants = plan

        video = str((existing.get(str(row["track_key"])) or {}).get("video") or "")
        if not args.covers_only and not video:
            suffixes = SUFFIXES[:1] if args.fast else SUFFIXES
            for slug, op in variants:
                video = resolve_video(slug, op, suffixes) or ""
                if video:
                    break
        if _busy >= 4:
            print("CDN ограничивает запросы — прерываю проход, продолжу позже", flush=True)
            break

        anime = str(row["anime"])
        cover = ""
        if not args.no_covers:
            if anime in known_anime:
                cover = known_anime[anime]
            else:
                cover_url = anilist_cover(query)
                cover = save_cover(anime, cover_url) if cover_url else ""
                known_anime[anime] = cover

        mark = "OK  " if (cover if args.covers_only else video) else "FAIL"
        print(f"{mark} {label:32.32} {anime[:32]:34.34} "
              f"video={(video.split('/')[-1] if video else '-'):34.34} "
              f"cover={bool(cover)}", flush=True)

        if not args.apply:
            continue
        with db.connect() as connection:
            with connection.cursor() as cursor:
                if video:
                    cursor.execute(
                        "UPDATE songless_tracks SET video = %s, updated_at = now() "
                        "WHERE track_key = %s", (video, row["track_key"]))
                    videos += cursor.rowcount
                if cover:
                    cursor.execute(
                        "UPDATE songless_tracks SET cover = %s, updated_at = now() "
                        "WHERE anime = %s AND (cover = '' OR cover IS NULL)",
                        (cover, anime))
                    covers += cursor.rowcount

    print(f"итог: video={videos}, cover={covers}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())