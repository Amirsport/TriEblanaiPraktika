# -*- coding: utf-8 -*-
"""Связь с Arduino и встроенный эмулятор датчиков.

Если указан COM-порт и установлен pyserial — данные читаются с реальной платы.
Если платы нет — включается эмулятор, который каждые 2 секунды генерирует
правдоподобные показания для 12 участков и пишет их в БД.

Протокол обмена (построчный JSON, '\n' в конце):

    Arduino -> сервер:
        {"type":"hello","fw":"1.0","zones":12}
        {"type":"readings","tank":78.5,"data":[{"zone":1,"temperature":24.5,
                                               "moisture":48,"light":12400}, ...]}
        {"type":"ack","zone":3,"device":"watering","on":true}

    сервер -> Arduino:
        {"cmd":"set","zone":3,"device":"watering","on":true,"seconds":10}
"""
from __future__ import annotations

import json
import random
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import sys
from pathlib import Path

try:  # pyserial нужен только для реального железа
    import serial  # type: ignore
except Exception:  # pragma: no cover
    serial = None  # type: ignore

try:  # запуск как модуль: python -m backend.server
    from .db import DEVICES, ZONE_COUNT, Database  # type: ignore
except ImportError:  # запуск как файл: python backend/server.py
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from db import DEVICES, ZONE_COUNT, Database  # type: ignore


