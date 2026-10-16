# -*- coding: utf-8 -*-
"""Игра «Угадай песню за 10 секунд»: короткий фрагмент и жёсткий таймер.

Правила простые и быстрые:
    * игрок выбирает тему (аниме, русский рэп, хип-хоп) и сложность —
      сложность и есть то самое «X секунд»: 5, 10 или 15 секунд на ответ;
    * звучит короткий фрагмент песни (`SLICE_SECONDS` секунд с припева),
      и на экране четыре названия: верное и три «обманки» из той же темы;
    * угадал — очки за ответ и добавка за скорость, не успел или промахнулся —
      раунд потерян; всего в заходе пять раундов.

Названия в вариантах не повторяются, а верный вариант живёт только на сервере:
страница получает варианты и адрес фрагмента, а исполнителя и год узнаёт лишь
после раунда. Записи песен защищены авторским правом, поэтому их добавляет
владелец сайта — файлами или ссылками (см. backend/seed_songguess.py). Пока
у песни нет записи, раунд на ней не строится.

Заходы живут в памяти процесса: это партия на минуту-другую, перезапуск сервера
ей переживать не нужно. Итог захода уходит в журнал (`songguess_runs`).
"""
from __future__ import annotations

import random
import sys
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Sequence

try:  # запуск как модуль: python -m backend.server
    from .songguess_data import (
        BASE_POINTS,
        CATEGORIES,
        CATEGORY_LABELS,
        DEFAULT_CLIP,
        DEFAULT_START,
        DIFFICULTIES,
        DIFFICULTY_LABELS,
        DIFFICULTY_SECONDS,
        OPTION_COUNT,
        REVEAL_SECONDS,
        ROUNDS_PER_GAME,
        SLICE_SECONDS,
        SPEED_POINTS,
        TRACKS,
        playable,
        public_track,
    )
except ImportError:  # запуск как файл: python backend/server.py
    from songguess_data import (  # type: ignore
        BASE_POINTS,
        CATEGORIES,
        CATEGORY_LABELS,
        DEFAULT_CLIP,
        DEFAULT_START,
        DIFFICULTIES,
        DIFFICULTY_LABELS,
        DIFFICULTY_SECONDS,
        OPTION_COUNT,
        REVEAL_SECONDS,
        ROUNDS_PER_GAME,
        SLICE_SECONDS,
        SPEED_POINTS,
        TRACKS,
        playable,
        public_track,
    )

# Заброшенный заход держим полчаса: партия короткая, возвращаться незачем.
RUN_TTL_SECONDS = 30 * 60
MAX_RUNS = 400


class SongGuessError(ValueError):
    """Ошибка правил игры: превращается в ответ 400 с понятным текстом."""


