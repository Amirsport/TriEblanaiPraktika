# -*- coding: utf-8 -*-
"""Канал «сервер ↔ домашний агент»: сервер работает там, где нет платы.

Зачем: сервер можно поставить на VPS, но Arduino подключена к COM-порту
домашнего ПК. Поэтому сервер не держит порт, а:

    * принимает показания, которые приносит домашний агент (`backend/device_agent.py`);
    * складывает команды исполнителям в очередь (таблица `device_commands`),
      а агент забирает их тем же запросом и подтверждает отдельным.

У класса тот же набор методов, что у `ArduinoLink`, поэтому `Application`
работает с ним без изменений: `start`, `stop`, `send_command`, `status`.
Отличие в том, что «связь» здесь — это не COM-порт, а регулярные обращения
агента: пока он выходит на связь, канал считается живым.

Просроченные команды не выполняются: если агент пропал, полив через час
после нажатия кнопки был бы опаснее, чем пропущенная команда.
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

try:  # запуск как модуль: python -m backend.server
    from .db import DEVICES, ZONE_COUNT, DatabaseLike  # type: ignore
except ImportError:  # запуск как файл: python backend/server.py
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from db import DEVICES, ZONE_COUNT, DatabaseLike  # type: ignore


# Сколько секунд молчания агента считаются обрывом связи. Агент спрашивает
# сервер каждые 2 с, поэтому минуты хватает с большим запасом.
AGENT_TIMEOUT = 60.0

# Через сколько секунд неподтверждённая команда считается просроченной.
COMMAND_MAX_AGE = 120.0

# Как часто убирать из очереди старые выполненные команды.
PRUNE_INTERVAL = 300.0


def _opt_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class RemoteDeviceLink:
    """Очередь команд агенту и приём показаний от него."""

    def __init__(
        self,
        db: DatabaseLike,
        token: str,
        timeout: float = AGENT_TIMEOUT,
        command_max_age: float = COMMAND_MAX_AGE,
    ):
        self.db = db
        self.token = token
        self.timeout = float(timeout)
        self.command_max_age = float(command_max_age)

        # Показываем то же, что и прямой канал: откуда данные и что с платой.
        self.source = "agent"
        self.connected = False
        self.port: Optional[str] = None
        self.firmware: Optional[str] = None
        self.last_seen: Optional[float] = None

        self.stats: Dict[str, Any] = {"frames": 0, "errors": 0, "commands_applied": 0}
        self.device_source = "unknown"  # что агент говорит о своём источнике данных
        self.note = ""  # причина, по которой агент работает без платы
        self.pending = 0  # команды, выданные агенту, но ещё не подтверждённые

        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._pruned_at = 0.0
        self._online = False

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> None:
        """Отдельного потока не нужно: агент сам приходит, а связь — это его запросы."""
        self._stop.clear()
        self._thread = threading.Thread(target=self._watchdog, name="device-link", daemon=True)
        self._thread.start()
        self.db.add_log("Сервер ждёт домашнего агента: команды идут через очередь", "info")

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)

    def _watchdog(self) -> None:
        """Замечает обрыв связи, даже если агент больше не придёт."""
        while not self._stop.wait(5.0):
            try:
                was_online = self.connected
                self._refresh()
                if was_online and not self.connected:
                    self.db.add_log(
                        f"Домашний агент не выходит на связь {int(self.timeout)} с — "
                        "команды копится в очереди", "warn")
            except Exception as exc:  # noqa: BLE001
                self.db.add_log(f"Сбой контроля связи с агентом: {exc}", "err")

    # ------------------------------------------------------------------- состояние
    def _alive(self) -> bool:
        return self.last_seen is not None and time.time() - self.last_seen <= self.timeout

    def _refresh(self) -> None:
        self.connected = self._alive()
        open_commands = [row for row in self.db.device_commands(limit=50)
                         if row.get("applied_at") is None]
        self.pending = len(open_commands)

    def status(self) -> Dict[str, Any]:
        self._refresh()
        seen = None if self.last_seen is None else round(time.time() - self.last_seen, 1)
        return {
            "source": "agent",
            "connected": self.connected,
            "mode": "remote",
            "port": self.port,
            "firmware": self.firmware,
            "last_seen": self.last_seen,
            "seen_seconds": seen,
            "frames": self.stats["frames"],
            "errors": self.stats["errors"],
            "commands_applied": self.stats["commands_applied"],
            "queued": self.pending,
            "device_source": self.device_source,
            "note": self.note,
        }

    # -------------------------------------------------------------------- команды
    def send_command(self, zone_id: int, device: str, on: bool,
                     seconds: Optional[float] = None) -> bool:
        """Кладёт команду в очередь. Выполнит её агент — но только пока свежую."""
        command_id = self.db.device_command_add(int(zone_id), device, bool(on), seconds)
        if not command_id:
            self.db.add_log("Не удалось поставить команду в очередь", "err")
            return False
        if not self._alive():
            name = f"Участок {zone_id}"
            if not self.db.has_recent_log(f"{name}: команда ждёт агента", 600):
                self.db.add_log(f"{name}: команда ждёт агента — связи с домом нет", "warn", zone_id)
        return True

    # --------------------------------------------------------------------- агент
    def ingest(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Принимает показания агента и отдаёт ему накопившиеся команды.

        Телеграмма агента:
            {"tank": 78.5, "source": "arduino", "port": "COM3", "firmware": "1.0",
             "note": "", "data": [{"zone": 1, "temperature": 24.5, ...}],
             "notes": [{"level": "warn", "message": "..."}]}
        """
        now = time.time()
        first = not self._online
        with self._lock:
            self.last_seen = now
            self.stats["frames"] += 1
            if payload.get("source"):
                self.device_source = str(payload["source"])
            if payload.get("port") is not None:
                self.port = str(payload["port"]) or None
            if payload.get("firmware"):
                self.firmware = str(payload["firmware"])
            self.note = str(payload.get("note") or "")

            self._apply_state(payload)
            self._apply_readings(payload.get("data"))
            self._apply_notes(payload.get("notes"))

        self.connected = True
        self._online = True
        if first:
            where = "Arduino " + (self.port or "?") if self.device_source == "arduino" else "эмулятор"
            self.db.add_log(f"Домашний агент на связи ({where})", "info")
            if self.note:
                self.db.add_log(f"Домашний агент: {self.note}", "warn")

        return {"ok": True, "mode": "remote", "commands": self.take_commands()}

    def take_commands(self) -> list:
        """Выдаёт агенту неподтверждённые команды, просроченные — закрывает."""
        commands = self.db.device_commands_pending(limit=50, max_age=self.command_max_age)
        self.pending = len(commands)
        return commands

    def acknowledge(self, applied: Any, errors: Any) -> int:
        """Отмечает команды выполненными: агент применил их к плате или сообщил об ошибке."""
        problems: Dict[Any, str] = {}
        if isinstance(errors, dict):
            problems = {key: str(value) for key, value in errors.items()}
        done = self.db.device_commands_ack(applied or [], problems)
        self.stats["commands_applied"] += done
        self.pending = max(0, self.pending - done)
        for command_id, message in problems.items():
            self.db.add_log(f"Агент не применил команду {command_id}: {message}", "warn")
        return done

    # ------------------------------------------------------------------ разбор поля
    def _apply_state(self, payload: Dict[str, Any]) -> None:
        fields: Dict[str, Any] = {}
        tank = _opt_float(payload.get("tank"))
        if tank is not None:
            fields["tank"] = tank
        if payload.get("source"):
            fields["source"] = str(payload["source"])
        if "port" in payload:
            fields["port"] = (str(payload["port"]) or None) if payload.get("port") else None
        if fields:
            self.db.set_state(**fields)

    def _apply_readings(self, data: Any) -> None:
        if not isinstance(data, list):
            return
        for item in data:
            if not isinstance(item, dict):
                continue
            try:
                zone_id = int(item["zone"])
            except (KeyError, TypeError, ValueError):
                self.stats["errors"] += 1
                continue
            if not 1 <= zone_id <= ZONE_COUNT:
                self.stats["errors"] += 1
                continue
            self.db.add_reading(
                zone_id,
                _opt_float(item.get("temperature")),
                _opt_float(item.get("moisture")),
                _opt_float(item.get("light")),
            )

    def _apply_notes(self, notes: Any) -> None:
        """Замечания домашней стороны («порт не открылся») попадают в журнал панели."""
        if not isinstance(notes, list):
            return
        for item in notes:
            if not isinstance(item, dict):
                continue
            message = str(item.get("message") or "").strip()
            if not message:
                continue
            level = str(item.get("level") or "info")
            self.db.add_log(f"Дома: {message}", level if level in ("info", "warn", "err") else "info")

    # -------------------------------------------------------------------- сервис
    def prune(self) -> None:
        """Вызывается из обработчика: очередь команд не должна расти бесконечно."""
        now = time.time()
        if now - self._pruned_at < PRUNE_INTERVAL:
            return
        self._pruned_at = now
        try:
            self.db.device_commands_prune()
        except Exception as exc:  # noqa: BLE001
            self.db.add_log(f"Не удалось почистить очередь команд: {exc}", "warn")

    def devices_payload(self) -> Dict[int, Dict[str, bool]]:
        """Состояние исполнителей: нужно агенту, когда он работает эмулятором дома."""
        return self.db.devices()


def remote_mode_help() -> str:
    """Подсказка для запуска: пригодится и в консоли, и в документации."""
    return ("Сервер в режиме агента: плата осталась дома. Запустите там "
            "backend/device_agent.py с адресом сервера и устройство-токеном.")


__all__ = ["RemoteDeviceLink", "AGENT_TIMEOUT", "COMMAND_MAX_AGE", "PRUNE_INTERVAL",
           "remote_mode_help", "DEVICES", "ZONE_COUNT"]
