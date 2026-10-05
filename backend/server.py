# -*- coding: utf-8 -*-
"""Сервер «Умной AI-Теплицы»: REST API + автоматика + раздача PWA-фронтенда.

Запуск:
    python backend/server.py                          # эмулятор датчиков, порт 8000
    python backend/server.py --serial COM3            # реальная Arduino
    python backend/server.py --port 8000 --db data/greenhouse.sqlite3

API (JSON):
    GET  /api/health                     состояние сервиса
    GET  /api/state                      полное состояние (12 участков + агрегаты)
    GET  /api/zones                      список участков
    GET  /api/zones/<id>                 один участок
    GET  /api/zones/<id>/history?limit=  история показаний участка
    GET  /api/history?zone_id=&limit=    история (все или один участок)
    GET  /api/logs?limit=&level=         журнал событий
    GET  /api/settings                   глобальные настройки
    GET  /api/arduino                    статус канала с платой
    POST /api/devices                    {"zone_id":1,"device":"watering","on":true,"seconds":10}
    POST /api/settings                   {"moisture_target":55,...}
    POST /api/mode                       {"mode":"auto|eco|boost|manual"}
    POST /api/logs/clear                 очистить журнал
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import re
import sys
import threading
import time
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse

try:  # запуск как модуль: python -m backend.server
    from .db import DEFAULT_SETTINGS, DEVICES, ZONE_COUNT, Database
    from .arduino import ArduinoLink
except ImportError:  # запуск как файл: python backend/server.py
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from db import DEFAULT_SETTINGS, DEVICES, ZONE_COUNT, Database  # type: ignore
    from arduino import ArduinoLink  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
FRONT = ROOT / "front"
DEFAULT_DB = ROOT / "data" / "greenhouse.sqlite3"

MODE_PRESETS: Dict[str, Optional[Dict[str, Any]]] = {
    "auto": {"moisture_target": 55, "moisture_threshold": 35, "temperature_threshold": 30, "light_threshold": 8000},
    "eco": {"moisture_target": 45, "moisture_threshold": 28, "temperature_threshold": 32, "light_threshold": 5000},
    "boost": {"moisture_target": 65, "moisture_threshold": 45, "temperature_threshold": 27, "light_threshold": 12000},
    "manual": None,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Application:
    """Связывает БД, канал Arduino и правила автоматики."""

    def __init__(self, db: Database, arduino: ArduinoLink):
        self.db = db
        self.arduino = arduino
        self._timers: Dict[Tuple[int, str], float] = {}
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._zone_names = {zone["id"]: zone["name"] for zone in db.zones()}

    # ---------------------------------------------------------------- lifecycle
    def start(self) -> None:
        self.arduino.start()
        self._stop.clear()
        self._thread = threading.Thread(target=self._automation_loop, name="automation", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
        self.arduino.stop()

    # ------------------------------------------------------------------- state
    def state_payload(self) -> Dict[str, Any]:
        state_row = self.db.state()
        settings = self.db.settings()
        readings = self.db.latest_readings()
        devices = self.db.devices()

        zones = []
        temps: list = []
        moistures: list = []
        lights: list = []

        for zone in self.db.zones():
            zone_id = zone["id"]
            reading = readings.get(zone_id, {})
            zone_devices = devices.get(zone_id, {d: False for d in DEVICES})

            if reading.get("temperature") is not None:
                temps.append(reading["temperature"])
            if reading.get("moisture") is not None:
                moistures.append(reading["moisture"])
            if reading.get("light") is not None:
                lights.append(reading["light"])

            zones.append({
                "id": zone_id,
                "name": zone["name"],
                "sensors": {
                    "temperature": reading.get("temperature"),
                    "moisture": reading.get("moisture"),
                    "light": reading.get("light"),
                },
                "devices": {
                    device: {"on": bool(zone_devices.get(device)), "remaining": self.remaining(zone_id, device)}
                    for device in DEVICES
                },
                "target": settings["moisture_target"],
                "status": self._zone_status(reading, settings),
                "updated_at": reading.get("recorded_at"),
            })

        def avg(values: list) -> Optional[float]:
            return round(sum(values) / len(values), 2) if values else None

        return {
            "online": True,
            "server_time": _now_iso(),
            "mode": settings["mode"],
            "tank": state_row.get("tank"),
            "window_open": state_row.get("window_open"),
            "source": state_row.get("source"),
            "arduino": self.arduino.status(),
            "settings": settings,
            "sensors": {
                "temperature": avg(temps),
                "moisture": avg(moistures),
                "light": avg(lights),
            },
            "devices": {
                device: {"on": any(devices[z].get(device) for z in range(1, ZONE_COUNT + 1))}
                for device in DEVICES
            },
            "zones": zones,
        }

    def zone_payload(self, zone_id: int) -> Optional[Dict[str, Any]]:
        payload = self.state_payload()
        for zone in payload["zones"]:
            if zone["id"] == zone_id:
                zone["history"] = self.db.history(zone_id=zone_id, limit=60)
                return zone
        return None

    def _zone_status(self, reading: Dict[str, Any], settings: Dict[str, Any]) -> str:
        moisture = reading.get("moisture")
        temperature = reading.get("temperature")
        light = reading.get("light")
        if moisture is not None and moisture < settings["moisture_threshold"]:
            return "dry"
        if temperature is not None and temperature > settings["temperature_threshold"]:
            return "hot"
        if light is not None and light < settings["light_threshold"]:
            return "dark"
        return "ok"

    # ----------------------------------------------------------------- devices
    def remaining(self, zone_id: int, device: str) -> float:
        end = self._timers.get((zone_id, device))
        if not end:
            return 0.0
        return max(0.0, round(end - time.time(), 1))

    def set_device(
        self,
        zone_id: int,
        device: str,
        on: bool,
        seconds: Optional[float] = None,
        reason: str = "",
        log: bool = True,
    ) -> None:
        if device not in DEVICES:
            raise ValueError(f"Неизвестный исполнитель: {device}")
        if not 1 <= zone_id <= ZONE_COUNT:
            raise ValueError(f"Неизвестный участок: {zone_id}")

        self.db.set_device(zone_id, device, on)

        if on and seconds:
            self._timers[(zone_id, device)] = time.time() + float(seconds)
        elif not on:
            self._timers.pop((zone_id, device), None)

        self.arduino.send_command(zone_id, device, on, seconds)

        if not log:
            return
        name = self._zone_names.get(zone_id, f"Участок {zone_id}")
        labels = {"watering": "Полив", "ventilation": "Проветривание", "lighting": "Досветка"}
        suffix = f" на {int(seconds)} с" if (on and seconds) else ""
        tail = f" ({reason})" if reason else ""
        self.db.add_log(f"{name}: {labels[device]} {'запущен' if on else 'остановлен'}{suffix}{tail}", "info", zone_id)

    def set_device_all(
        self,
        device: str,
        on: bool,
        seconds: Optional[float] = None,
        reason: str = "",
    ) -> None:
        """Команда сразу всем 12 участкам (zone_id = 0 в API)."""
        for zone_id in range(1, ZONE_COUNT + 1):
            self.set_device(zone_id, device, on, seconds, reason=reason, log=False)
        labels = {"watering": "Полив", "ventilation": "Проветривание", "lighting": "Досветка"}
        scope = "включён" if on else "выключен"
        suffix = f" на {int(seconds)} с" if (on and seconds) else ""
        tail = f" ({reason})" if reason else ""
        self.db.add_log(f"Все 12 участков: {labels[device]} {scope}{suffix}{tail}", "info")

    # ---------------------------------------------------------------- settings
    def update_settings(self, values: Dict[str, Any]) -> Dict[str, Any]:
        return self.db.update_settings(values)

    def apply_mode(self, mode: str) -> Dict[str, Any]:
        if mode not in MODE_PRESETS:
            raise ValueError(f"Неизвестный режим: {mode}")
        values: Dict[str, Any] = {"mode": mode}
        preset = MODE_PRESETS[mode]
        if preset:
            values.update(preset)
        return self.db.update_settings(values)

    # --------------------------------------------------------------- automatic
    def _automation_loop(self) -> None:
        while not self._stop.wait(2.0):
            try:
                self._automation_tick()
            except Exception as exc:  # noqa: BLE001
                self.db.add_log(f"Ошибка автоматики: {exc}", "err")

    def _automation_tick(self) -> None:
        self._expire_timers()

        settings = self.db.settings()
        if settings["mode"] == "manual":
            return

        readings = self.db.latest_readings()
        devices = self.db.devices()
        tank = float(self.db.state().get("tank") or 0.0)

        for zone_id in range(1, ZONE_COUNT + 1):
            reading = readings.get(zone_id, {})
            device_row = devices.get(zone_id, {})
            name = self._zone_names.get(zone_id, f"Участок {zone_id}")

            moisture = reading.get("moisture")
            temperature = reading.get("temperature")
            light = reading.get("light")

            if (settings["auto_watering"] and moisture is not None
                    and moisture < settings["moisture_threshold"] and not device_row.get("watering")):
                if tank > 5:
                    if not self.db.has_recent_log(f"{name}: автополив", 120):
                        self.db.add_log(f"{name}: автополив", "warn", zone_id)
                        self.set_device(zone_id, "watering", True, settings["watering_duration"],
                                        reason="низкая влажность")
                elif not self.db.has_recent_log("Бак пуст — полив остановлен", 300):
                    self.db.add_log("Бак пуст — полив остановлен", "warn")

            if (settings["auto_ventilation"] and temperature is not None
                    and temperature > settings["temperature_threshold"] and not device_row.get("ventilation")):
                if not self.db.has_recent_log(f"{name}: автопроветривание", 120):
                    self.db.add_log(f"{name}: автопроветривание", "warn", zone_id)
                    self.set_device(zone_id, "ventilation", True, settings["ventilation_duration"],
                                    reason="перегрев")

            if settings["auto_lighting"] and light is not None:
                should_glow = light < settings["light_threshold"]
                if should_glow != bool(device_row.get("lighting")):
                    self.set_device(zone_id, "lighting", should_glow, reason="фотопериод")

    def _expire_timers(self) -> None:
        now = time.time()
        for (zone_id, device), end in list(self._timers.items()):
            if end and now >= end:
                self._timers.pop((zone_id, device), None)
                self.set_device(zone_id, device, False, reason="таймер завершён")


# ============================================================================
# HTTP-слой
# ============================================================================
class Handler(BaseHTTPRequestHandler):
    server_version = "GreenhouseServer/2.0"
    protocol_version = "HTTP/1.1"

    @property
    def app(self) -> Application:
        return self.server.app  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args: Any) -> None:
        if self.path.startswith("/api/"):
            sys.stderr.write("  %s\n" % (fmt % args))

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _error(self, message: str, status: int = 400) -> None:
        self._json({"error": message, "status": status}, status)

    def _body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _query(self) -> Dict[str, str]:
        params = parse_qs(urlparse(self.path).query)
        return {key: values[0] for key, values in params.items() if values}

    # ------------------------------------------------------------- verbs
    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path.startswith("/api/"):
            self._handle_api("GET", path)
        else:
            self._serve_static(path)

    def do_HEAD(self) -> None:  # noqa: N802
        self.do_GET()

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path.startswith("/api/"):
            self._handle_api("POST", path)
        else:
            self._error("Только API принимает POST", 405)

    # ------------------------------------------------------------- API routes
    def _handle_api(self, method: str, path: str) -> None:
        app = self.app
        query = self._query()

        try:
            if method == "GET" and path == "/api/health":
                return self._json({"status": "ok", "time": _now_iso(), "zones": ZONE_COUNT,
                                   "arduino": app.arduino.status()})

            if method == "GET" and path == "/api/state":
                return self._json(app.state_payload())

            if method == "GET" and path == "/api/zones":
                return self._json({"zones": app.state_payload()["zones"]})

            match = re.fullmatch(r"/api/zones/(\d+)/history", path)
            if method == "GET" and match:
                zone_id = int(match.group(1))
                return self._json({"zone_id": zone_id, "history": app.db.history(zone_id, int(query.get("limit", 60)))})

            match = re.fullmatch(r"/api/zones/(\d+)", path)
            if method == "GET" and match:
                zone = app.zone_payload(int(match.group(1)))
                return self._json(zone) if zone else self._error("Участок не найден", 404)

            if method == "GET" and path == "/api/history":
                zone_id = int(query["zone_id"]) if query.get("zone_id") else None
                return self._json({"history": app.db.history(zone_id, int(query.get("limit", 60)))})

            if method == "GET" and path == "/api/logs":
                return self._json({"logs": app.db.logs(int(query.get("limit", 100)), query.get("level"))})

            if method == "GET" and path == "/api/settings":
                return self._json(app.db.settings())

            if method == "GET" and path == "/api/arduino":
                return self._json(app.arduino.status())

            if method == "POST" and path == "/api/devices":
                data = self._body()
                zone_id = int(data.get("zone_id") or 0)
                device = str(data.get("device") or "")
                on = bool(data.get("on"))
                seconds = float(data["seconds"]) if data.get("seconds") else None
                if not device:
                    return self._error("Не указан исполнитель (device)")
                if zone_id == 0:
                    app.set_device_all(device, on, seconds, reason="команда оператора")
                    return self._json({"ok": True, "scope": "all"})
                app.set_device(zone_id, device, on, seconds, reason="команда оператора")
                return self._json({"ok": True, "zone": app.zone_payload(zone_id)})

            if method == "POST" and path == "/api/settings":
                return self._json({"settings": app.update_settings(self._body())})

            if method == "POST" and path == "/api/mode":
                mode = str(self._body().get("mode") or "")
                app.apply_mode(mode)
                app.db.add_log(f"Режим переключён: {mode}", "info")
                return self._json({"ok": True, "settings": app.db.settings()})

            if method == "POST" and path == "/api/logs/clear":
                app.db.clear_logs()
                return self._json({"ok": True})

            return self._error(f"Не найдено: {method} {path}", 404)
        except ValueError as exc:
            return self._error(str(exc), 400)
        except Exception as exc:  # noqa: BLE001
            return self._error(f"Внутренняя ошибка: {exc}", 500)

    # ------------------------------------------------------------- static files
    def _serve_static(self, path: str) -> None:
        if path in ("", "/"):
            path = "/index.html"
        target = (FRONT / path.lstrip("/")).resolve()

        try:
            target.relative_to(FRONT.resolve())
        except ValueError:
            return self._error("Недопустимый путь", 403)

        if target.is_dir():
            target = target / "index.html"
        if not target.exists() or not target.is_file():
            return self._error("Файл не найден", 404)

        mime, _ = mimetypes.guess_type(str(target))
        if target.name.endswith(".webmanifest"):
            mime = "application/manifest+json"
        mime = mime or "application/octet-stream"
        if mime.startswith(("text/", "application/javascript", "application/json")) or target.suffix in (".js", ".css"):
            mime += "; charset=utf-8"
        body = target.read_bytes()

        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self._cors()
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)


def create_server(host: str, port: int, database: Path, serial_port: Optional[str],
                  baud: int, simulator: bool) -> ThreadingHTTPServer:
    db = Database(database)
    db.initialize()
    link = ArduinoLink(db, port=serial_port, baudrate=baud, allow_simulator=simulator)
    app = Application(db, link)

    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    server.app = app  # type: ignore[attr-defined]
    app.start()
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Сервер умной теплицы (12 участков)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--serial", dest="serial_port", default=None, help="COM-порт Arduino, например COM3")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--no-simulator", action="store_true", help="запретить эмулятор (нужна реальная плата)")
    parser.add_argument("--open", action="store_true", help="открыть панель в браузере")
    args = parser.parse_args()

    server = create_server(args.host, args.port, args.db,
                           args.serial_port, args.baud, not args.no_simulator)
    url = f"http://{args.host}:{server.server_port}/"
    print(f"Теплица: {url}")
    print(f"Участков: {ZONE_COUNT}, БД: {args.db}")
    print("Датчики: " + (f"Arduino {args.serial_port}" if args.serial_port else "эмулятор (Arduino не подключена)"))
    if args.open:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановка...")
    finally:
        server.app.stop()  # type: ignore[attr-defined]
        server.server_close()


if __name__ == "__main__":
    main()