class ArduinoLink:
    """Читает показания (реальные или эмулированные) и пишет их в БД."""

    def __init__(
        self,
        db: Database,
        port: Optional[str] = None,
        baudrate: int = 115200,
        interval: float = 2.0,
        allow_simulator: bool = True,
    ):
        self.db = db
        self.port = port
        self.baudrate = baudrate
        self.interval = interval
        self.allow_simulator = allow_simulator

        self.source = "simulator"
        self.connected = False
        self.last_seen: Optional[float] = None
        self.firmware: Optional[str] = None
        self.stats: Dict[str, Any] = {"frames": 0, "errors": 0}

        self._serial = None
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # состояние эмулятора по каждому участку
        self._sim: Dict[int, Dict[str, float]] = {}
        self._seed_simulator()

    # ------------------------------------------------------------------ public
    def start(self) -> None:
        if self.port and serial is not None:
            try:
                self._serial = serial.Serial(self.port, self.baudrate, timeout=1)
                self.source = "arduino"
                self.connected = True
                self.db.set_state(source="arduino", port=self.port)
                self.db.add_log(f"Подключена Arduino на порту {self.port}", "info")
            except Exception as exc:  # noqa: BLE001
                self.db.add_log(f"Не удалось открыть порт {self.port}: {exc}", "warn")
                self._serial = None
        elif self.port and serial is None:
            self.db.add_log("pyserial не установлен — работает эмулятор датчиков", "warn")

        if self._serial is None and not self.allow_simulator:
            raise RuntimeError("Нет ни Arduino, ни разрешения на эмулятор")

        if self._serial is None:
            self.source = "simulator"
            self.db.set_state(source="simulator", port=None)
            self.db.add_log("Датчики недоступны — включён эмулятор 12 участков", "info")

        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="arduino-link", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
        if self._serial:
            try:
                self._serial.close()
            except Exception:  # noqa: BLE001
                pass

    def send_command(self, zone_id: int, device: str, on: bool, seconds: Optional[float] = None) -> bool:
        """Отправляет команду на плату. Возвращает True, если ушла в порт."""
        payload: Dict[str, Any] = {"cmd": "set", "zone": int(zone_id), "device": device, "on": bool(on)}
        if seconds:
            payload["seconds"] = float(seconds)

        if self._serial:
            try:
                with self._lock:
                    self._serial.write((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
                self.last_seen = time.time()
                return True
            except Exception as exc:  # noqa: BLE001
                self.db.add_log(f"Ошибка отправки команды на Arduino: {exc}", "warn")
        return False

    def status(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "connected": self.connected and self._serial is not None,
            "port": self.port,
            "firmware": self.firmware,
            "last_seen": self.last_seen,
            "frames": self.stats["frames"],
            "errors": self.stats["errors"],
        }

    # ------------------------------------------------------------------ worker
    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                if self._serial is not None:
                    self._read_serial()
                else:
                    self._simulate()
            except Exception as exc:  # noqa: BLE001
                self.stats["errors"] += 1
                self.db.add_log(f"Сбой канала датчиков: {exc}", "err")
            self._stop.wait(self.interval)

    def _read_serial(self) -> None:
        assert self._serial is not None
        line = self._serial.readline()
        if not line:
            return
        text = line.decode("utf-8", errors="ignore").strip()
        if not text:
            return
        self.last_seen = time.time()
        try:
            message = json.loads(text)
        except json.JSONDecodeError:
            self.stats["errors"] += 1
            return
        self.stats["frames"] += 1
        self._handle_message(message)

    def _handle_message(self, message: Dict[str, Any]) -> None:
        kind = message.get("type") or ("readings" if "data" in message else None)

        if kind == "hello":
            self.firmware = message.get("fw")
            self.connected = True
            self.db.add_log(f"Arduino на связи (прошивка {self.firmware})", "info")
            return

        if kind == "ack":
            return

        data: List[Dict[str, Any]]
        if "data" in message and isinstance(message["data"], list):
            data = message["data"]
        else:  # одиночное показание
            data = [message]

        if "tank" in message and message["tank"] is not None:
            self.db.set_state(tank=float(message["tank"]))

        for item in data:
            try:
                zone_id = int(item["zone"])
            except (KeyError, TypeError, ValueError):
                continue
            if not 1 <= zone_id <= ZONE_COUNT:
                continue
            self.db.add_reading(
                zone_id,
                _opt_float(item.get("temperature")),
                _opt_float(item.get("moisture")),
                _opt_float(item.get("light")),
            )

    # --------------------------------------------------------------- simulator
    def _seed_simulator(self) -> None:
        random.seed(2026)
        for zone in range(1, ZONE_COUNT + 1):
            # участки по-разному освещены и сохнут (градиент от окна к центру)
            offset = (zone - 6.5) / 6.5  # -1..1
            self._sim[zone] = {
                "temperature": 24.0 + offset * 1.2,
                "moisture": 52.0 - offset * 6.0,
                "light": 12000.0 + offset * 2500.0,
            }

    def _simulate(self) -> None:
        row = self.db.state()
        devices = self.db.devices()
        tank = float(row.get("tank") or 0.0)
        window_open = float(row.get("window_open") or 0.0)

        hour = datetime.now().hour + datetime.now().minute / 60.0
        daylight = max(0.0, min(1.0, _sin_daylight(hour)))
        any_watering = any(devices[z]["watering"] for z in range(1, ZONE_COUNT + 1))
        lighting_global = any(devices[z]["lighting"] for z in range(1, ZONE_COUNT + 1))
        ventilation_global = any(devices[z]["ventilation"] for z in range(1, ZONE_COUNT + 1))

        lamp_boost = 9000.0 if lighting_global else 0.0
        base_light = daylight * 36000.0 + lamp_boost

        for zone in range(1, ZONE_COUNT + 1):
            sim = self._sim[zone]
            dev = devices[zone]

            sim["light"] = _clamp(base_light + random.uniform(-800, 800), 0, 45000)

            comfort = 24.0 - (window_open / 100.0) * 4.0 - random.uniform(0, 0.6)
            sim["temperature"] = _clamp(
                sim["temperature"] + (comfort - sim["temperature"]) * 0.15 + random.uniform(-0.25, 0.25),
                12, 42,
            )

            delta = -0.30 + random.uniform(-0.15, 0.15)
            if dev["watering"]:
                delta += 1.8
            if ventilation_global:
                delta -= 0.3
            sim["moisture"] = _clamp(sim["moisture"] + delta, 5, 100)

            self.db.add_reading(
                zone,
                round(sim["temperature"], 2),
                round(sim["moisture"], 2),
                round(sim["light"], 1),
            )

        if any_watering and tank > 0:
            tank = _clamp(tank - 0.5, 0, 100)
            self.db.set_state(tank=round(tank, 2))

        self.stats["frames"] += 1
        self.last_seen = time.time()


# ---------------------------------------------------------------------- utils
def _opt_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _sin_daylight(hour: float) -> float:
    import math

    return math.sin(((hour - 6.0) / 12.0) * math.pi)
