# -*- coding: utf-8 -*-
"""Проверки треков, вариантов, очков и серии без запуска сервера."""
import json
import random

from backend.db import songless_metrics_from_runs
from backend.songless import (
    BASE_POINTS,
    SPEED_POINTS,
    STREAK_BEYOND_STEP,
    STREAK_CAP,
    STREAK_STEP,
    Songless,
    SonglessError,
)


def track(index: int, anime: str = "") -> dict:
    return {
        "track_key": f"key-{index}",
        "anime": anime or f"Аниме {index}",
        "song": f"Опенинг {index}",
        "artist": "Исполнитель",
        "year": "2020",
        "audio": "https://example.com/op.webm",
        "cover": f"covers/{index}.jpg",
        "video": "https://example.com/op.webm",
        "clip_start": 0,
        "clip_length": 8,
    }


tracks = [track(0, "Общее аниме"), track(1, "Общее аниме")]
tracks += [track(index) for index in range(2, 12)]
game = Songless(tracks, rng=random.Random(7))
assert game.ready() and game.playable_count() == len(tracks)
assert game._points(20, 1) == BASE_POINTS + SPEED_POINTS
assert game._points(0, 1) == BASE_POINTS
assert game._points(0, 2) == BASE_POINTS + STREAK_STEP
assert game._points(0, 6) == BASE_POINTS + STREAK_CAP
# С седьмой серии бонус растёт по +3 и не упирается в потолок.
assert game._points(0, 7) == BASE_POINTS + STREAK_CAP + STREAK_BEYOND_STEP
assert game._points(0, 20) == BASE_POINTS + STREAK_CAP + 14 * STREAK_BEYOND_STEP

user = {"id": 1, "username": "tester"}
state = game.solo_start(user, 5)
assert state["phase"] == "round"
assert len(state["options"]) == 4 and len(set(state["options"])) == 4
correct = state["correct_choice"]
state = game.solo_answer(state["run"], user, correct)
assert state["phase"] == "reveal" and state["points"] > BASE_POINTS
assert state["spent"] is not None and state["spent"] >= 0
assert state["answer"] and state["answer"]["cover"] and state["answer"]["video"]
assert state["streak"] == 1
print("solo ok", state["points"])

custom = game.solo_start(user, 42)
assert custom["rounds_planned"] == 42
assert custom["rounds_min"] == 1 and custom["rounds_max"] == 100
print("custom rounds ok")

first = game.create({"id": 1, "username": "one"})
second = game.join(first["code"], {"id": 2, "username": "two"})
room = game.start(first["code"], {"id": 1, "username": "one"})
correct = game._rooms[first["code"]]["round"]["answer_index"]
def score(room_state, name):
    return next(item for item in room_state["players"] if item["name"] == name)["score"]

before = score(room, "one")
room = game.answer(first["code"], {"id": 1, "username": "one"}, correct)
# Пока раунд не закрыт, счёт не меняется: иначе чужая сумма выдаёт ответ.
assert score(room, "one") == before
assert room["phase"] == "round"
wrong = next(index for index in range(4) if index != correct)
room = game.answer(first["code"], {"id": 2, "username": "two"}, wrong)
# Разбор наступает сразу после последнего ответа, без дополнительной паузы.
assert room["phase"] == "reveal" and room["answer"]["anime"]
rows = {item["name"]: item for item in room["players"]}
assert rows["one"]["correct"] is True and rows["one"]["points"] > BASE_POINTS
assert rows["one"]["score"] == before + rows["one"]["points"]
assert rows["one"]["streak"] == 1
assert rows["one"]["spent"] is not None
assert rows["two"]["correct"] is False and rows["two"]["points"] == 0
assert rows["two"]["score"] == 0 and rows["two"]["streak"] == 0
assert rows["two"]["spent"] is not None
room = game.state(first["code"], {"id": 1, "username": "one"})
assert room["you"]["points"] > BASE_POINTS
assert room["you"]["streak"] == 1
print("online ok", room["you"]["points"])

# --- лобби: готовность как в Narutodle ---------------------------------------
alone = game.create({"id": 5, "username": "alone"})
state = game.set_ready(alone["code"], {"id": 5, "username": "alone"}, True)
assert state["phase"] == "waiting" and len(state["players"]) == 1

ready_first = game.create({"id": 3, "username": "ready-one"})
code = ready_first["code"]
game.join(code, {"id": 4, "username": "ready-two"})
state = game.set_ready(code, {"id": 3, "username": "ready-one"}, True)
assert state["phase"] == "waiting" and state["you"]["ready"] is True
assert [item["ready"] for item in state["players"]] == [True, False]
state = game.set_ready(code, {"id": 3, "username": "ready-one"}, False)
assert state["you"]["ready"] is False
state = game.set_ready(code, {"id": 3, "username": "ready-one"}, True)
state = game.set_ready(code, {"id": 4, "username": "ready-two"}, True)
assert state["phase"] == "round"
print("ready ok")

