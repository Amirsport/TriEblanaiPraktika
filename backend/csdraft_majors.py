# -*- coding: utf-8 -*-
"""Составы участников мейджоров 2013–2026 для игры «87-0».

Это второй, массовый набор паков: по одному пакету на каждое выступление команды
на мейджоре. Он дополняет небольшой выверенный набор из `csdraft_data.py`, не
дублируя его: паки, уже описанные там вручную, сюда не заносятся.

Как устроены данные:

    * список `EVENTS` — мейджоры по годам: название, год, эпоха, место и состав
      каждой команды (ник и роль, в которой игрок выступал в том составе);
    * карты пака берутся из маппула года (`YEAR_MAPS`) — три карты, детерминиро-
      ванно зависящие от команды, чтобы у составов были разные пулы;
    * оценки AIM/CLUTCH/IMP считаются по правилу (`PLACE_POWER`, `ROLE_SHIFT`
      и небольшая детерминированная поправка) — это игровые оценки для баланса,
      а не официальная статистика. Сильнее тот, кто на турнире выступил выше.

Честно про источник: список команд и ники собраны по памяти и требуют проверки.
Паки, в которых возможна неточность (стендин, спорная роль, границы состава),
помечены комментарием «проверить». Ники игроков, названия команд и турниров —
исторические факты и принадлежат их владельцам; игра некоммерческая и не связана
с Valve.
"""
from __future__ import annotations

import zlib
from typing import Any, Dict, List, Tuple

# Маппул года: у каждой команды свои три карты из этого набора.
YEAR_MAPS: Dict[int, Tuple[str, ...]] = {
    2013: ("Dust2", "Inferno", "Nuke", "Train", "Mirage"),
    2014: ("Dust2", "Inferno", "Nuke", "Mirage", "Cache", "Overpass", "Cobblestone"),
    2015: ("Dust2", "Inferno", "Mirage", "Cache", "Overpass", "Cobblestone", "Train"),
    2016: ("Dust2", "Mirage", "Cache", "Overpass", "Cobblestone", "Train", "Nuke"),
    2017: ("Mirage", "Cache", "Overpass", "Cobblestone", "Train", "Nuke", "Inferno"),
    2018: ("Mirage", "Inferno", "Cache", "Overpass", "Train", "Nuke", "Dust2"),
    2019: ("Mirage", "Inferno", "Overpass", "Train", "Nuke", "Dust2", "Vertigo"),
    2021: ("Mirage", "Inferno", "Overpass", "Nuke", "Dust2", "Vertigo", "Ancient"),
    2022: ("Mirage", "Inferno", "Overpass", "Nuke", "Dust2", "Vertigo", "Ancient"),
    2023: ("Mirage", "Inferno", "Overpass", "Nuke", "Dust2", "Vertigo", "Ancient", "Anubis"),
    2024: ("Mirage", "Inferno", "Overpass", "Nuke", "Dust2", "Vertigo", "Ancient", "Anubis"),
    2025: ("Mirage", "Inferno", "Nuke", "Dust2", "Ancient", "Anubis", "Train"),
    2026: ("Mirage", "Inferno", "Nuke", "Dust2", "Ancient", "Anubis", "Train"),
}

# Место на турнире — это базовая сила состава.
PLACE_POWER: Dict[str, float] = {
    "победитель": 89.0,
    "финалист": 86.0,
    "топ-4": 84.0,
    "топ-8": 82.0,
    "топ-12": 80.0,
    "группа": 78.0,
}

# Роль сдвигает оценки: у снайпера выше стрельба, у капитана — влияние, и так далее.
ROLE_SHIFT: Dict[str, Tuple[float, float, float]] = {
    "awp": (3.0, -1.0, 1.0),
    "igl": (-5.0, 1.5, -1.5),
    "entry": (1.5, -1.0, 2.0),
    "support": (-1.5, 1.5, 0.0),
    "lurker": (1.0, 1.5, 1.0),
}

