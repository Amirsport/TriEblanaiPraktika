# -*- coding: utf-8 -*-
"""Замеры тепличного контура: API, телеметрия и запись в БД.

Поднимает backend/server.py на свободном порту с временной базой (боевая
data/greenhouse.sqlite3 не затрагивается), снимает задержки API, полный цикл
команды, реакцию автоматики и прирост базы. Результат — JSON в stdout.

    python tools/bench_greenhouse.py
    python tools/bench_greenhouse.py --duration 60 --out metrics.json
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent


def call(base: str, path: str, payload=None, timeout: float = 10.0):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(base + path, data=data, headers=headers)
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
    return json.loads(body.decode("utf-8")), (time.perf_counter() - started) * 1000.0


def latency(values):
    values = sorted(values)
    n = len(values)

    def percentile(p):
        index = min(n - 1, max(0, int(round(p / 100.0 * (n - 1)))))
        return values[index]

    return {
        "n": n,
        "mean_ms": round(statistics.fmean(values), 2),
        "median_ms": round(statistics.median(values), 2),
        "p95_ms": round(percentile(95), 2),
        "max_ms": round(values[-1], 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Замеры тепличного контура")
    parser.add_argument("--duration", type=float, default=120.0,
                        help="сколько секунд держать сервер под телеметрией")
    parser.add_argument("--port", type=int, default=8077)
    parser.add_argument("--out", type=pathlib.Path, default=None)
    args = parser.parse_args()

    base = f"http://127.0.0.1:{args.port}"
    workdir = pathlib.Path(tempfile.mkdtemp(prefix="greenhouse-bench-"))
    db_path = workdir / "bench.sqlite3"
    log_path = workdir / "server.log"

    log = log_path.open("w", encoding="utf-8")
    server = subprocess.Popen(
        [sys.executable, str(ROOT / "backend" / "server.py"), "--db", str(db_path),
         "--host", "127.0.0.1", "--port", str(args.port),
         "--admin-password", "bench-only"],
        cwd=str(ROOT), stdout=log, stderr=subprocess.STDOUT,
    )
    started = time.perf_counter()
    result = {}
    try:
        for _ in range(100):
            try:
                call(base, "/api/health", timeout=2)
                break
            except Exception:
                time.sleep(0.1)
        result["startup_s"] = round(time.perf_counter() - started, 2)

        for _ in range(10):
            call(base, "/api/state")

        result["state_latency"] = latency([call(base, "/api/state")[1] for _ in range(300)])
        result["history_latency"] = latency(
            [call(base, "/api/zones/1/history?limit=60")[1] for _ in range(200)]
        )

        call(base, "/api/mode", {"mode": "manual"})
        post, full_cycle = [], []
        for i in range(20):
            want = i % 2 == 0
            _, post_ms = call(base, "/api/devices", {"zone_id": 1, "device": "watering",
                                                     "on": want, "seconds": 5})
            post.append(post_ms)
            probe = time.perf_counter()
            while (time.perf_counter() - probe) * 1000 < 3000:
                state, _ = call(base, "/api/state")
                if bool(state["zones"][0]["devices"]["watering"]["on"]) == want:
                    break
                time.sleep(0.02)
            full_cycle.append(post_ms + (time.perf_counter() - probe) * 1000.0)
        call(base, "/api/devices", {"zone_id": 1, "device": "watering", "on": False})
        result["command_post_latency"] = latency(post)
        result["command_cycle_latency"] = latency(full_cycle)

        call(base, "/api/devices", {"zone_id": 0, "device": "watering", "on": False})
        call(base, "/api/mode", {"mode": "auto"})
        call(base, "/api/settings", {"moisture_threshold": 99, "auto_watering": 1})
        probe = time.perf_counter()
        first_on = None
        all_on = None
        state = {"zones": []}
        while (time.perf_counter() - probe) < 12:
            state, _ = call(base, "/api/state")
            running = [zone for zone in state["zones"] if zone["devices"]["watering"]["on"]]
            if running and first_on is None:
                first_on = round(time.perf_counter() - probe, 2)
            if len(running) == len(state["zones"]) and state["zones"]:
                all_on = round(time.perf_counter() - probe, 2)
                break
            time.sleep(0.05)
        result["automation_first_on_s"] = first_on
        result["automation_all_on_s"] = all_on
        result["automation_zones_on"] = sum(
            1 for zone in state["zones"] if zone["devices"]["watering"]["on"]
        )
        call(base, "/api/mode", {"mode": "manual"})
        call(base, "/api/devices", {"zone_id": 0, "device": "watering", "on": False})

        while time.perf_counter() - started < args.duration:
            time.sleep(1)

        arduino, _ = call(base, "/api/arduino")
        result["arduino"] = arduino
        result["uptime_s"] = round(time.perf_counter() - started, 1)
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
        log.close()

    con = sqlite3.connect(str(db_path))
    try:
        rows = con.execute("select count(*) from readings").fetchone()[0]
        per_zone = con.execute(
            "select min(c), max(c) from (select zone_id, count(*) c from readings group by zone_id)"
        ).fetchone()
        result["db"] = {
            "size_bytes": os.path.getsize(db_path),
            "readings": rows,
            "zones": con.execute("select count(distinct zone_id) from readings").fetchone()[0],
            "min_ts": con.execute("select min(recorded_at) from readings").fetchone()[0],
            "max_ts": con.execute("select max(recorded_at) from readings").fetchone()[0],
            "per_zone_min_max": list(per_zone),
        }
        result["db"]["readings_per_s"] = round(rows / max(0.1, result["uptime_s"]), 2)
        span_s = max(1.0, result["uptime_s"] - 2.0)
        result["db"]["sampling_period_s"] = round(span_s / max(1, (per_zone[1] or 1)), 2)
    finally:
        con.close()

    shutil.rmtree(workdir, ignore_errors=True)

    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(payload, encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