# --- количество песен вводится числом, после партии снова готовность --------
rounds_room = game.create({"id": 6, "username": "rounds-one"})
rounds_code = rounds_room["code"]
game.join(rounds_code, {"id": 7, "username": "rounds-two"})
state = game.set_rounds(rounds_code, {"id": 6, "username": "rounds-one"}, 37)
assert state["rounds_planned"] == 37
state = game.set_rounds(rounds_code, {"id": 6, "username": "rounds-one"}, 1)
assert state["rounds_planned"] == 1
game.set_ready(rounds_code, {"id": 6, "username": "rounds-one"}, True)
state = game.set_ready(rounds_code, {"id": 7, "username": "rounds-two"}, True)
assert state["phase"] == "round"
correct = game._rooms[rounds_code]["round"]["answer_index"]
game.answer(rounds_code, {"id": 6, "username": "rounds-one"}, correct)
game.answer(rounds_code, {"id": 7, "username": "rounds-two"}, correct)
game._rooms[rounds_code]["round"]["reveal_until"] = 0
state = game.state(rounds_code, {"id": 6, "username": "rounds-one"})
assert state["phase"] == "finished"
assert all(not item["ready"] for item in state["players"])
state = game.set_ready(rounds_code, {"id": 6, "username": "rounds-one"}, True)
assert state["phase"] == "finished"
state = game.set_ready(rounds_code, {"id": 7, "username": "rounds-two"}, True)
assert state["phase"] == "round"
print("after-game ready ok")

# --- выбор треков: без недавних повторов и без перекоса в длинные сериалы ----
variety = Songless([track(index, f"Аниме {index % 15}") for index in range(60)],
                   rng=random.Random(11))
picked = [variety._pick_track([])["track_key"] for _ in range(20)]
assert len(set(picked)) == len(picked), "треки не должны повторяться подряд"
print("variety ok", len(set(picked)))

long_series = "Ван-Пис"
balanced = [track(index, long_series) for index in range(20)]
balanced += [track(100 + index, f"Короткое аниме {index}") for index in range(20)]
weighted = Songless(balanced, rng=random.Random(12))
picks = [weighted._pick_track([]) for _ in range(40)]
long_picks = sum(1 for item in picks if item["anime"] == long_series)
assert long_picks <= 10, "сериал с десятками опенингов не должен занимать полнабора"
used_long = [item["track_key"] for item in balanced if item["anime"] == long_series]
assert weighted._pick_track(used_long)["anime"] != long_series
print("balance ok", long_picks)

# --- секретное достижение Re:Zero -------------------------------------------
rows = [
    {"detail": json.dumps([
        {"anime": "Re:Zero. Жизнь с нуля в альтернативном мире", "song": "Redo",
         "track_key": "rezero-op1"},
        {"anime": "Re:Zero. Жизнь с нуля в альтернативном мире", "song": "Paradisus-Paradoxum",
         "track_key": "rezero-op2"},
        {"anime": "Ван-Пис", "song": "We Are!", "track_key": "onepiece-op1"},
    ], ensure_ascii=False)},
]
metrics = songless_metrics_from_runs(rows)
assert metrics["songless_rezero"] == 2
assert metrics["songless_guesses"] == 2
print("rezero achievement ok")

# --- пропуск ожидания следующего раунда в соло -------------------------------
skip_game = Songless([track(index) for index in range(12)], rng=random.Random(21))
skip_user = {"id": 9, "username": "skipper"}
state = skip_game.solo_start(skip_user, 5)
run_id = state["run"]
assert state["phase"] == "round" and state["round"] == 1
# Пока раунд идёт, пропускать нечего: кнопка не должна засчитывать пропуск.
try:
    skip_game.solo_skip(run_id, skip_user)
    raise AssertionError("пропуск во время раунда должен быть запрещён")
except SonglessError:
    pass
state = skip_game.solo_answer(run_id, skip_user, state["correct_choice"])
assert state["phase"] == "reveal" and state["reveal_in"] > 0
state = skip_game.solo_skip(run_id, skip_user)
assert state["phase"] == "round", "после пропуска сразу начинается следующий раунд"
assert state["round"] == 2 and state["reveal_in"] is None
assert state["seconds_left"] is not None
assert state["score"] > 0, "очки предыдущего раунда сохраняются"
print("solo skip ok")

# Три промаха заканчивают заход — пропуск в разборе не должен его продлевать.
finish_game = Songless([track(index) for index in range(12)], rng=random.Random(22))
finish_user = {"id": 10, "username": "finisher"}
state = finish_game.solo_start(finish_user, 0)
finish_run = state["run"]
for _ in range(3):
    wrong = next(index for index in range(4) if index != state["correct_choice"])
    state = finish_game.solo_answer(finish_run, finish_user, wrong)
    state = finish_game.solo_skip(finish_run, finish_user)
assert state["finished"] is True and state["phase"] == "finished"
try:
    finish_game.solo_skip(finish_run, finish_user)
    raise AssertionError("законченный заход пропускать нельзя")
except SonglessError:
    pass
print("solo skip finishes run ok")

print("ALL OK")