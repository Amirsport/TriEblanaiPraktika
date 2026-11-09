# -*- coding: utf-8 -*-
"""Скачивает опенинги для игры «Аниме-сонглесс» с YouTube в базу.

Скрипт разработческий. Он закрывает дыру, о которой честно пишут README и
страница игры: справочные сведения о треках есть, а записей нет — поэтому
играть нечего, пока владелец сайта не положит аудио. Здесь аудио берётся с
YouTube: для каждого аниме из `backend/songless_data.py` находится видео
опенинга через **YouTube Data API v3** (`search.list`), из него скачивается
лучшая звуковая дорожка (`yt-dlp`) и конвертируется в MP3 (ffmpeg).

Дальше файлы не раздаются с сайта: их режет и кладёт **в базу** `songs.py`
(маркер `db:clip`, фрагменты лежат в таблице `audio_clips`). Для этого скрипт
пишет рядом со скачанным музыку таблицу соответствий `music.json` и печатает
готовую команду `songs.py` (либо запускает её сам с `--attach`).

Как устроен сбор:

    * ключ читается из --api-key, переменной окружения YOUTUBE_API_KEY или
      файла `data/youtube-api-key.txt` (каталог `data/` в репозиторий не
      попадает); ключ берётся на https://console.cloud.google.com/ в проекте
      с включённым «YouTube Data API v3»;
    * если YouTube открыт только через прокси, путь задаётся ключом --proxy
      (например `socks5://127.0.0.1:10808`) или переменной HTTPS_PROXY —
      через него идут и поиск, и загрузка; для socks-прокси нужен PySocks;
    * на каждый трек пробуются по очереди несколько запросов (название
      опенинга, исполнитель, само аниме); ответы кэшируются в каталоге
      временных файлов, чтобы повторный запуск не тратил квоту;
    * `search.list` стоит 100 единиц квоты, дневной запас у нового проекта —
      10 000 единиц, то есть меньше сотни поисков в сутки: набор из ~70 песен
      укладывается, но с запасом впритык;
    * уже скачанные файлы не перекачиваются — только недостающие (--force
      перезаписывает).

Запуск (из корня проекта):

    # скачать музыку и нарезать фрагменты прямо в базу
    python _fetch_songless_audio.py --attach --dsn "postgresql://greenhouse@localhost:5432/greenhouse"

    # сперва посмотреть, что и по каким запросам будет найдено (без сети)
    python _fetch_songless_audio.py --dry-run

    # скачать только часть набора
    python _fetch_songless_audio.py --only "Наруто" --only "Блич"

    # YouTube доступен только через прокси
    python _fetch_songless_audio.py --proxy socks5://127.0.0.1:10808 --attach --dsn "..."

Перед запуском нужен `yt-dlp` (см. requirements-fetch.txt) и ffmpeg — либо в
системе, либо из пакета imageio-ffmpeg (он уже нужен `songs.py`).

**Про авторские права.** Опенинги защищены авторским правом. Скачивать их
можно только для личных нужд и проверок; выкладывать такие записи на сайте в
открытый доступ нельзя. Скрипт кладёт фрагменты в локальную базу и ничего не
публикует — ответственность за использование записей лежит на владельце сайта.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"

CACHE_DIR = Path(os.environ.get("TEMP") or os.environ.get("TMP") or ".") / "songless-youtube"
DEFAULT_OUT = ROOT / "_songless_audio"
DEFAULT_KEY_FILE = ROOT / "data" / "youtube-api-key.txt"
SEARCH_API = "https://www.googleapis.com/youtube/v3/search"
UA = "GreenhouseCraft/1.0 (personal non-commercial project; contact: site owner)"

# Символы, недопустимые в имени файла: на Windows из-за «:» в названии аниме
# вроде «Наруто: Ураганные хроники» файл просто не создать. Заменяем их, а
# исходное название храним в music.json — по нему songs.py и находит трек.
UNSAFE = re.compile(r'[\\/:*?"<>|]+')


def normalize(value: Any) -> str:
    """Ключ сравнения имён: регистр и лишние пробелы не важны."""
    return " ".join(str(value or "").split()).casefold()


def safe_stem(anime: str) -> str:
    """Имя файла для записи: без запрещённых символов и хвостовых точек."""
    cleaned = UNSAFE.sub("_", anime).strip().strip(".")
    return cleaned or "track"


def read_api_key(explicit: Optional[str]) -> Optional[str]:
    """Ключ YouTube Data API: аргумент, переменная окружения или файл."""
    if explicit:
        return explicit.strip()
    from_env = (os.environ.get("YOUTUBE_API_KEY") or os.environ.get("YT_API_KEY") or "").strip()
    if from_env:
        return from_env
    if DEFAULT_KEY_FILE.is_file():
        value = DEFAULT_KEY_FILE.read_text(encoding="utf-8-sig").strip()
        if value:
            return value
    return None


def tracks(only: Sequence[str], limit: Optional[int]) -> List[Dict[str, Any]]:
    """Треки из данных игры: при --only остаются только выбранные аниме."""
    sys.path.insert(0, str(BACKEND))
    import songless_data  # noqa: PLC0415 — подключается отсюда, а не на импорте файла

    wanted = [normalize(name) for name in only]
    rows: List[Dict[str, Any]] = []
    for row in songless_data.seed_rows():
        anime = str(row.get("anime") or "")
        if wanted and not any(word in normalize(anime) for word in wanted):
            continue
        rows.append(row)
    if limit is not None:
        rows = rows[: max(0, limit)]
    return rows


def queries_for(track: Dict[str, Any]) -> List[str]:
    """Запросы к YouTube по треку: от самого точного к самому общему.

    Первым идёт связка «опенинг — исполнитель»: название песни и исполнитель
    чаще записаны латиницей, и YouTube находит их точнее, чем русское название
    аниме. Дальше — аниме рядом с песней и, наконец, просто аниме.
    """
    song = str(track.get("song") or "").strip()
    anime = str(track.get("anime") or "").strip()
    artist = str(track.get("artist") or "").strip()
    raw = [
        f"{song} {artist} opening",
        f"{song} {anime} opening",
        f"{anime} opening",
    ]
    result: List[str] = []
    for query in raw:
        value = " ".join(query.split())
        if value and value not in result:
            result.append(value)
    return result


# Слова, которые встречаются почти в любом ролике и ничего не говорят о треке.
RELEVANCE_STOP = {
    "the", "and", "for", "with", "from", "opening", "openings", "version",
    "full", "song", "music", "video", "official", "anime", "опенинг", "опенинг",
    "клип", "песня", "видео", "официальный",
}


def relevance_tokens(value: Any) -> List[str]:
    """Значимые слова строки трека для проверки, что ролик действительно про него."""
    tokens: List[str] = []
    for word in re.split(r"[^0-9a-zа-яё]+", str(value or "").casefold()):
        if len(word) >= 3 and word not in RELEVANCE_STOP and word not in tokens:
            tokens.append(word)
    return tokens


# Пометки, по которым видно, что ролик — опенинг, а не кавер или клип.
OPENING_RE = re.compile(
    r"\b(op|ops|opening|openings|опенинг|опенинги|creditless|nc|tv\s*size)\b",
    re.IGNORECASE,
)

# Сборники и плейлисты: в них нужный опенинг есть, но угадывать по ним нельзя.
COMPILATION_RE = re.compile(
    r"\b(all|compilation|playlist|collection|medley|mix|hours?|hour|"
    r"best\s+of|top\s+\d+|full\s+album|every\s+opening)\b",
    re.IGNORECASE,
)

# Каверы, живые и «облегчённые» версии: песня та же, но звучит не как опенинг.
BAD_VERSION_RE = re.compile(
    r"\b(cover|covered|coverver|jazz|acoustic|piano|instrumental|karaoke|"
    r"nightcore|remix|lullaby|music\s*box|8-?bit|orchestra|orchestral|"
    r"philharmonic|live|arrange[ds]?|tribute|first\s+take)\b",
    re.IGNORECASE,
)


def relevance_score(item: Dict[str, Any], track: Dict[str, Any]) -> int:
    """Насколько ролик похож на нужный опенинг.

    Совпадение только по исполнителю ничего не значит: под тем же именем
    выкладывают каверы и колыбельные. Поэтому ролик принимается, лишь если в
    нём есть название песни, название аниме или пометка «opening», и это не
    сборник, кавер или концертная версия.
    """
    snippet = item.get("snippet") or {}
    text = " ".join(str(snippet.get(key) or "") for key in
                    ("title", "description", "channelTitle")).casefold()
    title = str(snippet.get("title") or "")
    if COMPILATION_RE.search(title) or BAD_VERSION_RE.search(title):
        return 0
    song_hits = sum(1 for token in relevance_tokens(track.get("song")) if token in text)
    anime_hits = sum(1 for token in relevance_tokens(track.get("anime")) if token in text)
    artist_hits = sum(1 for token in relevance_tokens(track.get("artist")) if token in text)
    opening = bool(OPENING_RE.search(title))
    if not (song_hits or anime_hits or opening):
        return 0
    return song_hits * 3 + anime_hits * 3 + artist_hits + (2 if opening else 0)


def params_without_key(params: Dict[str, str]) -> Dict[str, str]:
    """Параметры запроса для хэша кэша — без ключа API."""
    return {key: value for key, value in params.items() if key != "key"}


def explain_http(exc: urllib.error.HTTPError) -> str:
    """Человеческое объяснение частых ошибок YouTube Data API."""
    try:
        payload = json.loads(exc.read().decode("utf-8"))
    except Exception:  # noqa: BLE001 — тело ответа может быть не JSON
        return "не удалось прочитать ответ"
    error = payload.get("error") or {}
    reasons = [item.get("reason", "") for item in error.get("errors") or []]
    message = error.get("message", "")
    if "quotaExceeded" in reasons:
        return ("исчерпана дневная квота (search.list стоит 100 единиц из 10 000 "
                "в сутки). Попробуйте завтра или возьмите другой проект.")
    if "keyInvalid" in reasons or "badRequest" in reasons:
        return f"ключ не принят: {message}"
    if "ipRefererBlocked" in reasons:
        return "ключ ограничен по IP или Referer — снимите ограничения в консоли"
    return message or ", ".join(reason for reason in reasons if reason) or "неизвестная ошибка"


def fetch_json(request: urllib.request.Request, opener: Optional[Any] = None,
               attempts: int = 3) -> Dict[str, Any]:
    """Запрос к API с короткими повторами: сеть бывает нестабильной."""
    last: Optional[Exception] = None
    open_url = opener.open if opener is not None else urllib.request.urlopen
    for attempt in range(1, attempts + 1):
        try:
            with open_url(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code >= 500 and attempt < attempts:
                last = exc
                time.sleep(attempt)
                continue
            raise SystemExit(f"  YouTube ответил {exc.code}: {explain_http(exc)}") from None
        except urllib.error.URLError as exc:
            if attempt < attempts:
                last = exc
                time.sleep(attempt * 2)
                continue
            raise SystemExit(
                f"  нет связи с YouTube ({exc.reason}).\n"
                "  Проверьте, что этот компьютер открывает youtube.com и googleapis.com:"
                " сеть\n  может их блокировать (pypi.org при этом работает)."
            ) from None
    raise SystemExit(f"  не удалось получить ответ YouTube: {last}")


def search_video(query: str, track: Dict[str, Any], api_key: str,
                 opener: Optional[Any] = None) -> Optional[str]:
    """Идентификатор ролика из YouTube Data API v3; ответы кэшируются на диске.

    Берём несколько результатов и оставляем самый близкий к треку: у YouTube
    бывает, что верхняя выдача по запросу — совсем другое видео.
    """
    params = {
        "part": "snippet",
        "type": "video",
        "maxResults": "5",
        "q": query,
        "safeSearch": "none",
        # Опенинг длится полторы-две минуты: «short» отсекает часовые сборники
        # всех опенингов и полные альбомы.
        "videoDuration": "short",
        "key": api_key,
    }
    digest = hashlib.sha1(
        urllib.parse.urlencode(params_without_key(params)).encode("utf-8")
    ).hexdigest()
    cached = CACHE_DIR / f"search-{digest}.json"
    if cached.is_file():
        data = json.loads(cached.read_text(encoding="utf-8"))
    else:
        url = SEARCH_API + "?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(url, headers={"User-Agent": UA})
        data = fetch_json(request, opener)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cached.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    items = [item for item in data.get("items") or [] if isinstance(item, dict)]
    if not items:
        return None
    best = max(items, key=lambda item: relevance_score(item, track))
    if relevance_score(best, track) <= 0:
        return None
    return str((best.get("id") or {}).get("videoId") or "").strip() or None


def find_video(track: Dict[str, Any], api_key: str, verbose: bool,
               opener: Optional[Any] = None) -> Optional[str]:
    """Первый найденный ролик по очереди запросов трека."""
    for query in queries_for(track):
        if verbose:
            print(f"    ищу: {query}")
        video_id = search_video(query, track, api_key, opener)
        if video_id:
            return video_id
    return None


def download_audio(video_id: str, target: str, ffmpeg: str,
                   proxy: Optional[str] = None) -> None:
    """Скачивает лучшую звуковую дорожку ролика и кладёт её рядом как MP3."""
    try:
        import yt_dlp  # noqa: PLC0415 — тяжёлая зависимость, нужна только здесь
    except ImportError:
        raise SystemExit(
            "Не найден yt-dlp — он скачивает звук с YouTube. Установите его:\n"
            f"  {sys.executable} -m pip install -r requirements-fetch.txt"
        ) from None

    options = {
        "format": "bestaudio/best",
        "outtmpl": target,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "ffmpeg_location": ffmpeg,
        # Веб-клиенты YouTube часто отвечают «The page needs to be reloaded»
        # (антибот-проверка). Android-клиент отдаёт звук без неё.
        "extractor_args": {"youtube": {"player_client": ["android", "ios", "web"]}},
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "retries": 2,
    }
    if proxy:
        options["proxy"] = proxy
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([f"https://www.youtube.com/watch?v={video_id}"])


def prepare_proxy(proxy: Optional[str]) -> Optional[Any]:
    """Готовит выход в сеть через прокси: `http://` или `socks5://`.

    urllib сам SOCKS не умеет, поэтому для socks-прокси подключаем PySocks —
    он подменяет модуль socket, и обычные запросы идут через прокси.
    Для http-прокси возвращаем opener с ProxyHandler (его получает fetch_json).
    """
    if not proxy:
        return None
    scheme, separator, host_port = proxy.partition("://")
    if not separator:  # «127.0.0.1:10808» без схемы — считаем socks5
        scheme, host_port = "socks5", proxy
    scheme = scheme.lower()
    if scheme.startswith("socks"):
        try:
            import socks  # PySocks
        except ImportError:
            raise SystemExit(
                "Для socks-прокси нужен PySocks:\n"
                f"  {sys.executable} -m pip install -r requirements-fetch.txt"
            ) from None
        kind = socks.SOCKS5 if scheme in ("socks5", "socks5h") else socks.SOCKS4
        rdns = scheme.endswith("h") or scheme.endswith("a")
        host, _, port = host_port.partition(":")
        socks.set_default_proxy(kind, host, int(port or 1080), rdns=rdns)
        socket.socket = socks.socksocket
        return None
    return urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": proxy, "https": proxy})
    )


def find_ffmpeg(explicit: Optional[str]) -> Optional[str]:
    """ffmpeg из аргумента, PATH или пакета imageio-ffmpeg (как в songs.py)."""
    if explicit:
        return explicit
    from_path = shutil.which("ffmpeg")
    if from_path:
        return from_path
    try:
        import imageio_ffmpeg  # noqa: PLC0415

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001 — пакет не установлен или бинарник недоступен
        return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Опенинги «Аниме-сонглесса» с YouTube: скачать и нарезать в базу",
    )
    parser.add_argument("--api-key", help="ключ YouTube Data API (иначе YOUTUBE_API_KEY "
                                          f"или {DEFAULT_KEY_FILE})")
    parser.add_argument("--proxy", help="прокси для доступа к YouTube, напр. "
                                        "socks5://127.0.0.1:10808 или http://127.0.0.1:8080 "
                                        "(иначе HTTPS_PROXY/ALL_PROXY)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help=f"куда складывать скачанное (по умолчанию {DEFAULT_OUT.name})")
    parser.add_argument("--only", action="append", default=[],
                        help="только эти аниме (можно несколько раз)")
    parser.add_argument("--limit", type=int, help="обработать не больше N треков")
    parser.add_argument("--map", dest="map_file", type=Path,
                        help="куда положить music.json для songs.py")
    parser.add_argument("--ffmpeg", help="путь к ffmpeg (иначе ищется сам)")
    parser.add_argument("--force", action="store_true",
                        help="перекачать записи, которые уже лежат в --out")
    parser.add_argument("--dry-run", action="store_true",
                        help="показать план и запросы, ничего не скачивая")
    parser.add_argument("--attach", action="store_true",
                        help="сразу нарезать фрагменты в базу через songs.py")
    parser.add_argument("--db", help="файл SQLite для --attach (передаётся songs.py)")
    parser.add_argument("--dsn", help="строка PostgreSQL для --attach (передаётся songs.py)")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    args = build_parser().parse_args(argv)
    rows = tracks(args.only, args.limit)
    if not rows:
        print("Нет треков под указанные условия.")
        return 1

    out_dir: Path = args.out
    map_path: Path = args.map_file or (out_dir / "music.json")

    if args.dry_run:
        print(f"Треков: {len(rows)}. Запросы, которые пойдут в YouTube Data API:\n")
        for row in rows:
            print(f"  {row['anime']}  →  {safe_stem(row['anime'])}.mp3")
            for query in queries_for(row):
                print(f"      · {query}")
        print(f"\nФайлы: {out_dir}\nСоответствия: {map_path}")
        return 0

    api_key = read_api_key(args.api_key)
    if not api_key:
        print("Нужен ключ YouTube Data API: задайте --api-key, переменную окружения\n"
              f"YOUTUBE_API_KEY или положите ключ в {DEFAULT_KEY_FILE}.")
        return 2

    proxy = (args.proxy or os.environ.get("HTTPS_PROXY") or os.environ.get("ALL_PROXY")
             or os.environ.get("HTTP_PROXY") or "").strip() or None
    opener = prepare_proxy(proxy)
    if proxy:
        print(f"Сеть через прокси: {proxy}\n")

    ffmpeg = find_ffmpeg(args.ffmpeg)
    if not ffmpeg:
        print("Не найден ffmpeg — без него mp3 не собрать:\n"
              f"  {sys.executable} -m pip install -r requirements-fetch.txt")
        return 2

    out_dir.mkdir(parents=True, exist_ok=True)
    mapping: Dict[str, str] = {}
    saved = skipped = missing = errors = 0

    for number, row in enumerate(rows, 1):
        anime = str(row.get("anime") or "")
        stem = safe_stem(anime)
        target = out_dir / f"{stem}.mp3"
        print(f"[{number}/{len(rows)}] {anime} — {row.get('song')}")

        if target.is_file() and not args.force:
            mapping[stem] = anime
            print("  уже скачано")
            skipped += 1
            continue

        video_id = find_video(row, api_key, verbose=True, opener=opener)
        if not video_id:
            print("  не нашлось подходящего ролика")
            missing += 1
            continue

        try:
            download_audio(video_id, str(out_dir / f"{stem}.%(ext)s"), ffmpeg, proxy)
        except SystemExit:
            raise
        except Exception as exc:  # noqa: BLE001 — один трек не должен ронять всё
            print(f"  ошибка загрузки: {exc}")
            errors += 1
            continue

        if not target.is_file():
            print("  yt-dlp не оставил mp3-файл")
            errors += 1
            continue

        mapping[stem] = anime
        print(f"  сохранено: {target.name}  (youtube:{video_id})")
        saved += 1

    if mapping:
        map_path.parent.mkdir(parents=True, exist_ok=True)
        map_path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")

    print("\nГотово.")
    print(f"  скачано: {saved}")
    if skipped:
        print(f"  уже было: {skipped}")
    if missing:
        print(f"  без ролика: {missing}")
    if errors:
        print(f"  с ошибками: {errors}")
    print(f"  папка: {out_dir}")
    if mapping:
        print(f"  соответствия: {map_path}")

    attach_args = ["--only", "songless", "--audio", str(out_dir), "--map", str(map_path)]
    if args.force:
        attach_args.append("--force")
    if args.db:
        attach_args += ["--db", args.db]
    if args.dsn:
        attach_args += ["--dsn", args.dsn]

    if args.attach:
        print("\nНарезаю фрагменты в базу через songs.py…")
        sys.path.insert(0, str(ROOT))
        import songs  # noqa: PLC0415

        return songs.main(attach_args)

    print("\nДальше — нарезать фрагменты в базу:\n"
          f"  {sys.executable} songs.py " + " ".join(attach_args))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())