# -*- coding: utf-8 -*-
"""Игра «Аниме-сонглесс»: угадай аниме по фрагменту опенинга.

Два режима:
    * **соло** — серия раундов без соперников: три ошибки (или три пропуска)
      и заход закончен, очки копятся за скорость и точность;
    * **онлайн** — комната на 2..8 человек, пять раундов на всех: раунд идёт
      одновременно, за правильный ответ дают очки, за скорость — добавку;
      после пяти раундов видна общая таблица.

Ответ всегда один — название аниме, а вариантов четыре: верный и три «обманки».
Верный вариант живёт только здесь, на сервере: страница получает варианты и
адрес фрагмента, а название аниме узнаёт лишь после раунда.

Треки приходят из таблицы `songless_tracks` (читает сервер), поэтому набор
правится в базе. Играть можно только те треки, у которых есть запись: сами
записи опенингов защищены авторским правом, поэтому их добавляет владелец
сайта — файлами или ссылками (см. backend/seed_songless.py).

Соло-заходы и комнаты живут в памяти процесса: это партии на несколько минут,
перезапуск сервера им переживать не нужно.
"""
from __future__ import annotations

import random
import sys
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Sequence

try:  # запуск как модуль: python -m backend.server
    from .songless_data import (
        DEFAULT_CLIP,
        DEFAULT_START,
        OPTION_COUNT,
        TRACKS,
        playable,
        public_track,
    )
except ImportError:  # запуск как файл: python backend/server.py
    from songless_data import (  # type: ignore
        DEFAULT_CLIP,
        DEFAULT_START,
        OPTION_COUNT,
        TRACKS,
        playable,
        public_track,
    )

# Брошенная комната живёт два часа, потом исчезает вместе со счётом.
ROOM_TTL_SECONDS = 2 * 60 * 60
# Заброшенный соло-заход убираем быстрее: их можно начать сколько угодно.
RUN_TTL_SECONDS = 30 * 60

MIN_PLAYERS = 2
MAX_PLAYERS = 8
MAX_ROOMS = 200
MAX_RUNS = 400
ROUNDS_PER_GAME = 5
# Сколько раундов можно выбрать в комнате и в соло (0 — соло до трёх ошибок).
# Раньше был фиксированный список, теперь число вводится вручную.
MIN_ROUNDS = 1
MAX_ROUNDS = 100
ROUND_CHOICES = (3, 5, 10, 15, 20)

# Очки: базовые за верный ответ, добавка за скорость и серия верных ответов.
BASE_POINTS = 100
SPEED_POINTS = 80
STREAK_STEP = 10          # шаг серии до шестой включительно
STREAK_CAP = 50           # бонус на шестой серии
STREAK_BEYOND_STEP = 3    # дальше каждая серия добавляет по 3

SOLO_LIVES = 3

# Память о недавних раундах: треки и аниме из этого «хвоста» стараемся не
# брать снова, чтобы новый заход не начинался с тех же песен, что прошлый.
# Границы зависят от размера набора (см. Songless._recent_limits).
RECENT_TRACK_MIN = 12
RECENT_TRACK_MAX = 60
RECENT_ANIME_MIN = 6
RECENT_ANIME_MAX = 30

# Сколько даётся на ответ, сколько показываем разбор и запас на дорогу ответа.
ANSWER_SECONDS = 20.0
REVEAL_SECONDS = 5.0
ANSWER_GRACE = 3.0

# Без похожих символов (I/1, O/0): код диктуют голосом и вводят руками.
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 4


class SonglessError(ValueError):
    """Ошибка правил игры: превращается в ответ 400 с понятным текстом."""


