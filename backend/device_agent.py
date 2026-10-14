# -*- coding: utf-8 -*-
"""Домашний агент: держит COM-порт с Arduino и связывает плату с сервером на VPS.

Зачем: сервер теплицы можно поставить на VPS, тогда панель и игры работают
круглосуточно и без домашнего ПК. Но плата подключена дома, поэтому:

    Arduino ──(COM-порт)── device_agent.py ──(HTTPS)── сервер на VPS

Агент раз в пару секунд отправляет показания (POST /api/device/sync) и в ответ
получает команды, которые положила панель или автоматика сервера. Команды
применяются к плате, а результат подтверждается (POST /api/device/ack).
Если плата не подключена, агент работает эмулятором — как и сервер без платы.

Запуск (на домашнем ПК, где воткнута Arduino):

    python backend/device_agent.py --server https://api.example.ru --device-token СЕКРЕТ --serial COM3
    python backend/device_agent.py --server https://api.example.ru --device-token СЕКРЕТ          # эмулятор
    python backend/device_agent.py --server https://api.example.ru --device-token СЕКРЕТ --once    # один обмен

Токен устройства — тот же, что передан серверу в --device-token
(или GREENHOUSE_DEVICE_TOKEN): им агент доказывает, что он свой.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:  # запуск как модуль: python -m backend.device_agent
    from .arduino import ArduinoLink
    from .db import DEVICES, ZONE_COUNT
except ImportError:  # запуск как файл: python backend/device_agent.py
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from arduino import ArduinoLink  # type: ignore
    from db import DEVICES, ZONE_COUNT  # type: ignore

# Как часто напоминать о состоянии, если ничего не меняется, секунды.
REPORT_EVERY = 60.0

# Пауза между повторами, когда сервер недоступен, секунды.
RETRY_PAUSE = 10.0


class AgentError(RuntimeError):
    """Обмен с сервером не удался — сообщение показывается человеку."""


class ServerBridge:
    """Подменяет домашнему каналу базу данных: копит показания для сервера.

    `ArduinoLink` умеет читать плату и эмулировать датчики, но пишет показания
    в БД. Дома БД не нужна: показания уезжают на сервер, оттуда же приходит
    состояние исполнителей (полив меняет влажность и в эмуляторе).
    """

    def __init__(self) -> None:
        self._state: Dict[str, Any] = {"tank": 78.0, "window_open": 0.0,
                                       "source": "simulator", "port": None}
        self._devices: Dict[int, Dict[str, bool]] = {
            zone: {device: False for device in DEVICES} for zone in range(1, ZONE_COUNT + 1)}
        self._readings: Dict[int, Dict[str, Optional[float]]] = {}
        self._notes: List[Dict[str, str]] = []
        self._recent: Dict[str, float] = {}
        self.tank: Optional[float] = None

    # ---------------------------------------------------- то, что зовёт ArduinoLink
    def state(self) -> Dict[str, Any]:
        return dict(self._state)

    def devices(self) -> Dict[int, Dict[str, bool]]:
        return {zone: dict(flags) for zone, flags in self._devices.items()}

    def set_state(self, **fields: Any) -> None:
        for key, value in fields.items():
            self._state[key] = value
            if key == "tank" and value is not None:
                self.tank = float(value)

    def add_reading(self, zone_id: int, temperature: Optional[float],
                    moisture: Optional[float], light: Optional[float]) -> None:
        self._readings[int(zone_id)] = {"temperature": temperature,
                                        "moisture": moisture, "light": light}

    def add_log(self, message: str, level: str = "info",
                zone_id: Optional[int] = None) -> None:
        """Замечания платы и эмулятора уезжают на сервер, чтобы попасть в журнал панели."""
        now = time.time()
        self._recent[message] = now
        if level == "info":
            return
        self._notes.append({"level": level, "message": message})

    def has_recent_log(self, message: str, seconds: int = 120) -> bool:
        stamp = self._recent.get(message)
        return stamp is not None and time.time() - stamp < float(seconds)

    # ------------------------------------------------------------- обмен с сервером
    def take(self, link: ArduinoLink) -> Dict[str, Any]:
        """Собирает телеграмму для сервера и очищает буфер."""
        data = [dict(zone=zone, **values) for zone, values in sorted(self._readings.items())]
        notes, self._notes = self._notes, []
        payload: Dict[str, Any] = {
            "source": link.source,
            "port": link.port,
            "firmware": link.firmware,
            "data": data,
            "notes": notes[:20],
        }
        if self.tank is not None:
            payload["tank"] = self.tank
        if link.source != "arduino":
            payload["note"] = ("плата не подключена: агент считает показания эмулятором"
                               if link.port else "COM-порт не задан: агент считает показания эмулятором")
        self._readings = {}
        self.tank = None
        return payload

    def apply_devices(self, devices: Any) -> None:
        """Сервер сообщает, какие исполнители включены — нужно эмулятору."""
        if not isinstance(devices, dict):
            return
        for zone_key, flags in devices.items():
            try:
                zone = int(zone_key)
            except (TypeError, ValueError):
                continue
            if zone not in self._devices or not isinstance(flags, dict):
                continue
            for device in DEVICES:
                if device in flags:
                    self._devices[zone][device] = bool(flags[device])


class DeviceApi:
    """Клиент служебного раздела сервера: /api/device/*."""

    def __init__(self, server: str, token: str, timeout: float = 25.0):
        self.base = server.rstrip("/")
        self.token = token
        self.timeout = float(timeout)

    def post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        request = urllib.request.Request(self.base + path, method="POST",
                                         data=json.dumps(payload).encode("utf-8"))
        request.add_header("Content-Type", "application/json")
        request.add_header("X-Device-Token", self.token)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", "replace")
            try:
                message = str(json.loads(body).get("error") or body)
            except json.JSONDecodeError:
                message = body
            if error.code == 404:
                message += " (сервер запущен без --device-remote?)"
            raise AgentError(f"сервер ответил {error.code}: {message}") from None
        except urllib.error.URLError as error:
            raise AgentError(f"сервер недоступен: {error.reason}") from None


def exchange(api: DeviceApi, link: ArduinoLink, store: ServerBridge) -> Tuple[int, int]:
    """Один обмен: отдать показания, забрать и применить команды.

    Возвращает (сколько команд принято, сколько применено).
    """
    answer = api.post("/api/device/sync", store.take(link))
    store.apply_devices(answer.get("devices"))

    commands = answer.get("commands") or []
    applied: List[int] = []
    errors: Dict[int, str] = {}
    for command in commands:
        try:
            link.send_command(int(command["zone_id"]), str(command["device"]),
                              bool(command.get("on")), command.get("seconds"))
            applied.append(int(command["id"]))
        except Exception as exc:  # noqa: BLE001
            errors[int(command["id"])] = str(exc)

    if commands:
        api.post("/api/device/ack", {"applied": applied, "errors": errors})
    return len(commands), len(applied)


def run_once(api: DeviceApi, link: ArduinoLink, store: ServerBridge) -> Tuple[int, int]:
    """Разовый обмен: используется ключом --once и проверками."""
    link.start()
    try:
        link.tick()
        return exchange(api, link, store)
    finally:
        link.stop()


def main() -> int:
    parser = argparse.ArgumentParser(description="Домашний агент: Arduino ↔ сервер теплицы")
    parser.add_argument("--server", default=os.environ.get("GREENHOUSE_SERVER"),
                        help="адрес сервера, например https://api.example.ru")
    parser.add_argument("--device-token", default=os.environ.get("GREENHOUSE_DEVICE_TOKEN"),
                        help="токен устройства (тот же, что у сервера в --device-token)")
    parser.add_argument("--serial", dest="serial_port", default=None,
                        help="COM-порт Arduino, например COM3; без него работает эмулятор")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--interval", type=float, default=2.0,
                        help="как часто обмениваться с сервером, секунды")
    parser.add_argument("--no-simulator", action="store_true",
                        help="не эмулировать датчики, если платы нет")
    parser.add_argument("--once", action="store_true", help="сделать один обмен и выйти (проверка)")
    args = parser.parse_args()

    if not args.server:
        parser.error("укажите --server (или GREENHOUSE_SERVER): где живёт сервер теплицы")
    if not args.device_token:
        parser.error("укажите --device-token (или GREENHOUSE_DEVICE_TOKEN) — "
                     "иначе сервер не пустит агента в раздел /api/device/*")

    store = ServerBridge()
    link = ArduinoLink(store, port=args.serial_port, baudrate=args.baud,
                       interval=args.interval, allow_simulator=not args.no_simulator)
    api = DeviceApi(args.server, args.device_token)

    where = f"COM-порт {args.serial_port}" if args.serial_port else "эмулятор датчиков"
    # Стрелки и прочие «красивые» символы в консоли Windows (cp866/cp1251) не
    # печатаются вовсе, поэтому в выводе только ASCII.
    print(f"Агент: {where} -> {api.base} (обмен раз в {args.interval:g} с)")

    if args.once:
        try:
            received, applied = run_once(api, link, store)
        except AgentError as exc:
            print(f"Не получилось: {exc}", file=sys.stderr)
            return 1
        print(f"Обмен выполнен: команд получено {received}, применено {applied}")
        return 0

    link.start()
    print("Остановить: Ctrl+C")
    last_report = 0.0
    last_error = ""
    applied_total = 0
    try:
        while True:
            started = time.time()
            try:
                received, applied = exchange(api, link, store)
                applied_total += applied
                if received:
                    print(f"Команд получено {received}, применено {applied}")
                last_error = ""
                if time.time() - last_report >= REPORT_EVERY:
                    last_report = time.time()
                    print(f"На связи: источник {link.source}, кадров {link.stats['frames']}, "
                          f"команд применено {applied_total}")
            except AgentError as exc:
                text = str(exc)
                if text != last_error:
                    print(f"Обмен не удался: {text}", file=sys.stderr)
                    last_error = text
                time.sleep(RETRY_PAUSE)
            rest = args.interval - (time.time() - started)
            if rest > 0:
                time.sleep(rest)
    except KeyboardInterrupt:
        print("\nОстановка агента...")
    finally:
        link.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