def _positive(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if number > 0 else default


def _clip_of(track: Dict[str, Any]) -> Dict[str, float]:
    """Что и как долго слушать: начало записи и длина фрагмента.

    Игра быстрая, поэтому длинный фрагмент из базы подрезаем до SLICE_SECONDS.
    """
    start = track.get("clip_start")
    length = track.get("clip_length")
    length = _positive(length, DEFAULT_CLIP)
    return {
        "start": float(start) if start is not None else DEFAULT_START,
        "length": min(length, SLICE_SECONDS),
    }


class SongGuess:
    """Заходы «Угадай песню за 10 секунд»."""

    def __init__(self, tracks: Optional[Sequence[Dict[str, Any]]] = None,
                 rng: Optional[random.Random] = None,
                 provider: Optional[Callable[[], List[Dict[str, Any]]]] = None,
                 on_finish: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        self._lock = threading.Lock()
        self._runs: Dict[str, Dict[str, Any]] = {}
        self._rng = rng or random.Random()
        self._provider = provider
        self._on_finish = on_finish
        self._tracks: List[Dict[str, Any]] = []
        self._playable: List[Dict[str, Any]] = []
        self.reload_tracks(tracks)

    # -------------------------------------------------------------------- набор
    def reload_tracks(self, tracks: Optional[Sequence[Dict[str, Any]]] = None) -> int:
        """Берёт набор песен; играбельными считаются только записанные."""
        source = list(tracks) if tracks is not None else [dict(item) for item in TRACKS]
        if not source:
            source = [dict(item) for item in TRACKS]
        self._tracks = [dict(track) for track in source]
        self._playable = [track for track in self._tracks if playable(track)]
        return len(self._tracks)

    def refresh(self) -> int:
        """Перечитывает набор из источника; при сбое остаётся прежний набор."""
        if not self._provider:
            return len(self._tracks)
        try:
            tracks = self._provider()
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"  набор песен недоступен, играем прежним: {exc}\n")
            return len(self._tracks)
        return self.reload_tracks(tracks) if tracks else len(self._tracks)

    def track_count(self) -> int:
        return len(self._tracks)

    def playable_count(self) -> int:
        return len(self._playable)

    def category_counts(self) -> Dict[str, Dict[str, int]]:
        """Сколько песен в каждой теме: всего и сколько можно играть."""
        counts: Dict[str, Dict[str, int]] = {
            item["key"]: {"songs": 0, "playable": 0} for item in CATEGORIES}
        for track in self._tracks:
            bucket = counts.setdefault(str(track.get("category") or ""),
                                       {"songs": 0, "playable": 0})
            bucket["songs"] += 1
            if playable(track):
                bucket["playable"] += 1
        return counts

    def categories(self) -> List[Dict[str, Any]]:
        """Темы с подписями и числом играбельных песен — для страницы."""
        counts = self.category_counts()
        blocks: List[Dict[str, Any]] = []
        for item in CATEGORIES:
            bucket = counts.get(item["key"], {"songs": 0, "playable": 0})
            blocks.append({
                "key": item["key"],
                "label": item["label"],
                "hint": item["hint"],
                "songs": bucket["songs"],
                "playable": bucket["playable"],
                "titles": len({str(track["title"]).casefold() for track in self._tracks
                               if str(track.get("category")) == item["key"]}),
                "ready": self.ready(item["key"]),
            })
        return blocks

    def ready(self, category: Optional[str] = None) -> bool:
        """Играть можно, когда в теме есть записи хотя бы на четыре варианта."""
        return len(self._playable_of(category)) >= OPTION_COUNT

    def problems(self) -> List[str]:
        """Что мешает игре: без записей раунд не собрать."""
        problems: List[str] = []
        if not self._playable:
            problems.append("Ни к одной песне не привязана запись: положите файлы в"
                            " front/games/songguess/audio или укажите ссылки в базе")
        for block in self.categories():
            if block["ready"]:
                continue
            problems.append(f"Тема «{block['label']}»: записей {block['playable']} —"
                            f" для раунда нужно {OPTION_COUNT}")
        return problems

    def _playable_of(self, category: Optional[str]) -> List[Dict[str, Any]]:
        key = str(category or "").strip().lower()
        if not key:
            return list(self._playable)
        return [track for track in self._playable if str(track.get("category")) == key]

    # ----------------------------------------------------------------- служебное
    def _cleanup(self, now: float) -> None:
        for run_id in [run_id for run_id, run in self._runs.items()
                       if now - run["updated"] > RUN_TTL_SECONDS]:
            del self._runs[run_id]

    def _new_run_id(self) -> str:
        while True:
            run_id = "g" + "%07x" % self._rng.getrandbits(28)
            if run_id not in self._runs:
                return run_id

    def _run(self, run_id: str) -> Dict[str, Any]:
        run = self._runs.get(str(run_id or "").strip())
        if not run:
            raise SongGuessError("Заход не найден — начните новый")
        return run

    @staticmethod
    def _check_owner(run: Dict[str, Any], user: Dict[str, Any]) -> None:
        if user.get("role") == "admin":
            return
        if int(run["user_id"]) != int(user.get("id") or 0):
            raise SongGuessError("Это чужой заход")

    # ---------------------------------------------------------------------- старт
    def start(self, user: Dict[str, Any], category: str = "anime",
              difficulty: str = "normal") -> Dict[str, Any]:
        """Начинает заход: пять раундов в выбранной теме и с выбранным таймером."""
        key = str(category or "").strip().lower()
        if key not in CATEGORY_LABELS:
            raise SongGuessError("Неизвестная тема: выберите одну из списка")
        if difficulty not in DIFFICULTY_SECONDS:
            raise SongGuessError("Неизвестная сложность: выберите таймер")
        now = time.time()
        with self._lock:
            self._cleanup(now)
            self.refresh()
            if not self.ready(key):
                count = len(self._playable_of(key))
                raise SongGuessError(
                    f"В теме «{CATEGORY_LABELS[key]}» записей {count} —"
                    f" для раунда нужно {OPTION_COUNT}. Добавьте файлы в"
                    " front/games/songguess/audio или ссылки в базе")
            if len(self._runs) >= MAX_RUNS:
                raise SongGuessError("Слишком много заходов сразу, попробуйте через минуту")
            run: Dict[str, Any] = {
                "id": self._new_run_id(),
                "user_id": int(user.get("id") or 0),
                "user_name": str(user.get("username") or ""),
                "category": key,
                "difficulty": difficulty,
                "seconds": DIFFICULTY_SECONDS[difficulty],
                "created": now,
                "updated": now,
                "score": 0,
                "correct": 0,
                "rounds": 0,
                "rounds_total": ROUNDS_PER_GAME,
                "used": [],
                "fastest": None,
                "finished": False,
                "round": None,
                "history": [],
            }
            self._start_round(run, now)
            self._runs[run["id"]] = run
            return self._payload(run, now)

    def state(self, run_id: str, user: Dict[str, Any]) -> Dict[str, Any]:
        now = time.time()
        with self._lock:
            self._cleanup(now)
            run = self._run(run_id)
            self._check_owner(run, user)
            self._advance(run, now)
            return self._payload(run, now)

    def answer(self, run_id: str, user: Dict[str, Any], choice: Any) -> Dict[str, Any]:
        """Принимает выбор игрока: очки, разбор раунда и переход к следующему."""
        now = time.time()
        with self._lock:
            self._cleanup(now)
            run = self._run(run_id)
            self._check_owner(run, user)
            self._advance(run, now)
            round_ = run["round"]
            if round_ is None:
                raise SongGuessError("Заход закончен — начните новый")
            if round_["choice"] is not None or round_["missed"]:
                raise SongGuessError("Вы уже ответили в этом раунде")
            try:
                index = int(choice)
            except (TypeError, ValueError):
                raise SongGuessError("Выберите один из вариантов") from None
            if not 0 <= index < len(round_["options"]):
                raise SongGuessError("Такого варианта ответа нет")
            correct = index == round_["answer_index"]
            round_["choice"] = index
            round_["correct"] = correct
            round_["reveal_until"] = now + REVEAL_SECONDS
            if correct:
                left = max(0.0, round_["deadline"] - now)
                round_["points"] = self._points(left, run["seconds"])
                run["score"] += round_["points"]
                run["correct"] += 1
                spent = max(0.0, now - round_["started"])
                if run["fastest"] is None or spent < run["fastest"]:
                    run["fastest"] = spent
            else:
                round_["points"] = 0
            run["history"].append(self._round_result(round_))
            run["updated"] = now
            return self._payload(run, now)

    def clip_track(self, run_id: str, user: Dict[str, Any],
                   number: Optional[Any] = None) -> Dict[str, Any]:
        """Песня текущего раунда — для отдачи аудио."""
        now = time.time()
        with self._lock:
            self._cleanup(now)
            run = self._run(run_id)
            self._check_owner(run, user)
            self._advance(run, now)
            round_ = run["round"]
            if round_ is None:
                raise SongGuessError("Заход закончен")
            if number not in (None, "", str(round_["number"]), round_["number"]):
                raise SongGuessError("Этот раунд уже прошёл")
            return dict(round_["track"])

    # -------------------------------------------------------------------- раунды
    def _start_round(self, run: Dict[str, Any], now: float) -> None:
        """Готовит раунд: песня, четыре названия и таймер."""
        self.refresh()
        own = self._playable_of(run["category"])
        if len(run["used"]) >= max(1, len(own)):
            run["used"] = []      # записей меньше, чем раундов: идём по кругу
        fresh = [track for track in own if str(track["id"]) not in run["used"]]
        track = dict(self._rng.choice(fresh or own))
        run["used"].append(str(track["id"]))
        options = self._options(track, run["category"])
        run["round"] = {
            "number": run["rounds"] + 1,
            "track": track,
            "options": options,
            "answer_index": options.index(str(track["title"])),
            "started": now,
            "deadline": now + run["seconds"],
            "choice": None,
            "correct": None,
            "points": 0,
            "missed": False,
            "reveal_until": None,
        }
        run["rounds"] = run["round"]["number"]
        run["updated"] = now

    def _options(self, track: Dict[str, Any], category: str) -> List[str]:
        """Четыре названия: верное и три «обманки», порядок случайный.

        Сначала берём песни из той же темы — так варианты правдоподобнее;
        если там не набралось, добираем из остальных тем. Названия не
        повторяются, иначе «обманка» совпала бы с верным ответом.
        """
        target = str(track["title"])
        seen = {target.casefold()}
        options = [target]

        def add_from(source: Sequence[Dict[str, Any]]) -> None:
            titles = sorted({str(item["title"]) for item in source
                             if str(item["title"]).casefold() not in seen})
            self._rng.shuffle(titles)
            for title in titles:
                if len(options) >= OPTION_COUNT:
                    return
                seen.add(title.casefold())
                options.append(title)

        add_from([item for item in self._tracks if str(item.get("category")) == category])
        if len(options) < OPTION_COUNT:
            add_from(self._tracks)
        self._rng.shuffle(options)
        return options

    def _points(self, seconds_left: float, seconds: float) -> int:
        """Очки за верный ответ: базовые плюс доля за оставшееся время."""
        share = max(0.0, min(1.0, seconds_left / _positive(seconds, 10.0)))
        return BASE_POINTS + int(round(SPEED_POINTS * share))

    def _miss(self, run: Dict[str, Any], round_: Dict[str, Any], now: float) -> None:
        """Не успел: раунд потерян, показываем разбор."""
        round_["missed"] = True
        round_["points"] = 0
        round_["reveal_until"] = now + REVEAL_SECONDS
        run["history"].append(self._round_result(round_))

    def _advance(self, run: Dict[str, Any], now: float) -> None:
        """Ленивые переходы: время вышло — промах, разбор кончился — новый раунд."""
        round_ = run["round"]
        if round_ is None:
            return
        if round_["choice"] is None and not round_["missed"] and now > round_["deadline"]:
            self._miss(run, round_, now)
            run["updated"] = now
        if round_["reveal_until"] and now >= round_["reveal_until"]:
            if run["rounds"] < run["rounds_total"]:
                self._start_round(run, now)
            else:
                run["finished"] = True
                run["round"] = None
                run["updated"] = now
                self._finish(run)

    @staticmethod
    def _round_result(round_: Dict[str, Any]) -> Dict[str, Any]:
        """Строка истории раунда: что играло и чем кончилось."""
        track = round_["track"]
        return {
            "number": round_["number"],
            "title": str(track["title"]),
            "artist": str(track.get("artist") or ""),
            "year": str(track.get("year") or ""),
            "source": str(track.get("source") or ""),
            "correct": bool(round_["correct"]),
            "missed": bool(round_["missed"]),
            "points": int(round_["points"] or 0),
        }

    def _finish(self, run: Dict[str, Any]) -> None:
        """Итог захода уходит в журнал: он виден и игроку, и админу."""
        if self._on_finish is None:
            return
        fastest = f"{run['fastest']:.1f} с" if run["fastest"] is not None else "—"
        record = {
            "game": "songguess",
            "username": run["user_name"],
            "user_id": run["user_id"],
            "category": run["category"],
            "category_label": CATEGORY_LABELS.get(run["category"], run["category"]),
            "difficulty": run["difficulty"],
            "seconds": float(run["seconds"]),
            "rounds": int(run["rounds_total"]),
            "correct": int(run["correct"]),
            "score": int(run["score"]),
            "fastest": round(float(run["fastest"]), 2) if run["fastest"] is not None else None,
            "detail": "; ".join(
                f"{item['number']}: {'верно' if item['correct'] else ('пропуск' if item['missed'] else 'мимо')}"
                f" — {item['artist']} «{item['title']}»"
                for item in run["history"]),
            "best_note": f"лучший ответ {fastest}",
        }
        try:
            self._on_finish(record)
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"  итог захода не записан: {exc}\n")

    # -------------------------------------------------------------------- снимок
    def _payload(self, run: Dict[str, Any], now: float) -> Dict[str, Any]:
        round_ = run["round"]
        finished = bool(run["finished"]) or round_ is None
        revealed = bool(round_ and (round_["choice"] is not None or round_["missed"]))
        payload: Dict[str, Any] = {
            "run": run["id"],
            "mode": "solo",
            "player": {"id": run["user_id"], "name": run["user_name"]},
            "category": run["category"],
            "category_label": CATEGORY_LABELS.get(run["category"], run["category"]),
            "difficulty": run["difficulty"],
            "difficulty_label": DIFFICULTY_LABELS.get(run["difficulty"], run["difficulty"]),
            "seconds": run["seconds"],
            "slice_seconds": SLICE_SECONDS,
            "score": run["score"],
            "correct": run["correct"],
            "rounds": run["rounds"],
            "rounds_total": run["rounds_total"],
            "round": run["rounds"],
            "phase": "finished" if finished else ("reveal" if revealed else "round"),
            "finished": finished,
            "seconds_left": None,
            "reveal_in": None,
            "options": [],
            "choice": None,
            "correct_choice": None,
            "points": None,
            "max_points": BASE_POINTS + SPEED_POINTS,
            "answer": None,
            "missed": False,
            "fastest": round(run["fastest"], 1) if run["fastest"] is not None else None,
            "history": list(run["history"]),
            "clip": None,
            "tracks_total": len(self._tracks),
            "playable_total": len(self._playable),
            "updated": round(run["updated"], 3),
        }
        if round_ is None:
            return payload
        payload["round"] = round_["number"]
        payload["options"] = list(round_["options"])
        payload["choice"] = round_["choice"]
        payload["correct_choice"] = round_["answer_index"]
        payload["points"] = round_["points"]
        payload["missed"] = bool(round_["missed"])
        clip = _clip_of(round_["track"])
        payload["clip"] = {
            "url": f"/api/games/songguess/runs/{run['id']}/clip?round={round_['number']}",
            "start": clip["start"],
            "length": clip["length"],
        }
        if revealed:
            payload["answer"] = public_track(round_["track"])
            payload["reveal_in"] = max(0.0, round((round_["reveal_until"] or now) - now, 1))
        else:
            payload["seconds_left"] = max(0.0, round(round_["deadline"] - now, 1))
        return payload

    # -------------------------------------------------------------------- статус
    def stats(self) -> Dict[str, Any]:
        with self._lock:
            self._cleanup(time.time())
            return {
                "tracks": len(self._tracks),
                "playable": len(self._playable),
                "runs": len(self._runs),
                "categories": self.categories(),
            }

    def difficulty_blocks(self) -> List[Dict[str, Any]]:
        """Сложности для страницы: подпись и таймер."""
        return [{"key": key, "label": label, "seconds": seconds}
                for key, label, seconds in DIFFICULTIES]


__all__ = [
    "MAX_RUNS",
    "RUN_TTL_SECONDS",
    "SongGuess",
    "SongGuessError",
]
