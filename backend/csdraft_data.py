# -*- coding: utf-8 -*-
"""Данные для игры «87-0»: составы прошлых турниров по Counter-Strike.

Этот файл — исходный набор для первичного заполнения таблицы `csdraft_packs`
(см. backend/seed_csdraft.py): сервер проверяет её при запуске и, если она
пуста, заливает данные отсюда. Дальше источник правды — база.

Что здесь есть:
    * паки — реальный состав на конкретном турнире: команда, событие, год,
      место, регион, эпоха, карты того маппула и пять игроков;
    * роли игрока из набора ROLE; роль — та, в которой он выступал в этом
      составе (кто-то совмещал, тогда указана основная);
    * оценки AIM (стрельба), CLUTCH (игры в меньшинстве) и IMP (влияние на игру).

**Оценки — игровые, а не официальная статистика.** Они расставлены так, чтобы
сильные составы своей эпохи были сильнее, и чтобы у игроков разных амплуа был
смысл в драфте. Ники игроков, названия команд и турниров — исторические факты
и принадлежат их владельцам; игра некоммерческая и не связана с Valve.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

# Роли в составе. AWP — снайпер, IGL — капитан, остальные — по амплуа.
ROLES: Tuple[str, ...] = ("awp", "igl", "entry", "support", "lurker")

ROLE_LABELS: Dict[str, str] = {
    "awp": "AWP",
    "igl": "IGL",
    "entry": "Энтри",
    "support": "Сапорт",
    "lurker": "Луркер",
}

ERA_LABELS: Dict[str, str] = {
    "legacy": "Легенды (2013–2019)",
    "modern": "Новое время (2020–2025)",
}

# Вес оценок при подсчёте общего рейтинга игрока.
STAT_WEIGHTS: Dict[str, float] = {"aim": 0.45, "clutch": 0.25, "impact": 0.30}

# Паки: (id, команда, событие, год, место, мейджор, регион, эпоха, карты, игроки).
# Игрок: (ник, роль, AIM, CLUTCH, IMP).
PACKS: Tuple[Dict[str, Any], ...] = (
    # ------------------------------------------------------------ 2013–2015
    {
        "id": "nip-dhw2013", "team": "Ninjas in Pyjamas", "event": "DreamHack Winter 2013",
        "year": 2013, "place": "финалист", "major": True, "region": "EU", "era": "legacy",
        "maps": ["Dust2", "Inferno", "Nuke"],
        "players": [
            ("Fifflaren", "awp", 72, 74, 70),
            ("Xizt", "igl", 74, 80, 76),
            ("f0rest", "entry", 88, 84, 86),
            ("friberg", "support", 80, 78, 82),
            ("GeT_RiGhT", "lurker", 90, 92, 91),
        ],
    },
    {
        "id": "fnatic-dhw2013", "team": "Fnatic", "event": "DreamHack Winter 2013",
        "year": 2013, "place": "победитель", "major": True, "region": "EU", "era": "legacy",
        "maps": ["Dust2", "Inferno", "Train"],
        "players": [
            ("JW", "awp", 84, 82, 83),
            ("pronax", "igl", 70, 76, 72),
            ("olofmeister", "entry", 86, 82, 85),
            ("flusha", "support", 88, 90, 89),
            ("KRIMZ", "lurker", 85, 86, 86),
        ],
    },
    {
        "id": "titan-dhw2014", "team": "Titan", "event": "DreamHack Winter 2014",
        "year": 2014, "place": "топ-4", "major": True, "region": "EU", "era": "legacy",
        "maps": ["Cache", "Mirage", "Overpass"],
        "players": [
            ("kennyS", "awp", 91, 84, 88),
            ("Ex6TenZ", "igl", 70, 74, 72),
            ("shox", "lurker", 89, 90, 89),
            ("RpK", "support", 74, 78, 76),
            ("Maniac", "support", 71, 73, 72),
        ],
    },
    {
        "id": "ldlc-dhw2014", "team": "Team LDLC", "event": "DreamHack Winter 2014",
        "year": 2014, "place": "победитель", "major": True, "region": "EU", "era": "legacy",
        "maps": ["Cache", "Inferno", "Overpass"],
        "players": [
            ("SmithZz", "awp", 79, 78, 78),
            ("Happy", "igl", 82, 86, 84),
            ("shox", "lurker", 89, 90, 89),
            ("NBK-", "support", 78, 80, 79),
            ("kioShiMa", "entry", 80, 82, 81),
        ],
    },
    {
        "id": "fnatic-katowice2015", "team": "Fnatic", "event": "ESL One Katowice 2015",
        "year": 2015, "place": "победитель", "major": True, "region": "EU", "era": "legacy",
        "maps": ["Cache", "Cobblestone", "Dust2"],
        "players": [
            ("JW", "awp", 86, 84, 85),
            ("pronax", "igl", 70, 76, 72),
            ("olofmeister", "entry", 92, 88, 91),
            ("flusha", "support", 89, 91, 90),
            ("KRIMZ", "lurker", 86, 87, 87),
        ],
    },
    {
        "id": "envyus-cluj2015", "team": "Team EnVyUs", "event": "DreamHack Cluj-Napoca 2015",
        "year": 2015, "place": "победитель", "major": True, "region": "EU", "era": "legacy",
        "maps": ["Cobblestone", "Mirage", "Train"],
        "players": [
            ("kennyS", "awp", 91, 86, 89),
            ("Happy", "igl", 83, 88, 85),
            ("apEX", "entry", 85, 82, 84),
            ("NBK-", "support", 79, 81, 80),
            ("kioShiMa", "lurker", 80, 83, 81),
        ],
    },
    # ------------------------------------------------------------ 2016–2018
    {
        "id": "lg-columbus2016", "team": "Luminosity Gaming", "event": "MLG Columbus 2016",
        "year": 2016, "place": "победитель", "major": True, "region": "SA", "era": "legacy",
        "maps": ["Cache", "Cobblestone", "Overpass"],
        "players": [
            ("FalleN", "awp", 90, 88, 90),
            ("coldzera", "lurker", 93, 92, 93),
            ("fer", "entry", 88, 84, 87),
            ("fnx", "support", 82, 84, 83),
            ("TACO", "support", 74, 76, 75),
        ],
    },
    {
        "id": "sk-cologne2016", "team": "SK Gaming", "event": "ESL One Cologne 2016",
        "year": 2016, "place": "победитель", "major": True, "region": "SA", "era": "legacy",
        "maps": ["Cache", "Inferno", "Train"],
        "players": [
            ("FalleN", "awp", 91, 89, 91),
            ("coldzera", "lurker", 94, 93, 94),
            ("fer", "entry", 87, 84, 86),
            ("fnx", "support", 82, 83, 83),
            ("TACO", "support", 75, 76, 76),
        ],
    },
    {
        "id": "astralis-atlanta2017", "team": "Astralis", "event": "ELEAGUE Atlanta 2017",
        "year": 2017, "place": "победитель", "major": True, "region": "EU", "era": "legacy",
        "maps": ["Inferno", "Mirage", "Nuke"],
        "players": [
            ("device", "awp", 92, 90, 92),
            ("gla1ve", "igl", 83, 88, 86),
            ("dupreeh", "entry", 88, 86, 88),
            ("Xyp9x", "support", 85, 94, 88),
            ("Kjaerbye", "lurker", 86, 84, 86),
        ],
    },
    {
        "id": "c9-boston2018", "team": "Cloud9", "event": "ELEAGUE Boston 2018",
        "year": 2018, "place": "победитель", "major": True, "region": "NA", "era": "legacy",
        "maps": ["Inferno", "Mirage", "Overpass"],
        "players": [
            ("Skadoodle", "awp", 84, 82, 83),
            ("tarik", "igl", 84, 86, 85),
            ("Stewie2K", "entry", 86, 85, 86),
            ("autimatic", "lurker", 87, 88, 88),
            ("RUSH", "support", 78, 82, 80),
        ],
    },
    {
        "id": "faze-katowice2018", "team": "FaZe Clan", "event": "IEM Katowice 2018",
        "year": 2018, "place": "победитель", "major": False, "region": "EU", "era": "legacy",
        "maps": ["Cache", "Mirage", "Nuke"],
        "players": [
            ("GuardiaN", "awp", 89, 86, 88),
            ("karrigan", "igl", 76, 82, 79),
            ("NiKo", "entry", 93, 90, 92),
            ("rain", "lurker", 86, 88, 87),
            ("olofmeister", "support", 85, 84, 85),
        ],
    },
    {
        "id": "astralis-london2018", "team": "Astralis", "event": "FACEIT London 2018",
        "year": 2018, "place": "победитель", "major": True, "region": "EU", "era": "legacy",
        "maps": ["Inferno", "Nuke", "Overpass"],
        "players": [
            ("device", "awp", 93, 92, 93),
            ("gla1ve", "igl", 85, 90, 88),
            ("dupreeh", "entry", 89, 88, 89),
            ("Xyp9x", "support", 86, 95, 90),
            ("Magisk", "lurker", 88, 88, 88),
        ],
    },
    # ------------------------------------------------------------ 2019
    {
        "id": "astralis-katowice2019", "team": "Astralis", "event": "IEM Katowice 2019",
        "year": 2019, "place": "победитель", "major": True, "region": "EU", "era": "legacy",
        "maps": ["Dust2", "Inferno", "Nuke"],
        "players": [
            ("device", "awp", 94, 93, 94),
            ("gla1ve", "igl", 86, 91, 89),
            ("dupreeh", "entry", 90, 89, 90),
            ("Xyp9x", "support", 87, 96, 91),
            ("Magisk", "lurker", 90, 89, 90),
        ],
    },
    {
        "id": "ence-katowice2019", "team": "ENCE", "event": "IEM Katowice 2019",
        "year": 2019, "place": "финалист", "major": True, "region": "EU", "era": "legacy",
        "maps": ["Inferno", "Train", "Vertigo"],
        "players": [
            ("allu", "awp", 86, 84, 85),
            ("Aleksib", "igl", 78, 84, 81),
            ("sergej", "entry", 88, 86, 87),
            ("Aerial", "support", 78, 80, 79),
            ("xseveN", "lurker", 80, 80, 80),
        ],
    },
    {
        "id": "liquid-cologne2019", "team": "Team Liquid", "event": "ESL One Cologne 2019",
        "year": 2019, "place": "победитель", "major": False, "region": "NA", "era": "legacy",
        "maps": ["Dust2", "Inferno", "Overpass"],
        "players": [
            ("nitr0", "igl", 78, 84, 81),
            ("EliGE", "lurker", 92, 88, 91),
            ("Twistzz", "entry", 90, 86, 89),
            ("NAF", "support", 88, 90, 89),
            ("Stewie2K", "support", 84, 84, 84),
        ],
    },
    {
        "id": "astralis-berlin2019", "team": "Astralis", "event": "StarLadder Berlin 2019",
        "year": 2019, "place": "победитель", "major": True, "region": "EU", "era": "legacy",
        "maps": ["Dust2", "Inferno", "Overpass"],
        "players": [
            ("device", "awp", 93, 92, 93),
            ("gla1ve", "igl", 86, 91, 89),
            ("dupreeh", "entry", 89, 88, 89),
            ("Xyp9x", "support", 86, 95, 90),
            ("Magisk", "lurker", 90, 90, 90),
        ],
    },
    # ------------------------------------------------------------ 2020–2025
    {
        "id": "gambit-katowice2021", "team": "Gambit Esports", "event": "IEM Katowice 2021",
        "year": 2021, "place": "победитель", "major": False, "region": "EEU", "era": "modern",
        "maps": ["Inferno", "Overpass", "Train"],
        "players": [
            ("sh1ro", "awp", 90, 92, 91),
            ("nafany", "igl", 80, 86, 83),
            ("Ax1Le", "entry", 91, 88, 90),
            ("interz", "support", 78, 82, 80),
            ("HObbit", "lurker", 88, 90, 89),
        ],
    },
    {
        "id": "heroic-epl13", "team": "Heroic", "event": "ESL Pro League Season 13",
        "year": 2021, "place": "победитель", "major": False, "region": "EU", "era": "modern",
        "maps": ["Inferno", "Nuke", "Overpass"],
        "players": [
            ("cadiaN", "igl", 84, 88, 86),
            ("stavn", "lurker", 90, 89, 90),
            ("TeSeS", "entry", 84, 84, 84),
            ("sjuush", "support", 80, 82, 81),
            ("refrezh", "support", 82, 86, 84),
        ],
    },
    {
        "id": "navi-stockholm2021", "team": "Natus Vincere", "event": "PGL Stockholm 2021",
        "year": 2021, "place": "победитель", "major": True, "region": "EEU", "era": "modern",
        "maps": ["Ancient", "Dust2", "Nuke"],
        "players": [
            ("s1mple", "awp", 97, 94, 96),
            ("Boombl4", "igl", 80, 84, 82),
            ("electronic", "lurker", 90, 90, 90),
            ("b1t", "entry", 88, 86, 87),
            ("Perfecto", "support", 84, 88, 86),
        ],
    },
    {
        "id": "outsiders-rio2022", "team": "Outsiders", "event": "IEM Rio 2022",
        "year": 2022, "place": "победитель", "major": True, "region": "EEU", "era": "modern",
        "maps": ["Ancient", "Inferno", "Mirage"],
        "players": [
            ("Jame", "awp", 88, 90, 89),
            ("FL1T", "entry", 86, 84, 85),
            ("Qikert", "lurker", 84, 86, 85),
            ("n0rb3r7", "support", 80, 82, 81),
            ("fame", "support", 82, 80, 81),
        ],
    },
    {
        "id": "faze-antwerp2022", "team": "FaZe Clan", "event": "PGL Antwerp 2022",
        "year": 2022, "place": "победитель", "major": True, "region": "EU", "era": "modern",
        "maps": ["Ancient", "Inferno", "Nuke"],
        "players": [
            ("broky", "awp", 88, 90, 89),
            ("karrigan", "igl", 78, 86, 82),
            ("rain", "entry", 86, 88, 87),
            ("Twistzz", "lurker", 89, 88, 89),
            ("ropz", "support", 91, 92, 91),
        ],
    },
    {
        "id": "vitality-paris2023", "team": "Team Vitality", "event": "BLAST Paris Major 2023",
        "year": 2023, "place": "победитель", "major": True, "region": "EU", "era": "modern",
        "maps": ["Anubis", "Inferno", "Vertigo"],
        "players": [
            ("ZywOo", "awp", 96, 93, 95),
            ("apEX", "igl", 80, 86, 83),
            ("Spinx", "entry", 89, 87, 88),
            ("Magisk", "support", 86, 88, 87),
            ("dupreeh", "lurker", 86, 88, 87),
        ],
    },
    {
        "id": "spirit-copenhagen2024", "team": "Team Spirit", "event": "PGL Copenhagen 2024",
        "year": 2024, "place": "победитель", "major": True, "region": "EEU", "era": "modern",
        "maps": ["Ancient", "Anubis", "Mirage"],
        "players": [
            ("donk", "entry", 96, 92, 95),
            ("sh1ro", "awp", 91, 93, 92),
            ("chopper", "igl", 78, 84, 81),
            ("magixx", "support", 84, 86, 85),
            ("zont1x", "lurker", 86, 88, 87),
        ],
    },
    {
        "id": "navi-cologne2024", "team": "Natus Vincere", "event": "IEM Cologne 2024",
        "year": 2024, "place": "победитель", "major": False, "region": "EEU", "era": "modern",
        "maps": ["Ancient", "Inferno", "Nuke"],
        "players": [
            ("w0nderful", "awp", 89, 88, 88),
            ("Aleksib", "igl", 78, 86, 82),
            ("jL", "entry", 88, 90, 89),
            ("b1t", "lurker", 87, 86, 86),
            ("iM", "support", 85, 86, 85),
        ],
    },
    {
        "id": "mouz-katowice2025", "team": "MOUZ", "event": "IEM Katowice 2025",
        "year": 2025, "place": "финалист", "major": False, "region": "EU", "era": "modern",
        "maps": ["Anubis", "Inferno", "Nuke"],
        "players": [
            ("torzsi", "awp", 88, 90, 89),
            ("Brollan", "igl", 82, 84, 83),
            ("Jimpphat", "entry", 86, 84, 85),
            ("xertioN", "lurker", 88, 88, 88),
            ("siuhy", "support", 80, 84, 82),
        ],
    },
    {
        "id": "vitality-austin2025", "team": "Team Vitality", "event": "BLAST Austin 2025",
        "year": 2025, "place": "победитель", "major": True, "region": "EU", "era": "modern",
        "maps": ["Anubis", "Dust2", "Mirage"],
        "players": [
            ("ZywOo", "awp", 96, 94, 95),
            ("apEX", "igl", 80, 86, 83),
            ("ropz", "lurker", 92, 92, 92),
            ("flameZ", "entry", 90, 88, 89),
            ("mezii", "support", 84, 86, 85),
        ],
    },
)

# Известные связки: играли вместе много и хорошо. Даёт надбавку к сыгранности,
# если оба игрока в составе. Сравнение идёт без учёта регистра.
DUOS: Tuple[Tuple[str, str], ...] = (
    ("device", "dupreeh"),
    ("device", "Xyp9x"),
    ("dupreeh", "Xyp9x"),
    ("gla1ve", "dupreeh"),
    ("FalleN", "coldzera"),
    ("FalleN", "fer"),
    ("coldzera", "fer"),
    ("olofmeister", "KRIMZ"),
    ("JW", "flusha"),
    ("kennyS", "apEX"),
    ("shox", "NBK-"),
    ("s1mple", "electronic"),
    ("s1mple", "b1t"),
    ("donk", "sh1ro"),
    ("ZywOo", "apEX"),
    ("ZywOo", "dupreeh"),
    ("NiKo", "rain"),
    ("rain", "karrigan"),
    ("ropz", "karrigan"),
    ("Twistzz", "karrigan"),
    ("stavn", "cadiaN"),
    ("Ax1Le", "sh1ro"),
    ("EliGE", "NAF"),
    ("tarik", "Stewie2K"),
)

# Усилений в «87-0» нет: между стадиями ничего не выбирается, а маппул
# пополняется только картами из паков. Список пустой намеренно.
BOOSTS: Tuple[Dict[str, Any], ...] = ()


def overall(player: Dict[str, Any]) -> float:
    """Общий рейтинг игрока из трёх оценок: 0.45·AIM + 0.25·CLUTCH + 0.30·IMP."""
    total = sum(STAT_WEIGHTS[key] * float(player.get(key) or 0) for key in STAT_WEIGHTS)
    return round(total, 1)


def normalize_pack(pack: Dict[str, Any]) -> Dict[str, Any]:
    """Пак в том виде, в каком его ждёт движок: с посчитанным рейтингом игроков."""
    players = []
    for player in pack.get("players", ()):
        item = dict(player)
        item["aim"] = float(item.get("aim") or 0)
        item["clutch"] = float(item.get("clutch") or 0)
        item["impact"] = float(item.get("impact") or 0)
        item["ovr"] = float(item.get("ovr") or overall(item))
        players.append(item)
    result = dict(pack)
    result["year"] = int(pack.get("year") or 0)
    result["place"] = str(pack.get("place") or "")
    result["region"] = str(pack.get("region") or "")
    result["era"] = str(pack.get("era") or "legacy")
    result["major"] = bool(pack.get("major"))
    result["maps"] = [str(name) for name in pack.get("maps", ())]
    result["players"] = players
    return result


def _player_from_row(row: Any) -> Dict[str, Any]:
    """Игрок из набора: либо кортеж (ник, роль, AIM, CLUTCH, IMP), либо словарь."""
    if isinstance(row, dict):
        return {
            "name": str(row.get("name") or ""),
            "role": str(row.get("role") or ""),
            "aim": float(row.get("aim") or 0),
            "clutch": float(row.get("clutch") or 0),
            "impact": float(row.get("impact") or 0),
        }
    name, role, aim, clutch, impact = row
    return {"name": str(name), "role": str(role), "aim": float(aim),
            "clutch": float(clutch), "impact": float(impact)}


def packs() -> List[Dict[str, Any]]:
    """Набор паков в виде словарей (для движка и проверок)."""
    result: List[Dict[str, Any]] = []
    for row in PACKS:
        pack = {
            "id": str(row["id"]),
            "team": str(row["team"]),
            "event": str(row["event"]),
            "year": int(row["year"]),
            "place": str(row.get("place") or ""),
            "major": bool(row.get("major")),
            "region": str(row.get("region") or ""),
            "era": str(row.get("era") or "legacy"),
            "maps": [str(name) for name in row.get("maps", ())],
            "players": [_player_from_row(player) for player in row.get("players", ())],
        }
        result.append(pack)
    return result


def seed_rows() -> List[Dict[str, Any]]:
    """Паки для записи в базу: без посчитанных рейтингов — их считает движок."""
    rows = []
    for pack in packs():
        rows.append({
            "id": pack["id"],
            "team": pack["team"],
            "event": pack["event"],
            "year": pack["year"],
            "place": pack["place"],
            "major": pack["major"],
            "region": pack["region"],
            "era": pack["era"],
            "maps": list(pack["maps"]),
            "players": [dict(player) for player in pack["players"]],
        })
    return rows


def validate(rows: Iterable[Dict[str, Any]] | None = None) -> List[str]:
    """Проверка набора: уникальные id, известные роли, пять игроков и карты."""
    problems: List[str] = []
    seen = set()
    for pack in (list(rows) if rows is not None else packs()):
        pack_id = str(pack.get("id") or "")
        if not pack_id:
            problems.append("пак без идентификатора")
            continue
        if pack_id in seen:
            problems.append(f"повторяющийся идентификатор: {pack_id}")
        seen.add(pack_id)
        players = pack.get("players") or []
        if len(players) != 5:
            problems.append(f"{pack_id}: игроков {len(players)}, а нужно 5")
        for player in players:
            if player.get("role") not in ROLES:
                problems.append(f"{pack_id}: неизвестная роль у {player.get('name')}")
        if not pack.get("maps"):
            problems.append(f"{pack_id}: не указаны карты")
    return problems
