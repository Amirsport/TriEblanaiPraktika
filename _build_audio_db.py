# -*- coding: utf-8 -*-
"""Готовит 8-секундные MP3-фрагменты всех треков сонглесса.

Скачивает только начало записи (HTTP Range), режет ffmpeg и складывает
результат в _audio_db вместе с manifest.json для загрузки в audio_clips.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "backend" / "songless_catalog.json"
OUT = ROOT / "_audio_db"
COOKIES = ROOT / "_at_cookies.txt"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
REFERER = "https://animethemes.moe/"
CURL = "curl.exe" if os.name == "nt" else "curl"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def warm_cookies() -> None:
    subprocess.run(
        [CURL, "--ssl-no-revoke", "-c", str(COOKIES), "-b", str(COOKIES),
         "-e", REFERER, "-A", UA, "-sS", "-m", "20", "-o", os.devnull,
         REFERER],
        capture_output=True,
    )


_TLS = threading.local()


def thread_cookies() -> Path:
    path = getattr(_TLS, "cookies", None)
    if path is None:
        path = COOKIES.with_name(f"_at_cookies_{threading.get_ident()}.txt")
        if not path.exists():
            shutil.copyfile(COOKIES, path)
        _TLS.cookies = path
    return path


def cut_one(track: dict, byte_range: int) -> dict:
    key = str(track.get("track_key") or track.get("anime") or "")
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    target = OUT / f"{digest}.mp3"
    temp = OUT / f"{digest}.part.webm"
    if target.exists() and target.stat().st_size > 5000:
        return {"track_key": key, "file": target.name,
                "duration_ms": int(float(track.get("clip_length") or 8) * 1000),
                "source": "v.animethemes.moe"}
    url = str(track.get("audio") or track.get("video") or "")
    if not url:
        return {"track_key": key, "error": "нет ссылки"}
    download = None
    cookies = thread_cookies()
    for attempt in range(3):
        download = subprocess.run(
            [CURL, "--ssl-no-revoke", "-c", str(cookies), "-b", str(cookies),
             "-e", REFERER, "-A", UA, "-r", f"0-{byte_range}", "-sS", "-m", "40",
             "-o", str(temp), url],
            capture_output=True,
        )
        if (download.returncode == 0 and temp.exists()
                and temp.stat().st_size >= 50_000):
            break
        time.sleep(2 + attempt * 2)
    if (download is None or download.returncode != 0
            or not temp.exists() or temp.stat().st_size < 50_000):
        temp.unlink(missing_ok=True)
        return {"track_key": key, "error": f"download {download.returncode if download else '?'}"}
    length = float(track.get("clip_length") or 8)
    start = float(track.get("clip_start") or 0)
    cut = subprocess.run(
        [FFMPEG, "-nostdin", "-hide_banner", "-loglevel", "error",
         "-ss", f"{start:.3f}", "-i", str(temp), "-vn", "-t", f"{length:.3f}",
         "-acodec", "libmp3lame", "-b:a", "128k", "-f", "mp3", "-y", str(target)],
        capture_output=True,
    )
    temp.unlink(missing_ok=True)
    if cut.returncode != 0 or not target.exists() or target.stat().st_size < 5000:
        target.unlink(missing_ok=True)
        return {"track_key": key, "error": "ffmpeg"}
    return {"track_key": key, "file": target.name, "duration_ms": int(length * 1000),
            "source": "v.animethemes.moe"}


def main() -> int:
    import sys

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description="MP3-фрагменты в audio_clips")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--range", type=int, default=4_000_000,
                        help="сколько первых байт скачивать")
    args = parser.parse_args()

    tracks = json.loads(CATALOG.read_text(encoding="utf-8"))
    OUT.mkdir(exist_ok=True)
    warm_cookies()
    results = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(cut_one, track, args.range) for track in tracks]
        for index, future in enumerate(as_completed(futures), start=1):
            item = future.result()
            results.append(item)
            if "error" in item:
                print(f"{index}/{len(tracks)} FAIL {item['track_key']}: {item['error']}", flush=True)
            else:
                print(f"{index}/{len(tracks)} OK {item['track_key']}", flush=True)
    good = [item for item in results if "error" not in item]
    (OUT / "manifest.json").write_text(
        json.dumps(good, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"готово: {len(good)} из {len(tracks)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())