def _positive(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if number > 0 else default


def _rounds(value: Any, *, allow_infinite: bool = False) -> Optional[int]:
    """Сколько раундов выбрали: любое число от MIN_ROUNDS до MAX_ROUNDS.

    В соло 0 означает «до трёх ошибок». Некорректное число заменяется
    значением по умолчанию, чтобы из формы нельзя было прислать бесконечность.
    """
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0 if allow_infinite else ROUNDS_PER_GAME
    if allow_infinite and number == 0:
        return 0
    if MIN_ROUNDS <= number <= MAX_ROUNDS:
        return number
    return 0 if allow_infinite and number < 0 else ROUNDS_PER_GAME


def _elapsed(value: Any, server_elapsed: float) -> float:
    """Время нажатия от начала клиентского таймера в секундах.

    Клиент присылает его вместе с выбором: так пинг не отнимает очки и не
    превращает вовремя нажатый ответ в пропуск. Значение проверяем, чтобы
    нельзя было заявить больше времени, чем прошло на сервере, или отрицательное.
    """
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        seconds = server_elapsed
    seconds = max(0.0, seconds)
    # Клиент не мог нажать позже, чем сервер получил запрос, плюс небольшая
    # поправка на округления.
    if seconds > server_elapsed + 0.5:
        seconds = max(0.0, server_elapsed)
    return min(seconds, ANSWER_SECONDS + 0.5)


def _clip_of(track: Dict[str, Any]) -> Dict[str, Any]:
    """Что и как долго слушать: начало и длина фрагмента."""
    start = track.get("clip_start")
    length = track.get("clip_length")
    return {
        "start": float(start) if start is not None else DEFAULT_START,
        "length": _positive(length, DEFAULT_CLIP),
    }


class Songless:
    """Соло-заходы и комнаты «Аниме-сонглесса»."""

    def __init__(self, tracks: Optional[Sequence[Dict[str, Any]]] = None,
                 rng: Optional[random.Random] = None,
                 provider: Optional[Callable[[], List[Dict[str, Any]]]] = None,
                 on_finish: Optional[Callable[[Dict[str, Any]], None]] = None,
                 clip_signer: Optional[Callable[[str, int, int], str]] = None) -> None:
        self._lock = threading.Lock()
        self._rooms: Dict[str, Dict[str, Any]] = {}
        self._runs: Dict[str, Dict[str, Any]] = {}
        self._rng = rng or random.Random()
        self._on_finish = on_finish
        self._clip_signer = clip_signer
        # Недавно сыгранные треки и аниме: общие для соло и комнат, чтобы
        # подряд идущие партии не собирались из одних и тех же песен.
        self._recent_tracks: List[str] = []
        self._recent_anime: List[str] = []
        # Источник набора (обычно таблица в базе): перечитывается перед новым
        # раундом, поэтому правки видны без перезапуска сервера.
        self._provider = provider
        self.reload_tracks(tracks)

    # --------------------------------------------------------------- набор
    def reload_tracks(self, tracks: Optional[Sequence[Dict[str, Any]]] = None) -> int:
        """Берёт набор треков; играбельными считаются только записанные."""
        source = list(tracks) if tracks is not None else [dict(item) for item in TRACKS]
        if not source:
            source = [dict(item) for item in TRACKS]
        self._tracks = [dict(track) for track in source]
        self._playable = [track for track in self._tracks if playable(track)]
        # Набор могли почистить: забываем подсказки о треках, которых больше нет.
        known_keys = {self._track_key(track) for track in self._tracks}
        known_anime = {str(track.get("anime") or "") for track in self._tracks}
        self._recent_tracks[:] = [key for key in self._recent_tracks if key in known_keys]
        self._recent_anime[:] = [anime for anime in self._recent_anime if anime in known_anime]
        return len(self._tracks)

    def refresh(self) -> int:
        """Перечитывает набор из источника; при сбое остаётся прежний набор."""
        if not self._provider:
            return len(self._tracks)
        try:
            tracks = self._provider()
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"  набор треков недоступен, играем прежним: {exc}\n")
            return len(self._tracks)
        return self.reload_tracks(tracks) if tracks else len(self._tracks)

    def track_count(self) -> int:
        return len(self._tracks)

    def playable_count(self) -> int:
        return len(self._playable)

    def ready(self) -> bool:
        """Играть можно, когда записей хватает на четыре варианта ответа."""
        return len(self._playable) >= OPTION_COUNT

    @staticmethod
    def _track_key(track: Dict[str, Any]) -> str:
        """Ключ строки набора: у одного аниме может быть несколько опенингов."""
        return str(track.get("track_key") or track.get("anime") or "")

    def _recent_limits(self) -> tuple:
        """Сколько последних треков и аниме помнить для защиты от повторов."""
        tracks = len(self._playable)
        anime = len({str(track.get("anime") or "") for track in self._playable})
        track_limit = max(RECENT_TRACK_MIN, min(RECENT_TRACK_MAX, tracks // 3))
        anime_limit = max(RECENT_ANIME_MIN, min(RECENT_ANIME_MAX, anime // 2))
        return track_limit, anime_limit

    def _remember(self, track: Dict[str, Any]) -> None:
        """Запоминает трек и аниме как только что сыгранные."""
        self._recent_tracks.append(self._track_key(track))
        self._recent_anime.append(str(track.get("anime") or ""))
        track_limit, anime_limit = self._recent_limits()
        del self._recent_tracks[:-track_limit]
        del self._recent_anime[:-anime_limit]

    def _pick_track(self, used: Sequence[str]) -> Dict[str, Any]:
        """Играбельный трек без повторов, с равновесием между аниме.

        Порядок отсева:
            1. треки, уже сыгранные в этой партии (``used``);
            2. аниме, которые в этой партии уже были;
            3. треки и аниме из последних раундов прошлых заходов.

        Затем аниме выбирается равновероятно, а не трек: у сериалов вроде
        «Ван-Писа» десятки опенингов, и при выборе по трекам они выпадали бы
        в разы чаще остальных. Внутри аниме по-прежнему предпочитаем локальную
        запись: она начинает звучать сразу, без ожидания редиректа с CDN.
        """
        used = set(used)
        fresh = [track for track in self._playable
                 if self._track_key(track) not in used]
        if not fresh:
            fresh = list(self._playable)
        if not fresh:
            return {}
        used_anime = {str(track.get("anime") or "") for track in self._playable
                      if self._track_key(track) in used}
        pool = [track for track in fresh
                if str(track.get("anime") or "") not in used_anime] or fresh
        pool = [track for track in pool
                if self._track_key(track) not in self._recent_tracks] or pool
        recent_anime = set(self._recent_anime)
        pool = [track for track in pool
                if str(track.get("anime") or "") not in recent_anime] or pool
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for track in pool:
            groups.setdefault(str(track.get("anime") or ""), []).append(track)
        variants = groups[self._rng.choice(sorted(groups))]
        local = [track for track in variants
                 if not str(track.get("audio") or "").startswith(("http://", "https://"))]
        track = dict(self._rng.choice(local or variants))
        self._remember(track)
        return track

    def _options(self, track: Dict[str, Any]) -> List[str]:
        """Четыре варианта ответа: верный и три чужих аниме, порядок случайный.

        Названия в вариантах не повторяются даже если в наборе случайно
        оказались тёзки: иначе «обманка» совпала бы с верным ответом.
        """
        target = str(track["anime"])
        others = sorted({str(item["anime"]) for item in self._tracks} - {target})
        self._rng.shuffle(others)
        options = [target] + others[:OPTION_COUNT - 1]
        self._rng.shuffle(options)
        return options

    def _option_covers(self, options: Sequence[str]) -> Dict[str, str]:
        """Обложки вариантов ответа: по названию аниме из набора."""
        covers = {str(track.get("anime") or ""): str(track.get("cover") or "")
                  for track in self._tracks}
        return {name: covers.get(name, "") for name in options}

    def _clip_entry(self, track: Dict[str, Any], url: str,
                    scope: str, number: int, user_id: int) -> Dict[str, Any]:
        """Адрес фрагмента: подпись, начало, длина и признак внешней записи."""
        if self._clip_signer:
            try:
                signature = self._clip_signer(str(scope), int(number), int(user_id))
            except Exception:  # noqa: BLE001 — подпись не должна ломать раунд
                signature = ""
            if signature:
                url += "&sig=" + signature
        audio = str(track.get("audio") or "")
        return {
            "url": url,
            "start": _clip_of(track)["start"],
            "length": _clip_of(track)["length"],
            "external": audio.startswith(("http://", "https://")),
        }

    # -------------------------------------------------------------- служебное
    def _cleanup(self, now: float) -> None:
        """Убирает заброшенные комнаты и заходы (вызывать под замком)."""
        for code in [code for code, room in self._rooms.items()
                     if now - room["updated"] > ROOM_TTL_SECONDS]:
            del self._rooms[code]
        for run_id in [run_id for run_id, run in self._runs.items()
                       if now - run["updated"] > RUN_TTL_SECONDS]:
            del self._runs[run_id]

    def _new_code(self) -> str:
        while True:
            code = "".join(self._rng.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
            if code not in self._rooms:
                return code

    def _new_run_id(self) -> str:
        return "s" + "".join(self._rng.choice(CODE_ALPHABET) for _ in range(8))

    def _room(self, code: str) -> Dict[str, Any]:
        room = self._rooms.get((code or "").strip().upper())
        if not room:
            raise SonglessError("Комната не найдена — проверьте код приглашения")
        return room

    def _run(self, run_id: str) -> Dict[str, Any]:
        run = self._runs.get((run_id or "").strip())
        if not run:
            raise SonglessError("Заход не найден — начните новый")
        return run

    @staticmethod
    def _player(room: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        player = room["players"].get(user["id"])
        if not player:
            raise SonglessError("Вы не участник этой комнаты")
        return player

    def _points(self, seconds_left: float, streak: int = 0) -> int:
        """Очки: база, скорость и серия верных ответов подряд.

        До шестой серии бонус растёт по 10 (максимум 50), дальше — по 3 за
        каждую следующую: потолка нет, длинная серия стоит всё дороже.
        """
        share = max(0.0, min(1.0, seconds_left / _positive(ANSWER_SECONDS, 20.0)))
        streak = max(0, int(streak))
        if streak <= 6:
            bonus = STREAK_STEP * max(0, streak - 1)
        else:
            bonus = STREAK_CAP + STREAK_BEYOND_STEP * (streak - 6)
        return BASE_POINTS + int(round(SPEED_POINTS * share)) + bonus

    # ------------------------------------------------------------- снимок раунда
    # ------------------------------------------------------------------- соло
    def solo_start(self, user: Dict[str, Any], rounds: Any = None) -> Dict[str, Any]:
        """Начинает соло-заход: раунды идут один за другим до трёх ошибок.

        ``rounds`` — сколько песен сыграть (0 — до трёх ошибок, иначе 1..100).
        Значение проверяется по MIN_ROUNDS/MAX_ROUNDS, поэтому из формы нельзя
        прислать что угодно.
        """
        now = time.time()
        with self._lock:
            self._cleanup(now)
            self.refresh()
            if not self.ready():
                raise SonglessError(
                    "К игре пока не добавлено ни одной записи: положите файлы в"
                    " front/games/animesongless/audio или укажите ссылки в базе")
            if len(self._runs) >= MAX_RUNS:
                raise SonglessError("Слишком много заходов сразу, попробуйте через минуту")
            run_id = self._new_run_id()
            run: Dict[str, Any] = {
                "id": run_id,
                "user_id": user["id"],
                "user_name": user["username"],
                "created": now,
                "updated": now,
                "score": 0,
                "lives": SOLO_LIVES,
                "rounds": 0,
                "rounds_total": _rounds(rounds, allow_infinite=True) or 0,
                "time": 0.0,
                "streak": 0,
                "fast": 0,
                "guesses": [],
                "correct": 0,
                "used": [],
                "finished": False,
                "round": None,
            }
            self._start_solo_round(run, now)
            self._runs[run_id] = run
            return self._solo_payload(run, now)

    def solo_state(self, run_id: str, user: Dict[str, Any]) -> Dict[str, Any]:
        now = time.time()
        with self._lock:
            self._cleanup(now)
            run = self._run(run_id)
            self._check_owner(run, user)
            self._advance_solo(run, now)
            return self._solo_payload(run, now)

    def solo_answer(self, run_id: str, user: Dict[str, Any], choice: int,
                    elapsed: Any = None) -> Dict[str, Any]:
        now = time.time()
        with self._lock:
            self._cleanup(now)
            run = self._run(run_id)
            self._check_owner(run, user)
            self._advance_solo(run, now)
            self._take_answer(run, run["round"], choice, now, elapsed)
            run["updated"] = now
            return self._solo_payload(run, now)

    def solo_skip(self, run_id: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Пропускает ожидание следующего раунда в соло-заходе.

        Разбор раунда висит несколько секунд, и это ожидание можно не терпеть:
        кнопка «Дальше» сразу начинает следующий раунд (или заканчивает заход,
        если жизни кончились или раунды по плану закончились). Пока раунд не
        отвечен и не пропущен по времени, кнопка не работает — иначе её нажатие
        засчитывало бы пропуск вместо игрока.
        """
        now = time.time()
        with self._lock:
            self._cleanup(now)
            run = self._run(run_id)
            self._check_owner(run, user)
            self._advance_solo(run, now)
            round_ = run["round"]
            if run.get("finished") or round_ is None:
                raise SonglessError("Заход закончен — начните новый")
            if round_["choice"] is None and not round_["missed"]:
                raise SonglessError("Этот раунд ещё идёт: ответьте или дождитесь конца")
            total = int(run.get("rounds_total") or 0)
            if run["lives"] > 0 and (not total or run["rounds"] < total):
                self._start_solo_round(run, now)
            else:
                run["finished"] = True
                run["round"] = None
                self._report_solo(run)
            run["updated"] = now
            return self._solo_payload(run, now)

    def solo_clip_track(self, run_id: str, user: Dict[str, Any],
                        number: Optional[int]) -> Dict[str, Any]:
        """Трек текущего раунда захода — для отдачи аудио."""
        now = time.time()
        with self._lock:
            self._cleanup(now)
            run = self._run(run_id)
            self._check_owner(run, user)
            self._advance_solo(run, now)
            round_ = run["round"]
            if round_ is None or (number is not None and int(number) != round_["number"]):
                raise SonglessError("Этот раунд уже прошёл")
            return dict(round_["track"])

    @staticmethod
    def _check_owner(run: Dict[str, Any], user: Dict[str, Any]) -> None:
        if run["user_id"] != user["id"]:
            raise SonglessError("Это чужой заход")

    def _start_solo_round(self, run: Dict[str, Any], now: float) -> None:
        self.refresh()
        if len(run["used"]) >= max(1, len(self._playable)):
            run["used"] = []      # записей меньше, чем раундов: начинаем по кругу
        track = self._pick_track(run["used"])
        run["used"].append(str(track.get("track_key") or track["anime"]))
        options = self._options(track)
        run["round"] = {
            "number": run["rounds"] + 1,
            "track": track,
            "options": options,
            "answer_index": options.index(str(track["anime"])),
            "started": now,
            "deadline": now + _positive(ANSWER_SECONDS, 20.0),
            "close_at": now + _positive(ANSWER_SECONDS, 20.0) + ANSWER_GRACE,
            "choice": None,
            "correct": None,
            "points": 0,
            "spent": None,
            "missed": False,
            "reveal_until": None,
        }
        run["rounds"] = run["round"]["number"]
        run["updated"] = now

    def _advance_solo(self, run: Dict[str, Any], now: float) -> None:
        """Ленивые переходы: время вышло — засчитываем пропуск, разбор кончился — новый раунд."""
        round_ = run["round"]
        if round_ is None:
            return
        if round_["choice"] is None and not round_["missed"] and now > round_.get(
                "close_at", round_["deadline"]):
            self._miss(run, round_, now)
        if round_["reveal_until"] and now >= round_["reveal_until"]:
            total = int(run.get("rounds_total") or 0)
            if run["lives"] > 0 and (not total or run["rounds"] < total):
                self._start_solo_round(run, now)
            else:
                if not run.get("finished"):
                    run["finished"] = True
                    run["round"] = None
                    self._report_solo(run)

    def _miss(self, run: Dict[str, Any], round_: Dict[str, Any], now: float) -> None:
        """Пропуск по времени в соло: это такая же ошибка, как неверный ответ."""
        round_["missed"] = True
        round_["points"] = 0
        run["streak"] = 0
        run["lives"] = max(0, run.get("lives", SOLO_LIVES) - 1)
        round_["reveal_until"] = now + _positive(REVEAL_SECONDS, 8.0)

    def _take_answer(self, run: Dict[str, Any], round_: Dict[str, Any],
                     choice: Any, now: float, elapsed: Any = None) -> None:
        """Принимает выбор игрока: очки, жизнь и переход к разбору."""
        if round_ is None:
            raise SonglessError("Заход закончен — начните новый")
        if round_["choice"] is not None or round_["missed"]:
            raise SonglessError("Вы уже ответили в этом раунде")
        try:
            index = int(choice)
        except (TypeError, ValueError):
            raise SonglessError("Выберите один из вариантов") from None
        if not 0 <= index < len(round_["options"]):
            raise SonglessError("Такого варианта ответа нет")
        if now > round_.get("close_at", round_["deadline"]) + 0.5:
            raise SonglessError("Время на этот раунд уже вышло")
        spent = _elapsed(elapsed, max(0.0, now - round_["started"]))
        correct = index == round_["answer_index"]
        round_["choice"] = index
        round_["correct"] = correct
        round_["spent"] = spent
        round_["reveal_until"] = now + _positive(REVEAL_SECONDS, 8.0)
        if correct:
            run["streak"] = run.get("streak", 0) + 1
            points = self._points(ANSWER_SECONDS - spent, run["streak"])
            round_["points"] = points
            run["score"] = run.get("score", 0) + points
            run["correct"] = run.get("correct", 0) + 1
            run["time"] = run.get("time", 0.0) + spent
            if spent <= 2.0:
                run["fast"] = run.get("fast", 0) + 1
            run.setdefault("guesses", []).append({
                "anime": str(round_["track"]["anime"]),
                "song": str(round_["track"].get("song") or ""),
                "track_key": str(round_["track"].get("track_key")
                                  or round_["track"]["anime"]),
            })
        else:
            run["streak"] = 0
            run["lives"] = max(0, run.get("lives", SOLO_LIVES) - 1)

    def _report_solo(self, run: Dict[str, Any]) -> None:
        """Отдаёт итог соло-захода в журнал достижений."""
        if not self._on_finish:
            return
        total = int(run.get("rounds") or 0)
        record = {
            "username": run.get("user_name") or "",
            "user_id": run.get("user_id"),
            "mode": "solo",
            "rounds": total,
            "correct": int(run.get("correct") or 0),
            "score": int(run.get("score") or 0),
            "perfect": bool(total and run.get("correct") == total),
            "fast": int(run.get("fast") or 0),
            "place": 1,
            "winner": True,
            "detail": list(run.get("guesses") or []),
        }
        try:
            self._on_finish(record)
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"  итог «Аниме-сонглесса» не записан: {exc}\n")

    def _report_room(self, room: Dict[str, Any]) -> None:
        """Отдаёт итог партии команды/комнаты по каждому игроку."""
        if not self._on_finish or room.get("logged"):
            return
        room["logged"] = True
        places = {row["id"]: row for row in room.get("standings") or []}
        for player in room["players"].values():
            row = places.get(player["id"]) or {}
            record = {
                "username": player.get("name") or "",
                "user_id": player.get("id"),
                "mode": "online",
                "rounds": int(room.get("rounds") or 0),
                "correct": int(player.get("correct") or 0),
                "score": int(player.get("score") or 0),
                "perfect": bool(room.get("rounds")
                                and player.get("correct") == room.get("rounds")),
                "fast": int(player.get("fast") or 0),
                "place": int(row.get("place") or 0),
                "winner": bool(row.get("winner")),
                "detail": list(player.get("guesses") or []),
            }
            try:
                self._on_finish(record)
            except Exception as exc:  # noqa: BLE001
                sys.stderr.write(f"  итог «Аниме-сонглесса» не записан: {exc}\n")

    def _solo_payload(self, run: Dict[str, Any], now: float) -> Dict[str, Any]:
        round_ = run["round"]
        finished = bool(run["finished"]) or round_ is None
        revealed = bool(round_ and (round_["choice"] is not None or round_["missed"]))
        payload: Dict[str, Any] = {
            "run": run["id"],
            "mode": "solo",
            "player": {"id": run["user_id"], "name": run["user_name"]},
            "score": run["score"],
            "streak": int(run.get("streak") or 0),
            "lives": run["lives"],
            "lives_total": SOLO_LIVES,
            "rounds": run["rounds"],
            "round": run["rounds"],
            "rounds_planned": int(run.get("rounds_total") or 0),
            "rounds_choices": list(ROUND_CHOICES),
            "rounds_min": MIN_ROUNDS,
            "rounds_max": MAX_ROUNDS,
            "answer_seconds": ANSWER_SECONDS,
            "server_time": round(now, 3),
            "correct": run["correct"],
            "finished": finished,
            "phase": "finished" if finished else ("reveal" if revealed else "round"),
            "track_count": len(self._tracks),
            "playable_count": len(self._playable),
            "seconds_left": None,
            "reveal_in": None,
            "options": [],
            "option_covers": {},
            "choice": None,
            "correct_choice": None,
            "points": None,
            "spent": None,
            "answer": None,
            "clip": None,
            "updated": round(run["updated"], 3),
        }
        if round_ is None:
            return payload
        payload["round"] = round_["number"]
        payload["options"] = list(round_["options"])
        payload["option_covers"] = self._option_covers(round_["options"])
        payload["choice"] = round_["choice"]
        payload["correct_choice"] = round_["answer_index"]
        payload["points"] = round_["points"]
        spent = round_.get("spent")
        payload["spent"] = None if spent is None else round(float(spent), 1)
        payload["clip"] = self._clip_entry(
            round_["track"],
            f"/api/games/songless/solo/{run['id']}/clip?round={round_['number']}",
            run["id"], round_["number"], run["user_id"])
        if revealed:
            payload["answer"] = public_track(round_["track"])
            payload["missed"] = bool(round_["missed"])
            payload["reveal_in"] = max(0.0, round((round_["reveal_until"] or now) - now, 1))
        else:
            payload["seconds_left"] = max(0.0, round(round_["deadline"] - now, 1))
        return payload

    # ------------------------------------------------------------------ онлайн
    def create(self, user: Dict[str, Any], rounds: Any = None) -> Dict[str, Any]:
        """Создаёт комнату: игрок становится первым и ждёт остальных."""
        now = time.time()
        with self._lock:
            self._cleanup(now)
            self.refresh()
            if not self.ready():
                raise SonglessError(
                    "К игре пока не добавлено ни одной записи: положите файлы в"
                    " front/games/animesongless/audio или укажите ссылки в базе")
            if len(self._rooms) >= MAX_ROOMS:
                raise SonglessError("На сервере слишком много активных комнат, попробуйте позже")
            code = self._new_code()
            room: Dict[str, Any] = {
                "code": code,
                "created": now,
                "updated": now,
                "phase": "waiting",
                "host_id": user["id"],
                "players": {user["id"]: self._new_player(user)},
                "order": [user["id"]],
                "round": None,
                "rounds": 0,
                "rounds_total": _rounds(rounds),
                "logged": False,
                "used": [],
                "history": [],
                "standings": [],
            }
            self._rooms[code] = room
            return self._payload(room, user, now)

    @staticmethod
    def _new_player(user: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": user["id"],
            "name": user["username"],
            "score": 0,
            "correct": 0,
            "time": 0.0,
            "choice": None,
            "correct_choice": None,
            "points": 0,
            "missed": False,
            "spent": 0.0,
            "streak": 0,
            "fast": 0,
            "guesses": [],
            "ready": False,
        }

    def join(self, code: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Входит в комнату до начала игры (повторный вход ничего не ломает)."""
        now = time.time()
        with self._lock:
            self._cleanup(now)
            room = self._room(code)
            if user["id"] not in room["players"]:
                if room["phase"] != "waiting":
                    raise SonglessError("Игра уже началась — дождитесь следующей")
                if len(room["players"]) >= MAX_PLAYERS:
                    raise SonglessError(f"В комнате уже {MAX_PLAYERS} игроков")
                room["players"][user["id"]] = self._new_player(user)
                room["order"].append(user["id"])
            room["updated"] = now
            return self._payload(room, user, now)

    def set_ready(self, code: str, user: Dict[str, Any],
                  ready: bool = True) -> Dict[str, Any]:
        """Готовность в лобби или после партии: когда готовы все, игра стартует.

        Как в Narutodle: каждый отмечается сам, а последний «готов» запускает
        игру. После партии та же кнопка начинает новую. Хозяин по-прежнему может
        начать вручную кнопкой «Начать игру».
        """
        now = time.time()
        with self._lock:
            self._cleanup(now)
            room = self._room(code)
            player = self._player(room, user)
            if room["phase"] not in ("waiting", "finished"):
                raise SonglessError("Игра уже началась")
            player["ready"] = bool(ready)
            room["updated"] = now
            players = list(room["players"].values())
            everyone = (bool(ready) and len(players) >= MIN_PLAYERS
                        and all(item.get("ready") for item in players))
            if everyone:
                if room["phase"] == "finished":
                    self._reset_room(room, now)
                self._start_round(room, now)
            return self._payload(room, user, now)

    def start(self, code: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Начинает партию: только хозяин комнаты и не меньше двух игроков."""
        now = time.time()
        with self._lock:
            self._cleanup(now)
            room = self._room(code)
            self._player(room, user)
            if room["phase"] != "waiting":
                raise SonglessError("Игра уже идёт")
            if user["id"] != room["host_id"]:
                raise SonglessError("Игру начинает тот, кто создал комнату")
            if len(room["players"]) < MIN_PLAYERS:
                raise SonglessError("Нужен хотя бы один соперник: отправьте ссылку другу")
            self._start_round(room, now)
            return self._payload(room, user, now)

    def state(self, code: str, user: Dict[str, Any]) -> Dict[str, Any]:
        now = time.time()
        with self._lock:
            self._cleanup(now)
            room = self._room(code)
            self._player(room, user)
            self._advance(room, now)
            return self._payload(room, user, now)

    def answer(self, code: str, user: Dict[str, Any], choice: Any,
               elapsed: Any = None) -> Dict[str, Any]:
        now = time.time()
        with self._lock:
            self._cleanup(now)
            room = self._room(code)
            player = self._player(room, user)
            self._advance(room, now)
            round_ = room["round"]
            if room["phase"] != "round" or round_ is None:
                raise SonglessError("Сейчас не время отвечать")
            if player["choice"] is not None or player["missed"]:
                raise SonglessError("Вы уже ответили в этом раунде")
            try:
                index = int(choice)
            except (TypeError, ValueError):
                raise SonglessError("Выберите один из вариантов") from None
            if not 0 <= index < len(round_["options"]):
                raise SonglessError("Такого варианта ответа нет")
            if now > round_.get("close_at", round_["deadline"]) + 0.5:
                raise SonglessError("Время на этот раунд уже вышло")
            spent = _elapsed(elapsed, max(0.0, now - round_["started"]))
            correct = index == round_["answer_index"]
            player["choice"] = index
            player["correct_choice"] = correct
            player["spent"] = spent
            # Очки за раунд считаем сразу, но в счёт и в серию они попадают
            # только в разборе (см. _apply_round): пока раунд идёт, чужая
            # сумма не должна выдавать, кто уже угадал.
            if correct:
                player["points"] = self._points(ANSWER_SECONDS - spent,
                                                player.get("streak", 0) + 1)
            else:
                player["points"] = 0
            player["fast_pending"] = bool(correct and spent <= 2.0)
            player["time"] += spent
            room["updated"] = now
            self._maybe_reveal(room, now)
            return self._payload(room, user, now)

    def _reset_room(self, room: Dict[str, Any], now: float) -> None:
        """Обнуляет счёт и историю перед новой партией."""
        for player in room["players"].values():
            player.update(
                score=0, correct=0, time=0.0, choice=None, correct_choice=None,
                points=0, missed=False, streak=0, fast=0, guesses=[], ready=False,
                fast_pending=False)
        room["used"] = []
        room["rounds"] = 0
        room["round"] = None
        room["logged"] = False
        room["history"] = []
        room["standings"] = []
        room["updated"] = now

    def rematch(self, code: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Начинает новую партию в той же комнате (счёт обнуляется)."""
        now = time.time()
        with self._lock:
            self._cleanup(now)
            room = self._room(code)
            self._player(room, user)
            if room["phase"] != "finished":
                raise SonglessError("Партия ещё идёт")
            self._reset_room(room, now)
            self._start_round(room, now)
            return self._payload(room, user, now)

    def clip_track(self, code: str, user: Dict[str, Any],
                   number: Optional[int]) -> Dict[str, Any]:
        """Трек текущего раунда комнаты — для отдачи аудио."""
        now = time.time()
        with self._lock:
            self._cleanup(now)
            room = self._room(code)
            self._player(room, user)
            self._advance(room, now)
            round_ = room["round"]
            if round_ is None or (number is not None and int(number) != round_["number"]):
                raise SonglessError("Этот раунд уже прошёл")
            return dict(round_["track"])

    def stats(self) -> Dict[str, int]:
        with self._lock:
            self._cleanup(time.time())
            return {
                "rooms": len(self._rooms),
                "runs": len(self._runs),
                "players": sum(len(room["players"]) for room in self._rooms.values()),
                "playable": len(self._playable),
                "tracks": len(self._tracks),
            }

    # -------------------------------------------------------- ход партии
    def _start_round(self, room: Dict[str, Any], now: float) -> None:
        self.refresh()
        if len(room["used"]) >= max(1, len(self._playable)):
            room["used"] = []
        track = self._pick_track(room["used"])
        room["used"].append(str(track.get("track_key") or track["anime"]))
        options = self._options(track)
        room["round"] = {
            "number": room["rounds"] + 1,
            "track": track,
            "options": options,
            "answer_index": options.index(str(track["anime"])),
            "started": now,
            "deadline": now + _positive(ANSWER_SECONDS, 20.0),
            "close_at": now + _positive(ANSWER_SECONDS, 20.0) + ANSWER_GRACE,
            "reveal_until": None,
        }
        room["rounds"] = room["round"]["number"]
        room["phase"] = "round"
        for player in room["players"].values():
            player["choice"] = None
            player["correct_choice"] = None
            player["points"] = 0
            player["missed"] = False
            player["spent"] = 0.0
            player["fast_pending"] = False
        room["updated"] = now

    def set_rounds(self, code: str, user: Dict[str, Any], rounds: Any) -> Dict[str, Any]:
        """Сколько песен играть: выбирает хозяин комнаты до старта."""
        now = time.time()
        with self._lock:
            self._cleanup(now)
            room = self._room(code)
            self._player(room, user)
            if user["id"] != room["host_id"]:
                raise SonglessError("Количество песен выбирает хозяин комнаты")
            if room["phase"] != "waiting":
                raise SonglessError("Количество песен можно менять только в лобби")
            room["rounds_total"] = _rounds(rounds)
            room["updated"] = now
            return self._payload(room, user, now)

    def _maybe_reveal(self, room: Dict[str, Any], now: float) -> None:
        """Раунд кончается сразу, как ответили все, или по времени.

        Ждать дополнительных секунд после последнего ответа не нужно: ответ
        каждого уже принят сервером, а опоздавшие после дедлайна получают
        обычный запас ANSWER_GRACE в close_at.
        """
        if room["phase"] != "round" or room["round"] is None:
            return
        round_ = room["round"]
        close_at = round_.get("close_at", round_["deadline"])
        answered = all(player["choice"] is not None or player["missed"]
                       for player in room["players"].values())
        if not answered and now < close_at:
            return
        for player in room["players"].values():
            if player["choice"] is None and not player["missed"]:
                player["missed"] = True
        # Счёт, серии и угаданные треки обновляем ровно один раз — когда раунд
        # закрыт и результаты показываются всем.
        if not round_.get("applied"):
            self._apply_round(room, round_)
            round_["applied"] = True
        round_["reveal_until"] = now + _positive(REVEAL_SECONDS, 8.0)
        room["phase"] = "reveal"
        room["updated"] = now
        room["history"].append({
            "round": round_["number"],
            "answer": public_track(round_["track"]),
            "choices": {player["name"]: player["choice"]
                        for player in room["players"].values()},
            "points": {player["name"]: player["points"]
                       for player in room["players"].values()},
        })

    def _apply_round(self, room: Dict[str, Any], round_: Dict[str, Any]) -> None:
        """Начисляет очки за закрытый раунд: счёт, серии и угаданные треки.

        Вызывается один раз — в момент, когда результаты показываются всем,
        поэтому до разбора ни у кого не меняется сумма.
        """
        track = round_["track"]
        for player in room["players"].values():
            if player.get("correct_choice"):
                player["streak"] = int(player.get("streak") or 0) + 1
                points = int(player.get("points") or 0)
                player["score"] = int(player.get("score") or 0) + points
                player["correct"] = int(player.get("correct") or 0) + 1
                if player.get("fast_pending"):
                    player["fast"] = int(player.get("fast") or 0) + 1
                player.setdefault("guesses", []).append({
                    "anime": str(track["anime"]),
                    "song": str(track.get("song") or ""),
                    "track_key": str(track.get("track_key") or track["anime"]),
                })
            else:
                player["points"] = 0
                player["streak"] = 0
            player["fast_pending"] = False

    def _advance(self, room: Dict[str, Any], now: float) -> None:
        """Ленивые переходы: раунд → разбор → следующий раунд → итог."""
        if room["phase"] == "round":
            self._maybe_reveal(room, now)
        if room["phase"] == "reveal" and room["round"] is not None:
            if now >= (room["round"]["reveal_until"] or now):
                if room["rounds"] >= int(room.get("rounds_total") or ROUNDS_PER_GAME):
                    room["standings"] = self._standings(room)
                    room["phase"] = "finished"
                    room["round"] = None
                    for player in room["players"].values():
                        player["ready"] = False
                    room["updated"] = now
                    self._report_room(room)
                else:
                    self._start_round(room, now)

    def _standings(self, room: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Таблица очков: очки, потом точность, потом меньшее время."""
        players = sorted(
            room["players"].values(),
            key=lambda player: (-player["score"], -player["correct"], player["time"],
                                room["order"].index(player["id"])),
        )
        best = max([player["score"] for player in players] or [0])
        return [
            {
                "place": place,
                "id": player["id"],
                "name": player["name"],
                "score": player["score"],
                "correct": player["correct"],
                "time": round(player["time"], 1),
                "winner": bool(player["score"] == best and best > 0),
            }
            for place, player in enumerate(players, start=1)
        ]

    def _payload(self, room: Dict[str, Any], user: Dict[str, Any], now: float) -> Dict[str, Any]:
        """Состояние комнаты с точки зрения одного игрока.

        Верного варианта здесь нет, пока раунд не закончился: иначе ответ
        читался бы прямо из ответа сервера.
        """
        player = room["players"][user["id"]]
        round_ = room["round"]
        phase = room["phase"]
        revealed = phase in ("reveal", "finished")
        payload: Dict[str, Any] = {
            "code": room["code"],
            "mode": "online",
            "phase": phase,
            "round": round_["number"] if round_ else room["rounds"],
            "rounds_planned": int(room.get("rounds_total") or ROUNDS_PER_GAME),
            "rounds_choices": list(ROUND_CHOICES),
            "rounds_min": MIN_ROUNDS,
            "rounds_max": MAX_ROUNDS,
            "answer_seconds": ANSWER_SECONDS,
            "server_time": round(now, 3),
            "min_players": MIN_PLAYERS,
            "max_players": MAX_PLAYERS,
            "host": room["host_id"] == user["id"],
            "players": [
                {
                    "id": item["id"],
                    "name": item["name"],
                    "score": item["score"],
                    "streak": int(item.get("streak") or 0),
                    "answered": item["choice"] is not None or item["missed"],
                    "ready": bool(item.get("ready")),
                    # Данные ответа отдаём только в разборе: до него знание
                    # чужого выбора подсказывало бы верный вариант.
                    "choice": item["choice"] if revealed else None,
                    "correct": bool(item.get("correct_choice")) if revealed else None,
                    "points": int(item.get("points") or 0) if revealed else None,
                    "spent": (None if item.get("missed")
                              else round(float(item.get("spent") or 0), 1))
                             if revealed else None,
                    "missed": bool(item.get("missed")) if revealed else None,
                }
                for item in room["players"].values()
            ],
            "you": {
                "id": player["id"],
                "name": player["name"],
                "score": player["score"],
                "streak": int(player.get("streak") or 0),
                "correct": player["correct"],
                "choice": player["choice"],
                "correct_choice": player["correct_choice"],
                "points": player["points"],
                "missed": player["missed"],
                "ready": bool(player.get("ready")),
                "spent": round(float(player.get("spent") or 0), 3),
            },
            "track_count": len(self._tracks),
            "playable_count": len(self._playable),
            "options": [],
            "option_covers": {},
            "clip": None,
            "answer": None,
            "choices": {},
            "history": list(room["history"]),
            "standings": list(room["standings"]),
            "seconds_left": None,
            "reveal_in": None,
            "updated": round(room["updated"], 3),
        }
        if round_ is None:
            return payload
        payload["clip"] = self._clip_entry(
            round_["track"],
            f"/api/games/songless/rooms/{room['code']}/clip?round={round_['number']}",
            room["code"], round_["number"], player["id"])
        payload["options"] = list(round_["options"])
        payload["option_covers"] = self._option_covers(round_["options"])
        payload["choices"] = {
            item["name"]: item["choice"] for item in room["players"].values()
        }
        if revealed:
            payload["answer"] = public_track(round_["track"])
            payload["correct_choice"] = round_["answer_index"]
            if phase == "reveal":
                payload["reveal_in"] = max(0.0, round((round_["reveal_until"] or now) - now, 1))
        else:
            payload["seconds_left"] = max(0.0, round(round_["deadline"] - now, 1))
        return payload


__all__ = [
    "ANSWER_SECONDS",
    "MAX_PLAYERS",
    "MIN_PLAYERS",
    "ROUNDS_PER_GAME",
    "SOLO_LIVES",
    "Songless",
    "SonglessError",
]