# Мейджоры: (событие, год, эпоха, команды). Команда: (название, регион, место,
# игроки). Игрок: (ник, роль).
EVENTS: Tuple[Dict[str, Any], ...] = (
    # ------------------------------------------------------------------ 2013
    {
        "event": "DreamHack Winter 2013, Jönköping",
        "year": 2013,
        "era": "legacy",
        "teams": (
            ("Fnatic", "EU", "победитель", (
                ("JW", "awp"), ("pronax", "igl"), ("flusha", "support"),
                ("schneider", "entry"), ("Devilwalk", "lurker"),
            )),
            ("Ninjas in Pyjamas", "EU", "финалист", (
                ("Fifflaren", "awp"), ("Xizt", "igl"), ("f0rest", "entry"),
                ("friberg", "support"), ("GeT_RiGhT", "lurker"),
            )),
            ("VeryGames", "EU", "топ-4", (
                ("SmithZz", "awp"), ("Ex6TenZ", "igl"), ("ScreaM", "entry"),
                ("NBK-", "support"), ("shox", "lurker"),
            )),
            ("compLexity", "NA", "топ-8", (  # проверить состав
                ("swag", "awp"), ("semphis", "igl"), ("n0thing", "entry"),
                ("Hiko", "lurker"), ("fRoD", "support"),
            )),
            ("Astana Dragons", "CIS", "топ-8", (
                ("markeloff", "awp"), ("ANGE1", "igl"), ("Dosia", "lurker"),
                ("AdreN", "entry"), ("kUcheR", "support"),
            )),
            ("Universal Soldiers", "EU", "топ-8", (
                ("pashaBiceps", "awp"), ("NEO", "igl"), ("Snax", "entry"),
                ("TaZ", "support"), ("byali", "lurker"),
            )),
            ("LGB eSports", "EU", "группа", (  # проверить состав
                ("twist", "awp"), ("zende", "igl"), ("olofmeister", "entry"),
                ("KRIMZ", "support"), ("dennis", "lurker"),
            )),
            ("Team Dignitas", "EU", "группа", (  # проверить состав
                ("device", "awp"), ("FeTiSh", "igl"), ("dupreeh", "entry"),
                ("Xyp9x", "support"), ("3k2", "lurker"),
            )),
            ("iBUYPOWER", "NA", "группа", (  # проверить состав
                ("Skadoodle", "awp"), ("DaZeD", "igl"), ("swag", "entry"),
                ("Steel", "lurker"), ("AZK", "support"),
            )),
        ),
    },
    {
        "event": "EMS One Katowice 2014",
        "year": 2014,
        "era": "legacy",
        "teams": (
            ("Virtus.pro", "EU", "победитель", (
                ("pashaBiceps", "awp"), ("NEO", "igl"), ("Snax", "entry"),
                ("TaZ", "support"), ("byali", "lurker"),
            )),
            ("Ninjas in Pyjamas", "EU", "финалист", (
                ("Fifflaren", "awp"), ("Xizt", "igl"), ("f0rest", "entry"),
                ("friberg", "support"), ("GeT_RiGhT", "lurker"),
            )),
            ("Team Dignitas", "EU", "топ-4", (  # проверить состав
                ("device", "awp"), ("FeTiSh", "igl"), ("dupreeh", "entry"),
                ("Xyp9x", "support"), ("3k2", "lurker"),
            )),
            ("LGB eSports", "EU", "топ-4", (  # проверить состав
                ("twist", "awp"), ("zende", "igl"), ("olofmeister", "entry"),
                ("KRIMZ", "support"), ("dennis", "lurker"),
            )),
            ("Titan", "EU", "топ-8", (
                ("kennyS", "awp"), ("Ex6TenZ", "igl"), ("ScreaM", "entry"),
                ("NBK-", "support"), ("shox", "lurker"),
            )),
            ("Natus Vincere", "CIS", "группа", (  # проверить состав
                ("GuardiaN", "awp"), ("Zeus", "igl"), ("Edward", "entry"),
                ("seized", "support"), ("starix", "lurker"),
            )),
            ("Fnatic", "EU", "группа", (  # проверить состав
                ("JW", "awp"), ("pronax", "igl"), ("flusha", "support"),
                ("schneider", "entry"), ("Devilwalk", "lurker"),
            )),
            ("HellRaisers", "CIS", "группа", (  # проверить состав
                ("markeloff", "awp"), ("ANGE1", "igl"), ("Dosia", "lurker"),
                ("AdreN", "entry"), ("kUcheR", "support"),
            )),
            ("mousesports", "EU", "группа", (  # проверить состав
                ("chrisJ", "awp"), ("tabseN", "igl"), ("LEGIJA", "entry"),
                ("gob b", "support"), ("nex", "lurker"),
            )),
            ("iBUYPOWER", "NA", "группа", (  # проверить состав
                ("Skadoodle", "awp"), ("DaZeD", "igl"), ("swag", "entry"),
                ("Steel", "lurker"), ("AZK", "support"),
            )),
            ("Vox Eminor", "AU", "группа", (  # проверить состав
                ("SPUNJ", "awp"), ("AZR", "igl"), ("jks", "lurker"),
                ("Rickeh", "entry"), ("USTILO", "support"),
            )),
        ),
    },
    {
        "event": "ESL One Cologne 2014",
        "year": 2014,
        "era": "legacy",
        "teams": (
            ("Ninjas in Pyjamas", "EU", "победитель", (
                ("Fifflaren", "awp"), ("Xizt", "igl"), ("f0rest", "entry"),
                ("friberg", "support"), ("GeT_RiGhT", "lurker"),
            )),
            ("Fnatic", "EU", "финалист", (
                ("JW", "awp"), ("pronax", "igl"), ("flusha", "support"),
                ("olofmeister", "entry"), ("KRIMZ", "lurker"),
            )),
            ("Team LDLC", "EU", "топ-4", (
                ("SmithZz", "awp"), ("Happy", "igl"), ("kioShiMa", "entry"),
                ("NBK-", "support"), ("shox", "lurker"),
            )),
            ("Cloud9", "NA", "топ-4", (  # проверить состав
                ("n0thing", "awp"), ("semphis", "igl"), ("Hiko", "lurker"),
                ("shroud", "entry"), ("seang@res", "support"),
            )),
            ("Virtus.pro", "EU", "топ-8", (
                ("pashaBiceps", "awp"), ("NEO", "igl"), ("Snax", "entry"),
                ("TaZ", "support"), ("byali", "lurker"),
            )),
            ("Team Dignitas", "EU", "топ-8", (  # проверить состав
                ("device", "awp"), ("FeTiSh", "igl"), ("dupreeh", "entry"),
                ("Xyp9x", "support"), ("cajunb", "lurker"),
            )),
            ("Natus Vincere", "CIS", "топ-8", (  # проверить состав
                ("GuardiaN", "awp"), ("Zeus", "igl"), ("Edward", "entry"),
                ("seized", "support"), ("starix", "lurker"),
            )),
            ("Epsilon eSports", "EU", "группа", (  # проверить состав
                ("Maikelele", "awp"), ("schneider", "igl"), ("jkaem", "entry"),
                ("rain", "support"), ("RUBINO", "lurker"),
            )),
            ("dAT Team", "EU", "группа", (  # проверить состав
                ("chrisJ", "awp"), ("gob b", "igl"), ("LEGIJA", "entry"),
                ("tabseN", "support"), ("nex", "lurker"),
            )),
            ("iBUYPOWER", "NA", "группа", (  # проверить состав
                ("Skadoodle", "awp"), ("DaZeD", "igl"), ("swag", "entry"),
                ("Steel", "lurker"), ("AZK", "support"),
            )),
        ),
    },
    {
        "event": "DreamHack Winter 2014, Jönköping",
        "year": 2014,
        "era": "legacy",
        "teams": (
            ("Team LDLC", "EU", "победитель", (
                ("SmithZz", "awp"), ("Happy", "igl"), ("kioShiMa", "entry"),
                ("NBK-", "support"), ("shox", "lurker"),
            )),
            ("Ninjas in Pyjamas", "EU", "финалист", (
                ("Maikelele", "awp"), ("Xizt", "igl"), ("f0rest", "entry"),
                ("friberg", "support"), ("GeT_RiGhT", "lurker"),
            )),
            ("Virtus.pro", "EU", "топ-4", (
                ("pashaBiceps", "awp"), ("NEO", "igl"), ("Snax", "entry"),
                ("TaZ", "support"), ("byali", "lurker"),
            )),
            ("Cloud9", "NA", "топ-4", (  # проверить состав
                ("n0thing", "awp"), ("semphis", "igl"), ("Hiko", "lurker"),
                ("shroud", "entry"), ("seang@res", "support"),
            )),
            ("Fnatic", "EU", "топ-8", (  # проверить состав: четвертьфинал с LDLC
                ("JW", "awp"), ("pronax", "igl"), ("flusha", "support"),
                ("olofmeister", "entry"), ("KRIMZ", "lurker"),
            )),
            ("Team Dignitas", "EU", "топ-8", (  # проверить состав
                ("device", "awp"), ("FeTiSh", "igl"), ("dupreeh", "entry"),
                ("Xyp9x", "support"), ("cajunb", "lurker"),
            )),
            ("Natus Vincere", "CIS", "группа", (  # проверить состав
                ("GuardiaN", "awp"), ("Zeus", "igl"), ("Edward", "entry"),
                ("seized", "support"), ("starix", "lurker"),
            )),
            ("HellRaisers", "CIS", "группа", (  # проверить состав
                ("markeloff", "awp"), ("ANGE1", "igl"), ("Dosia", "lurker"),
                ("AdreN", "entry"), ("kUcheR", "support"),
            )),
            ("mousesports", "EU", "группа", (  # проверить состав
                ("chrisJ", "awp"), ("tabseN", "igl"), ("LEGIJA", "entry"),
                ("gob b", "support"), ("nex", "lurker"),
            )),
        ),
    },
    # ------------------------------------------------------------------ 2015
    {
        "event": "ESL One Katowice 2015",
        "year": 2015,
        "era": "legacy",
        "teams": (
            ("Fnatic", "EU", "победитель", (
                ("JW", "awp"), ("pronax", "igl"), ("flusha", "support"),
                ("olofmeister", "entry"), ("KRIMZ", "lurker"),
            )),
            ("Ninjas in Pyjamas", "EU", "финалист", (
                ("allu", "awp"), ("Xizt", "igl"), ("f0rest", "entry"),
                ("friberg", "support"), ("GeT_RiGhT", "lurker"),
            )),
            ("Virtus.pro", "EU", "топ-4", (
                ("pashaBiceps", "awp"), ("NEO", "igl"), ("Snax", "entry"),
                ("TaZ", "support"), ("byali", "lurker"),
            )),
            ("Team EnVyUs", "EU", "топ-4", (
                ("kennyS", "awp"), ("Happy", "igl"), ("apEX", "entry"),
                ("NBK-", "support"), ("kioShiMa", "lurker"),
            )),
            ("Team SoloMid", "EU", "топ-8", (
                ("device", "awp"), ("karrigan", "igl"), ("dupreeh", "entry"),
                ("Xyp9x", "support"), ("cajunb", "lurker"),
            )),
            ("Natus Vincere", "CIS", "топ-8", (
                ("GuardiaN", "awp"), ("Zeus", "igl"), ("Edward", "entry"),
                ("seized", "support"), ("flamie", "lurker"),
            )),
            ("Cloud9", "NA", "топ-8", (  # проверить состав
                ("ShahZaM", "awp"), ("seang@res", "igl"), ("shroud", "entry"),
                ("n0thing", "support"), ("semphis", "lurker"),
            )),
            ("Counter Logic Gaming", "NA", "топ-8", (  # проверить состав
                ("jdm64", "awp"), ("hazed", "igl"), ("tarik", "entry"),
                ("Cutler", "support"), ("FNS", "lurker"),
            )),
            ("Vox Eminor", "AU", "группа", (  # проверить состав
                ("SPUNJ", "awp"), ("AZR", "igl"), ("jks", "lurker"),
                ("Rickeh", "entry"), ("USTILO", "support"),
            )),
            ("LGB eSports", "EU", "группа", (  # проверить состав
                ("jkaem", "awp"), ("RUBINO", "igl"), ("rain", "entry"),
                ("Maikelele", "support"), ("Polly", "lurker"),
            )),
        ),
    },
    {
        "event": "ESL One Cologne 2015",
        "year": 2015,
        "era": "legacy",
        "teams": (
            ("Fnatic", "EU", "победитель", (
                ("JW", "awp"), ("pronax", "igl"), ("flusha", "support"),
                ("olofmeister", "entry"), ("KRIMZ", "lurker"),
            )),
            ("Team EnVyUs", "EU", "финалист", (
                ("kennyS", "awp"), ("Happy", "igl"), ("apEX", "entry"),
                ("NBK-", "support"), ("kioShiMa", "lurker"),
            )),
            ("Virtus.pro", "EU", "топ-4", (
                ("pashaBiceps", "awp"), ("NEO", "igl"), ("Snax", "entry"),
                ("TaZ", "support"), ("byali", "lurker"),
            )),
            ("Team SoloMid", "EU", "топ-4", (
                ("device", "awp"), ("karrigan", "igl"), ("dupreeh", "entry"),
                ("Xyp9x", "support"), ("cajunb", "lurker"),
            )),
            ("Natus Vincere", "CIS", "топ-8", (
                ("GuardiaN", "awp"), ("Zeus", "igl"), ("Edward", "entry"),
                ("seized", "support"), ("flamie", "lurker"),
            )),
            ("Ninjas in Pyjamas", "EU", "топ-8", (
                ("allu", "awp"), ("Xizt", "igl"), ("f0rest", "entry"),
                ("friberg", "support"), ("GeT_RiGhT", "lurker"),
            )),
            ("Cloud9", "NA", "топ-8", (  # проверить состав
                ("Skadoodle", "awp"), ("n0thing", "igl"), ("shroud", "entry"),
                ("fREAKAZOiD", "support"), ("seang@res", "lurker"),
            )),
            ("Team Kinguin", "EU", "топ-8", (  # проверить состав
                ("Maikelele", "awp"), ("dennis", "igl"), ("ScreaM", "entry"),
                ("rain", "support"), ("fox", "lurker"),
            )),
            ("Counter Logic Gaming", "NA", "группа", (  # проверить состав
                ("jdm64", "awp"), ("hazed", "igl"), ("tarik", "entry"),
                ("Cutler", "support"), ("FNS", "lurker"),
            )),
            ("Luminosity Gaming", "BR", "группа", (  # проверить состав
                ("FalleN", "awp"), ("steel", "igl"), ("fer", "entry"),
                ("coldzera", "lurker"), ("boltz", "support"),
            )),
            ("Renegades", "AU", "группа", (  # проверить состав
                ("SPUNJ", "awp"), ("AZR", "igl"), ("jks", "lurker"),
                ("Rickeh", "entry"), ("USTILO", "support"),
            )),
        ),
    },
    {
        "event": "DreamHack Open Cluj-Napoca 2015",
        "year": 2015,
        "era": "legacy",
        "teams": (
            ("Team EnVyUs", "EU", "победитель", (
                ("kennyS", "awp"), ("Happy", "igl"), ("apEX", "entry"),
                ("NBK-", "support"), ("kioShiMa", "lurker"),
            )),
            ("Natus Vincere", "CIS", "финалист", (
                ("GuardiaN", "awp"), ("Zeus", "igl"), ("Edward", "entry"),
                ("seized", "support"), ("flamie", "lurker"),
            )),
            ("Ninjas in Pyjamas", "EU", "топ-4", (
                ("allu", "awp"), ("Xizt", "igl"), ("f0rest", "entry"),
                ("friberg", "support"), ("GeT_RiGhT", "lurker"),
            )),
            ("G2 Esports", "EU", "топ-4", (  # проверить состав
                ("Maikelele", "awp"), ("dennis", "igl"), ("ScreaM", "entry"),
                ("rain", "support"), ("fox", "lurker"),
            )),
            ("Fnatic", "EU", "топ-8", (  # проверить состав: pronax или dennis
                ("JW", "awp"), ("pronax", "igl"), ("flusha", "support"),
                ("olofmeister", "entry"), ("KRIMZ", "lurker"),
            )),
            ("Virtus.pro", "EU", "топ-8", (
                ("pashaBiceps", "awp"), ("NEO", "igl"), ("Snax", "entry"),
                ("TaZ", "support"), ("byali", "lurker"),
            )),
            ("Team SoloMid", "EU", "топ-8", (
                ("device", "awp"), ("karrigan", "igl"), ("dupreeh", "entry"),
                ("Xyp9x", "support"), ("cajunb", "lurker"),
            )),
            ("Cloud9", "NA", "группа", (  # проверить состав
                ("Skadoodle", "awp"), ("n0thing", "igl"), ("shroud", "entry"),
                ("fREAKAZOiD", "support"), ("seang@res", "lurker"),
            )),
            ("Luminosity Gaming", "BR", "группа", (  # проверить состав
                ("FalleN", "awp"), ("steel", "igl"), ("fer", "entry"),
                ("coldzera", "lurker"), ("boltz", "support"),
            )),
            ("Team Liquid", "NA", "группа", (  # проверить состав
                ("adreN", "awp"), ("Hiko", "igl"), ("EliGE", "entry"),
                ("nitr0", "support"), ("FugLy", "lurker"),
            )),
        ),
    },
    # ------------------------------------------------------------------ 2016
    {
        "event": "MLG Columbus 2016",
        "year": 2016,
        "era": "legacy",
        "teams": (
            ("Luminosity Gaming", "BR", "победитель", (
                ("FalleN", "awp"), ("fnx", "igl"), ("fer", "entry"),
                ("TACO", "support"), ("coldzera", "lurker"),
            )),
            ("Natus Vincere", "CIS", "финалист", (
                ("GuardiaN", "awp"), ("Zeus", "igl"), ("Edward", "entry"),
                ("seized", "support"), ("flamie", "lurker"),
            )),
            ("Astralis", "EU", "топ-4", (
                ("device", "awp"), ("karrigan", "igl"), ("dupreeh", "entry"),
                ("Xyp9x", "support"), ("Kjaerbye", "lurker"),
            )),
            ("Team Liquid", "NA", "топ-4", (  # проверить состав
                ("s1mple", "awp"), ("Hiko", "igl"), ("EliGE", "entry"),
                ("nitr0", "support"), ("adreN", "lurker"),
            )),
            ("Fnatic", "EU", "топ-8", (  # проверить состав
                ("JW", "awp"), ("dennis", "igl"), ("flusha", "support"),
                ("olofmeister", "entry"), ("KRIMZ", "lurker"),
            )),
            ("Virtus.pro", "EU", "топ-8", (
                ("pashaBiceps", "awp"), ("NEO", "igl"), ("Snax", "entry"),
                ("TaZ", "support"), ("byali", "lurker"),
            )),
            ("Ninjas in Pyjamas", "EU", "топ-8", (
                ("allu", "awp"), ("Xizt", "igl"), ("f0rest", "entry"),
                ("friberg", "support"), ("GeT_RiGhT", "lurker"),
            )),
            ("mousesports", "EU", "группа", (  # проверить состав
                ("chrisJ", "awp"), ("NiKo", "igl"), ("denis", "entry"),
                ("Spiidi", "support"), ("nex", "lurker"),
            )),
            ("G2 Esports", "EU", "группа", (  # проверить состав
                ("SmithZz", "awp"), ("shox", "igl"), ("ScreaM", "entry"),
                ("RpK", "support"), ("bodyy", "lurker"),
            )),
            ("Cloud9", "NA", "группа", (  # проверить состав
                ("Skadoodle", "awp"), ("n0thing", "igl"), ("shroud", "entry"),
                ("fREAKAZOiD", "support"), ("Stewie2K", "lurker"),
            )),
        ),
    },
    {
        "event": "ESL One Cologne 2016",
        "year": 2016,
        "era": "legacy",
        "teams": (
            ("SK Gaming", "BR", "победитель", (
                ("FalleN", "awp"), ("fnx", "igl"), ("fer", "entry"),
                ("TACO", "support"), ("coldzera", "lurker"),
            )),
            ("Team Liquid", "NA", "финалист", (  # проверить состав
                ("s1mple", "awp"), ("Hiko", "igl"), ("EliGE", "entry"),
                ("nitr0", "support"), ("adreN", "lurker"),
            )),
            ("Astralis", "EU", "топ-4", (
                ("device", "awp"), ("karrigan", "igl"), ("dupreeh", "entry"),
                ("Xyp9x", "support"), ("Kjaerbye", "lurker"),
            )),
            ("Natus Vincere", "CIS", "топ-4", (
                ("GuardiaN", "awp"), ("Zeus", "igl"), ("Edward", "entry"),
                ("seized", "support"), ("flamie", "lurker"),
            )),
            ("Fnatic", "EU", "топ-8", (
                ("JW", "awp"), ("dennis", "igl"), ("flusha", "support"),
                ("olofmeister", "entry"), ("KRIMZ", "lurker"),
            )),
            ("Ninjas in Pyjamas", "EU", "топ-8", (
                ("allu", "awp"), ("Xizt", "igl"), ("f0rest", "entry"),
                ("friberg", "support"), ("GeT_RiGhT", "lurker"),
            )),
            ("G2 Esports", "EU", "топ-8", (
                ("SmithZz", "awp"), ("shox", "igl"), ("ScreaM", "entry"),
                ("RpK", "support"), ("bodyy", "lurker"),
            )),
            ("Virtus.pro", "EU", "топ-8", (
                ("pashaBiceps", "awp"), ("NEO", "igl"), ("Snax", "entry"),
                ("TaZ", "support"), ("byali", "lurker"),
            )),
            ("FaZe Clan", "EU", "группа", (  # проверить состав
                ("fox", "awp"), ("kioShiMa", "igl"), ("rain", "entry"),
                ("aizy", "support"), ("Maikelele", "lurker"),
            )),
            ("Gambit Gaming", "CIS", "группа", (  # проверить состав
                ("mou", "awp"), ("Dosia", "igl"), ("AdreN", "entry"),
                ("HObbit", "lurker"), ("wayLander", "support"),
            )),
            ("mousesports", "EU", "группа", (  # проверить состав
                ("chrisJ", "awp"), ("NiKo", "igl"), ("denis", "entry"),
                ("Spiidi", "support"), ("nex", "lurker"),
            )),
            ("Cloud9", "NA", "группа", (  # проверить состав
                ("Skadoodle", "awp"), ("n0thing", "igl"), ("shroud", "entry"),
                ("fREAKAZOiD", "support"), ("Stewie2K", "lurker"),
            )),
        ),
    },
    # ------------------------------------------------------------------ 2017
    {
        "event": "ELEAGUE Atlanta 2017",
        "year": 2017,
        "era": "legacy",
        "teams": (
            ("Astralis", "EU", "победитель", (
                ("device", "awp"), ("gla1ve", "igl"), ("dupreeh", "entry"),
                ("Xyp9x", "support"), ("Kjaerbye", "lurker"),
            )),
            ("Virtus.pro", "EU", "финалист", (
                ("pashaBiceps", "awp"), ("NEO", "igl"), ("Snax", "entry"),
                ("TaZ", "support"), ("byali", "lurker"),
            )),
            ("Fnatic", "EU", "топ-4", (
                ("JW", "awp"), ("dennis", "igl"), ("flusha", "support"),
                ("olofmeister", "entry"), ("KRIMZ", "lurker"),
            )),
            ("SK Gaming", "BR", "топ-4", (
                ("FalleN", "awp"), ("fnx", "igl"), ("fer", "entry"),
                ("TACO", "support"), ("coldzera", "lurker"),
            )),
            ("Natus Vincere", "CIS", "топ-8", (
                ("GuardiaN", "awp"), ("seized", "igl"), ("flamie", "entry"),
                ("Edward", "support"), ("s1mple", "lurker"),
            )),
            ("North", "EU", "топ-8", (  # проверить состав
                ("cajunb", "awp"), ("MSL", "igl"), ("k0nfig", "entry"),
                ("Magisk", "support"), ("valde", "lurker"),
            )),
            ("Gambit Gaming", "CIS", "топ-8", (  # проверить состав
                ("mou", "awp"), ("Dosia", "igl"), ("AdreN", "entry"),
                ("HObbit", "lurker"), ("Zeus", "support"),
            )),
            ("FaZe Clan", "EU", "топ-8", (  # проверить состав
                ("allu", "awp"), ("karrigan", "igl"), ("rain", "entry"),
                ("kioShiMa", "support"), ("aizy", "lurker"),
            )),
            ("OpTic Gaming", "NA", "группа", (  # проверить состав
                ("mixwell", "awp"), ("stanislaw", "igl"), ("RUSH", "entry"),
                ("NAF", "support"), ("tarik", "lurker"),
            )),
            ("G2 Esports", "EU", "группа", (  # проверить состав
                ("kennyS", "awp"), ("shox", "igl"), ("apEX", "entry"),
                ("NBK-", "support"), ("bodyy", "lurker"),
            )),
        ),
    },
    {
        "event": "PGL Kraków 2017",
        "year": 2017,
        "era": "legacy",
        "teams": (
            ("Gambit Gaming", "CIS", "победитель", (
                ("mou", "awp"), ("Zeus", "igl"), ("AdreN", "entry"),
                ("HObbit", "support"), ("Dosia", "lurker"),
            )),
            ("Immortals", "BR", "финалист", (  # проверить состав
                ("HEN1", "awp"), ("steel", "igl"), ("kNgV-", "entry"),
                ("boltz", "support"), ("LUCAS1", "lurker"),
            )),
            ("Astralis", "EU", "топ-4", (
                ("device", "awp"), ("gla1ve", "igl"), ("dupreeh", "entry"),
                ("Xyp9x", "support"), ("Kjaerbye", "lurker"),
            )),
            ("SK Gaming", "BR", "топ-8", (
                ("FalleN", "awp"), ("felps", "igl"), ("fer", "entry"),
                ("TACO", "support"), ("coldzera", "lurker"),
            )),
            ("Fnatic", "EU", "топ-8", (
                ("JW", "awp"), ("dennis", "igl"), ("flusha", "support"),
                ("olofmeister", "entry"), ("KRIMZ", "lurker"),
            )),
            ("Virtus.pro", "EU", "топ-8", (
                ("pashaBiceps", "awp"), ("NEO", "igl"), ("Snax", "entry"),
                ("TaZ", "support"), ("byali", "lurker"),
            )),
            ("FaZe Clan", "EU", "топ-8", (  # проверить состав
                ("kioShiMa", "awp"), ("karrigan", "igl"), ("NiKo", "entry"),
                ("rain", "support"), ("aizy", "lurker"),
            )),
            ("Cloud9", "NA", "группа", (  # проверить состав
                ("Skadoodle", "awp"), ("n0thing", "igl"), ("Stewie2K", "entry"),
                ("autimatic", "support"), ("shroud", "lurker"),
            )),
            ("G2 Esports", "EU", "группа", (
                ("kennyS", "awp"), ("shox", "igl"), ("apEX", "entry"),
                ("NBK-", "support"), ("bodyy", "lurker"),
            )),
            ("mousesports", "EU", "группа", (  # проверить состав
                ("oskar", "awp"), ("chrisJ", "igl"), ("ropz", "entry"),
                ("STYKO", "support"), ("suNny", "lurker"),
            )),
        ),
    },
    # ------------------------------------------------------------------ 2018
    {
        "event": "ELEAGUE Boston 2018",
        "year": 2018,
        "era": "legacy",
        "teams": (
            ("Cloud9", "NA", "победитель", (
                ("Skadoodle", "awp"), ("tarik", "igl"), ("Stewie2K", "entry"),
                ("autimatic", "support"), ("RUSH", "lurker"),
            )),
            ("FaZe Clan", "EU", "финалист", (
                ("GuardiaN", "awp"), ("karrigan", "igl"), ("NiKo", "entry"),
                ("rain", "support"), ("olofmeister", "lurker"),
            )),
            ("Natus Vincere", "CIS", "топ-4", (
                ("s1mple", "awp"), ("Zeus", "igl"), ("flamie", "entry"),
                ("Edward", "support"), ("electronic", "lurker"),
            )),
            ("SK Gaming", "BR", "топ-4", (  # проверить состав
                ("FalleN", "awp"), ("boltz", "igl"), ("fer", "entry"),
                ("TACO", "support"), ("coldzera", "lurker"),
            )),
            ("Quantum Bellator Fire", "CIS", "топ-8", (  # проверить состав
                ("waterfaLLZ", "awp"), ("Boombl4", "igl"), ("jmqa", "entry"),
                ("Balblna", "support"), ("KrizzeN", "lurker"),
            )),
            ("G2 Esports", "EU", "топ-8", (
                ("kennyS", "awp"), ("shox", "igl"), ("apEX", "entry"),
                ("NBK-", "support"), ("bodyy", "lurker"),
            )),
            ("Astralis", "EU", "топ-8", (  # проверить состав: Kjaerbye или Magisk
                ("device", "awp"), ("gla1ve", "igl"), ("dupreeh", "entry"),
                ("Xyp9x", "support"), ("Kjaerbye", "lurker"),
            )),
            ("mousesports", "EU", "топ-8", (  # проверить состав
                ("oskar", "awp"), ("chrisJ", "igl"), ("ropz", "entry"),
                ("STYKO", "support"), ("suNny", "lurker"),
            )),
            ("Team Liquid", "NA", "группа", (  # проверить состав
                ("nitr0", "awp"), ("steel", "igl"), ("EliGE", "entry"),
                ("NAF", "support"), ("Twistzz", "lurker"),
            )),
            ("Gambit Gaming", "CIS", "группа", (  # проверить состав
                ("mou", "awp"), ("Dosia", "igl"), ("AdreN", "entry"),
                ("HObbit", "support"), ("fitch", "lurker"),
            )),
        ),
    },
    {
        "event": "FACEIT London 2018",
        "year": 2018,
        "era": "legacy",
        "teams": (
            ("Astralis", "EU", "победитель", (
                ("device", "awp"), ("gla1ve", "igl"), ("dupreeh", "entry"),
                ("Xyp9x", "support"), ("Magisk", "lurker"),
            )),
            ("Natus Vincere", "CIS", "финалист", (
                ("s1mple", "awp"), ("Zeus", "igl"), ("flamie", "entry"),
                ("Edward", "support"), ("electronic", "lurker"),
            )),
            ("Team Liquid", "NA", "топ-4", (  # проверить состав
                ("TACO", "awp"), ("nitr0", "igl"), ("EliGE", "entry"),
                ("NAF", "support"), ("Twistzz", "lurker"),
            )),
            ("MIBR", "BR", "топ-4", (  # проверить состав
                ("FalleN", "awp"), ("Stewie2K", "igl"), ("fer", "entry"),
                ("tarik", "support"), ("coldzera", "lurker"),
            )),
            ("FaZe Clan", "EU", "топ-8", (  # проверить состав
                ("GuardiaN", "awp"), ("karrigan", "igl"), ("NiKo", "entry"),
                ("rain", "support"), ("olofmeister", "lurker"),
            )),
            ("BIG", "EU", "топ-8", (  # проверить состав
                ("smooya", "awp"), ("gob b", "igl"), ("tabseN", "entry"),
                ("tiziaN", "support"), ("nex", "lurker"),
            )),
            ("HellRaisers", "CIS", "топ-8", (  # проверить состав
                ("woxic", "awp"), ("ANGE1", "igl"), ("oskar", "entry"),
                ("ISSAA", "support"), ("deadFox", "lurker"),
            )),
            ("G2 Esports", "EU", "группа", (
                ("kennyS", "awp"), ("shox", "igl"), ("apEX", "entry"),
                ("NBK-", "support"), ("bodyy", "lurker"),
            )),
            ("Fnatic", "EU", "группа", (  # проверить состав
                ("JW", "awp"), ("Golden", "igl"), ("KRIMZ", "entry"),
                ("flusha", "support"), ("Lekr0", "lurker"),
            )),
            ("Ninjas in Pyjamas", "EU", "группа", (  # проверить состав
                ("dennis", "awp"), ("Lekr0", "igl"), ("f0rest", "entry"),
                ("REZ", "support"), ("GeT_RiGhT", "lurker"),
            )),
        ),
    },
    # ------------------------------------------------------------------ 2019
    {
        "event": "IEM Katowice 2019",
        "year": 2019,
        "era": "legacy",
        "teams": (
            ("Astralis", "EU", "победитель", (
                ("device", "awp"), ("gla1ve", "igl"), ("dupreeh", "entry"),
                ("Xyp9x", "support"), ("Magisk", "lurker"),
            )),
            ("ENCE", "EU", "финалист", (
                ("allu", "awp"), ("Aleksib", "igl"), ("sergej", "entry"),
                ("xseveN", "support"), ("Aerial", "lurker"),
            )),
            ("Natus Vincere", "CIS", "топ-4", (
                ("s1mple", "awp"), ("Zeus", "igl"), ("flamie", "entry"),
                ("Edward", "support"), ("electronic", "lurker"),
            )),
            ("MIBR", "BR", "топ-4", (  # проверить состав
                ("FalleN", "awp"), ("felps", "igl"), ("fer", "entry"),
                ("TACO", "support"), ("coldzera", "lurker"),
            )),
            ("Team Liquid", "NA", "топ-8", (
                ("Stewie2K", "awp"), ("nitr0", "igl"), ("EliGE", "entry"),
                ("NAF", "support"), ("Twistzz", "lurker"),
            )),
            ("FaZe Clan", "EU", "топ-8", (  # проверить состав
                ("GuardiaN", "awp"), ("AdreN", "igl"), ("NiKo", "entry"),
                ("rain", "support"), ("olofmeister", "lurker"),
            )),
            ("Renegades", "AU", "топ-8", (  # проверить состав
                ("Gratisfaction", "awp"), ("AZR", "igl"), ("jks", "entry"),
                ("liazz", "support"), ("jkaem", "lurker"),
            )),
            ("Team Vitality", "EU", "топ-8", (
                ("ZywOo", "awp"), ("NBK-", "igl"), ("apEX", "entry"),
                ("RpK", "support"), ("ALEX", "lurker"),
            )),
            ("NRG Esports", "NA", "группа", (  # проверить состав
                ("CeRq", "awp"), ("daps", "igl"), ("Brehze", "entry"),
                ("Ethan", "support"), ("stanislaw", "lurker"),
            )),
            ("AVANGAR", "CIS", "группа", (  # проверить состав
                ("Jame", "awp"), ("AdreN", "igl"), ("buster", "entry"),
                ("KrizzeN", "support"), ("qikert", "lurker"),
            )),
            ("FURIA Esports", "BR", "группа", (  # проверить состав
                ("ableJ", "awp"), ("arT", "igl"), ("yuurih", "entry"),
                ("VINI", "support"), ("KSCERATO", "lurker"),
            )),
            ("Ninjas in Pyjamas", "EU", "группа", (  # проверить состав
                ("dennis", "awp"), ("Lekr0", "igl"), ("f0rest", "entry"),
                ("REZ", "support"), ("GeT_RiGhT", "lurker"),
            )),
        ),
    },
    {
        "event": "StarLadder Berlin 2019",
        "year": 2019,
        "era": "legacy",
        "teams": (
            ("Astralis", "EU", "победитель", (
                ("device", "awp"), ("gla1ve", "igl"), ("dupreeh", "entry"),
                ("Xyp9x", "support"), ("Magisk", "lurker"),
            )),
            ("AVANGAR", "CIS", "финалист", (  # проверить состав
                ("Jame", "awp"), ("AdreN", "igl"), ("buster", "entry"),
                ("KrizzeN", "support"), ("qikert", "lurker"),
            )),
            ("NRG Esports", "NA", "топ-4", (  # проверить состав
                ("CeRq", "awp"), ("stanislaw", "igl"), ("Brehze", "entry"),
                ("Ethan", "support"), ("daps", "lurker"),
            )),
            ("Team Vitality", "EU", "топ-4", (
                ("ZywOo", "awp"), ("NBK-", "igl"), ("apEX", "entry"),
                ("RpK", "support"), ("ALEX", "lurker"),
            )),
            ("Natus Vincere", "CIS", "топ-8", (  # проверить состав
                ("s1mple", "awp"), ("Boombl4", "igl"), ("flamie", "entry"),
                ("GuardiaN", "support"), ("electronic", "lurker"),
            )),
            ("Team Liquid", "NA", "топ-8", (
                ("Stewie2K", "awp"), ("nitr0", "igl"), ("EliGE", "entry"),
                ("NAF", "support"), ("Twistzz", "lurker"),
            )),
            ("ENCE", "EU", "топ-8", (
                ("allu", "awp"), ("Aleksib", "igl"), ("sergej", "entry"),
                ("xseveN", "support"), ("Aerial", "lurker"),
            )),
            ("MIBR", "BR", "топ-8", (  # проверить состав
                ("FalleN", "awp"), ("LUCAS1", "igl"), ("fer", "entry"),
                ("TACO", "support"), ("felps", "lurker"),
            )),
            ("G2 Esports", "EU", "группа", (  # проверить состав
                ("kennyS", "awp"), ("shox", "igl"), ("huNter-", "entry"),
                ("nexa", "support"), ("AmaNEk", "lurker"),
            )),
            ("Renegades", "AU", "группа", (  # проверить состав
                ("Gratisfaction", "awp"), ("AZR", "igl"), ("jks", "entry"),
                ("liazz", "support"), ("jkaem", "lurker"),
            )),
        ),
    },
    # ------------------------------------------------------------------ 2021
    {
        "event": "PGL Major Stockholm 2021",
        "year": 2021,
        "era": "modern",
        "teams": (
            ("Natus Vincere", "CIS", "победитель", (
                ("s1mple", "awp"), ("Boombl4", "igl"), ("electronic", "entry"),
                ("Perfecto", "support"), ("b1t", "lurker"),
            )),
            ("G2 Esports", "EU", "финалист", (  # проверить состав
                ("AmaNEk", "awp"), ("nexa", "igl"), ("huNter-", "entry"),
                ("NiKo", "lurker"), ("JaCkz", "support"),
            )),
            ("Gambit Esports", "CIS", "топ-4", (
                ("sh1ro", "awp"), ("nafany", "igl"), ("Ax1Le", "entry"),
                ("interz", "support"), ("HObbit", "lurker"),
            )),
            ("Team Heroic", "EU", "топ-4", (  # проверить состав
                ("cadiaN", "awp"), ("TeSeS", "igl"), ("stavn", "entry"),
                ("sjuush", "support"), ("refrezh", "lurker"),
            )),
            ("Team Vitality", "EU", "топ-8", (  # проверить состав
                ("ZywOo", "awp"), ("apEX", "igl"), ("dupreeh", "entry"),
                ("Magisk", "support"), ("misutaaa", "lurker"),
            )),
            ("FURIA Esports", "BR", "топ-8", (  # проверить состав
                ("drop", "awp"), ("arT", "igl"), ("yuurih", "entry"),
                ("VINI", "support"), ("KSCERATO", "lurker"),
            )),
            ("Astralis", "EU", "группа", (  # проверить состав
                ("Lucky", "awp"), ("gla1ve", "igl"), ("blameF", "entry"),
                ("Xyp9x", "support"), ("Bubzkji", "lurker"),
            )),
            ("Ninjas in Pyjamas", "EU", "группа", (  # проверить состав
                ("device", "awp"), ("hampus", "igl"), ("REZ", "entry"),
                ("Plopski", "support"), ("LNZ", "lurker"),
            )),
            ("FaZe Clan", "EU", "группа", (  # проверить состав
                ("broky", "awp"), ("karrigan", "igl"), ("rain", "entry"),
                ("Twistzz", "support"), ("olofmeister", "lurker"),
            )),
            ("MOUZ", "EU", "группа", (  # проверить состав
                ("acoR", "awp"), ("dexter", "igl"), ("frozen", "entry"),
                ("Bymas", "support"), ("ropz", "lurker"),
            )),
            ("Copenhagen Flames", "EU", "группа", (  # проверить состав
                ("nicoodoz", "awp"), ("HooXi", "igl"), ("jabbi", "entry"),
                ("Zyphon", "support"), ("roeJ", "lurker"),
            )),
            ("Team Liquid", "NA", "группа", (  # проверить состав
                ("FalleN", "awp"), ("nitr0", "igl"), ("EliGE", "entry"),
                ("Grim", "support"), ("Stewie2K", "lurker"),
            )),
        ),
    },
    # ------------------------------------------------------------------ 2022
    {
        "event": "PGL Major Antwerp 2022",
        "year": 2022,
        "era": "modern",
        "teams": (
            ("FaZe Clan", "EU", "победитель", (
                ("broky", "awp"), ("karrigan", "igl"), ("rain", "entry"),
                ("ropz", "support"), ("Twistzz", "lurker"),
            )),
            ("Natus Vincere", "CIS", "финалист", (
                ("s1mple", "awp"), ("Boombl4", "igl"), ("electronic", "entry"),
                ("Perfecto", "support"), ("b1t", "lurker"),
            )),
            ("Team Spirit", "CIS", "топ-4", (  # проверить состав
                ("degster", "awp"), ("chopper", "igl"), ("Patsi", "entry"),
                ("s1ren", "support"), ("magixx", "lurker"),
            )),
            ("ENCE", "EU", "топ-4", (  # проверить состав
                ("hades", "awp"), ("Snax", "igl"), ("dycha", "entry"),
                ("Maden", "support"), ("Spinx", "lurker"),
            )),
            ("Team Vitality", "EU", "топ-8", (  # проверить состав
                ("ZywOo", "awp"), ("apEX", "igl"), ("dupreeh", "entry"),
                ("Magisk", "support"), ("misutaaa", "lurker"),
            )),
            ("Team Heroic", "EU", "топ-8", (  # проверить состав
                ("cadiaN", "awp"), ("TeSeS", "igl"), ("stavn", "entry"),
                ("sjuush", "support"), ("refrezh", "lurker"),
            )),
            ("Copenhagen Flames", "EU", "топ-8", (  # проверить состав
                ("nicoodoz", "awp"), ("HooXi", "igl"), ("jabbi", "entry"),
                ("Zyphon", "support"), ("roeJ", "lurker"),
            )),
            ("G2 Esports", "EU", "группа", (  # проверить состав
                ("m0NESY", "awp"), ("HooXi", "igl"), ("huNter-", "entry"),
                ("NiKo", "lurker"), ("jks", "support"),
            )),
            ("Outsiders", "CIS", "группа", (  # проверить состав
                ("Jame", "awp"), ("Qikert", "igl"), ("FL1T", "entry"),
                ("n0rb3r7", "support"), ("fame", "lurker"),
            )),
            ("Imperial Esports", "BR", "группа", (  # проверить состав
                ("FalleN", "awp"), ("fnx", "igl"), ("fer", "entry"),
                ("VINI", "support"), ("boltz", "lurker"),
            )),
            ("Team Liquid", "NA", "группа", (  # проверить состав
                ("oSee", "awp"), ("nitr0", "igl"), ("YEKINDAR", "entry"),
                ("NAF", "support"), ("EliGE", "lurker"),
            )),
            ("FURIA Esports", "BR", "группа", (  # проверить состав
                ("saffee", "awp"), ("arT", "igl"), ("yuurih", "entry"),
                ("drop", "support"), ("KSCERATO", "lurker"),
            )),
        ),
    },
    {
        "event": "IEM Rio 2022",
        "year": 2022,
        "era": "modern",
        "teams": (
            ("Outsiders", "CIS", "победитель", (
                ("Jame", "awp"), ("fame", "igl"), ("FL1T", "entry"),
                ("n0rb3r7", "support"), ("Qikert", "lurker"),
            )),
            ("Team Heroic", "EU", "финалист", (  # проверить состав
                ("cadiaN", "awp"), ("TeSeS", "igl"), ("stavn", "entry"),
                ("sjuush", "support"), ("jabbi", "lurker"),
            )),
            ("MOUZ", "EU", "топ-4", (  # проверить состав
                ("torzsi", "awp"), ("dexter", "igl"), ("xertioN", "entry"),
                ("frozen", "support"), ("JDC", "lurker"),
            )),
            ("FURIA Esports", "BR", "топ-4", (  # проверить состав
                ("saffee", "awp"), ("arT", "igl"), ("yuurih", "entry"),
                ("drop", "support"), ("KSCERATO", "lurker"),
            )),
            ("Natus Vincere", "CIS", "топ-8", (  # проверить состав
                ("s1mple", "awp"), ("electroNic", "igl"), ("b1t", "entry"),
                ("Perfecto", "support"), ("sdy", "lurker"),
            )),
            ("Cloud9", "CIS", "топ-8", (
                ("sh1ro", "awp"), ("nafany", "igl"), ("Ax1Le", "entry"),
                ("interz", "support"), ("HObbit", "lurker"),
            )),
            ("Team Spirit", "CIS", "топ-8", (  # проверить состав
                ("degster", "awp"), ("chopper", "igl"), ("Patsi", "entry"),
                ("s1ren", "support"), ("magixx", "lurker"),
            )),
            ("Team Liquid", "NA", "топ-8", (  # проверить состав
                ("oSee", "awp"), ("nitr0", "igl"), ("YEKINDAR", "entry"),
                ("NAF", "support"), ("EliGE", "lurker"),
            )),
            ("FaZe Clan", "EU", "группа", (
                ("broky", "awp"), ("karrigan", "igl"), ("rain", "entry"),
                ("ropz", "support"), ("Twistzz", "lurker"),
            )),
            ("Team Vitality", "EU", "группа", (  # проверить состав
                ("ZywOo", "awp"), ("apEX", "igl"), ("dupreeh", "entry"),
                ("Magisk", "support"), ("Spinx", "lurker"),
            )),
        ),
    },
    # ------------------------------------------------------------------ 2023
    {
        "event": "BLAST.tv Paris Major 2023",
        "year": 2023,
        "era": "modern",
        "teams": (
            ("Team Vitality", "EU", "победитель", (
                ("ZywOo", "awp"), ("apEX", "igl"), ("dupreeh", "entry"),
                ("Magisk", "support"), ("Spinx", "lurker"),
            )),
            ("GamerLegion", "EU", "финалист", (  # проверить состав
                ("acoR", "awp"), ("siuhy", "igl"), ("iM", "entry"),
                ("Keoz", "support"), ("neaLaN", "lurker"),
            )),
            ("Team Heroic", "EU", "топ-4", (  # проверить состав
                ("cadiaN", "awp"), ("TeSeS", "igl"), ("stavn", "entry"),
                ("sjuush", "support"), ("jabbi", "lurker"),
            )),
            ("Apeks", "EU", "топ-4", (  # проверить состав
                ("nawwk", "awp"), ("STYKO", "igl"), ("jkaem", "entry"),
                ("kyxsan", "support"), ("kito", "lurker"),
            )),
            ("FaZe Clan", "EU", "топ-8", (
                ("broky", "awp"), ("karrigan", "igl"), ("rain", "entry"),
                ("ropz", "support"), ("Twistzz", "lurker"),
            )),
            ("Natus Vincere", "CIS", "топ-8", (  # проверить состав
                ("s1mple", "awp"), ("Aleksib", "igl"), ("b1t", "entry"),
                ("npl", "support"), ("Perfecto", "lurker"),
            )),
            ("Team Liquid", "NA", "топ-8", (  # проверить состав
                ("oSee", "awp"), ("nitr0", "igl"), ("YEKINDAR", "entry"),
                ("NAF", "support"), ("EliGE", "lurker"),
            )),
            ("Into the Breach", "EU", "топ-8", (  # проверить состав
                ("CYPHER", "awp"), ("Thomas", "igl"), ("rallen", "entry"),
                ("volt", "support"), ("Adam9130", "lurker"),
            )),
            ("G2 Esports", "EU", "группа", (  # проверить состав
                ("m0NESY", "awp"), ("HooXi", "igl"), ("jks", "entry"),
                ("huNter-", "support"), ("NiKo", "lurker"),
            )),
            ("MOUZ", "EU", "группа", (  # проверить состав
                ("torzsi", "awp"), ("dexter", "igl"), ("xertioN", "entry"),
                ("frozen", "support"), ("JDC", "lurker"),
            )),
            ("FURIA Esports", "BR", "группа", (  # проверить состав
                ("saffee", "awp"), ("arT", "igl"), ("yuurih", "entry"),
                ("drop", "support"), ("KSCERATO", "lurker"),
            )),
            ("Bad News Eagles", "EU", "группа", (  # проверить состав
                ("rigoN", "awp"), ("gxx-", "igl"), ("juanflatroo", "entry"),
                ("SENER1", "support"), ("sinnopsyy", "lurker"),
            )),
        ),
    },
    # ------------------------------------------------------------------ 2024
    {
        "event": "PGL Major Copenhagen 2024",
        "year": 2024,
        "era": "modern",
        "teams": (
            ("Natus Vincere", "CIS", "победитель", (
                ("w0nderful", "awp"), ("Aleksib", "igl"), ("b1t", "entry"),
                ("iM", "support"), ("jL", "lurker"),
            )),
            ("FaZe Clan", "EU", "финалист", (  # проверить состав
                ("broky", "awp"), ("karrigan", "igl"), ("rain", "entry"),
                ("ropz", "support"), ("frozen", "lurker"),
            )),
            ("Team Spirit", "CIS", "топ-4", (
                ("sh1ro", "awp"), ("chopper", "igl"), ("donk", "entry"),
                ("magixx", "support"), ("zont1x", "lurker"),
            )),
            ("G2 Esports", "EU", "топ-4", (  # проверить состав
                ("m0NESY", "awp"), ("HooXi", "igl"), ("NiKo", "entry"),
                ("huNter-", "support"), ("nexa", "lurker"),
            )),
            ("Team Vitality", "EU", "топ-8", (
                ("ZywOo", "awp"), ("apEX", "igl"), ("flameZ", "entry"),
                ("mezii", "support"), ("Spinx", "lurker"),
            )),
            ("MOUZ", "EU", "топ-8", (
                ("torzsi", "awp"), ("siuhy", "igl"), ("xertioN", "entry"),
                ("Brollan", "support"), ("Jimpphat", "lurker"),
            )),
            ("Cloud9", "CIS", "топ-8", (  # проверить состав
                ("ICY", "awp"), ("Boombl4", "igl"), ("Ax1Le", "entry"),
                ("HObbit", "support"), ("electroNic", "lurker"),
            )),
            ("Complexity", "NA", "топ-8", (  # проверить состав
                ("hallzerk", "awp"), ("floppy", "igl"), ("EliGE", "entry"),
                ("JT", "support"), ("Grim", "lurker"),
            )),
            ("Team Liquid", "NA", "группа", (  # проверить состав
                ("cadiaN", "awp"), ("Twistzz", "igl"), ("YEKINDAR", "entry"),
                ("NAF", "support"), ("skullz", "lurker"),
            )),
            ("Eternal Fire", "EU", "группа", (  # проверить состав
                ("woxic", "awp"), ("MAJ3R", "igl"), ("XANTARES", "entry"),
                ("Wicadia", "support"), ("Calyx", "lurker"),
            )),
            ("The MongolZ", "AS", "группа", (  # проверить состав
                ("910", "awp"), ("bLitz", "igl"), ("Techno", "entry"),
                ("mzinho", "support"), ("Senzu", "lurker"),
            )),
            ("HEROIC", "EU", "группа", (  # проверить состав
                ("nicoodoz", "awp"), ("NertZ", "igl"), ("jabbi", "entry"),
                ("sjuush", "support"), ("TeSeS", "lurker"),
            )),
        ),
    },
    {
        "event": "Perfect World Shanghai 2024",
        "year": 2024,
        "era": "modern",
        "teams": (
            ("Team Spirit", "CIS", "победитель", (
                ("sh1ro", "awp"), ("chopper", "igl"), ("donk", "entry"),
                ("magixx", "support"), ("zont1x", "lurker"),
            )),
            ("FaZe Clan", "EU", "финалист", (
                ("broky", "awp"), ("karrigan", "igl"), ("rain", "entry"),
                ("ropz", "support"), ("frozen", "lurker"),
            )),
            ("G2 Esports", "EU", "топ-4", (  # проверить состав
                ("m0NESY", "awp"), ("Snax", "igl"), ("NiKo", "entry"),
                ("huNter-", "support"), ("malbsMd", "lurker"),
            )),
            ("Team Vitality", "EU", "топ-4", (
                ("ZywOo", "awp"), ("apEX", "igl"), ("flameZ", "entry"),
                ("mezii", "support"), ("Spinx", "lurker"),
            )),
            ("MOUZ", "EU", "топ-8", (
                ("torzsi", "awp"), ("siuhy", "igl"), ("xertioN", "entry"),
                ("Brollan", "support"), ("Jimpphat", "lurker"),
            )),
            ("Natus Vincere", "CIS", "топ-8", (
                ("w0nderful", "awp"), ("Aleksib", "igl"), ("b1t", "entry"),
                ("iM", "support"), ("jL", "lurker"),
            )),
            ("HEROIC", "EU", "топ-8", (  # проверить состав
                ("nicoodoz", "awp"), ("NertZ", "igl"), ("jabbi", "entry"),
                ("sjuush", "support"), ("TeSeS", "lurker"),
            )),
            ("Team Liquid", "NA", "топ-8", (  # проверить состав
                ("ultimate", "awp"), ("jks", "igl"), ("YEKINDAR", "entry"),
                ("NAF", "support"), ("Twistzz", "lurker"),
            )),
            ("The MongolZ", "AS", "группа", (
                ("910", "awp"), ("bLitz", "igl"), ("Techno", "entry"),
                ("mzinho", "support"), ("Senzu", "lurker"),
            )),
            ("FURIA Esports", "BR", "группа", (  # проверить состав
                ("FalleN", "awp"), ("yuurih", "igl"), ("KSCERATO", "entry"),
                ("molodoy", "support"), ("skullz", "lurker"),
            )),
            ("paiN Gaming", "BR", "группа", (  # проверить состав
                ("nqz", "awp"), ("biguzera", "igl"), ("lux", "entry"),
                ("snow", "support"), ("kauez", "lurker"),
            )),
            ("Cloud9", "CIS", "группа", (  # проверить состав
                ("ICY", "awp"), ("Boombl4", "igl"), ("Ax1Le", "entry"),
                ("HObbit", "support"), ("electroNic", "lurker"),
            )),
        ),
    },
    # ------------------------------------------------------------------ 2025
    {
        "event": "BLAST.tv Austin Major 2025",
        "year": 2025,
        "era": "modern",
        "teams": (
            ("Team Vitality", "EU", "победитель", (
                ("ZywOo", "awp"), ("apEX", "igl"), ("flameZ", "entry"),
                ("mezii", "support"), ("ropz", "lurker"),
            )),
            # Дальше состав и места участников собраны по памяти: перед выпуском
            # набора эти паки стоит сверить с таблицей турнира.
            ("The MongolZ", "AS", "топ-4", (
                ("910", "awp"), ("bLitz", "igl"), ("Techno", "entry"),
                ("mzinho", "support"), ("Senzu", "lurker"),
            )),
            ("Team Spirit", "CIS", "топ-4", (
                ("sh1ro", "awp"), ("chopper", "igl"), ("donk", "entry"),
                ("magixx", "support"), ("zont1x", "lurker"),
            )),
            ("MOUZ", "EU", "топ-8", (
                ("torzsi", "awp"), ("Brollan", "igl"), ("xertioN", "entry"),
                ("Spinx", "support"), ("Jimpphat", "lurker"),
            )),
            ("FaZe Clan", "EU", "топ-8", (
                ("broky", "awp"), ("karrigan", "igl"), ("rain", "entry"),
                ("frozen", "support"), ("ropz", "lurker"),
            )),
            ("Natus Vincere", "CIS", "топ-8", (
                ("w0nderful", "awp"), ("Aleksib", "igl"), ("b1t", "entry"),
                ("iM", "support"), ("jL", "lurker"),
            )),
            ("G2 Esports", "EU", "группа", (
                ("m0NESY", "awp"), ("Snax", "igl"), ("NiKo", "entry"),
                ("huNter-", "support"), ("malbsMd", "lurker"),
            )),
            ("FURIA Esports", "BR", "группа", (
                ("FalleN", "awp"), ("yuurih", "igl"), ("KSCERATO", "entry"),
                ("molodoy", "support"), ("skullz", "lurker"),
            )),
        ),
    },
    # Мейджоры 2025 года после Austin и турниры 2026 года в набор не занесены:
    # их состав и итоги нужно взять из таблиц турниров, а не по памяти.
)


