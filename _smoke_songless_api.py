# -*- coding: utf-8 -*-
"""Сквозная проверка новых возможностей «Аниме-сонглесса» через живой сервер.

Поднимает сервер на временной SQLite-базе (рабочая база не затрагивается),
проходит соло-заход кнопкой «следующий раунд» и смотрит лидерборды:
за сегодня, отдельно соло и отдельно онлайн.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from backend.db import open_database

PORT = 8099
DB_PATH = Path(tempfile.gettempdir()) / "songless_smoke.sqlite3"
DB_PATH.unlink(missing_ok=True)


def track(index: int) -> dict:
    return {
        "track_key": f"smoke-{index}",
        "anime": f"Тестовое аниме {index}",
        "song": f"Опенинг {index}",
        "artist": "",
        "year": "",
        "audio": "https://example.com/op.webm",
        "cover": "",
        "video": "",
        "clip_start": 0,
        "clip_length": 8,
    }


seed = open_database(DB_PATH)
seed.initialize()
seed.songless_save_tracks([track(index) for index in range(12)])

proc = subprocess.Popen(
    [sys.executable, str(ROOT / "backend" / "server.py"), "--db", str(DB_PATH),
     "--port", str(PORT), "--admin-password", "smoke-admin-pass"],
    stdout=open(Path(tempfile.gettempdir()) / "songless_smoke_server.log", "w",
                encoding="utf-8"),
    stderr=subprocess.STDOUT)


def call(path: str, data=None, token: str = "") -> dict:
    url = f"http://127.0.0.1:{PORT}{path}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    request = urllib.request.Request(url, data=body,
                                     method="POST" if data is not None else "GET")
    request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


try:
    for _ in range(60):
        if proc.poll() is not None:
            log = (Path(tempfile.gettempdir()) / "songless_smoke_server.log").read_text(
                encoding="utf-8", errors="replace")
            raise AssertionError("сервер упал при запуске:\n" + log)
        try:
            status = call("/api/games/songless/status")
            break
        except (urllib.error.URLError, ConnectionError):
            time.sleep(0.25)
    else:
        raise AssertionError("сервер не поднялся")
    assert status["ready"] is True and status["playable"] == 12, status
    print("status ok:", status["playable"], "играбельных треков")

    auth = call("/api/auth/register", {"username": "smoke_user", "password": "smoke-pass-123"})
    token = auth["token"]

    state = call("/api/games/songless/solo", {"rounds": 5}, token)["state"]
    run_id = state["run"]
    assert state["phase"] == "round" and state["round"] == 1

    state = call(f"/api/games/songless/solo/{run_id}/answer",
                 {"choice": state["correct_choice"], "elapsed": 1.0}, token)["state"]
    assert state["phase"] == "reveal", state["phase"]
    state = call(f"/api/games/songless/solo/{run_id}/skip", {}, token)["state"]
    assert state["phase"] == "round" and state["round"] == 2, state["phase"]
    print("skip ok: раунд 2 начался без ожидания")

    guard = 0
    while not state["finished"] and guard < 20:
        guard += 1
        state = call(f"/api/games/songless/solo/{run_id}/answer",
                     {"choice": state["correct_choice"], "elapsed": 1.0}, token)["state"]
        state = call(f"/api/games/songless/solo/{run_id}/skip", {}, token)["state"]
    assert state["finished"] is True, state
    print("solo run finished, очки:", state["score"])

    boards = {
        "все": call("/api/games/songless/leaderboard?limit=5"),
        "соло": call("/api/games/songless/leaderboard?limit=5&mode=solo"),
        "онлайн": call("/api/games/songless/leaderboard?limit=5&mode=online"),
        "сегодня": call("/api/games/songless/leaderboard?limit=5&today=1"),
    }
    assert boards["соло"]["mode"] == "solo" and boards["сегодня"]["today"] is True
    assert boards["онлайн"]["leaderboard"] == [], "в онлайн-таблице не должно быть соло-захода"
    names = [row["username"] for row in boards["соло"]["leaderboard"]]
    today_names = [row["username"] for row in boards["сегодня"]["leaderboard"]]
    assert "smoke_user" in names, names
    assert "smoke_user" in today_names, today_names
    print("leaderboard ok: соло", names, "| сегодня", today_names)
    print("ALL OK")
finally:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()