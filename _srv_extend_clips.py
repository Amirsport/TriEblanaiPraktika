#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Перерезает фрагменты «Аниме-сонглесса» на всю длину раунда.

Раунд длится ANSWER_SECONDS = 20 с, а фрагменты были по 8. Скрипт заново качает
начало записи с animethemes (Range + cookie-сессия), режет TARGET секунд и
кладёт новый MP3 в audio_clips, выставляя clip_length. Уже перерезанные треки
пропускаются, поэтому прогон можно прерывать и продолжать.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, "/opt/greenhouse")

from backend.db import AUDIO_IN_DB, open_database  # noqa: E402

OUT = Path("/var/tmp/clips_ext")
LOCK = Path("/var/tmp/clips_ext.lock")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")
REFERER = "https://animethemes.moe/"
CURL = shutil.which("curl") or "curl"
FFMPEG = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"
JAR = Path("/var/tmp/clips_jar.txt")
PAUSE = 2.5            # минимальный интервал между запросами (общий на все потоки)
_throttle = threading.Lock()
_last_request = 0.0
TARGET = 20.5          # раунд 20 с + небольшой запас


def dsn() -> str:
    env = Path("/etc/greenhouse.env").read_text(encoding="utf-8")
    match = re.search(r"^GREENHOUSE_DSN=(.+)$", env, re.M)
    if not match:
        raise SystemExit("нет GREENHOUSE_DSN")
    return match.group(1).strip().strip('"').strip("'")


def run(cmd: list, timeout: float):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                              timeout=timeout)
    except subprocess.TimeoutExpired:
        return None


def warm() -> None:
    JAR.unlink(missing_ok=True)
    run([CURL, "-s", "-c", str(JAR), "-b", str(JAR), "-e", REFERER, "-A", UA,
         "-m", "25", "-o", os.devnull, REFERER], timeout=35)


def fetch(url: str, target: Path, byte_range: int):
    global _last_request
    with _throttle:
        wait = PAUSE - (time.time() - _last_request)
        if wait > 0:
            time.sleep(wait)
        _last_request = time.time()
    started = time.time()
    curl = run([CURL, "-s", "-c", str(JAR), "-b", str(JAR), "-e", REFERER, "-A", UA,
                "-r", f"0-{byte_range}", "-m", "90", "-o", str(target),
                "-w", "%{http_code}", url], timeout=110)
    elapsed = time.time() - started
    if curl is None:
        return -1, elapsed
    code = (curl.stdout or "").strip()[-3:]
    return (int(code) if code.isdigit() else 0), elapsed


def duration(path: Path) -> float:
    probe = run([FFMPEG, "-nostdin", "-hide_banner", "-i", str(path)], timeout=20)
    if probe is None:
        return 0.0
    match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", probe.stderr)
    if not match:
        return 0.0
    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def build(track: dict):
    """Готовит MP3 нужной длины; возвращает (путь, заметка) или (None, причина)."""
    key = str(track["track_key"])
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    target = OUT / f"{digest}.mp3"
    temp = OUT / f"{digest}.part.webm"
    url = str(track.get("video") or track.get("audio") or "")
    start = float(track.get("clip_start") or 0)
    if not url:
        return None, "нет ссылки"

    if target.exists() and duration(target) >= TARGET - 0.4:
        return target, "готово раньше"

    byte_range = 12_000_000
    deadline = time.time() + 240
    for attempt in range(10):
        if time.time() > deadline:
            break
        code, _elapsed = fetch(url, temp, byte_range)
        size = temp.stat().st_size if temp.exists() else 0
        if code in (200, 206) and size >= 100_000:
            cut = run([FFMPEG, "-nostdin", "-hide_banner", "-loglevel", "error",
                       "-ss", f"{start:.3f}", "-i", str(temp), "-vn",
                       "-t", f"{TARGET:.3f}", "-acodec", "libmp3lame", "-b:a", "128k",
                       "-f", "mp3", "-y", str(target)], timeout=120)
            temp.unlink(missing_ok=True)
            if cut is not None and cut.returncode == 0 and target.exists():
                got = duration(target)
                if got >= TARGET - 0.4:
                    return target, "ok"
                target.unlink(missing_ok=True)
                byte_range = min(byte_range * 2, 48_000_000)
                continue
            target.unlink(missing_ok=True)
            time.sleep(1)
            continue
        temp.unlink(missing_ok=True)
        time.sleep(1.5)
        if attempt % 4 == 3:
            warm()
    return None, "не удалось"


def pending_tracks(db):
    """Треки, у которых запись ещё петля (или короче раунда)."""
    result = []
    for track in db.songless_tracks():
        clip = db.audio_clip_get("songless", str(track["track_key"]))
        short = float(track.get("clip_length") or 0) < TARGET - 0.1
        looped = str((clip or {}).get("source") or "") == "loop"
        if clip is None or short or looped:
            result.append(track)
    return result


def main() -> int:
    import signal

    parser = argparse.ArgumentParser(description="фрагменты на всю длину раунда")
    parser.add_argument("--once", action="store_true", help="один проход и выход")
    args = parser.parse_args()

    OUT.mkdir(exist_ok=True)
    if LOCK.exists() and time.time() - LOCK.stat().st_mtime >= 7200:
        LOCK.unlink(missing_ok=True)
    try:
        handle = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise SystemExit("уже выполняется другой прогон")
    os.write(handle, str(os.getpid()).encode("ascii"))
    os.close(handle)

    def stop(*_):
        LOCK.unlink(missing_ok=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    try:
        warm()
        while True:
            db = open_database(None, dsn())
            pending = pending_tracks(db)
            print(f"[{time.strftime('%H:%M:%S')}] осталось перерезать: {len(pending)}",
                  flush=True)
            if not pending:
                if args.once:
                    return 0
                print("все записи полноценные — пауза 30 минут", flush=True)
                time.sleep(1800)
                continue

            failures = 0
            for track in pending:
                path, note = build(track)
                if path is None:
                    failures += 1
                    print(f"FAIL {track['anime']}: {note}", flush=True)
                    if failures >= 5:
                        print("CDN ограничивает — пауза 10 минут", flush=True)
                        time.sleep(600)
                        failures = 0
                    continue
                failures = 0
                data = path.read_bytes()
                path.unlink(missing_ok=True)
                db.audio_clip_save("songless", str(track["track_key"]), data,
                                   "audio/mpeg", int(TARGET * 1000), "v.animethemes.moe")
                db.songless_set_audio(str(track["anime"]), AUDIO_IN_DB, clip_start=0,
                                      clip_length=TARGET, track_key=str(track["track_key"]))
                print(f"OK {track['anime']} ({len(data) // 1024} КБ)", flush=True)
                LOCK.touch()
                if args.once:
                    return 0
            time.sleep(30)
    finally:
        LOCK.unlink(missing_ok=True)
        for leftover in OUT.glob("*.part.webm"):
            leftover.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())