def _slug(text: str) -> str:
    """Идентификатор пака: латиница в нижнем регистре, остальное — дефис."""
    cleaned = [char.lower() if char.isalnum() and char.isascii() else "-" for char in text]
    slug = "".join(cleaned)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def _maps_for(year: int, pack_key: str) -> List[str]:
    """Три карты из маппула года: выбор зависит от команды и турнира."""
    pool = YEAR_MAPS.get(year) or YEAR_MAPS[max(YEAR_MAPS)]
    start = zlib.crc32(pack_key.encode("utf-8")) % len(pool)
    return [pool[(start + step) % len(pool)] for step in range(3)]


def _scores(pack_key: str, place: str, role: str, name: str) -> Tuple[float, float, float]:
    """Оценки игрока: сила по месту на турнире, сдвиг по роли и поправка на игрока.

    Значения всегда в пределах 60–95, повторный прогон даёт те же числа: набор
    детерминирован, иначе состав «дрожал» бы при каждой загрузке.
    """
    base = PLACE_POWER.get(place, PLACE_POWER["группа"])
    aim_shift, clutch_shift, impact_shift = ROLE_SHIFT.get(role, (0.0, 0.0, 0.0))
    jitter = (zlib.crc32(f"{pack_key}|{name}".encode("utf-8")) % 5) - 2
    values = (base + aim_shift + jitter, base + clutch_shift + jitter, base + impact_shift + jitter)
    return tuple(round(max(60.0, min(95.0, value)), 1) for value in values)  # type: ignore[return-value]


def major_packs() -> List[Dict[str, Any]]:
    """Паки мейджоров в том же виде, что и строки набора в csdraft_data."""
    result: List[Dict[str, Any]] = []
    for event in EVENTS:
        title = str(event["event"])
        year = int(event["year"])
        era = str(event.get("era") or ("legacy" if year <= 2019 else "modern"))
        for team, region, place, players in event["teams"]:
            pack_id = f"{_slug(str(team))}-{_slug(title)}"
            maps = _maps_for(year, pack_id)
            result.append({
                "id": pack_id,
                "team": str(team),
                "event": title,
                "year": year,
                "place": str(place),
                "major": True,
                "region": str(region),
                "era": era,
                "maps": maps,
                "players": [
                    (str(name), str(role), *_scores(pack_id, str(place), str(role), str(name)))
                    for name, role in players
                ],
            })
    return result


__all__ = ["EVENTS", "PLACE_POWER", "ROLE_SHIFT", "YEAR_MAPS", "major_packs"]
