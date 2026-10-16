# -*- coding: utf-8 -*-
"""Полные составы участников мейджоров 2013–2026 (сгенерировано).

Файл создан скриптом `_fetch_major_rosters.py` из данных Liquipedia
(CC-BY-SA 3.0) и править его вручную не нужно: правки затрутся при
следующей сборке. Роли игроков в Liquipedia не публикуются: известные
роли взяты из словаря в скрипте, остальные подставлены по правилу и
помечены комментарием «роль не подтверждена».
"""
from __future__ import annotations

from typing import Any, Dict, Tuple

# Мейджоры: (событие, год, эпоха, команды). Команда: (название, регион,
# место, игроки). Игрок: (ник, роль).
EVENTS: Tuple[Dict[str, Any], ...] = (
    {
        "event": "DreamHack Winter 2013, Jönköping",
        "year": 2013,
        "era": "legacy",
        "teams": (
            ("Fnatic", "EU", "победитель", (
                ("JW", "awp"),
                ("Flusha", "support"),
                ("Znajder", "entry"),  # роль не подтверждена
                ("Devilwalk", "support"),
                ("Pronax", "igl"),
            )),
            ("N!faculty", "EU", "топ-12", (
                ("Gla1ve", "igl"),
                ("Karrigan", "igl"),
                ("Cajunb", "awp"),
                ("Pimp", "lurker"),
                ("Raalz", "support"),
            )),
            ("Universal Soldiers", "EU", "топ-12", (
                ("TaZ", "support"),
                ("NEO", "lurker"),
                ("PashaBiceps", "awp"),
                ("Snax", "entry"),
                ("Byali", "lurker"),
            )),
            ("Clan-Mystik", "EU", "топ-12", (
                ("HaRts", "awp"),  # роль не подтверждена
                ("IoRek", "entry"),  # роль не подтверждена
                ("KioShiMa", "support"),
                ("KQLY", "lurker"),  # роль не подтверждена
                ("ApEX", "igl"),
            )),
            ("Reason Gaming", "EU", "топ-12", (
                ("MSL", "igl"),
                ("ColoN", "awp"),  # роль не подтверждена
                ("SmF", "entry"),  # роль не подтверждена
                ("EXR", "support"),  # роль не подтверждена
                ("LOMME", "lurker"),  # роль не подтверждена
            )),
            ("SK Gaming", "SA", "топ-16", (
                ("Pita", "support"),
                ("Twist", "awp"),
                ("Xelos", "support"),
                ("Delpan", "lurker"),
                ("MODDII", "entry"),
            )),
            ("Team iBUYPOWER", "EU", "топ-16", (
                ("Anger", "entry"),  # роль не подтверждена
                ("Skadoodle", "awp"),
                ("AdreN", "igl"),
                ("AZK", "support"),  # роль не подтверждена
                ("DaZeD", "igl"),
            )),
            ("Natus Vincere", "EEU", "топ-16", (
                ("Zeus", "awp"),  # роль не подтверждена
                ("Starix", "igl"),
                ("Ceh9", "entry"),  # роль не подтверждена
                ("Seized", "lurker"),
                ("Tonyblack", "support"),  # роль не подтверждена
            )),
            ("Xapso", "EU", "топ-16", (
                ("Ultra", "awp"),  # роль не подтверждена
                ("Centeks", "entry"),  # роль не подтверждена
                ("CadiaN", "igl"),
                ("Aizy", "support"),  # роль не подтверждена
                ("Robiin", "lurker"),  # роль не подтверждена
            )),
            ("CompLexity Gaming", "NA", "топ-4", (
                ("Hiko", "lurker"),
                ("Sgares", "awp"),  # роль не подтверждена
                ("SEMPHIS", "igl"),
                ("Swag", "entry"),  # роль не подтверждена
                ("N0thing", "lurker"),
            )),
            ("VeryGames", "EU", "топ-4", (
                ("Ex6TenZ", "igl"),
                ("NBK-", "support"),
                ("SmithZz", "awp"),  # роль не подтверждена
                ("ScreaM", "entry"),
                ("Shox", "lurker"),
            )),
            ("Copenhagen Wolves", "EU", "топ-8", (
                ("FeTiSh", "igl"),
                ("Dupreeh", "entry"),
                ("Xyp9x", "support"),
                ("Dev1ce", "awp"),
                ("Nico", "lurker"),  # роль не подтверждена
            )),
            ("Astana Dragons", "EU", "топ-8", (
                ("ANGE1", "igl"),
                ("Dosia", "lurker"),
                ("AdreN", "igl"),
                ("Markeloff", "awp"),
                ("KUcheR", "support"),
            )),
            ("LGB eSports", "EU", "топ-8", (
                ("SKYTTEN", "awp"),  # роль не подтверждена
                ("Maikelele", "igl"),  # роль не подтверждена
                ("KRIMZ", "support"),
                ("Dennis", "entry"),
                ("Olofmeister", "entry"),
            )),
            ("Recursive eSports", "EU", "топ-8", (
                ("Happy", "igl"),
                ("GMX", "entry"),  # роль не подтверждена
                ("KennyS", "awp"),
                ("Uzzziii", "support"),  # роль не подтверждена
                ("Maniac", "lurker"),  # роль не подтверждена
            )),
            ("Ninjas in Pyjamas", "EU", "финалист", (
                ("F0rest", "entry"),
                ("GeT RiGhT", "lurker"),
                ("Xizt", "igl"),
                ("Fifflaren", "awp"),
                ("Friberg", "support"),  # роль не подтверждена
            )),
        ),
    },
    {
        "event": "EMS One Katowice 2014",
        "year": 2014,
        "era": "legacy",
        "teams": (
            ("Virtus.pro", "EEU", "победитель", (
                ("TaZ", "support"),
                ("NEO", "lurker"),
                ("PashaBiceps", "awp"),
                ("Snax", "entry"),
                ("Byali", "lurker"),
            )),
            ("Titan", "EU", "топ-12", (
                ("Ex6TenZ", "igl"),
                ("NBK-", "support"),
                ("SmithZz", "awp"),  # роль не подтверждена
                ("ScreaM", "entry"),
                ("Shox", "lurker"),
            )),
            ("Reason Gaming", "EU", "топ-12", (
                ("EXR", "awp"),  # роль не подтверждена
                ("LOMME", "entry"),  # роль не подтверждена
                ("Friis", "support"),  # роль не подтверждена
                ("Karrigan", "igl"),
                ("SmF", "lurker"),  # роль не подтверждена
            )),
            ("Clan-Mystik", "EU", "топ-12", (
                ("HaRts", "igl"),  # роль не подтверждена
                ("KioShiMa", "support"),
                ("Sf", "entry"),  # роль не подтверждена
                ("GMX", "lurker"),  # роль не подтверждена
                ("KennyS", "awp"),
            )),
            ("3DMAX", "EU", "топ-12", (
                ("Gla1ve", "igl"),
                ("Pimp", "lurker"),
                ("Raalz", "support"),
                ("MSL", "igl"),
                ("Aizy", "awp"),  # роль не подтверждена
            )),
            ("Natus Vincere", "EEU", "топ-16", (
                ("Zeus", "entry"),  # роль не подтверждена
                ("Starix", "igl"),
                ("Seized", "lurker"),
                ("Edward", "support"),
                ("GuardiaN", "awp"),
            )),
            ("Mousesports", "EU", "топ-16", (
                ("ChrisJ", "awp"),
                ("LEGIJA", "support"),  # роль не подтверждена
                ("TiziaN", "entry"),
                ("CadiaN", "igl"),
                ("TabseN", "lurker"),  # роль не подтверждена
            )),
            ("Team iBUYPOWER", "EU", "топ-16", (
                ("Anger", "entry"),  # роль не подтверждена
                ("Skadoodle", "awp"),
                ("AdreN", "igl"),
                ("AZK", "support"),  # роль не подтверждена
                ("DaZeD", "igl"),
            )),
            ("Vox Eminor", "EU", "топ-16", (
                ("SPUNJ", "awp"),  # роль не подтверждена
                ("AZR", "igl"),  # роль не подтверждена
                ("Havoc", "entry"),  # роль не подтверждена
                ("SnypeR", "support"),  # роль не подтверждена
                ("TopguN", "lurker"),  # роль не подтверждена
            )),
            ("LGB eSports", "EU", "топ-4", (
                ("KRIMZ", "support"),
                ("Dennis", "entry"),
                ("Olofmeister", "entry"),
                ("Twist", "awp"),
                ("Cype", "igl"),  # роль не подтверждена
            )),
            ("Team Dignitas", "EU", "топ-4", (
                ("FeTiSh", "igl"),
                ("Dupreeh", "entry"),
                ("Xyp9x", "support"),
                ("Dev1ce", "awp"),
                ("Cajunb", "awp"),
            )),
            ("Fnatic", "EU", "топ-8", (
                ("JW", "awp"),
                ("Flusha", "support"),
                ("Znajder", "entry"),  # роль не подтверждена
                ("Devilwalk", "support"),
                ("Pronax", "igl"),
            )),
            ("CompLexity Gaming", "NA", "топ-8", (
                ("Hiko", "lurker"),
                ("SEMPHIS", "igl"),
                ("Sgares", "awp"),  # роль не подтверждена
                ("Swag", "entry"),  # роль не подтверждена
                ("N0thing", "lurker"),
            )),
            ("Team LDLC.com", "EU", "топ-8", (
                ("Happy", "igl"),
                ("Uzzziii", "awp"),  # роль не подтверждена
                ("Maniac", "entry"),  # роль не подтверждена
                ("KQLY", "support"),  # роль не подтверждена
                ("ApEX", "igl"),
            )),
            ("HellRaisers", "EEU", "топ-8", (
                ("ANGE1", "igl"),
                ("Dosia", "lurker"),
                ("AdreN", "igl"),
                ("Markeloff", "awp"),
                ("KUcheR", "support"),
            )),
            ("Ninjas in Pyjamas", "EU", "финалист", (
                ("F0rest", "entry"),
                ("GeT RiGhT", "lurker"),
                ("Xizt", "igl"),
                ("Fifflaren", "awp"),
                ("Friberg", "support"),  # роль не подтверждена
            )),
        ),
    },
    {
        "event": "ESL One Cologne 2014",
        "year": 2014,
        "era": "legacy",
        "teams": (
            ("Ninjas in Pyjamas", "EU", "победитель", (
                ("F0rest", "entry"),
                ("GeT RiGhT", "lurker"),
                ("Xizt", "igl"),
                ("Fifflaren", "awp"),
                ("Friberg", "support"),  # роль не подтверждена
            )),
            ("HellRaisers", "EEU", "топ-12", (
                ("ANGE1", "igl"),
                ("Dosia", "lurker"),
                ("AdreN", "igl"),
                ("Markeloff", "awp"),
                ("KUcheR", "support"),
            )),
            ("Titan", "EU", "топ-12", (
                ("Ex6TenZ", "igl"),
                ("NBK-", "support"),
                ("SmithZz", "lurker"),  # роль не подтверждена
                ("ScreaM", "entry"),
                ("KennyS", "awp"),
            )),
            ("Copenhagen Wolves", "EU", "топ-12", (
                ("Gla1ve", "igl"),
                ("Karrigan", "igl"),
                ("Cajunb", "awp"),
                ("Pimp", "lurker"),
                ("Nico", "entry"),  # роль не подтверждена
            )),
            ("Team iBUYPOWER", "EU", "топ-12", (
                ("Skadoodle", "awp"),
                ("AZK", "entry"),  # роль не подтверждена
                ("DaZeD", "igl"),
                ("Steel", "support"),  # роль не подтверждена
                ("Swag", "lurker"),  # роль не подтверждена
            )),
            ("London Conspiracy", "EU", "топ-16", (
                ("Polly", "entry"),
                ("Skurk", "awp"),  # роль не подтверждена
                ("RUBINO", "igl"),  # роль не подтверждена
                ("Rain", "entry"),
                ("Prb", "support"),  # роль не подтверждена
            )),
            ("DAT Team", "EU", "топ-16", (
                ("B1ad3", "igl"),
                ("WorldEdit", "awp"),  # роль не подтверждена
                ("Bondik", "entry"),
                ("Ub1que", "support"),  # роль не подтверждена
                ("Flamie", "lurker"),
            )),
            ("Vox Eminor", "EU", "топ-16", (
                ("SPUNJ", "awp"),  # роль не подтверждена
                ("AZR", "igl"),  # роль не подтверждена
                ("Havoc", "entry"),  # роль не подтверждена
                ("TopguN", "support"),  # роль не подтверждена
                ("Jks", "lurker"),
            )),
            ("Team Wolf", "EU", "топ-16", (
                ("RiTz", "awp"),  # роль не подтверждена
                ("RiX", "igl"),  # роль не подтверждена
                ("AstaRR", "entry"),  # роль не подтверждена
                ("Ace", "support"),  # роль не подтверждена
                ("MithilF", "lurker"),  # роль не подтверждена
            )),
            ("Team Dignitas", "EU", "топ-4", (
                ("FeTiSh", "igl"),
                ("Dupreeh", "entry"),
                ("Xyp9x", "support"),
                ("Dev1ce", "awp"),
                ("Aizy", "lurker"),  # роль не подтверждена
            )),
            ("Team LDLC.com", "EU", "топ-4", (
                ("Happy", "igl"),
                ("Uzzziii", "awp"),  # роль не подтверждена
                ("Maniac", "entry"),  # роль не подтверждена
                ("KQLY", "support"),  # роль не подтверждена
                ("ApEX", "igl"),
            )),
            ("Virtus.pro", "EEU", "топ-8", (
                ("TaZ", "support"),
                ("NEO", "lurker"),
                ("PashaBiceps", "awp"),
                ("Snax", "entry"),
                ("Byali", "lurker"),
            )),
            ("Cloud9", "NA", "топ-8", (
                ("Hiko", "lurker"),
                ("SEMPHIS", "igl"),
                ("Sgares", "awp"),  # роль не подтверждена
                ("N0thing", "lurker"),
                ("Shroud", "entry"),  # роль не подтверждена
            )),
            ("Epsilon eSports", "EU", "топ-8", (
                ("KioShiMa", "support"),
                ("Sf", "awp"),  # роль не подтверждена
                ("GMX", "igl"),  # роль не подтверждена
                ("Shox", "lurker"),
                ("Fxy0", "entry"),  # роль не подтверждена
            )),
            ("Natus Vincere", "EEU", "топ-8", (
                ("Zeus", "entry"),  # роль не подтверждена
                ("Starix", "igl"),
                ("Seized", "lurker"),
                ("Edward", "support"),
                ("GuardiaN", "awp"),
            )),
            ("Fnatic", "EU", "финалист", (
                ("JW", "awp"),
                ("Flusha", "support"),
                ("Pronax", "igl"),
                ("Olofmeister", "entry"),
                ("KRIMZ", "support"),
            )),
        ),
    },
    {
        "event": "DreamHack Winter 2014, Jönköping",
        "year": 2014,
        "era": "legacy",
        "teams": (
            ("Team LDLC.com", "EU", "победитель", (
                ("NBK-", "support"),
                ("SmithZz", "awp"),  # роль не подтверждена
                ("KioShiMa", "support"),
                ("Shox", "lurker"),
                ("Happy", "igl"),
            )),
            ("Cloud9", "NA", "топ-12", (
                ("Hiko", "lurker"),
                ("Sgares", "awp"),  # роль не подтверждена
                ("SEMPHIS", "igl"),
                ("N0thing", "lurker"),
                ("Shroud", "entry"),  # роль не подтверждена
            )),
            ("ESC Gaming", "EU", "топ-12", (
                ("Innocent", "awp"),  # роль не подтверждена
                ("SZPERO", "igl"),  # роль не подтверждена
                ("Mouz", "support"),  # роль не подтверждена
                ("MINISE", "lurker"),  # роль не подтверждена
                ("Rallen", "entry"),
            )),
            ("Team iBUYPOWER", "EU", "топ-12", (
                ("AZK", "entry"),  # роль не подтверждена
                ("Skadoodle", "awp"),
                ("Swag", "support"),  # роль не подтверждена
                ("Nitr0", "igl"),
                ("Desi", "lurker"),  # роль не подтверждена
            )),
            ("FlipSid3 Tactics", "EEU", "топ-12", (
                ("Twist", "awp"),
                ("Berg", "igl"),  # роль не подтверждена
                ("Zende", "entry"),  # роль не подтверждена
                ("BENDJI", "support"),  # роль не подтверждена
                ("Dumas", "lurker"),  # роль не подтверждена
            )),
            ("Planetkey Dynamics", "EU", "топ-16", (
                ("Strux1", "awp"),  # роль не подтверждена
                ("Stavros", "igl"),  # роль не подтверждена
                ("AlexRr", "entry"),  # роль не подтверждена
                ("Troubley", "support"),  # роль не подтверждена
                ("Nex", "lurker"),  # роль не подтверждена
            )),
            ("MyXMG", "EU", "топ-16", (
                ("MSL", "igl"),
                ("HUNDEN", "awp"),  # роль не подтверждена
                ("AcilioN", "entry"),  # роль не подтверждена
                ("Friis", "support"),  # роль не подтверждена
                ("SmF", "lurker"),  # роль не подтверждена
            )),
            ("Copenhagen Wolves", "EU", "топ-16", (
                ("Gla1ve", "igl"),
                ("Pimp", "lurker"),
                ("Tenzki", "awp"),  # роль не подтверждена
                ("Kjaerbye", "entry"),  # роль не подтверждена
                ("CadiaN", "igl"),
            )),
            ("Bravado Gaming", "EU", "топ-16", (
                ("Cent", "awp"),  # роль не подтверждена
                ("Detrony", "igl"),  # роль не подтверждена
                ("Racno", "entry"),  # роль не подтверждена
                ("BlackpoisoN", "support"),  # роль не подтверждена
                ("DeviaNt", "lurker"),  # роль не подтверждена
            )),
            ("Natus Vincere", "EEU", "топ-4", (
                ("Zeus", "entry"),  # роль не подтверждена
                ("Starix", "igl"),
                ("Seized", "lurker"),
                ("Edward", "support"),
                ("GuardiaN", "awp"),
            )),
            ("Virtus.pro", "EEU", "топ-4", (
                ("TaZ", "support"),
                ("NEO", "lurker"),
                ("PashaBiceps", "awp"),
                ("Snax", "entry"),
                ("Byali", "lurker"),
            )),
            ("Fnatic", "EU", "топ-8", (
                ("JW", "awp"),
                ("Flusha", "support"),
                ("Pronax", "igl"),
                ("Olofmeister", "entry"),
                ("KRIMZ", "support"),
            )),
            ("Team Dignitas", "EU", "топ-8", (
                ("FeTiSh", "igl"),
                ("Dupreeh", "entry"),
                ("Xyp9x", "support"),
                ("Dev1ce", "awp"),
                ("Cajunb", "awp"),
            )),
            ("PENTA Sports", "EU", "топ-8", (
                ("Fel1x", "awp"),  # роль не подтверждена
                ("KRYSTAL", "igl"),  # роль не подтверждена
                ("R0bs3n", "support"),  # роль не подтверждена
                ("Denis", "entry"),
                ("Spiidi", "entry"),
            )),
            ("HellRaisers", "EEU", "топ-8", (
                ("ANGE1", "igl"),
                ("Dosia", "lurker"),
                ("Markeloff", "awp"),
                ("KUcheR", "support"),
                ("S1mple", "awp"),
            )),
            ("Ninjas in Pyjamas", "EU", "финалист", (
                ("F0rest", "entry"),
                ("GeT RiGhT", "lurker"),
                ("Xizt", "igl"),
                ("Friberg", "awp"),  # роль не подтверждена
                ("Maikelele", "support"),  # роль не подтверждена
            )),
        ),
    },
    {
        "event": "ESL One Katowice 2015",
        "year": 2015,
        "era": "legacy",
        "teams": (
            ("Fnatic", "EU", "победитель", (
                ("Flusha", "support"),
                ("JW", "awp"),
                ("Pronax", "igl"),
                ("Olofmeister", "entry"),
                ("KRIMZ", "support"),
            )),
            ("Counter Logic Gaming", "NA", "топ-12", (
                ("ReltuC", "entry"),  # роль не подтверждена
                ("Hazed", "support"),
                ("Tarik", "igl"),
                ("Ptr", "awp"),
                ("FNS", "igl"),
            )),
            ("LGB eSports", "EU", "топ-12", (
                ("RUBINO", "awp"),  # роль не подтверждена
                ("Rain", "entry"),
                ("Jkaem", "entry"),
                ("ZEVES", "igl"),  # роль не подтверждена
                ("Polly", "entry"),
            )),
            ("Cloud9", "NA", "топ-12", (
                ("N0thing", "lurker"),
                ("Sgares", "entry"),  # роль не подтверждена
                ("SEMPHIS", "igl"),
                ("Shroud", "support"),  # роль не подтверждена
                ("ShahZaM", "awp"),
            )),
            ("Vox Eminor", "EU", "топ-12", (
                ("AZR", "awp"),  # роль не подтверждена
                ("Havoc", "igl"),  # роль не подтверждена
                ("Jks", "lurker"),
                ("SPUNJ", "entry"),  # роль не подтверждена
                ("TopguN", "support"),  # роль не подтверждена
            )),
            ("HellRaisers", "EEU", "топ-16", (
                ("ANGE1", "igl"),
                ("KUcheR", "support"),
                ("Dosia", "lurker"),
                ("AdreN", "igl"),
                ("Flamie", "lurker"),
            )),
            ("FlipSid3 Tactics", "EEU", "топ-16", (
                ("B1ad3", "igl"),
                ("Bondik", "entry"),
                ("WorldEdit", "support"),  # роль не подтверждена
                ("Markeloff", "awp"),
                ("DavCost", "lurker"),  # роль не подтверждена
            )),
            ("Titan", "EU", "топ-16", (
                ("KennyS", "awp"),
                ("Ex6TenZ", "igl"),
                ("ApEX", "igl"),
                ("Maniac", "entry"),  # роль не подтверждена
                ("RpK", "support"),
            )),
            ("3DMAX", "EU", "топ-16", (
                ("DiSTURBED", "awp"),  # роль не подтверждена
                ("Natu", "igl"),  # роль не подтверждена
                ("KHRN", "entry"),  # роль не подтверждена
                ("Stonde", "support"),  # роль не подтверждена
                ("XartE", "lurker"),  # роль не подтверждена
            )),
            ("Team EnVyUs", "EU", "топ-4", (
                ("Happy", "igl"),
                ("NBK-", "support"),
                ("KioShiMa", "support"),
                ("Shox", "lurker"),
                ("SmithZz", "awp"),  # роль не подтверждена
            )),
            ("Virtus.pro", "EEU", "топ-4", (
                ("TaZ", "support"),
                ("NEO", "lurker"),
                ("PashaBiceps", "awp"),
                ("Snax", "entry"),
                ("Byali", "lurker"),
            )),
            ("Natus Vincere", "EEU", "топ-8", (
                ("Zeus", "entry"),  # роль не подтверждена
                ("Starix", "igl"),
                ("Seized", "lurker"),
                ("Edward", "support"),
                ("GuardiaN", "awp"),
            )),
            ("PENTA Sports", "EU", "топ-8", (
                ("Troubley", "awp"),  # роль не подтверждена
                ("KRYSTAL", "igl"),  # роль не подтверждена
                ("Nex", "support"),  # роль не подтверждена
                ("Denis", "entry"),
                ("Spiidi", "entry"),
            )),
            ("Team SoloMid", "EU", "топ-8", (
                ("Dev1ce", "awp"),
                ("Dupreeh", "entry"),
                ("Xyp9x", "support"),
                ("Cajunb", "awp"),
                ("Karrigan", "igl"),
            )),
            ("Keyd Stars", "SA", "топ-8", (
                ("FalleN", "awp"),
                ("Fer", "igl"),  # роль не подтверждена
                ("Steel", "entry"),  # роль не подтверждена
                ("Zqk", "support"),  # роль не подтверждена
                ("Boltz", "lurker"),  # роль не подтверждена
            )),
            ("Ninjas in Pyjamas", "EU", "финалист", (
                ("F0rest", "entry"),
                ("GeT RiGhT", "lurker"),
                ("Xizt", "igl"),
                ("Friberg", "awp"),  # роль не подтверждена
                ("Allu", "support"),  # роль не подтверждена
            )),
        ),
    },
    {
        "event": "ESL One Cologne 2015",
        "year": 2015,
        "era": "legacy",
        "teams": (
            ("Fnatic", "EU", "победитель", (
                ("JW", "awp"),
                ("Flusha", "support"),
                ("Pronax", "igl"),
                ("Olofmeister", "entry"),
                ("KRIMZ", "support"),
            )),
            ("FlipSid3 Tactics", "EEU", "топ-12", (
                ("B1ad3", "igl"),
                ("WorldEdit", "support"),  # роль не подтверждена
                ("Bondik", "entry"),
                ("Markeloff", "awp"),
                ("DavCost", "lurker"),  # роль не подтверждена
            )),
            ("Counter Logic Gaming", "NA", "топ-12", (
                ("ReltuC", "entry"),  # роль не подтверждена
                ("FNS", "igl"),
                ("Hazed", "support"),
                ("Tarik", "igl"),
                ("Jdm64", "awp"),
            )),
            ("Cloud9", "NA", "топ-12", (
                ("Sgares", "igl"),  # роль не подтверждена
                ("N0thing", "lurker"),
                ("Shroud", "entry"),  # роль не подтверждена
                ("Freakazoid", "support"),  # роль не подтверждена
                ("Skadoodle", "awp"),
            )),
            ("Renegades", "EU", "топ-12", (
                ("SPUNJ", "awp"),  # роль не подтверждена
                ("AZR", "igl"),  # роль не подтверждена
                ("Havoc", "entry"),  # роль не подтверждена
                ("Jks", "lurker"),
                ("Yam", "support"),  # роль не подтверждена
            )),
            ("Mousesports", "EU", "топ-16", (
                ("ChrisJ", "awp"),
                ("Gob b", "igl"),
                ("Denis", "entry"),
                ("Spiidi", "entry"),
                ("Nex", "support"),  # роль не подтверждена
            )),
            ("Team eBettle", "EU", "топ-16", (
                ("Furlan", "awp"),  # роль не подтверждена
                ("Hyper", "igl"),  # роль не подтверждена
                ("GruBy", "support"),  # роль не подтверждена
                ("Peet", "lurker"),  # роль не подтверждена
                ("Rallen", "entry"),
            )),
            ("Titan", "EU", "топ-16", (
                ("Ex6TenZ", "igl"),
                ("Maniac", "awp"),  # роль не подтверждена
                ("RpK", "support"),
                ("SmithZz", "entry"),  # роль не подтверждена
                ("Shox", "lurker"),
            )),
            ("Team Immunity", "EU", "топ-16", (
                ("SnypeR", "awp"),  # роль не подтверждена
                ("Rickeh", "igl"),  # роль не подтверждена
                ("James", "entry"),  # роль не подтверждена
                ("Emagine", "support"),  # роль не подтверждена
                ("USTILO", "lurker"),  # роль не подтверждена
            )),
            ("Virtus.pro", "EEU", "топ-4", (
                ("TaZ", "support"),
                ("NEO", "lurker"),
                ("PashaBiceps", "awp"),
                ("Snax", "entry"),
                ("Byali", "lurker"),
            )),
            ("Team SoloMid", "EU", "топ-4", (
                ("Dev1ce", "awp"),
                ("Dupreeh", "entry"),
                ("Xyp9x", "support"),
                ("Cajunb", "awp"),
                ("Karrigan", "igl"),
            )),
            ("Ninjas in Pyjamas", "EU", "топ-8", (
                ("F0rest", "entry"),
                ("GeT RiGhT", "lurker"),
                ("Xizt", "igl"),
                ("Friberg", "awp"),  # роль не подтверждена
                ("Allu", "support"),  # роль не подтверждена
            )),
            ("Luminosity Gaming", "EU", "топ-8", (
                ("FalleN", "awp"),
                ("Fer", "igl"),  # роль не подтверждена
                ("Steel", "entry"),  # роль не подтверждена
                ("Boltz", "support"),  # роль не подтверждена
                ("Coldzera", "lurker"),
            )),
            ("Natus Vincere", "EEU", "топ-8", (
                ("Zeus", "igl"),  # роль не подтверждена
                ("Seized", "lurker"),
                ("Edward", "support"),
                ("GuardiaN", "awp"),
                ("Flamie", "lurker"),
            )),
            ("Team Kinguin", "EU", "топ-8", (
                ("ScreaM", "entry"),
                ("Maikelele", "awp"),  # роль не подтверждена
                ("Rain", "entry"),
                ("Fox", "igl"),  # роль не подтверждена
                ("Dennis", "entry"),
            )),
            ("Team EnVyUs", "EU", "финалист", (
                ("Happy", "igl"),
                ("NBK-", "support"),
                ("KioShiMa", "support"),
                ("KennyS", "awp"),
                ("ApEX", "igl"),
            )),
        ),
    },
    {
        "event": "DreamHack Open Cluj-Napoca 2015",
        "year": 2015,
        "era": "legacy",
        "teams": (
            ("Team EnVyUs", "EU", "победитель", (
                ("Happy", "igl"),
                ("NBK-", "support"),
                ("KioShiMa", "support"),
                ("KennyS", "awp"),
                ("ApEX", "igl"),
            )),
            ("Cloud9", "NA", "топ-12", (
                ("N0thing", "lurker"),
                ("Sgares", "igl"),  # роль не подтверждена
                ("Shroud", "entry"),  # роль не подтверждена
                ("Freakazoid", "support"),  # роль не подтверждена
                ("Skadoodle", "awp"),
            )),
            ("Counter Logic Gaming", "NA", "топ-12", (
                ("ReltuC", "entry"),  # роль не подтверждена
                ("FNS", "igl"),
                ("Hazed", "support"),
                ("Tarik", "igl"),
                ("Jdm64", "awp"),
            )),
            ("Mousesports", "EU", "топ-12", (
                ("ChrisJ", "awp"),
                ("Gob b", "igl"),
                ("NiKo", "support"),  # роль не подтверждена
                ("Nex", "lurker"),  # роль не подтверждена
                ("Denis", "entry"),
            )),
            ("Titan", "EU", "топ-12", (
                ("Ex6TenZ", "igl"),
                ("RpK", "support"),
                ("Shox", "lurker"),
                ("SmithZz", "awp"),  # роль не подтверждена
                ("ScreaM", "entry"),
            )),
            ("Team Dignitas", "EU", "топ-16", (
                ("Aizy", "awp"),  # роль не подтверждена
                ("Kjaerbye", "entry"),  # роль не подтверждена
                ("Pimp", "lurker"),
                ("MSL", "igl"),
                ("Tenzki", "support"),  # роль не подтверждена
            )),
            ("FlipSid3 Tactics", "EEU", "топ-16", (
                ("B1ad3", "igl"),
                ("WorldEdit", "support"),  # роль не подтверждена
                ("Bondik", "entry"),
                ("Markeloff", "awp"),
                ("DavCost", "lurker"),  # роль не подтверждена
            )),
            ("Team Liquid", "NA", "топ-16", (
                ("AdreN", "igl"),
                ("Nitr0", "igl"),
                ("FugLy", "awp"),  # роль не подтверждена
                ("EliGE", "lurker"),
                ("Hiko", "lurker"),
            )),
            ("Vexed Gaming", "EU", "топ-16", (
                ("Furlan", "awp"),  # роль не подтверждена
                ("Hyper", "igl"),  # роль не подтверждена
                ("GruBy", "support"),  # роль не подтверждена
                ("Peet", "lurker"),  # роль не подтверждена
                ("Rallen", "entry"),
            )),
            ("G2 Esports", "EU", "топ-4", (
                ("Maikelele", "awp"),  # роль не подтверждена
                ("Fox", "igl"),  # роль не подтверждена
                ("Rain", "entry"),
                ("Dennis", "entry"),
                ("Jkaem", "entry"),
            )),
            ("Ninjas in Pyjamas", "EU", "топ-4", (
                ("F0rest", "entry"),
                ("GeT RiGhT", "lurker"),
                ("Xizt", "igl"),
                ("Friberg", "awp"),  # роль не подтверждена
                ("Allu", "support"),  # роль не подтверждена
            )),
            ("Fnatic", "EU", "топ-8", (
                ("JW", "awp"),
                ("Flusha", "support"),
                ("Pronax", "igl"),
                ("Olofmeister", "entry"),
                ("KRIMZ", "support"),
            )),
            ("Virtus.pro", "EEU", "топ-8", (
                ("TaZ", "support"),
                ("NEO", "lurker"),
                ("PashaBiceps", "awp"),
                ("Snax", "entry"),
                ("Byali", "lurker"),
            )),
            ("Team SoloMid", "EU", "топ-8", (
                ("Dev1ce", "awp"),
                ("Dupreeh", "entry"),
                ("Xyp9x", "support"),
                ("Cajunb", "awp"),
                ("Karrigan", "igl"),
            )),
            ("Luminosity Gaming", "EU", "топ-8", (
                ("FalleN", "awp"),
                ("Fer", "igl"),  # роль не подтверждена
                ("Boltz", "entry"),  # роль не подтверждена
                ("Steel", "support"),  # роль не подтверждена
                ("Coldzera", "lurker"),
            )),
            ("Natus Vincere", "EEU", "финалист", (
                ("Zeus", "igl"),  # роль не подтверждена
                ("Seized", "lurker"),
                ("Edward", "support"),
                ("GuardiaN", "awp"),
                ("Flamie", "lurker"),
            )),
        ),
    },
    {
        "event": "MLG Columbus 2016",
        "year": 2016,
        "era": "legacy",
        "teams": (
            ("Luminosity Gaming", "EU", "победитель", (
                ("FalleN", "awp"),
                ("Fer", "igl"),  # роль не подтверждена
                ("Coldzera", "lurker"),
                ("Fnx", "entry"),  # роль не подтверждена
                ("TACO", "support"),
            )),
            ("FaZe Clan", "EU", "топ-12", (
                ("Maikelele", "awp"),  # роль не подтверждена
                ("Rain", "entry"),
                ("Fox", "igl"),  # роль не подтверждена
                ("Jkaem", "entry"),
                ("Aizy", "support"),  # роль не подтверждена
            )),
            ("G2 Esports", "EU", "топ-12", (
                ("Ex6TenZ", "igl"),
                ("RpK", "support"),
                ("Shox", "lurker"),
                ("SmithZz", "awp"),  # роль не подтверждена
                ("ScreaM", "entry"),
            )),
            ("Mousesports", "EU", "топ-12", (
                ("NiKo", "igl"),  # роль не подтверждена
                ("ChrisJ", "awp"),
                ("Nex", "support"),  # роль не подтверждена
                ("Denis", "entry"),
                ("Spiidi", "entry"),
            )),
            ("Gambit Gaming", "EU", "топ-12", (
                ("Hooch", "awp"),  # роль не подтверждена
                ("Dosia", "lurker"),
                ("AdreN", "igl"),
                ("Mou", "lurker"),
                ("WayLander", "entry"),
            )),
            ("Team EnVyUs", "EU", "топ-16", (
                ("Happy", "igl"),
                ("NBK-", "support"),
                ("KennyS", "awp"),
                ("ApEX", "igl"),
                ("DEVIL", "entry"),  # роль не подтверждена
            )),
            ("Splyce", "EU", "топ-16", (
                ("Arya", "awp"),  # роль не подтверждена
                ("AbE", "igl"),  # роль не подтверждена
                ("JasonR", "entry"),  # роль не подтверждена
                ("Professor Chaos", "support"),  # роль не подтверждена
                ("DAVEY", "lurker"),  # роль не подтверждена
            )),
            ("FlipSid3 Tactics", "EEU", "топ-16", (
                ("B1ad3", "igl"),
                ("Bondik", "entry"),
                ("Markeloff", "awp"),
                ("Shara", "igl"),
                ("WorldEdit", "support"),  # роль не подтверждена
            )),
            ("Cloud9", "NA", "топ-16", (
                ("N0thing", "lurker"),
                ("Shroud", "igl"),  # роль не подтверждена
                ("Skadoodle", "awp"),
                ("Freakazoid", "entry"),  # роль не подтверждена
                ("Stewie2K", "lurker"),
            )),
            ("Astralis", "EU", "топ-4", (
                ("Dev1ce", "awp"),
                ("Dupreeh", "entry"),
                ("Xyp9x", "support"),
                ("Cajunb", "awp"),
                ("Karrigan", "igl"),
            )),
            ("Team Liquid", "NA", "топ-4", (
                ("Nitr0", "igl"),
                ("EliGE", "lurker"),
                ("Hiko", "lurker"),
                ("S1mple", "awp"),
                ("AdreN", "igl"),
            )),
            ("Ninjas in Pyjamas", "EU", "топ-8", (
                ("F0rest", "entry"),
                ("GeT RiGhT", "lurker"),
                ("Xizt", "igl"),
                ("Friberg", "awp"),  # роль не подтверждена
                ("THREAT", "support"),  # роль не подтверждена
            )),
            ("Fnatic", "EU", "топ-8", (
                ("Flusha", "support"),
                ("JW", "awp"),
                ("Olofmeister", "entry"),
                ("KRIMZ", "support"),
                ("Dennis", "entry"),
            )),
            ("Virtus.pro", "EEU", "топ-8", (
                ("TaZ", "support"),
                ("NEO", "lurker"),
                ("PashaBiceps", "awp"),
                ("Snax", "entry"),
                ("Byali", "lurker"),
            )),
            ("Counter Logic Gaming", "NA", "топ-8", (
                ("Hazed", "support"),
                ("Jdm64", "awp"),
                ("FugLy", "entry"),  # роль не подтверждена
                ("Tarik", "igl"),
                ("ReltuC", "lurker"),  # роль не подтверждена
            )),
            ("Natus Vincere", "EEU", "финалист", (
                ("Zeus", "igl"),  # роль не подтверждена
                ("Edward", "support"),
                ("Seized", "lurker"),
                ("Flamie", "lurker"),
                ("GuardiaN", "awp"),
            )),
        ),
    },
    {
        "event": "ESL One Cologne 2016",
        "year": 2016,
        "era": "legacy",
        "teams": (
            ("SK Gaming", "SA", "победитель", (
                ("FalleN", "awp"),
                ("Fer", "igl"),  # роль не подтверждена
                ("Coldzera", "lurker"),
                ("Fnx", "entry"),  # роль не подтверждена
                ("TACO", "support"),
            )),
            ("Ninjas in Pyjamas", "EU", "топ-12", (
                ("F0rest", "entry"),
                ("GeT RiGhT", "lurker"),
                ("Xizt", "igl"),
                ("Friberg", "awp"),  # роль не подтверждена
                ("Pyth", "support"),  # роль не подтверждена
            )),
            ("Mousesports", "EU", "топ-12", (
                ("ChrisJ", "awp"),
                ("NiKo", "igl"),  # роль не подтверждена
                ("Denis", "entry"),
                ("Nex", "support"),  # роль не подтверждена
                ("Spiidi", "entry"),
            )),
            ("FaZe Clan", "EU", "топ-12", (
                ("Rain", "entry"),
                ("Fox", "awp"),  # роль не подтверждена
                ("Jkaem", "entry"),
                ("Aizy", "igl"),  # роль не подтверждена
                ("KioShiMa", "support"),
            )),
            ("Team Dignitas", "EU", "топ-12", (
                ("MSL", "igl"),
                ("Tenzki", "entry"),  # роль не подтверждена
                ("K0nfig", "support"),  # роль не подтверждена
                ("RUBINO", "lurker"),  # роль не подтверждена
                ("Cajunb", "awp"),
            )),
            ("Counter Logic Gaming", "NA", "топ-16", (
                ("ReltuC", "awp"),  # роль не подтверждена
                ("Hazed", "support"),
                ("Tarik", "igl"),
                ("Koosta", "entry"),  # роль не подтверждена
                ("Pita", "support"),
            )),
            ("OpTic Gaming", "NA", "топ-16", (
                ("Daps", "igl"),
                ("RUSH", "awp"),  # роль не подтверждена
                ("NAF", "lurker"),
                ("Stanislaw", "igl"),
                ("Mixwell", "entry"),  # роль не подтверждена
            )),
            ("Team EnVyUs", "EU", "топ-16", (
                ("Happy", "igl"),
                ("NBK-", "support"),
                ("KennyS", "awp"),
                ("ApEX", "igl"),
                ("DEVIL", "entry"),  # роль не подтверждена
            )),
            ("G2 Esports", "EU", "топ-16", (
                ("RpK", "support"),
                ("SmithZz", "awp"),  # роль не подтверждена
                ("Shox", "lurker"),
                ("ScreaM", "entry"),
                ("Bodyy", "igl"),  # роль не подтверждена
            )),
            ("Fnatic", "EU", "топ-4", (
                ("JW", "awp"),
                ("Flusha", "support"),
                ("Olofmeister", "entry"),
                ("KRIMZ", "support"),
                ("Dennis", "entry"),
            )),
            ("Virtus.pro", "EEU", "топ-4", (
                ("TaZ", "support"),
                ("NEO", "lurker"),
                ("PashaBiceps", "awp"),
                ("Snax", "entry"),
                ("Byali", "lurker"),
            )),
            ("Natus Vincere", "EEU", "топ-8", (
                ("Zeus", "igl"),  # роль не подтверждена
                ("Seized", "lurker"),
                ("Edward", "support"),
                ("GuardiaN", "awp"),
                ("Flamie", "lurker"),
            )),
            ("Astralis", "EU", "топ-8", (
                ("Dev1ce", "awp"),
                ("Dupreeh", "entry"),
                ("Xyp9x", "support"),
                ("Karrigan", "igl"),
                ("Gla1ve", "igl"),
            )),
            ("Gambit Gaming", "EU", "топ-8", (
                ("Hooch", "awp"),  # роль не подтверждена
                ("Dosia", "lurker"),
                ("AdreN", "igl"),
                ("Mou", "lurker"),
                ("Spaze", "entry"),  # роль не подтверждена
            )),
            ("FlipSid3 Tactics", "EEU", "топ-8", (
                ("B1ad3", "igl"),
                ("WorldEdit", "support"),  # роль не подтверждена
                ("Markeloff", "awp"),
                ("Shara", "igl"),
                ("WayLander", "entry"),
            )),
            ("Team Liquid", "NA", "финалист", (
                ("Nitr0", "igl"),
                ("EliGE", "lurker"),
                ("Hiko", "lurker"),
                ("S1mple", "awp"),
                ("Jdm64", "awp"),
            )),
        ),
    },
    {
        "event": "ELEAGUE Atlanta 2017",
        "year": 2017,
        "era": "legacy",
        "teams": (
            ("Astralis", "EU", "победитель", (
                ("Dev1ce", "awp"),
                ("Dupreeh", "entry"),
                ("Xyp9x", "support"),
                ("Kjaerbye", "lurker"),  # роль не подтверждена
                ("Gla1ve", "igl"),
            )),
            ("Team Liquid", "NA", "топ-12", (
                ("Nitr0", "igl"),
                ("EliGE", "lurker"),
                ("Hiko", "lurker"),
                ("Jdm64", "awp"),
                ("Pimp", "lurker"),
            )),
            ("GODSENT", "EU", "топ-12", (
                ("Pronax", "igl"),
                ("Znajder", "lurker"),  # роль не подтверждена
                ("Flusha", "support"),
                ("JW", "awp"),
                ("Lekr0", "entry"),
            )),
            ("Mousesports", "EU", "топ-12", (
                ("ChrisJ", "awp"),
                ("NiKo", "igl"),  # роль не подтверждена
                ("Denis", "entry"),
                ("Spiidi", "entry"),
                ("LoWel", "support"),  # роль не подтверждена
            )),
            ("OpTic Gaming", "NA", "топ-12", (
                ("NAF", "lurker"),
                ("RUSH", "awp"),  # роль не подтверждена
                ("Mixwell", "entry"),  # роль не подтверждена
                ("Tarik", "igl"),
                ("Stanislaw", "igl"),
            )),
            ("Team EnVyUs", "EU", "топ-12", (
                ("Happy", "igl"),
                ("NBK-", "support"),
                ("KennyS", "awp"),
                ("ApEX", "igl"),
                ("SIXER", "entry"),  # роль не подтверждена
            )),
            ("G2 Esports", "EU", "топ-12", (
                ("Shox", "lurker"),
                ("RpK", "support"),
                ("SmithZz", "awp"),  # роль не подтверждена
                ("ScreaM", "entry"),
                ("Bodyy", "igl"),  # роль не подтверждена
            )),
            ("FlipSid3 Tactics", "EEU", "топ-16", (
                ("B1ad3", "igl"),
                ("Markeloff", "awp"),
                ("WorldEdit", "support"),  # роль не подтверждена
                ("WayLander", "entry"),
                ("ElectroNic", "lurker"),  # роль не подтверждена
            )),
            ("HellRaisers", "EEU", "топ-16", (
                ("ANGE1", "igl"),
                ("STYKO", "support"),
                ("Zero", "awp"),  # роль не подтверждена
                ("Bondik", "entry"),
                ("DeadFox", "lurker"),  # роль не подтверждена
            )),
            ("SK Gaming", "SA", "топ-4", (
                ("FalleN", "awp"),
                ("Fer", "igl"),  # роль не подтверждена
                ("Coldzera", "lurker"),
                ("TACO", "support"),
                ("Fox", "entry"),  # роль не подтверждена
            )),
            ("Fnatic", "EU", "топ-4", (
                ("Olofmeister", "entry"),
                ("Dennis", "entry"),
                ("Twist", "awp"),
                ("KRIMZ", "support"),
                ("Disco doplan", "igl"),  # роль не подтверждена
            )),
            ("Natus Vincere", "EEU", "топ-8", (
                ("Seized", "lurker"),
                ("Edward", "support"),
                ("GuardiaN", "awp"),
                ("Flamie", "lurker"),
                ("S1mple", "awp"),
            )),
            ("Gambit Esports", "EEU", "топ-8", (
                ("Dosia", "lurker"),
                ("AdreN", "igl"),
                ("Mou", "lurker"),
                ("Zeus", "awp"),  # роль не подтверждена
                ("HObbit", "lurker"),
            )),
            ("FaZe Clan", "EU", "топ-8", (
                ("Rain", "entry"),
                ("Aizy", "awp"),  # роль не подтверждена
                ("Allu", "lurker"),  # роль не подтверждена
                ("Karrigan", "igl"),
                ("KioShiMa", "support"),
            )),
            ("North", "EU", "топ-8", (
                ("MSL", "igl"),
                ("K0nfig", "entry"),  # роль не подтверждена
                ("RUBINO", "support"),  # роль не подтверждена
                ("Cajunb", "awp"),
                ("Magisk", "lurker"),  # роль не подтверждена
            )),
            ("Virtus.pro", "EEU", "финалист", (
                ("TaZ", "support"),
                ("NEO", "lurker"),
                ("PashaBiceps", "awp"),
                ("Snax", "entry"),
                ("Byali", "lurker"),
            )),
        ),
    },
    {
        "event": "PGL Kraków 2017",
        "year": 2017,
        "era": "legacy",
        "teams": (
            ("Gambit Esports", "EEU", "победитель", (
                ("Dosia", "lurker"),
                ("AdreN", "igl"),
                ("Mou", "lurker"),
                ("Zeus", "awp"),  # роль не подтверждена
                ("HObbit", "lurker"),
            )),
            ("Natus Vincere", "EEU", "топ-12", (
                ("Seized", "lurker"),
                ("GuardiaN", "awp"),
                ("Edward", "support"),
                ("Flamie", "lurker"),
                ("S1mple", "awp"),
            )),
            ("Mousesports", "EU", "топ-12", (
                ("ChrisJ", "awp"),
                ("Denis", "entry"),
                ("Oskar", "awp"),
                ("LoWel", "igl"),  # роль не подтверждена
                ("Ropz", "lurker"),
            )),
            ("G2 Esports", "EU", "топ-12", (
                ("Shox", "lurker"),
                ("Bodyy", "entry"),  # роль не подтверждена
                ("NBK-", "support"),
                ("KennyS", "awp"),
                ("ApEX", "igl"),
            )),
            ("Cloud9", "NA", "топ-12", (
                ("N0thing", "lurker"),
                ("Shroud", "igl"),  # роль не подтверждена
                ("Skadoodle", "awp"),
                ("Stewie2K", "lurker"),
                ("Autimatic", "entry"),  # роль не подтверждена
            )),
            ("PENTA Sports", "EU", "топ-12", (
                ("KRYSTAL", "awp"),  # роль не подтверждена
                ("SuNny", "entry"),
                ("HS", "igl"),  # роль не подтверждена
                ("Innocent", "support"),  # роль не подтверждена
                ("ZehN", "lurker"),  # роль не подтверждена
            )),
            ("FlipSid3 Tactics", "EEU", "топ-12", (
                ("B1ad3", "igl"),
                ("WorldEdit", "support"),  # роль не подтверждена
                ("Markeloff", "awp"),
                ("WayLander", "entry"),
                ("ElectroNic", "lurker"),  # роль не подтверждена
            )),
            ("FaZe Clan", "EU", "топ-16", (
                ("Rain", "entry"),
                ("Allu", "awp"),  # роль не подтверждена
                ("Karrigan", "igl"),
                ("KioShiMa", "support"),
                ("NiKo", "lurker"),  # роль не подтверждена
            )),
            ("Vega Squadron", "EEU", "топ-16", (
                ("Mir", "entry"),
                ("Chopper", "igl"),
                ("JR", "awp"),  # роль не подтверждена
                ("Keshandr", "support"),  # роль не подтверждена
                ("Hutji", "entry"),
            )),
            ("Astralis", "EU", "топ-4", (
                ("Dev1ce", "awp"),
                ("Dupreeh", "entry"),
                ("Xyp9x", "support"),
                ("Kjaerbye", "lurker"),  # роль не подтверждена
                ("Gla1ve", "igl"),
            )),
            ("Virtus.pro", "EEU", "топ-4", (
                ("TaZ", "support"),
                ("NEO", "lurker"),
                ("PashaBiceps", "awp"),
                ("Snax", "entry"),
                ("Byali", "lurker"),
            )),
            ("Fnatic", "EU", "топ-8", (
                ("Olofmeister", "entry"),
                ("Dennis", "entry"),
                ("KRIMZ", "support"),
                ("JW", "awp"),
                ("Flusha", "support"),
            )),
            ("SK Gaming", "SA", "топ-8", (
                ("FalleN", "awp"),
                ("Fer", "igl"),  # роль не подтверждена
                ("Coldzera", "lurker"),
                ("TACO", "support"),
                ("Felps", "entry"),  # роль не подтверждена
            )),
            ("North", "EU", "топ-8", (
                ("MSL", "igl"),
                ("K0nfig", "entry"),  # роль не подтверждена
                ("Cajunb", "awp"),
                ("Magisk", "support"),  # роль не подтверждена
                ("Aizy", "lurker"),  # роль не подтверждена
            )),
            ("BIG", "EU", "топ-8", (
                ("Gob b", "igl"),
                ("LEGIJA", "awp"),  # роль не подтверждена
                ("TabseN", "entry"),  # роль не подтверждена
                ("Nex", "support"),  # роль не подтверждена
                ("Keev", "lurker"),  # роль не подтверждена
            )),
            ("Immortals", "SA", "финалист", (
                ("HEN1", "awp"),  # роль не подтверждена
                ("LUCAS1", "entry"),
                ("Boltz", "igl"),  # роль не подтверждена
                ("Steel", "support"),  # роль не подтверждена
                ("KNgV-", "lurker"),  # роль не подтверждена
            )),
        ),
    },
    {
        "event": "ELEAGUE Boston 2018",
        "year": 2018,
        "era": "legacy",
        "teams": (
            ("Immortals", "SA", "группа", (
                ("HEN1", "awp"),  # роль не подтверждена
                ("LUCAS1", "entry"),
                ("Boltz", "igl"),  # роль не подтверждена
                ("Steel", "support"),  # роль не подтверждена
                ("KNgV-", "lurker"),  # роль не подтверждена
            )),
            ("FlipSid3 Tactics", "EEU", "группа", (
                ("B1ad3", "igl"),
                ("WorldEdit", "support"),  # роль не подтверждена
                ("Markeloff", "awp"),
                ("WayLander", "entry"),
                ("Seized", "lurker"),
            )),
            ("Sprout", "EU", "группа", (
                ("KRYSTAL", "awp"),  # роль не подтверждена
                ("Innocent", "igl"),  # роль не подтверждена
                ("ZehN", "support"),  # роль не подтверждена
                ("Denis", "entry"),
                ("Spiidi", "entry"),
            )),
            ("AVANGAR", "EEU", "группа", (
                ("Buster", "entry"),
                ("KrizzeN", "igl"),  # роль не подтверждена
                ("Qikert", "support"),
                ("Dimasick", "lurker"),  # роль не подтверждена
                ("Jame", "awp"),
            )),
            ("Renegades", "EU", "группа", (
                ("AZR", "awp"),  # роль не подтверждена
                ("Jks", "lurker"),
                ("USTILO", "igl"),  # роль не подтверждена
                ("Nifty", "entry"),  # роль не подтверждена
                ("NAF", "lurker"),
            )),
            ("Team Envy", "EU", "группа", (
                ("Happy", "igl"),
                ("SIXER", "awp"),  # роль не подтверждена
                ("RpK", "support"),
                ("Xms", "lurker"),  # роль не подтверждена
                ("ScreaM", "entry"),
            )),
            ("Misfits Gaming", "EU", "группа", (
                ("Sgares", "igl"),  # роль не подтверждена
                ("SicK", "entry"),  # роль не подтверждена
                ("ShahZaM", "awp"),
                ("AMANEK", "support"),
                ("Devoduvek", "lurker"),  # роль не подтверждена
            )),
            ("Flash Gaming", "EU", "группа", (
                ("Summer", "lurker"),
                ("Karsa", "awp"),  # роль не подтверждена
                ("LOVEYY", "igl"),  # роль не подтверждена
                ("Attacker", "entry"),
                ("Kaze", "support"),  # роль не подтверждена
            )),
            ("TYLOO", "CN", "группа", (
                ("CaptainMo", "awp"),  # роль не подтверждена
                ("DD", "igl"),  # роль не подтверждена
                ("Somebody", "support"),
                ("BnTeT", "entry"),
                ("Bondik", "entry"),
            )),
            ("Cloud9", "NA", "победитель", (
                ("Skadoodle", "awp"),
                ("Stewie2K", "lurker"),
                ("Autimatic", "entry"),  # роль не подтверждена
                ("RUSH", "support"),  # роль не подтверждена
                ("Tarik", "igl"),
            )),
            ("Gambit Esports", "EEU", "топ-12", (
                ("Dosia", "lurker"),
                ("AdreN", "igl"),
                ("Mou", "lurker"),
                ("HObbit", "lurker"),
                ("Fitch", "entry"),
            )),
            ("Astralis", "EU", "топ-12", (
                ("Dev1ce", "awp"),
                ("Dupreeh", "entry"),
                ("Xyp9x", "support"),
                ("Kjaerbye", "lurker"),  # роль не подтверждена
                ("Gla1ve", "igl"),
            )),
            ("BIG", "EU", "топ-12", (
                ("Gob b", "igl"),
                ("LEGIJA", "awp"),  # роль не подтверждена
                ("TabseN", "entry"),  # роль не подтверждена
                ("Nex", "support"),  # роль не подтверждена
                ("Keev", "lurker"),  # роль не подтверждена
            )),
            ("Vega Squadron", "EEU", "топ-12", (
                ("Mir", "entry"),
                ("Chopper", "igl"),
                ("JR", "awp"),  # роль не подтверждена
                ("Keshandr", "support"),  # роль не подтверждена
                ("Hutji", "entry"),
            )),
            ("Space Soldiers", "EU", "топ-12", (
                ("XANTARES", "entry"),
                ("NgiN", "awp"),  # роль не подтверждена
                ("Paz", "igl"),  # роль не подтверждена
                ("MAJ3R", "support"),  # роль не подтверждена
                ("Calyx", "entry"),
            )),
            ("Team Liquid", "NA", "топ-12", (
                ("Nitr0", "igl"),
                ("EliGE", "lurker"),
                ("Jdm64", "awp"),
                ("Twistzz", "lurker"),
                ("Zews", "support"),
            )),
            ("Virtus.pro", "EEU", "топ-16", (
                ("TaZ", "support"),
                ("NEO", "lurker"),
                ("PashaBiceps", "awp"),
                ("Snax", "entry"),
                ("Byali", "lurker"),
            )),
            ("North", "EU", "топ-16", (
                ("MSL", "igl"),
                ("K0nfig", "entry"),  # роль не подтверждена
                ("Cajunb", "awp"),
                ("Aizy", "support"),  # роль не подтверждена
                ("Valde", "lurker"),
            )),
            ("SK Gaming", "SA", "топ-4", (
                ("FalleN", "awp"),
                ("Fer", "igl"),  # роль не подтверждена
                ("Coldzera", "lurker"),
                ("TACO", "support"),
                ("Felps", "entry"),  # роль не подтверждена
            )),
            ("Natus Vincere", "EEU", "топ-4", (
                ("Edward", "support"),
                ("Flamie", "lurker"),
                ("S1mple", "awp"),
                ("Zeus", "igl"),  # роль не подтверждена
                ("ElectroNic", "entry"),  # роль не подтверждена
            )),
            ("Fnatic", "EU", "топ-8", (
                ("KRIMZ", "support"),
                ("JW", "awp"),
                ("Flusha", "support"),
                ("Golden", "igl"),
                ("Lekr0", "entry"),
            )),
            ("G2 Esports", "EU", "топ-8", (
                ("Shox", "lurker"),
                ("Bodyy", "entry"),  # роль не подтверждена
                ("NBK-", "support"),
                ("KennyS", "awp"),
                ("ApEX", "igl"),
            )),
            ("Mousesports", "EU", "топ-8", (
                ("ChrisJ", "awp"),
                ("Oskar", "awp"),
                ("Ropz", "lurker"),
                ("SuNny", "entry"),
                ("STYKO", "support"),
            )),
            ("Quantum Bellator Fire", "EU", "топ-8", (
                ("Balblna", "awp"),  # роль не подтверждена
                ("Kvik", "igl"),  # роль не подтверждена
                ("Jmqa", "support"),  # роль не подтверждена
                ("WaterfaLLZ", "entry"),
                ("Boombl4", "lurker"),  # роль не подтверждена
            )),
            ("FaZe Clan", "EU", "финалист", (
                ("Rain", "entry"),
                ("Karrigan", "igl"),
                ("NiKo", "support"),  # роль не подтверждена
                ("GuardiaN", "awp"),
                ("Olofmeister", "entry"),
            )),
        ),
    },
    {
        "event": "FACEIT London 2018",
        "year": 2018,
        "era": "legacy",
        "teams": (
            ("Gambit Esports", "EEU", "группа", (
                ("Dosia", "lurker"),
                ("AdreN", "igl"),
                ("Mou", "lurker"),
                ("HObbit", "lurker"),
                ("Mir", "entry"),
            )),
            ("Space Soldiers", "EU", "группа", (
                ("XANTARES", "entry"),
                ("Paz", "awp"),  # роль не подтверждена
                ("MAJ3R", "igl"),  # роль не подтверждена
                ("Calyx", "entry"),
                ("Hardstyle", "support"),  # роль не подтверждена
            )),
            ("North", "EU", "группа", (
                ("MSL", "igl"),
                ("Aizy", "awp"),  # роль не подтверждена
                ("Valde", "lurker"),
                ("Kjaerbye", "entry"),  # роль не подтверждена
                ("Niko", "support"),  # роль не подтверждена
            )),
            ("Virtus.pro", "EEU", "группа", (
                ("NEO", "lurker"),
                ("PashaBiceps", "awp"),
                ("Byali", "lurker"),
                ("MICHU", "entry"),
                ("Snatchie", "igl"),  # роль не подтверждена
            )),
            ("Renegades", "EU", "группа", (
                ("AZR", "awp"),  # роль не подтверждена
                ("Jks", "lurker"),
                ("USTILO", "igl"),  # роль не подтверждена
                ("Nifty", "support"),  # роль не подтверждена
                ("Jkaem", "entry"),
            )),
            ("OpTic Gaming", "NA", "группа", (
                ("K0nfig", "entry"),  # роль не подтверждена
                ("Cajunb", "awp"),
                ("Gade", "lurker"),
                ("Snappi", "igl"),
                ("JUGi", "support"),  # роль не подтверждена
            )),
            ("Rogue", "EU", "группа", (
                ("Vice", "awp"),  # роль не подтверждена
                ("Hiko", "lurker"),
                ("CadiaN", "igl"),
                ("SicK", "entry"),  # роль не подтверждена
                ("Rickeh", "support"),  # роль не подтверждена
            )),
            ("Team Spirit", "EEU", "группа", (
                ("COLDYY1", "awp"),  # роль не подтверждена
                ("S0tF1k", "igl"),  # роль не подтверждена
                ("DavCost", "support"),  # роль не подтверждена
                ("Dimaoneshot", "lurker"),  # роль не подтверждена
                ("Sdy", "entry"),
            )),
            ("Astralis", "EU", "победитель", (
                ("Dev1ce", "awp"),
                ("Dupreeh", "entry"),
                ("Xyp9x", "support"),
                ("Gla1ve", "igl"),
                ("Magisk", "lurker"),  # роль не подтверждена
            )),
            ("Cloud9", "NA", "топ-12", (
                ("Skadoodle", "awp"),
                ("Autimatic", "entry"),  # роль не подтверждена
                ("RUSH", "lurker"),  # роль не подтверждена
                ("Golden", "igl"),
                ("STYKO", "support"),
            )),
            ("G2 Esports", "EU", "топ-12", (
                ("Shox", "lurker"),
                ("Bodyy", "entry"),  # роль не подтверждена
                ("KennyS", "awp"),
                ("SmithZz", "support"),  # роль не подтверждена
                ("Ex6TenZ", "igl"),
            )),
            ("Fnatic", "EU", "топ-12", (
                ("KRIMZ", "support"),
                ("JW", "awp"),
                ("Flusha", "support"),
                ("Xizt", "igl"),
                ("Draken", "awp"),
            )),
            ("Vega Squadron", "EEU", "топ-12", (
                ("Chopper", "igl"),
                ("JR", "awp"),  # роль не подтверждена
                ("Hutji", "entry"),
                ("Crush", "support"),  # роль не подтверждена
                ("Tonyblack", "lurker"),  # роль не подтверждена
            )),
            ("Ninjas in Pyjamas", "EU", "топ-12", (
                ("F0rest", "entry"),
                ("GeT RiGhT", "lurker"),
                ("REZ", "entry"),
                ("Dennis", "entry"),
                ("Lekr0", "entry"),
            )),
            ("TYLOO", "CN", "топ-12", (
                ("CaptainMo", "awp"),  # роль не подтверждена
                ("DD", "igl"),  # роль не подтверждена
                ("Somebody", "support"),
                ("BnTeT", "entry"),
                ("Xccurate", "lurker"),  # роль не подтверждена
            )),
            ("Mousesports", "EU", "топ-16", (
                ("ChrisJ", "awp"),
                ("Oskar", "awp"),
                ("Ropz", "lurker"),
                ("SuNny", "entry"),
                ("Snax", "entry"),
            )),
            ("Winstrike Team", "EU", "топ-16", (
                ("Balblna", "awp"),  # роль не подтверждена
                ("Kvik", "igl"),  # роль не подтверждена
                ("Jmqa", "support"),  # роль не подтверждена
                ("WaterfaLLZ", "entry"),
                ("Boombl4", "lurker"),  # роль не подтверждена
            )),
            ("MIBR", "SA", "топ-4", (
                ("FalleN", "awp"),
                ("Fer", "entry"),  # роль не подтверждена
                ("Coldzera", "lurker"),
                ("Stewie2K", "lurker"),
                ("Tarik", "igl"),
            )),
            ("Team Liquid", "NA", "топ-4", (
                ("Nitr0", "igl"),
                ("EliGE", "lurker"),
                ("Twistzz", "lurker"),
                ("NAF", "lurker"),
                ("TACO", "support"),
            )),
            ("FaZe Clan", "EU", "топ-8", (
                ("Rain", "entry"),
                ("Karrigan", "igl"),
                ("NiKo", "support"),  # роль не подтверждена
                ("GuardiaN", "awp"),
                ("Olofmeister", "entry"),
            )),
            ("BIG", "EU", "топ-8", (
                ("Gob b", "igl"),
                ("TabseN", "support"),  # роль не подтверждена
                ("Nex", "lurker"),  # роль не подтверждена
                ("TiziaN", "entry"),
                ("Smooya", "awp"),
            )),
            ("CompLexity Gaming", "NA", "топ-8", (
                ("Dephh", "entry"),  # роль не подтверждена
                ("ANDROID", "support"),  # роль не подтверждена
                ("Yay", "lurker"),  # роль не подтверждена
                ("Stanislaw", "igl"),
                ("ShahZaM", "awp"),
            )),
            ("HellRaisers", "EEU", "топ-8", (
                ("ANGE1", "igl"),
                ("Bondik", "entry"),
                ("DeadFox", "lurker"),  # роль не подтверждена
                ("Woxic", "awp"),
                ("ISSAA", "support"),
            )),
            ("Natus Vincere", "EEU", "финалист", (
                ("Edward", "support"),
                ("Flamie", "lurker"),
                ("S1mple", "awp"),
                ("Zeus", "igl"),  # роль не подтверждена
                ("ElectroNic", "entry"),  # роль не подтверждена
            )),
        ),
    },
    {
        "event": "IEM Katowice 2019",
        "year": 2019,
        "era": "legacy",
        "teams": (
            ("Fnatic", "EU", "группа", (
                ("KRIMZ", "support"),
                ("JW", "awp"),
                ("Xizt", "igl"),
                ("Twist", "awp"),
                ("Brollan", "entry"),  # роль не подтверждена
            )),
            ("Vega Squadron", "EEU", "группа", (
                ("Chopper", "igl"),
                ("JR", "awp"),  # роль не подтверждена
                ("Hutji", "entry"),
                ("Crush", "support"),  # роль не подтверждена
                ("Tonyblack", "lurker"),  # роль не подтверждена
            )),
            ("TYLOO", "CN", "группа", (
                ("Somebody", "support"),
                ("BnTeT", "entry"),
                ("Xccurate", "awp"),  # роль не подтверждена
                ("Summer", "lurker"),
                ("Attacker", "entry"),
            )),
            ("FURIA Esports", "EU", "группа", (
                ("Yuurih", "awp"),  # роль не подтверждена
                ("ArT", "igl"),
                ("VINI", "support"),
                ("KSCERATO", "entry"),  # роль не подтверждена
                ("AbleJ", "lurker"),  # роль не подтверждена
            )),
            ("Team Spirit", "EEU", "группа", (
                ("COLDYY1", "awp"),  # роль не подтверждена
                ("S0tF1k", "igl"),  # роль не подтверждена
                ("DavCost", "support"),  # роль не подтверждена
                ("Dimaoneshot", "lurker"),  # роль не подтверждена
                ("Sdy", "entry"),
            )),
            ("Grayhound Gaming", "EU", "группа", (
                ("ErkaSt", "awp"),  # роль не подтверждена
                ("Dexter", "igl"),  # роль не подтверждена
                ("DickStacy", "entry"),  # роль не подтверждена
                ("Malta", "support"),  # роль не подтверждена
                ("Sterling", "lurker"),  # роль не подтверждена
            )),
            ("Winstrike Team", "EU", "группа", (
                ("Boombl4", "awp"),  # роль не подтверждена
                ("Kvik", "igl"),  # роль не подтверждена
                ("N0rb3r7", "support"),  # роль не подтверждена
                ("WorldEdit", "lurker"),  # роль не подтверждена
                ("WayLander", "entry"),
            )),
            ("ViCi Gaming", "CN", "группа", (
                ("ZhokiNg", "awp"),  # роль не подтверждена
                ("Freeman", "igl"),  # роль не подтверждена
                ("AumaN", "entry"),  # роль не подтверждена
                ("Advent", "support"),  # роль не подтверждена
                ("Kaze", "lurker"),  # роль не подтверждена
            )),
            ("Astralis", "EU", "победитель", (
                ("Dev1ce", "awp"),
                ("Dupreeh", "entry"),
                ("Xyp9x", "support"),
                ("Gla1ve", "igl"),
                ("Magisk", "lurker"),  # роль не подтверждена
            )),
            ("CompLexity Gaming", "NA", "топ-12", (
                ("Dephh", "entry"),  # роль не подтверждена
                ("Stanislaw", "igl"),
                ("ShahZaM", "awp"),
                ("Rickeh", "support"),  # роль не подтверждена
                ("N0thing", "lurker"),
            )),
            ("HellRaisers", "EEU", "топ-12", (
                ("ANGE1", "igl"),
                ("DeadFox", "entry"),  # роль не подтверждена
                ("Woxic", "awp"),
                ("ISSAA", "support"),
                ("HObbit", "lurker"),
            )),
            ("G2 Esports", "EU", "топ-12", (
                ("Shox", "lurker"),
                ("Bodyy", "igl"),  # роль не подтверждена
                ("KennyS", "awp"),
                ("Lucky", "entry"),  # роль не подтверждена
                ("JACKZ", "support"),  # роль не подтверждена
            )),
            ("Cloud9", "NA", "топ-12", (
                ("Autimatic", "awp"),  # роль не подтверждена
                ("RUSH", "igl"),  # роль не подтверждена
                ("Flusha", "support"),
                ("KioShiMa", "support"),
                ("Zellsis", "entry"),  # роль не подтверждена
            )),
            ("AVANGAR", "EEU", "топ-12", (
                ("Buster", "entry"),
                ("KrizzeN", "igl"),  # роль не подтверждена
                ("Qikert", "support"),
                ("Jame", "awp"),
                ("Fitch", "entry"),
            )),
            ("Team Vitality", "EU", "топ-12", (
                ("NBK-", "support"),
                ("ApEX", "igl"),
                ("RpK", "support"),
                ("ZywOo", "awp"),
                ("ALEX", "igl"),
            )),
            ("BIG", "EU", "топ-16", (
                ("Gob b", "igl"),
                ("TabseN", "awp"),  # роль не подтверждена
                ("Nex", "support"),  # роль не подтверждена
                ("TiziaN", "entry"),
                ("XANTARES", "entry"),
            )),
            ("NRG Esports", "NA", "топ-16", (
                ("FugLy", "entry"),  # роль не подтверждена
                ("Daps", "igl"),
                ("Brehze", "support"),  # роль не подтверждена
                ("CeRq", "awp"),
                ("Ethan", "lurker"),
            )),
            ("Natus Vincere", "EEU", "топ-4", (
                ("Edward", "support"),
                ("Flamie", "lurker"),
                ("S1mple", "awp"),
                ("Zeus", "igl"),  # роль не подтверждена
                ("ElectroNic", "entry"),  # роль не подтверждена
            )),
            ("MIBR", "SA", "топ-4", (
                ("FalleN", "awp"),
                ("Fer", "igl"),  # роль не подтверждена
                ("Coldzera", "lurker"),
                ("TACO", "support"),
                ("Felps", "entry"),  # роль не подтверждена
            )),
            ("Team Liquid", "NA", "топ-8", (
                ("Nitr0", "igl"),
                ("EliGE", "lurker"),
                ("Twistzz", "lurker"),
                ("NAF", "lurker"),
                ("Stewie2K", "lurker"),
            )),
            ("FaZe Clan", "EU", "топ-8", (
                ("Rain", "entry"),
                ("NiKo", "support"),  # роль не подтверждена
                ("GuardiaN", "awp"),
                ("Olofmeister", "entry"),
                ("AdreN", "igl"),
            )),
            ("Ninjas in Pyjamas", "EU", "топ-8", (
                ("F0rest", "entry"),
                ("GeT RiGhT", "lurker"),
                ("REZ", "entry"),
                ("Dennis", "entry"),
                ("Lekr0", "entry"),
            )),
            ("Renegades", "EU", "топ-8", (
                ("AZR", "awp"),  # роль не подтверждена
                ("Jks", "lurker"),
                ("Jkaem", "entry"),
                ("Liazz", "support"),
                ("Gratisfaction", "igl"),  # роль не подтверждена
            )),
            ("ENCE", "EU", "финалист", (
                ("Allu", "awp"),  # роль не подтверждена
                ("Aleksib", "igl"),  # роль не подтверждена
                ("Sergej", "entry"),
                ("Aerial", "support"),  # роль не подтверждена
                ("XseveN", "entry"),
            )),
        ),
    },
    {
        "event": "StarLadder Berlin 2019",
        "year": 2019,
        "era": "legacy",
        "teams": (
            ("HellRaisers", "EEU", "группа", (
                ("ANGE1", "igl"),
                ("ISSAA", "support"),
                ("Oskar", "awp"),
                ("LoWel", "entry"),  # роль не подтверждена
                ("Nukkye", "lurker"),
            )),
            ("Complexity Gaming", "NA", "группа", (
                ("Dephh", "igl"),  # роль не подтверждена
                ("ShahZaM", "awp"),
                ("Rickeh", "entry"),  # роль не подтверждена
                ("SicK", "support"),  # роль не подтверждена
                ("OBo", "lurker"),  # роль не подтверждена
            )),
            ("ForZe", "EEU", "группа", (
                ("Facecrack", "igl"),  # роль не подтверждена
                ("Jerry", "entry"),  # роль не подтверждена
                ("Almazer", "lurker"),  # роль не подтверждена
                ("Xsepower", "awp"),
                ("FL1T", "support"),
            )),
            ("Grayhound Gaming", "EU", "группа", (
                ("ErkaSt", "awp"),  # роль не подтверждена
                ("Dexter", "igl"),  # роль не подтверждена
                ("DickStacy", "entry"),  # роль не подтверждена
                ("Malta", "support"),  # роль не подтверждена
                ("Sico", "lurker"),  # роль не подтверждена
            )),
            ("FURIA Esports", "EU", "группа", (
                ("Yuurih", "awp"),  # роль не подтверждена
                ("ArT", "igl"),
                ("VINI", "support"),
                ("KSCERATO", "entry"),  # роль не подтверждена
                ("AbleJ", "lurker"),  # роль не подтверждена
            )),
            ("Syman Gaming", "EU", "группа", (
                ("NeaLaN", "awp"),  # роль не подтверждена
                ("T0rick", "igl"),  # роль не подтверждена
                ("Perfecto", "support"),
                ("Ramz1k", "entry"),  # роль не подтверждена
                ("Keoz", "lurker"),  # роль не подтверждена
            )),
            ("TYLOO", "CN", "группа", (
                ("Somebody", "support"),
                ("BnTeT", "entry"),
                ("Summer", "lurker"),
                ("Attacker", "entry"),
                ("Freeman", "awp"),  # роль не подтверждена
            )),
            ("INTZ", "EU", "группа", (
                ("KNgV-", "awp"),  # роль не подтверждена
                ("Chelo", "igl"),  # роль не подтверждена
                ("Xand", "entry"),  # роль не подтверждена
                ("Destiny", "support"),  # роль не подтверждена
                ("Yel", "lurker"),  # роль не подтверждена
            )),
            ("Astralis", "EU", "победитель", (
                ("Dev1ce", "awp"),
                ("Dupreeh", "entry"),
                ("Xyp9x", "support"),
                ("Gla1ve", "igl"),
                ("Magisk", "lurker"),  # роль не подтверждена
            )),
            ("MIBR", "SA", "топ-12", (
                ("FalleN", "awp"),
                ("Fer", "igl"),  # роль не подтверждена
                ("TACO", "support"),
                ("LUCAS1", "entry"),
                ("Zews", "support"),
            )),
            ("FaZe Clan", "EU", "топ-12", (
                ("Rain", "entry"),
                ("NiKo", "igl"),  # роль не подтверждена
                ("GuardiaN", "awp"),
                ("Olofmeister", "entry"),
                ("NEO", "lurker"),
            )),
            ("G2 Esports", "EU", "топ-12", (
                ("Shox", "lurker"),
                ("KennyS", "awp"),
                ("Lucky", "igl"),  # роль не подтверждена
                ("JACKZ", "entry"),  # роль не подтверждена
                ("AMANEK", "support"),
            )),
            ("Mousesports", "EU", "топ-12", (
                ("ChrisJ", "awp"),
                ("Ropz", "lurker"),
                ("Karrigan", "igl"),
                ("Woxic", "awp"),
                ("Frozen", "lurker"),
            )),
            ("CR4ZY", "EU", "топ-12", (
                ("LETN1", "igl"),  # роль не подтверждена
                ("HuNter-", "lurker"),
                ("Nexa", "entry"),  # роль не подтверждена
                ("EspiranTo", "support"),  # роль не подтверждена
                ("OttoNd", "awp"),
            )),
            ("North", "EU", "топ-12", (
                ("Aizy", "awp"),  # роль не подтверждена
                ("Valde", "lurker"),
                ("Kjaerbye", "igl"),  # роль не подтверждена
                ("Gade", "lurker"),
                ("JUGi", "entry"),  # роль не подтверждена
            )),
            ("Ninjas in Pyjamas", "EU", "топ-16", (
                ("F0rest", "entry"),
                ("GeT RiGhT", "lurker"),
                ("REZ", "entry"),
                ("Lekr0", "entry"),
                ("Golden", "igl"),
            )),
            ("DreamEaters", "EU", "топ-16", (
                ("Speed4k", "awp"),  # роль не подтверждена
                ("Kinqie", "igl"),  # роль не подтверждена
                ("Krad", "support"),  # роль не подтверждена
                ("Forester", "entry"),
                ("Svyat", "lurker"),  # роль не подтверждена
            )),
            ("Renegades", "EU", "топ-4", (
                ("AZR", "awp"),  # роль не подтверждена
                ("Jks", "lurker"),
                ("Jkaem", "entry"),
                ("Liazz", "support"),
                ("Gratisfaction", "igl"),  # роль не подтверждена
            )),
            ("NRG Esports", "NA", "топ-4", (
                ("Brehze", "entry"),  # роль не подтверждена
                ("CeRq", "awp"),
                ("Ethan", "lurker"),
                ("Tarik", "igl"),
                ("Stanislaw", "igl"),
            )),
            ("ENCE", "EU", "топ-8", (
                ("Allu", "awp"),  # роль не подтверждена
                ("Aleksib", "igl"),  # роль не подтверждена
                ("Sergej", "entry"),
                ("Aerial", "support"),  # роль не подтверждена
                ("XseveN", "entry"),
            )),
            ("Natus Vincere", "EEU", "топ-8", (
                ("Flamie", "lurker"),
                ("S1mple", "awp"),
                ("Zeus", "igl"),  # роль не подтверждена
                ("ElectroNic", "entry"),  # роль не подтверждена
                ("Boombl4", "support"),  # роль не подтверждена
            )),
            ("Team Liquid", "NA", "топ-8", (
                ("Nitr0", "igl"),
                ("EliGE", "lurker"),
                ("Twistzz", "lurker"),
                ("NAF", "lurker"),
                ("Stewie2K", "lurker"),
            )),
            ("Team Vitality", "EU", "топ-8", (
                ("NBK-", "support"),
                ("ApEX", "igl"),
                ("RpK", "support"),
                ("ZywOo", "awp"),
                ("ALEX", "igl"),
            )),
            ("AVANGAR", "EEU", "финалист", (
                ("Buster", "entry"),
                ("Qikert", "support"),
                ("Jame", "awp"),
                ("SANJI", "lurker"),  # роль не подтверждена
                ("AdreN", "igl"),
            )),
        ),
    },
    {
        "event": "PGL Major Stockholm 2021",
        "year": 2021,
        "era": "modern",
        "teams": (
            ("BIG", "EU", "группа", (
                ("TabseN", "awp"),  # роль не подтверждена
                ("TiziaN", "entry"),
                ("SyrsoN", "igl"),  # роль не подтверждена
                ("K1to", "entry"),
                ("Gade", "lurker"),
            )),
            ("Movistar Riders", "EU", "группа", (
                ("Mopoz", "awp"),  # роль не подтверждена
                ("Alex", "igl"),
                ("DeathZz", "entry"),  # роль не подтверждена
                ("SunPayus", "support"),  # роль не подтверждена
                ("Dav1g", "lurker"),  # роль не подтверждена
            )),
            ("PaiN Gaming", "SA", "группа", (
                ("PKL", "igl"),  # роль не подтверждена
                ("Biguzera", "entry"),  # роль не подтверждена
                ("Hardzao", "support"),  # роль не подтверждена
                ("NEKIZ", "lurker"),  # роль не подтверждена
                ("Saffee", "awp"),
            )),
            ("Team Spirit", "EEU", "группа", (
                ("Sdy", "entry"),
                ("Chopper", "igl"),
                ("Mir", "entry"),
                ("Magixx", "lurker"),
                ("Degster", "awp"),  # роль не подтверждена
            )),
            ("Copenhagen Flames", "EU", "группа", (
                ("Jabbi", "entry"),  # роль не подтверждена
                ("Nicoodoz", "awp"),
                ("RoeJ", "support"),  # роль не подтверждена
                ("HooXi", "igl"),
                ("Zyphon", "lurker"),  # роль не подтверждена
            )),
            ("GODSENT", "EU", "группа", (
                ("TACO", "support"),
                ("Felps", "awp"),  # роль не подтверждена
                ("Latto", "igl"),  # роль не подтверждена
                ("B4rtiN", "lurker"),  # роль не подтверждена
                ("Dumau", "entry"),
            )),
            ("Sharks Esports", "EU", "группа", (
                ("Jnt", "awp"),  # роль не подтверждена
                ("Pancc", "igl"),  # роль не подтверждена
                ("Lucaozy", "entry"),  # роль не подтверждена
                ("Realz1n", "support"),  # роль не подтверждена
                ("Zevy", "lurker"),  # роль не подтверждена
            )),
            ("TYLOO", "CN", "группа", (
                ("Somebody", "support"),
                ("Summer", "lurker"),
                ("Attacker", "entry"),
                ("SLOWLY", "awp"),  # роль не подтверждена
                ("DANK1NG", "igl"),  # роль не подтверждена
            )),
            ("Renegades", "EU", "группа", (
                ("Malta", "awp"),  # роль не подтверждена
                ("Sico", "igl"),  # роль не подтверждена
                ("INS", "entry"),  # роль не подтверждена
                ("Hatz", "support"),  # роль не подтверждена
                ("AliStair", "lurker"),  # роль не подтверждена
            )),
            ("Natus Vincere", "EEU", "победитель", (
                ("S1mple", "awp"),
                ("ElectroNic", "igl"),  # роль не подтверждена
                ("Boombl4", "entry"),  # роль не подтверждена
                ("Perfecto", "support"),
                ("B1t", "lurker"),  # роль не подтверждена
            )),
            ("Team Liquid", "NA", "топ-12", (
                ("EliGE", "lurker"),
                ("NAF", "lurker"),
                ("Stewie2K", "lurker"),
                ("Grim", "entry"),
                ("FalleN", "awp"),
            )),
            ("Astralis", "EU", "топ-12", (
                ("Dupreeh", "entry"),
                ("Xyp9x", "support"),
                ("Gla1ve", "igl"),
                ("Magisk", "awp"),  # роль не подтверждена
                ("Lucky", "lurker"),  # роль не подтверждена
            )),
            ("MOUZ", "EU", "топ-12", (
                ("Ropz", "lurker"),
                ("Frozen", "lurker"),
                ("Bymas", "awp"),  # роль не подтверждена
                ("AcoR", "igl"),  # роль не подтверждена
                ("Dexter", "entry"),  # роль не подтверждена
            )),
            ("FaZe Clan", "EU", "топ-12", (
                ("Rain", "entry"),
                ("Olofmeister", "entry"),
                ("Broky", "awp"),  # роль не подтверждена
                ("Twistzz", "lurker"),
                ("Karrigan", "igl"),
            )),
            ("Entropiq", "EU", "топ-12", (
                ("El1an", "awp"),
                ("Lack1", "igl"),  # роль не подтверждена
                ("NickelBack", "support"),  # роль не подтверждена
                ("Krad", "lurker"),  # роль не подтверждена
                ("Forester", "entry"),
            )),
            ("Evil Geniuses", "NA", "топ-16", (
                ("Brehze", "support"),  # роль не подтверждена
                ("CeRq", "awp"),
                ("Stanislaw", "igl"),
                ("OBo", "lurker"),  # роль не подтверждена
                ("MICHU", "entry"),
            )),
            ("ENCE", "EU", "топ-16", (
                ("Doto", "awp"),  # роль не подтверждена
                ("Snappi", "igl"),
                ("Spinx", "entry"),
                ("Dycha", "support"),
                ("Hades", "entry"),
            )),
            ("Gambit Esports", "EEU", "топ-4", (
                ("Nafany", "igl"),
                ("Sh1ro", "awp"),
                ("Interz", "support"),
                ("Ax1Le", "entry"),  # роль не подтверждена
                ("HObbit", "lurker"),
            )),
            ("Heroic", "EU", "топ-4", (
                ("Stavn", "entry"),
                ("CadiaN", "igl"),
                ("TeSeS", "awp"),  # роль не подтверждена
                ("Refrezh", "support"),  # роль не подтверждена
                ("Sjuush", "lurker"),  # роль не подтверждена
            )),
            ("Ninjas in Pyjamas", "EU", "топ-8", (
                ("REZ", "entry"),
                ("Plopski", "support"),
                ("Hampus", "igl"),
                ("Dev1ce", "awp"),
                ("LNZ", "lurker"),  # роль не подтверждена
            )),
            ("Team Vitality", "EU", "топ-8", (
                ("ApEX", "igl"),
                ("ZywOo", "awp"),
                ("Shox", "lurker"),
                ("Misutaaa", "entry"),
                ("Kyojin", "support"),  # роль не подтверждена
            )),
            ("FURIA Esports", "EU", "топ-8", (
                ("Yuurih", "awp"),  # роль не подтверждена
                ("ArT", "igl"),
                ("VINI", "support"),
                ("KSCERATO", "entry"),  # роль не подтверждена
                ("Drop", "lurker"),  # роль не подтверждена
            )),
            ("Virtus.pro", "EEU", "топ-8", (
                ("Buster", "entry"),
                ("Qikert", "support"),
                ("Jame", "awp"),
                ("YEKINDAR", "entry"),
                ("FL1T", "support"),
            )),
            ("G2 Esports", "EU", "финалист", (
                ("JACKZ", "awp"),  # роль не подтверждена
                ("AMANEK", "support"),
                ("Nexa", "igl"),  # роль не подтверждена
                ("HuNter-", "lurker"),
                ("NiKo", "entry"),  # роль не подтверждена
            )),
        ),
    },
    {
        "event": "PGL Major Antwerp 2022",
        "year": 2022,
        "era": "modern",
        "teams": (
            ("ForZe", "EEU", "группа", (
                ("Jerry", "igl"),  # роль не подтверждена
                ("KENSi", "entry"),  # роль не подтверждена
                ("Zorte", "awp"),
                ("Norwi", "support"),  # роль не подтверждена
                ("Shalfey", "lurker"),  # роль не подтверждена
            )),
            ("Astralis", "EU", "группа", (
                ("Xyp9x", "support"),
                ("Gla1ve", "igl"),
                ("K0nfig", "awp"),  # роль не подтверждена
                ("BlameF", "entry"),  # роль не подтверждена
                ("Farlig", "lurker"),  # роль не подтверждена
            )),
            ("MIBR", "SA", "группа", (
                ("Chelo", "awp"),  # роль не подтверждена
                ("Exit", "igl"),  # роль не подтверждена
                ("WOOD7", "entry"),  # роль не подтверждена
                ("Tuurtle", "support"),  # роль не подтверждена
                ("JOTA", "lurker"),  # роль не подтверждена
            )),
            ("Eternal Fire", "EEU", "группа", (
                ("XANTARES", "entry"),
                ("Woxic", "awp"),
                ("Calyx", "entry"),
                ("ImoRR", "igl"),  # роль не подтверждена
                ("Xfl0ud", "support"),  # роль не подтверждена
            )),
            ("Complexity Gaming", "NA", "группа", (
                ("JT", "awp"),  # роль не подтверждена
                ("FaNg", "igl"),  # роль не подтверждена
                ("Floppy", "support"),  # роль не подтверждена
                ("Grim", "entry"),
                ("Junior", "lurker"),  # роль не подтверждена
            )),
            ("IHC Esports", "EU", "группа", (
                ("BLitz", "awp"),  # роль не подтверждена
                ("Techno4K", "igl"),  # роль не подтверждена
                ("Kabal", "entry"),  # роль не подтверждена
                ("Nin9", "support"),  # роль не подтверждена
                ("Sk0R", "lurker"),  # роль не подтверждена
            )),
            ("Renegades", "EU", "группа", (
                ("Sico", "awp"),  # роль не подтверждена
                ("INS", "igl"),  # роль не подтверждена
                ("Hatz", "entry"),  # роль не подтверждена
                ("AliStair", "lurker"),  # роль не подтверждена
                ("Liazz", "support"),
            )),
            ("9z Team", "SA", "группа", (
                ("Dgt", "awp"),  # роль не подтверждена
                ("Max", "igl"),  # роль не подтверждена
                ("Rox", "entry"),  # роль не подтверждена
                ("Luken", "support"),  # роль не подтверждена
                ("Dav1deuS", "lurker"),  # роль не подтверждена
            )),
            ("FaZe Clan", "EU", "победитель", (
                ("Rain", "entry"),
                ("Broky", "awp"),  # роль не подтверждена
                ("Twistzz", "lurker"),
                ("Karrigan", "igl"),
                ("Ropz", "lurker"),
            )),
            ("BIG", "EU", "топ-12", (
                ("TabseN", "awp"),  # роль не подтверждена
                ("TiziaN", "entry"),
                ("SyrsoN", "igl"),  # роль не подтверждена
                ("FaveN", "support"),  # роль не подтверждена
                ("Krimbo", "lurker"),  # роль не подтверждена
            )),
            ("Cloud9", "NA", "топ-12", (
                ("Nafany", "igl"),
                ("Sh1ro", "awp"),
                ("Interz", "support"),
                ("Ax1Le", "entry"),  # роль не подтверждена
                ("HObbit", "lurker"),
            )),
            ("G2 Esports", "EU", "топ-12", (
                ("JACKZ", "awp"),  # роль не подтверждена
                ("HuNter-", "lurker"),
                ("NiKo", "igl"),  # роль не подтверждена
                ("M0NESY", "entry"),  # роль не подтверждена
                ("Aleksib", "support"),  # роль не подтверждена
            )),
            ("Team Vitality", "EU", "топ-12", (
                ("ApEX", "igl"),
                ("ZywOo", "awp"),
                ("Misutaaa", "entry"),
                ("Dupreeh", "entry"),
                ("Magisk", "support"),  # роль не подтверждена
            )),
            ("Imperial Esports", "EU", "топ-12", (
                ("FalleN", "awp"),
                ("Fer", "igl"),  # роль не подтверждена
                ("Fnx", "entry"),  # роль не подтверждена
                ("Boltz", "lurker"),  # роль не подтверждена
                ("VINI", "support"),
            )),
            ("Outsiders", "EU", "топ-12", (
                ("Buster", "entry"),
                ("Qikert", "support"),
                ("Jame", "awp"),
                ("YEKINDAR", "entry"),
                ("FL1T", "support"),
            )),
            ("Bad News Eagles", "EU", "топ-16", (
                ("SENER1", "awp"),  # роль не подтверждена
                ("Gxx-", "igl"),  # роль не подтверждена
                ("Juanflatroo", "entry"),
                ("Sinnopsyy", "support"),  # роль не подтверждена
                ("RigoN", "lurker"),  # роль не подтверждена
            )),
            ("Team Liquid", "NA", "топ-16", (
                ("EliGE", "lurker"),
                ("NAF", "lurker"),
                ("OSee", "awp"),
                ("Shox", "lurker"),
                ("Nitr0", "igl"),
            )),
            ("ENCE", "EU", "топ-4", (
                ("Snappi", "igl"),
                ("Spinx", "entry"),
                ("Dycha", "support"),
                ("Hades", "entry"),
                ("Maden", "awp"),  # роль не подтверждена
            )),
            ("Team Spirit", "EEU", "топ-4", (
                ("Chopper", "igl"),
                ("Magixx", "lurker"),
                ("Degster", "awp"),  # роль не подтверждена
                ("Patsi", "entry"),  # роль не подтверждена
                ("S1ren", "support"),  # роль не подтверждена
            )),
            ("Heroic", "EU", "топ-8", (
                ("Stavn", "entry"),
                ("CadiaN", "igl"),
                ("TeSeS", "awp"),  # роль не подтверждена
                ("Refrezh", "support"),  # роль не подтверждена
                ("Sjuush", "lurker"),  # роль не подтверждена
            )),
            ("Copenhagen Flames", "EU", "топ-8", (
                ("Jabbi", "entry"),  # роль не подтверждена
                ("Nicoodoz", "awp"),
                ("RoeJ", "support"),  # роль не подтверждена
                ("HooXi", "igl"),
                ("Zyphon", "lurker"),  # роль не подтверждена
            )),
            ("FURIA Esports", "EU", "топ-8", (
                ("Yuurih", "entry"),  # роль не подтверждена
                ("ArT", "igl"),
                ("KSCERATO", "support"),  # роль не подтверждена
                ("Drop", "lurker"),  # роль не подтверждена
                ("Saffee", "awp"),
            )),
            ("Ninjas in Pyjamas", "EU", "топ-8", (
                ("REZ", "entry"),
                ("Plopski", "support"),
                ("Hampus", "igl"),
                ("Es3tag", "awp"),  # роль не подтверждена
                ("Brollan", "lurker"),  # роль не подтверждена
            )),
            ("Natus Vincere", "EEU", "финалист", (
                ("S1mple", "awp"),
                ("ElectroNic", "igl"),  # роль не подтверждена
                ("Boombl4", "entry"),  # роль не подтверждена
                ("Perfecto", "support"),
                ("B1t", "lurker"),  # роль не подтверждена
            )),
        ),
    },
    {
        "event": "IEM Rio 2022",
        "year": 2022,
        "era": "modern",
        "teams": (
            ("OG", "EU", "группа", (
                ("FlameZ", "entry"),
                ("Nexa", "awp"),  # роль не подтверждена
                ("NEOFRAG", "igl"),  # роль не подтверждена
                ("F1KU", "support"),  # роль не подтверждена
                ("Degster", "lurker"),  # роль не подтверждена
            )),
            ("Evil Geniuses", "NA", "группа", (
                ("Brehze", "igl"),  # роль не подтверждена
                ("CeRq", "awp"),
                ("Autimatic", "support"),  # роль не подтверждена
                ("HexT", "entry"),
                ("NeaLaN", "lurker"),  # роль не подтверждена
            )),
            ("9z Team", "SA", "группа", (
                ("Dgt", "igl"),  # роль не подтверждена
                ("Max", "entry"),  # роль не подтверждена
                ("Dav1deuS", "support"),  # роль не подтверждена
                ("Nqz", "awp"),
                ("Buda", "lurker"),  # роль не подтверждена
            )),
            ("Team GamerLegion", "EU", "группа", (
                ("IM", "entry"),
                ("Isak", "awp"),  # роль не подтверждена
                ("AcoR", "igl"),  # роль не подтверждена
                ("Siuhy", "support"),  # роль не подтверждена
                ("Keoz", "lurker"),  # роль не подтверждена
            )),
            ("00 Nation", "EU", "группа", (
                ("Coldzera", "lurker"),
                ("Try", "awp"),  # роль не подтверждена
                ("TACO", "support"),
                ("Latto", "igl"),  # роль не подтверждена
                ("Dumau", "entry"),
            )),
            ("IHC Esports", "EU", "группа", (
                ("BLitz", "awp"),  # роль не подтверждена
                ("Techno4K", "igl"),  # роль не подтверждена
                ("Kabal", "entry"),  # роль не подтверждена
                ("Sk0R", "support"),  # роль не подтверждена
                ("ANNIHILATION", "lurker"),  # роль не подтверждена
            )),
            ("Imperial Esports", "EU", "группа", (
                ("FalleN", "awp"),
                ("Fer", "igl"),  # роль не подтверждена
                ("Boltz", "entry"),  # роль не подтверждена
                ("VINI", "support"),
                ("Chelo", "lurker"),  # роль не подтверждена
            )),
            ("Grayhound Gaming", "EU", "группа", (
                ("Sico", "awp"),  # роль не подтверждена
                ("INS", "igl"),  # роль не подтверждена
                ("AliStair", "entry"),  # роль не подтверждена
                ("Liazz", "support"),
                ("Vexite", "lurker"),  # роль не подтверждена
            )),
            ("Outsiders", "EU", "победитель", (
                ("Qikert", "support"),
                ("Jame", "awp"),
                ("FL1T", "support"),
                ("N0rb3r7", "igl"),  # роль не подтверждена
                ("Fame", "support"),
            )),
            ("ENCE", "EU", "топ-12", (
                ("Snappi", "igl"),
                ("Dycha", "support"),
                ("Maden", "awp"),  # роль не подтверждена
                ("SunPayus", "entry"),  # роль не подтверждена
                ("Valde", "lurker"),
            )),
            ("Sprout", "EU", "топ-12", (
                ("Slaxz-", "awp"),  # роль не подтверждена
                ("Staehr", "igl"),  # роль не подтверждена
                ("LauNX", "entry"),  # роль не подтверждена
                ("Zyphon", "support"),  # роль не подтверждена
                ("Refrezh", "lurker"),  # роль не подтверждена
            )),
            ("Team Liquid", "NA", "топ-12", (
                ("EliGE", "lurker"),
                ("NAF", "lurker"),
                ("OSee", "awp"),
                ("Nitr0", "igl"),
                ("YEKINDAR", "entry"),
            )),
            ("Team Vitality", "EU", "топ-12", (
                ("ApEX", "igl"),
                ("ZywOo", "awp"),
                ("Dupreeh", "entry"),
                ("Magisk", "support"),  # роль не подтверждена
                ("Spinx", "entry"),
            )),
            ("BIG", "EU", "топ-12", (
                ("TabseN", "awp"),  # роль не подтверждена
                ("SyrsoN", "igl"),  # роль не подтверждена
                ("FaveN", "support"),  # роль не подтверждена
                ("Krimbo", "lurker"),  # роль не подтверждена
                ("K1to", "entry"),
            )),
            ("Bad News Eagles", "EU", "топ-12", (
                ("SENER1", "awp"),  # роль не подтверждена
                ("Gxx-", "igl"),  # роль не подтверждена
                ("Juanflatroo", "entry"),
                ("Sinnopsyy", "support"),  # роль не подтверждена
                ("RigoN", "lurker"),  # роль не подтверждена
            )),
            ("FaZe Clan", "EU", "топ-16", (
                ("Rain", "entry"),
                ("Broky", "awp"),  # роль не подтверждена
                ("Twistzz", "lurker"),
                ("Karrigan", "igl"),
                ("Ropz", "lurker"),
            )),
            ("Ninjas in Pyjamas", "EU", "топ-16", (
                ("REZ", "entry"),
                ("Hampus", "igl"),
                ("Es3tag", "awp"),  # роль не подтверждена
                ("Brollan", "support"),  # роль не подтверждена
                ("Aleksib", "lurker"),  # роль не подтверждена
            )),
            ("MOUZ", "EU", "топ-4", (
                ("Frozen", "lurker"),
                ("Dexter", "igl"),  # роль не подтверждена
                ("Torzsi", "awp"),
                ("JDC", "entry"),  # роль не подтверждена
                ("XertioN", "support"),  # роль не подтверждена
            )),
            ("FURIA Esports", "EU", "топ-4", (
                ("Yuurih", "entry"),  # роль не подтверждена
                ("ArT", "igl"),
                ("KSCERATO", "support"),  # роль не подтверждена
                ("Drop", "lurker"),  # роль не подтверждена
                ("Saffee", "awp"),
            )),
            ("Natus Vincere", "EEU", "топ-8", (
                ("S1mple", "awp"),
                ("ElectroNic", "igl"),  # роль не подтверждена
                ("Perfecto", "support"),
                ("B1t", "lurker"),  # роль не подтверждена
                ("Sdy", "entry"),
            )),
            ("Team Spirit", "EEU", "топ-8", (
                ("Chopper", "igl"),
                ("Magixx", "lurker"),
                ("Patsi", "entry"),  # роль не подтверждена
                ("S1ren", "support"),  # роль не подтверждена
                ("W0nderful", "awp"),
            )),
            ("Cloud9", "NA", "топ-8", (
                ("Nafany", "igl"),
                ("Sh1ro", "awp"),
                ("Interz", "support"),
                ("Ax1Le", "entry"),  # роль не подтверждена
                ("HObbit", "lurker"),
            )),
            ("Fnatic", "EU", "топ-8", (
                ("KRIMZ", "support"),
                ("Mezii", "igl"),  # роль не подтверждена
                ("Nicoodoz", "awp"),
                ("RoeJ", "entry"),  # роль не подтверждена
                ("FASHR", "awp"),
            )),
            ("Heroic", "EU", "финалист", (
                ("Stavn", "entry"),
                ("CadiaN", "igl"),
                ("TeSeS", "awp"),  # роль не подтверждена
                ("Sjuush", "support"),  # роль не подтверждена
                ("Jabbi", "lurker"),  # роль не подтверждена
            )),
        ),
    },
    {
        "event": "BLAST.tv Paris Major 2023",
        "year": 2023,
        "era": "modern",
        "teams": (
            ("PaiN Gaming", "SA", "группа", (
                ("Biguzera", "awp"),  # роль не подтверждена
                ("Hardzao", "igl"),  # роль не подтверждена
                ("NEKIZ", "support"),  # роль не подтверждена
                ("Zevy", "lurker"),  # роль не подтверждена
                ("Skullz", "entry"),
            )),
            ("FORZE Esports", "EU", "группа", (
                ("Jerry", "igl"),  # роль не подтверждена
                ("Zorte", "awp"),
                ("Shalfey", "entry"),  # роль не подтверждена
                ("Krad", "support"),  # роль не подтверждена
                ("R3salt", "lurker"),  # роль не подтверждена
            )),
            ("OG", "EU", "группа", (
                ("FlameZ", "entry"),
                ("NEOFRAG", "awp"),  # роль не подтверждена
                ("F1KU", "igl"),  # роль не подтверждена
                ("Degster", "support"),  # роль не подтверждена
                ("Niko", "lurker"),  # роль не подтверждена
            )),
            ("MOUZ", "EU", "группа", (
                ("Frozen", "lurker"),
                ("Dexter", "igl"),  # роль не подтверждена
                ("Torzsi", "awp"),
                ("JDC", "entry"),  # роль не подтверждена
                ("XertioN", "support"),  # роль не подтверждена
            )),
            ("Grayhound Gaming", "EU", "группа", (
                ("Sico", "awp"),  # роль не подтверждена
                ("INS", "igl"),  # роль не подтверждена
                ("AliStair", "entry"),  # роль не подтверждена
                ("Liazz", "support"),
                ("Vexite", "lurker"),  # роль не подтверждена
            )),
            ("Complexity Gaming", "NA", "группа", (
                ("JT", "igl"),  # роль не подтверждена
                ("FaNg", "support"),  # роль не подтверждена
                ("Floppy", "lurker"),  # роль не подтверждена
                ("Grim", "entry"),
                ("Hallzerk", "awp"),
            )),
            ("The MongolZ", "APAC", "группа", (
                ("BLitz", "awp"),  # роль не подтверждена
                ("Techno4K", "igl"),  # роль не подтверждена
                ("Bart4k", "entry"),  # роль не подтверждена
                ("ANNIHILATION", "support"),  # роль не подтверждена
                ("Sk0R", "lurker"),  # роль не подтверждена
            )),
            ("Fluxo", "EU", "группа", (
                ("Felps", "awp"),  # роль не подтверждена
                ("Lucaozy", "igl"),  # роль не подтверждена
                ("V$m", "entry"),  # роль не подтверждена
                ("WOOD7", "support"),  # роль не подтверждена
                ("History", "lurker"),  # роль не подтверждена
            )),
            ("Team Vitality", "EU", "победитель", (
                ("ApEX", "igl"),
                ("ZywOo", "awp"),
                ("Dupreeh", "entry"),
                ("Magisk", "support"),  # роль не подтверждена
                ("Spinx", "entry"),
            )),
            ("Natus Vincere", "EEU", "топ-12", (
                ("S1mple", "awp"),
                ("ElectroNic", "igl"),  # роль не подтверждена
                ("Perfecto", "support"),
                ("B1t", "entry"),  # роль не подтверждена
                ("Npl", "lurker"),  # роль не подтверждена
            )),
            ("Fnatic", "EU", "топ-12", (
                ("KRIMZ", "support"),
                ("Mezii", "igl"),  # роль не подтверждена
                ("Nicoodoz", "awp"),
                ("RoeJ", "entry"),  # роль не подтверждена
                ("FASHR", "awp"),
            )),
            ("Bad News Eagles", "EU", "топ-12", (
                ("SENER1", "awp"),  # роль не подтверждена
                ("Gxx-", "igl"),  # роль не подтверждена
                ("Juanflatroo", "entry"),
                ("Sinnopsyy", "support"),  # роль не подтверждена
                ("RigoN", "lurker"),  # роль не подтверждена
            )),
            ("G2 Esports", "EU", "топ-12", (
                ("HuNter-", "lurker"),
                ("NiKo", "awp"),  # роль не подтверждена
                ("M0NESY", "entry"),  # роль не подтверждена
                ("Jks", "lurker"),
                ("HooXi", "igl"),
            )),
            ("Ninjas in Pyjamas", "EU", "топ-12", (
                ("REZ", "entry"),
                ("Brollan", "awp"),  # роль не подтверждена
                ("Aleksib", "igl"),  # роль не подтверждена
                ("Headtr1ck", "support"),  # роль не подтверждена
                ("K0nfig", "lurker"),  # роль не подтверждена
            )),
            ("ENCE", "EU", "топ-12", (
                ("Snappi", "igl"),
                ("Dycha", "support"),
                ("Maden", "awp"),  # роль не подтверждена
                ("SunPayus", "entry"),  # роль не подтверждена
                ("NertZ", "lurker"),  # роль не подтверждена
            )),
            ("9INE", "EU", "топ-16", (
                ("Goofy", "awp"),  # роль не подтверждена
                ("KEi", "igl"),  # роль не подтверждена
                ("Kylar", "support"),  # роль не подтверждена
                ("Mynio", "lurker"),  # роль не подтверждена
                ("Hades", "entry"),
            )),
            ("FURIA Esports", "EU", "топ-16", (
                ("Yuurih", "entry"),  # роль не подтверждена
                ("ArT", "igl"),
                ("KSCERATO", "support"),  # роль не подтверждена
                ("Drop", "lurker"),  # роль не подтверждена
                ("Saffee", "awp"),
            )),
            ("Heroic", "EU", "топ-4", (
                ("Stavn", "entry"),
                ("CadiaN", "igl"),
                ("TeSeS", "awp"),  # роль не подтверждена
                ("Sjuush", "support"),  # роль не подтверждена
                ("Jabbi", "lurker"),  # роль не подтверждена
            )),
            ("Apeks", "EU", "топ-4", (
                ("Nawwk", "awp"),  # роль не подтверждена
                ("Jkaem", "entry"),
                ("STYKO", "support"),
                ("JL", "igl"),  # роль не подтверждена
                ("Kyxsan", "support"),
            )),
            ("Into The Breach", "EU", "топ-8", (
                ("Thomas", "lurker"),
                ("CYPHER", "entry"),
                ("Rallen", "entry"),
                ("Volt", "awp"),  # роль не подтверждена
                ("CRUC1AL", "igl"),  # роль не подтверждена
            )),
            ("Monte", "EU", "топ-8", (
                ("Woro2k", "awp"),  # роль не подтверждена
                ("BOROS", "lurker"),
                ("DemQQ", "igl"),  # роль не подтверждена
                ("KRaSnaL", "support"),  # роль не подтверждена
                ("Sdy", "entry"),
            )),
            ("Team Liquid", "NA", "топ-8", (
                ("EliGE", "lurker"),
                ("NAF", "lurker"),
                ("OSee", "awp"),
                ("Nitr0", "igl"),
                ("YEKINDAR", "entry"),
            )),
            ("FaZe Clan", "EU", "топ-8", (
                ("Rain", "entry"),
                ("Broky", "awp"),  # роль не подтверждена
                ("Twistzz", "lurker"),
                ("Karrigan", "igl"),
                ("Ropz", "lurker"),
            )),
            ("GamerLegion", "EU", "финалист", (
                ("IM", "entry"),
                ("Isak", "awp"),  # роль не подтверждена
                ("AcoR", "igl"),  # роль не подтверждена
                ("Siuhy", "support"),  # роль не подтверждена
                ("Keoz", "lurker"),  # роль не подтверждена
            )),
        ),
    },
    {
        "event": "PGL Major Copenhagen 2024",
        "year": 2024,
        "era": "modern",
        "teams": (
            ("ENCE", "EU", "группа", (
                ("Dycha", "support"),
                ("Gla1ve", "igl"),
                ("Goofy", "awp"),  # роль не подтверждена
                ("Kylar", "lurker"),  # роль не подтверждена
                ("Hades", "entry"),
            )),
            ("Apeks", "EU", "группа", (
                ("Nawwk", "awp"),  # роль не подтверждена
                ("Jkaem", "entry"),
                ("STYKO", "support"),
                ("CacaNito", "igl"),  # роль не подтверждена
                ("Sense", "lurker"),  # роль не подтверждена
            )),
            ("GamerLegion", "EU", "группа", (
                ("Isak", "awp"),  # роль не подтверждена
                ("AcoR", "igl"),  # роль не подтверждена
                ("Keoz", "support"),  # роль не подтверждена
                ("Volt", "lurker"),  # роль не подтверждена
                ("Snax", "entry"),
            )),
            ("SAW", "EU", "группа", (
                ("MUTiRiS", "awp"),  # роль не подтверждена
                ("Rmn", "igl"),  # роль не подтверждена
                ("Ewjerkz", "entry"),  # роль не подтверждена
                ("Story", "support"),  # роль не подтверждена
                ("Arrozdoce", "lurker"),  # роль не подтверждена
            )),
            ("ECSTATIC", "EU", "группа", (
                ("Kraghen", "awp"),  # роль не подтверждена
                ("Queenix", "igl"),  # роль не подтверждена
                ("Salazar", "entry"),  # роль не подтверждена
                ("Nodios", "support"),  # роль не подтверждена
                ("Patti", "lurker"),  # роль не подтверждена
            )),
            ("Lynn Vision Gaming", "EU", "группа", (
                ("Westmelon", "awp"),  # роль не подтверждена
                ("Z4kr", "igl"),  # роль не подтверждена
                ("Starry", "entry"),  # роль не подтверждена
                ("EmiliaQAQ", "support"),  # роль не подтверждена
                ("Jee", "lurker"),  # роль не подтверждена
            )),
            ("AMKAL ESPORTS", "EU", "группа", (
                ("TRAVIS", "awp"),  # роль не подтверждена
                ("Forester", "entry"),
                ("NickelBack", "igl"),  # роль не подтверждена
                ("Krad", "support"),  # роль не подтверждена
                ("ICY", "lurker"),  # роль не подтверждена
            )),
            ("KOI", "EU", "группа", (
                ("Mopoz", "awp"),  # роль не подтверждена
                ("Dav1g", "igl"),  # роль не подтверждена
                ("JUST", "entry"),  # роль не подтверждена
                ("AdamS", "support"),  # роль не подтверждена
                ("Stadodo", "lurker"),  # роль не подтверждена
            )),
            ("Legacy", "EU", "группа", (
                ("Coldzera", "lurker"),
                ("Latto", "awp"),  # роль не подтверждена
                ("Dumau", "entry"),
                ("NEKIZ", "igl"),  # роль не подтверждена
                ("B4rtiN", "support"),  # роль не подтверждена
            )),
            ("9Pandas", "EU", "группа", (
                ("Seized", "lurker"),
                ("D1Ledez", "awp"),  # роль не подтверждена
                ("Clax", "igl"),  # роль не подтверждена
                ("IDISBALANCE", "entry"),  # роль не подтверждена
                ("Glowiing", "support"),  # роль не подтверждена
            )),
            ("Natus Vincere", "EEU", "победитель", (
                ("B1t", "igl"),  # роль не подтверждена
                ("Aleksib", "support"),  # роль не подтверждена
                ("JL", "lurker"),  # роль не подтверждена
                ("IM", "entry"),
                ("W0nderful", "awp"),
            )),
            ("Complexity Gaming", "NA", "топ-12", (
                ("JT", "igl"),  # роль не подтверждена
                ("Floppy", "support"),  # роль не подтверждена
                ("Grim", "entry"),
                ("Hallzerk", "awp"),
                ("EliGE", "lurker"),
            )),
            ("Virtus.pro", "EEU", "топ-12", (
                ("Jame", "awp"),
                ("FL1T", "support"),
                ("Fame", "support"),
                ("N0rb3r7", "igl"),  # роль не подтверждена
                ("Mir", "entry"),
            )),
            ("HEROIC", "EU", "топ-12", (
                ("TeSeS", "igl"),  # роль не подтверждена
                ("Sjuush", "entry"),  # роль не подтверждена
                ("NertZ", "lurker"),  # роль не подтверждена
                ("Nicoodoz", "awp"),
                ("Kyxsan", "support"),
            )),
            ("Imperial Esports", "EU", "топ-12", (
                ("VINI", "support"),
                ("HEN1", "awp"),  # роль не подтверждена
                ("Felps", "igl"),  # роль не подтверждена
                ("Noway", "entry"),  # роль не подтверждена
                ("Decenty", "lurker"),  # роль не подтверждена
            )),
            ("PaiN Gaming", "SA", "топ-12", (
                ("Biguzera", "igl"),  # роль не подтверждена
                ("Lux", "entry"),  # роль не подтверждена
                ("Kauez", "support"),  # роль не подтверждена
                ("Nqz", "awp"),
                ("N1ssim", "lurker"),  # роль не подтверждена
            )),
            ("FURIA Esports", "EU", "топ-16", (
                ("Yuurih", "entry"),  # роль не подтверждена
                ("ArT", "igl"),
                ("KSCERATO", "support"),  # роль не подтверждена
                ("FalleN", "awp"),
                ("Chelo", "lurker"),  # роль не подтверждена
            )),
            ("The MongolZ", "APAC", "топ-16", (
                ("BLitz", "awp"),  # роль не подтверждена
                ("Techno4K", "igl"),  # роль не подтверждена
                ("910", "support"),  # роль не подтверждена
                ("Mzinho", "entry"),
                ("Senzu", "lurker"),  # роль не подтверждена
            )),
            ("Team Vitality", "EU", "топ-4", (
                ("ApEX", "igl"),
                ("ZywOo", "awp"),
                ("Spinx", "entry"),
                ("FlameZ", "entry"),
                ("Mezii", "support"),  # роль не подтверждена
            )),
            ("G2 Esports", "EU", "топ-4", (
                ("HuNter-", "lurker"),
                ("NiKo", "awp"),  # роль не подтверждена
                ("M0NESY", "entry"),  # роль не подтверждена
                ("HooXi", "igl"),
                ("Nexa", "support"),  # роль не подтверждена
            )),
            ("Team Spirit", "EEU", "топ-8", (
                ("Chopper", "igl"),
                ("Magixx", "lurker"),
                ("Zont1x", "lurker"),
                ("Donk", "entry"),
                ("Sh1ro", "awp"),
            )),
            ("MOUZ", "EU", "топ-8", (
                ("Torzsi", "awp"),
                ("XertioN", "igl"),  # роль не подтверждена
                ("Siuhy", "support"),  # роль не подтверждена
                ("Jimpphat", "entry"),
                ("Brollan", "lurker"),  # роль не подтверждена
            )),
            ("Cloud9", "NA", "топ-8", (
                ("Ax1Le", "awp"),  # роль не подтверждена
                ("HObbit", "lurker"),
                ("ElectroNic", "igl"),  # роль не подтверждена
                ("Perfecto", "support"),
                ("Boombl4", "entry"),  # роль не подтверждена
            )),
            ("Eternal Fire", "EEU", "топ-8", (
                ("XANTARES", "entry"),
                ("Calyx", "entry"),
                ("MAJ3R", "igl"),  # роль не подтверждена
                ("Wicadia", "support"),  # роль не подтверждена
                ("Woxic", "awp"),
            )),
            ("FaZe Clan", "EU", "финалист", (
                ("Rain", "entry"),
                ("Broky", "awp"),  # роль не подтверждена
                ("Karrigan", "igl"),
                ("Ropz", "lurker"),
                ("Frozen", "lurker"),
            )),
        ),
    },
    {
        "event": "Perfect World Shanghai 2024",
        "year": 2024,
        "era": "modern",
        "teams": (
            ("Virtus.pro", "EEU", "группа", (
                ("Jame", "awp"),
                ("FL1T", "support"),
                ("Fame", "support"),
                ("N0rb3r7", "igl"),  # роль не подтверждена
                ("ElectroNic", "entry"),  # роль не подтверждена
            )),
            ("Complexity Gaming", "NA", "группа", (
                ("JT", "igl"),  # роль не подтверждена
                ("Floppy", "support"),  # роль не подтверждена
                ("Grim", "entry"),
                ("Hallzerk", "awp"),
                ("EliGE", "lurker"),
            )),
            ("Fnatic", "EU", "группа", (
                ("KRIMZ", "support"),
                ("Afro", "awp"),  # роль не подтверждена
                ("Bodyy", "igl"),  # роль не подтверждена
                ("Matys", "entry"),  # роль не подтверждена
                ("BlameF", "lurker"),  # роль не подтверждена
            )),
            ("Cloud9", "NA", "группа", (
                ("Ax1Le", "awp"),  # роль не подтверждена
                ("Boombl4", "igl"),  # роль не подтверждена
                ("Perfecto", "support"),
                ("HeavyGod", "entry"),
                ("ICY", "lurker"),  # роль не подтверждена
            )),
            ("FlyQuest", "EU", "группа", (
                ("INS", "awp"),  # роль не подтверждена
                ("AliStair", "igl"),  # роль не подтверждена
                ("Liazz", "support"),
                ("Vexite", "entry"),  # роль не подтверждена
                ("Dexter", "lurker"),  # роль не подтверждена
            )),
            ("Passion UA", "EU", "группа", (
                ("Jambo", "awp"),  # роль не подтверждена
                ("Jackasmo", "igl"),  # роль не подтверждена
                ("ZeRRoFIX", "entry"),  # роль не подтверждена
                ("S-chilla", "support"),  # роль не подтверждена
                ("Fear", "lurker"),  # роль не подтверждена
            )),
            ("Rare Atom", "CN", "группа", (
                ("Somebody", "support"),
                ("Summer", "lurker"),
                ("L1haNg", "awp"),  # роль не подтверждена
                ("ChildKing", "igl"),  # роль не подтверждена
                ("Kaze", "entry"),  # роль не подтверждена
            )),
            ("Imperial Esports", "EU", "группа", (
                ("VINI", "support"),
                ("Felps", "awp"),  # роль не подтверждена
                ("Noway", "igl"),  # роль не подтверждена
                ("Decenty", "entry"),  # роль не подтверждена
                ("Try", "lurker"),  # роль не подтверждена
            )),
            ("Team Spirit", "EEU", "победитель", (
                ("Chopper", "igl"),
                ("Magixx", "lurker"),
                ("Zont1x", "lurker"),
                ("Donk", "entry"),
                ("Sh1ro", "awp"),
            )),
            ("Natus Vincere", "EEU", "топ-12", (
                ("B1t", "igl"),  # роль не подтверждена
                ("Aleksib", "support"),  # роль не подтверждена
                ("JL", "lurker"),  # роль не подтверждена
                ("IM", "entry"),
                ("W0nderful", "awp"),
            )),
            ("3DMAX", "EU", "топ-12", (
                ("Lucky", "awp"),  # роль не подтверждена
                ("Djoko", "igl"),  # роль не подтверждена
                ("Ex3rcice", "entry"),  # роль не подтверждена
                ("Maka", "support"),  # роль не подтверждена
                ("Graviti", "lurker"),  # роль не подтверждена
            )),
            ("FURIA Esports", "EU", "топ-12", (
                ("Yuurih", "igl"),  # роль не подтверждена
                ("KSCERATO", "support"),  # роль не подтверждена
                ("FalleN", "awp"),
                ("Chelo", "lurker"),  # роль не подтверждена
                ("Skullz", "entry"),
            )),
            ("PaiN Gaming", "SA", "топ-12", (
                ("Biguzera", "igl"),  # роль не подтверждена
                ("Lux", "entry"),  # роль не подтверждена
                ("Kauez", "support"),  # роль не подтверждена
                ("Nqz", "awp"),
                ("Snow", "lurker"),  # роль не подтверждена
            )),
            ("GamerLegion", "EU", "топ-12", (
                ("Volt", "awp"),  # роль не подтверждена
                ("Sl3nd", "igl"),  # роль не подтверждена
                ("ANdu", "entry"),  # роль не подтверждена
                ("FL4MUS", "support"),  # роль не подтверждена
                ("Ztr", "lurker"),  # роль не подтверждена
            )),
            ("MIBR", "SA", "топ-12", (
                ("Exit", "igl"),  # роль не подтверждена
                ("Brnz4n", "entry"),  # роль не подтверждена
                ("Insani", "support"),  # роль не подтверждена
                ("Drop", "lurker"),  # роль не подтверждена
                ("Saffee", "awp"),
            )),
            ("BIG", "EU", "топ-16", (
                ("TabseN", "awp"),  # роль не подтверждена
                ("Krimbo", "igl"),  # роль не подтверждена
                ("SyrsoN", "entry"),  # роль не подтверждена
                ("JDC", "support"),  # роль не подтверждена
                ("RigoN", "lurker"),  # роль не подтверждена
            )),
            ("Wildcard", "NA", "топ-16", (
                ("Stanislaw", "igl"),
                ("JBa", "entry"),  # роль не подтверждена
                ("Sonic", "support"),  # роль не подтверждена
                ("Susp", "lurker"),  # роль не подтверждена
                ("Phzy", "awp"),
            )),
            ("G2 Esports", "EU", "топ-4", (
                ("HuNter-", "lurker"),
                ("NiKo", "awp"),  # роль не подтверждена
                ("M0NESY", "igl"),  # роль не подтверждена
                ("MalbsMd", "entry"),
                ("Snax", "entry"),
            )),
            ("MOUZ", "EU", "топ-4", (
                ("Torzsi", "awp"),
                ("XertioN", "igl"),  # роль не подтверждена
                ("Siuhy", "support"),  # роль не подтверждена
                ("Jimpphat", "entry"),
                ("Brollan", "lurker"),  # роль не подтверждена
            )),
            ("Team Vitality", "EU", "топ-8", (
                ("ApEX", "igl"),
                ("ZywOo", "awp"),
                ("Spinx", "entry"),
                ("FlameZ", "entry"),
                ("Mezii", "support"),  # роль не подтверждена
            )),
            ("HEROIC", "EU", "топ-8", (
                ("TeSeS", "awp"),  # роль не подтверждена
                ("Sjuush", "igl"),  # роль не подтверждена
                ("NertZ", "entry"),  # роль не подтверждена
                ("Kyxsan", "support"),
                ("Degster", "lurker"),  # роль не подтверждена
            )),
            ("Team Liquid", "NA", "топ-8", (
                ("NAF", "lurker"),
                ("YEKINDAR", "entry"),
                ("Twistzz", "lurker"),
                ("Ultimate", "awp"),  # роль не подтверждена
                ("Jks", "lurker"),
            )),
            ("The MongolZ", "APAC", "топ-8", (
                ("BLitz", "awp"),  # роль не подтверждена
                ("Techno4K", "igl"),  # роль не подтверждена
                ("910", "support"),  # роль не подтверждена
                ("Mzinho", "entry"),
                ("Senzu", "lurker"),  # роль не подтверждена
            )),
            ("FaZe Clan", "EU", "финалист", (
                ("Rain", "entry"),
                ("Broky", "awp"),  # роль не подтверждена
                ("Karrigan", "igl"),
                ("Ropz", "lurker"),
                ("Frozen", "lurker"),
            )),
        ),
    },
    {
        "event": "BLAST.tv Austin Major 2025",
        "year": 2025,
        "era": "modern",
        "teams": (
            ("G2 Esports", "EU", "группа", (
                ("HuNter-", "lurker"),
                ("MalbsMd", "entry"),
                ("Snax", "entry"),
                ("HeavyGod", "entry"),
                ("Hades", "entry"),
            )),
            ("Aurora Gaming", "EU", "группа", (
                ("XANTARES", "entry"),
                ("MAJ3R", "igl"),  # роль не подтверждена
                ("Wicadia", "support"),  # роль не подтверждена
                ("Woxic", "awp"),
                ("JottAAA", "lurker"),  # роль не подтверждена
            )),
            ("Team Liquid", "NA", "группа", (
                ("NAF", "lurker"),
                ("Twistzz", "lurker"),
                ("Ultimate", "awp"),  # роль не подтверждена
                ("NertZ", "igl"),  # роль не подтверждена
                ("Siuhy", "entry"),  # роль не подтверждена
            )),
            ("Team Falcons", "APAC", "группа", (
                ("Magisk", "awp"),  # роль не подтверждена
                ("NiKo", "igl"),  # роль не подтверждена
                ("TeSeS", "entry"),  # роль не подтверждена
                ("Kyxsan", "support"),
                ("M0NESY", "lurker"),  # роль не подтверждена
            )),
            ("3DMAX", "EU", "группа", (
                ("Lucky", "awp"),  # роль не подтверждена
                ("Ex3rcice", "igl"),  # роль не подтверждена
                ("Maka", "entry"),  # роль не подтверждена
                ("Graviti", "support"),  # роль не подтверждена
                ("Bodyy", "lurker"),  # роль не подтверждена
            )),
            ("Virtus.pro", "EEU", "группа", (
                ("FL1T", "support"),
                ("Fame", "support"),
                ("ElectroNic", "awp"),  # роль не подтверждена
                ("FL4MUS", "igl"),  # роль не подтверждена
                ("ICY", "entry"),  # роль не подтверждена
            )),
            ("MIBR", "SA", "группа", (
                ("Exit", "igl"),  # роль не подтверждена
                ("Brnz4n", "entry"),  # роль не подтверждена
                ("Insani", "support"),  # роль не подтверждена
                ("Saffee", "awp"),
                ("Lucaozy", "lurker"),  # роль не подтверждена
            )),
            ("M80", "NA", "группа", (
                ("Swisher", "awp"),  # роль не подтверждена
                ("Reck", "igl"),  # роль не подтверждена
                ("Slaxz-", "entry"),  # роль не подтверждена
                ("S1n", "support"),  # роль не подтверждена
                ("Lake", "lurker"),  # роль не подтверждена
            )),
            ("Complexity", "NA", "группа", (
                ("JT", "igl"),  # роль не подтверждена
                ("Grim", "entry"),
                ("Hallzerk", "awp"),
                ("Cxzi", "support"),  # роль не подтверждена
                ("Nicx", "lurker"),  # роль не подтверждена
            )),
            ("HEROIC", "EU", "группа", (
                ("SunPayus", "awp"),  # роль не подтверждена
                ("LNZ", "igl"),  # роль не подтверждена
                ("Yxngstxr", "entry"),  # роль не подтверждена
                ("Xfl0ud", "support"),  # роль не подтверждена
                ("TN1R", "lurker"),  # роль не подтверждена
            )),
            ("B8", "EU", "группа", (
                ("Npl", "awp"),  # роль не подтверждена
                ("Esenthial", "igl"),  # роль не подтверждена
                ("Headtr1ck", "entry"),  # роль не подтверждена
                ("Alex666", "support"),  # роль не подтверждена
                ("Kensizor", "lurker"),  # роль не подтверждена
            )),
            ("BetBoom Team", "EU", "группа", (
                ("S1ren", "igl"),  # роль не подтверждена
                ("Zorte", "awp"),
                ("Magnojez", "entry"),  # роль не подтверждена
                ("Ax1Le", "support"),  # роль не подтверждена
                ("Boombl4", "lurker"),  # роль не подтверждена
            )),
            ("TYLOO", "CN", "группа", (
                ("Attacker", "entry"),
                ("JamYoung", "awp"),  # роль не подтверждена
                ("Moseyuh", "igl"),  # роль не подтверждена
                ("Mercury", "support"),  # роль не подтверждена
                ("Jee", "lurker"),  # роль не подтверждена
            )),
            ("Lynn Vision Gaming", "EU", "группа", (
                ("Westmelon", "awp"),  # роль не подтверждена
                ("Z4kr", "igl"),  # роль не подтверждена
                ("EmiliaQAQ", "entry"),  # роль не подтверждена
                ("Starry", "support"),  # роль не подтверждена
                ("C4LLM3SU3", "lurker"),  # роль не подтверждена
            )),
            ("Wildcard", "NA", "группа", (
                ("Stanislaw", "igl"),
                ("JBa", "entry"),  # роль не подтверждена
                ("Sonic", "support"),  # роль не подтверждена
                ("Susp", "lurker"),  # роль не подтверждена
                ("Phzy", "awp"),
            )),
            ("FlyQuest", "EU", "группа", (
                ("INS", "awp"),  # роль не подтверждена
                ("Liazz", "support"),
                ("Vexite", "igl"),  # роль не подтверждена
                ("Regali", "entry"),  # роль не подтверждена
                ("Nettik", "lurker"),  # роль не подтверждена
            )),
            ("OG", "EU", "группа", (
                ("F1KU", "igl"),  # роль не подтверждена
                ("Chr1zN", "entry"),  # роль не подтверждена
                ("Buzz", "support"),  # роль не подтверждена
                ("Spooke", "lurker"),  # роль не подтверждена
                ("Nicoodoz", "awp"),
            )),
            ("Chinggis Warriors", "EU", "группа", (
                ("Controlez", "awp"),  # роль не подтверждена
                ("Ariucle", "igl"),  # роль не подтверждена
                ("ROUX", "entry"),  # роль не подтверждена
                ("Efire", "support"),  # роль не подтверждена
                ("Cool4st", "lurker"),  # роль не подтверждена
            )),
            ("Imperial Esports", "EU", "группа", (
                ("VINI", "support"),
                ("Noway", "awp"),  # роль не подтверждена
                ("Decenty", "igl"),  # роль не подтверждена
                ("Try", "entry"),  # роль не подтверждена
                ("ChayJESUS", "lurker"),  # роль не подтверждена
            )),
            ("Nemiga Gaming", "EU", "группа", (
                ("1eeR", "awp"),  # роль не подтверждена
                ("KhaN", "igl"),  # роль не подтверждена
                ("Riskyb0b", "entry"),  # роль не подтверждена
                ("Xant3r", "support"),  # роль не подтверждена
                ("Zweih", "lurker"),  # роль не подтверждена
            )),
            ("NRG", "NA", "группа", (
                ("OSee", "awp"),
                ("HexT", "entry"),
                ("Nitr0", "igl"),
                ("Jeorge", "lurker"),  # роль не подтверждена
                ("Br0", "support"),
            )),
            ("Legacy", "EU", "группа", (
                ("Latto", "awp"),  # роль не подтверждена
                ("Dumau", "entry"),
                ("Saadzin", "igl"),  # роль не подтверждена
                ("N1ssim", "support"),  # роль не подтверждена
                ("Lux", "lurker"),  # роль не подтверждена
            )),
            ("Metizport", "EU", "группа", (
                ("Adamb", "awp"),  # роль не подтверждена
                ("Plopski", "support"),
                ("L00m1", "entry"),  # роль не подтверждена
                ("Isak", "lurker"),  # роль не подтверждена
                ("Hampus", "igl"),
            )),
            ("Fluxo", "EU", "группа", (
                ("Zevy", "awp"),  # роль не подтверждена
                ("ArT", "igl"),
                ("Kye", "entry"),  # роль не подтверждена
                ("Piriajr", "support"),  # роль не подтверждена
                ("Mlhzin", "lurker"),  # роль не подтверждена
            )),
            ("BESTIA", "EU", "группа", (
                ("Noktse", "awp"),  # роль не подтверждена
                ("Luchov", "igl"),  # роль не подтверждена
                ("Tomaszin", "entry"),  # роль не подтверждена
                ("Cass1n", "support"),  # роль не подтверждена
                ("Timo", "lurker"),  # роль не подтверждена
            )),
            ("Team Vitality", "EU", "победитель", (
                ("ApEX", "igl"),
                ("ZywOo", "awp"),
                ("FlameZ", "entry"),
                ("Mezii", "support"),  # роль не подтверждена
                ("Ropz", "lurker"),
            )),
            ("MOUZ", "EU", "топ-4", (
                ("Torzsi", "awp"),
                ("XertioN", "igl"),  # роль не подтверждена
                ("Jimpphat", "entry"),
                ("Brollan", "support"),  # роль не подтверждена
                ("Spinx", "entry"),
            )),
            ("PaiN Gaming", "SA", "топ-4", (
                ("Biguzera", "igl"),  # роль не подтверждена
                ("Nqz", "awp"),
                ("Snow", "entry"),  # роль не подтверждена
                ("Dav1deuS", "support"),  # роль не подтверждена
                ("Dgt", "lurker"),  # роль не подтверждена
            )),
            ("Team Spirit", "EEU", "топ-8", (
                ("Chopper", "igl"),
                ("Magixx", "lurker"),
                ("Zont1x", "lurker"),
                ("Donk", "entry"),
                ("Sh1ro", "awp"),
            )),
            ("Natus Vincere", "EEU", "топ-8", (
                ("B1t", "igl"),  # роль не подтверждена
                ("Aleksib", "support"),  # роль не подтверждена
                ("JL", "lurker"),  # роль не подтверждена
                ("IM", "entry"),
                ("W0nderful", "awp"),
            )),
            ("FaZe Clan", "EU", "топ-8", (
                ("Rain", "entry"),
                ("Broky", "awp"),  # роль не подтверждена
                ("Karrigan", "igl"),
                ("Frozen", "lurker"),
                ("EliGE", "lurker"),
            )),
            ("FURIA", "SA", "топ-8", (
                ("Yuurih", "igl"),  # роль не подтверждена
                ("KSCERATO", "support"),  # роль не подтверждена
                ("FalleN", "awp"),
                ("Skullz", "entry"),
                ("Molodoy", "lurker"),  # роль не подтверждена
            )),
            ("The MongolZ", "APAC", "финалист", (
                ("BLitz", "awp"),  # роль не подтверждена
                ("Techno4K", "igl"),  # роль не подтверждена
                ("910", "support"),  # роль не подтверждена
                ("Mzinho", "entry"),
                ("Senzu", "lurker"),  # роль не подтверждена
            )),
        ),
    },
    {
        "event": "StarLadder Budapest 2025",
        "year": 2025,
        "era": "modern",
        "teams": (
            ("Aurora Gaming", "EU", "группа", (
                ("XANTARES", "entry"),
                ("MAJ3R", "igl"),  # роль не подтверждена
                ("Wicadia", "support"),  # роль не подтверждена
                ("Woxic", "awp"),
                ("JottAAA", "lurker"),  # роль не подтверждена
            )),
            ("Astralis", "EU", "группа", (
                ("Dev1ce", "awp"),
                ("Staehr", "entry"),  # роль не подтверждена
                ("Jabbi", "support"),  # роль не подтверждена
                ("HooXi", "igl"),
                ("Magisk", "lurker"),  # роль не подтверждена
            )),
            ("TYLOO", "CN", "группа", (
                ("Attacker", "entry"),
                ("JamYoung", "awp"),  # роль не подтверждена
                ("Moseyuh", "igl"),  # роль не подтверждена
                ("Mercury", "support"),  # роль не подтверждена
                ("Jee", "lurker"),  # роль не подтверждена
            )),
            ("MIBR", "SA", "группа", (
                ("Exit", "awp"),  # роль не подтверждена
                ("Brnz4n", "igl"),  # роль не подтверждена
                ("Insani", "entry"),  # роль не подтверждена
                ("Kl1m", "lurker"),  # роль не подтверждена
                ("Qikert", "support"),
            )),
            ("Legacy", "EU", "группа", (
                ("Latto", "awp"),  # роль не подтверждена
                ("Dumau", "entry"),
                ("Saadzin", "igl"),  # роль не подтверждена
                ("N1ssim", "support"),  # роль не подтверждена
                ("Lux", "lurker"),  # роль не подтверждена
            )),
            ("GamerLegion", "EU", "группа", (
                ("Ztr", "awp"),  # роль не подтверждена
                ("Tauson", "igl"),  # роль не подтверждена
                ("PR", "support"),  # роль не подтверждена
                ("REZ", "entry"),
                ("Kursy", "lurker"),  # роль не подтверждена
            )),
            ("Fnatic", "EU", "группа", (
                ("KRIMZ", "support"),
                ("BlameF", "awp"),  # роль не подтверждена
                ("Fear", "igl"),  # роль не подтверждена
                ("Jambo", "lurker"),  # роль не подтверждена
                ("CYPHER", "entry"),
            )),
            ("Ninjas in Pyjamas", "EU", "группа", (
                ("R1nkle", "awp"),  # роль не подтверждена
                ("Ewjerkz", "entry"),  # роль не подтверждена
                ("Sjuush", "support"),  # роль не подтверждена
                ("Snappi", "igl"),
                ("XKacpersky", "lurker"),  # роль не подтверждена
            )),
            ("FlyQuest", "EU", "группа", (
                ("INS", "awp"),  # роль не подтверждена
                ("Vexite", "igl"),  # роль не подтверждена
                ("Regali", "entry"),  # роль не подтверждена
                ("Nettik", "support"),  # роль не подтверждена
                ("Jks", "lurker"),
            )),
            ("Lynn Vision Gaming", "EU", "группа", (
                ("Westmelon", "awp"),  # роль не подтверждена
                ("Z4kr", "igl"),  # роль не подтверждена
                ("EmiliaQAQ", "entry"),  # роль не подтверждена
                ("Starry", "support"),  # роль не подтверждена
                ("C4LLM3SU3", "lurker"),  # роль не подтверждена
            )),
            ("M80", "NA", "группа", (
                ("Swisher", "awp"),  # роль не подтверждена
                ("Slaxz-", "igl"),  # роль не подтверждена
                ("S1n", "support"),  # роль не подтверждена
                ("Lake", "lurker"),  # роль не подтверждена
                ("HexT", "entry"),
            )),
            ("Fluxo", "EU", "группа", (
                ("Zevy", "awp"),  # роль не подтверждена
                ("ArT", "igl"),
                ("Kye", "entry"),  # роль не подтверждена
                ("Decenty", "support"),  # роль не подтверждена
                ("Lucaozy", "lurker"),  # роль не подтверждена
            )),
            ("RED Canids", "EU", "группа", (
                ("Venomzera", "awp"),  # роль не подтверждена
                ("Drop", "igl"),  # роль не подтверждена
                ("Kauez", "entry"),  # роль не подтверждена
                ("History", "support"),  # роль не подтверждена
                ("ChayJESUS", "lurker"),  # роль не подтверждена
            )),
            ("The Huns Esports", "EU", "группа", (
                ("Nin9", "awp"),  # роль не подтверждена
                ("Bart4k", "igl"),  # роль не подтверждена
                ("Cobrazera", "entry"),  # роль не подтверждена
                ("Xerolte", "support"),  # роль не подтверждена
                ("Sk0R", "lurker"),  # роль не подтверждена
            )),
            ("NRG", "NA", "группа", (
                ("Nitr0", "igl"),
                ("Jeorge", "awp"),  # роль не подтверждена
                ("Br0", "support"),
                ("XotiC", "entry"),
                ("Sonic", "lurker"),  # роль не подтверждена
            )),
            ("Rare Atom", "CN", "группа", (
                ("Summer", "lurker"),
                ("L1haNg", "awp"),  # роль не подтверждена
                ("ChildKing", "igl"),  # роль не подтверждена
                ("TiGeR", "entry"),  # роль не подтверждена
                ("Marek", "support"),  # роль не подтверждена
            )),
            ("Team Vitality", "EU", "победитель", (
                ("ApEX", "igl"),
                ("ZywOo", "awp"),
                ("FlameZ", "entry"),
                ("Mezii", "support"),  # роль не подтверждена
                ("Ropz", "lurker"),
            )),
            ("G2 Esports", "EU", "топ-12", (
                ("HuNter-", "lurker"),
                ("MalbsMd", "entry"),
                ("HeavyGod", "entry"),
                ("SunPayus", "awp"),  # роль не подтверждена
                ("Matys", "igl"),  # роль не подтверждена
            )),
            ("PaiN Gaming", "SA", "топ-12", (
                ("Biguzera", "igl"),  # роль не подтверждена
                ("Nqz", "awp"),
                ("Snow", "entry"),  # роль не подтверждена
                ("Dav1deuS", "support"),  # роль не подтверждена
                ("Dgt", "lurker"),  # роль не подтверждена
            )),
            ("3DMAX", "EU", "топ-12", (
                ("Lucky", "awp"),  # роль не подтверждена
                ("Ex3rcice", "igl"),  # роль не подтверждена
                ("Maka", "entry"),  # роль не подтверждена
                ("Graviti", "support"),  # роль не подтверждена
                ("Bodyy", "lurker"),  # роль не подтверждена
            )),
            ("Passion UA", "EU", "топ-12", (
                ("Kvem", "igl"),  # роль не подтверждена
                ("JT", "support"),  # роль не подтверждена
                ("Grim", "entry"),
                ("Hallzerk", "awp"),
                ("Nicx", "lurker"),  # роль не подтверждена
            )),
            ("B8", "EU", "топ-12", (
                ("Npl", "awp"),  # роль не подтверждена
                ("Esenthial", "igl"),  # роль не подтверждена
                ("Headtr1ck", "entry"),  # роль не подтверждена
                ("Alex666", "support"),  # роль не подтверждена
                ("Kensizor", "lurker"),  # роль не подтверждена
            )),
            ("Imperial Esports", "EU", "топ-12", (
                ("VINI", "support"),
                ("Noway", "awp"),  # роль не подтверждена
                ("Try", "igl"),  # роль не подтверждена
                ("Chelo", "lurker"),  # роль не подтверждена
                ("Skullz", "entry"),
            )),
            ("Team Liquid", "NA", "топ-16", (
                ("NAF", "lurker"),
                ("Ultimate", "awp"),  # роль не подтверждена
                ("NertZ", "igl"),  # роль не подтверждена
                ("Siuhy", "entry"),  # роль не подтверждена
                ("EliGE", "lurker"),
            )),
            ("PARIVISION", "EU", "топ-16", (
                ("BELCHONOKK", "igl"),  # роль не подтверждена
                ("Jame", "awp"),
                ("Nota", "entry"),  # роль не подтверждена
                ("XiELO", "support"),  # роль не подтверждена
                ("AW", "lurker"),  # роль не подтверждена
            )),
            ("Team Spirit", "EEU", "топ-4", (
                ("Chopper", "igl"),
                ("Zont1x", "lurker"),
                ("Donk", "entry"),
                ("Sh1ro", "awp"),
                ("Zweih", "support"),  # роль не подтверждена
            )),
            ("Natus Vincere", "EEU", "топ-4", (
                ("B1t", "igl"),  # роль не подтверждена
                ("Aleksib", "support"),  # роль не подтверждена
                ("IM", "entry"),
                ("W0nderful", "awp"),
                ("Makazze", "lurker"),  # роль не подтверждена
            )),
            ("FURIA", "SA", "топ-8", (
                ("Yuurih", "igl"),  # роль не подтверждена
                ("KSCERATO", "support"),  # роль не подтверждена
                ("FalleN", "awp"),
                ("Molodoy", "lurker"),  # роль не подтверждена
                ("YEKINDAR", "entry"),
            )),
            ("Team Falcons", "APAC", "топ-8", (
                ("NiKo", "awp"),  # роль не подтверждена
                ("TeSeS", "igl"),  # роль не подтверждена
                ("Kyxsan", "support"),
                ("M0NESY", "entry"),  # роль не подтверждена
                ("Kyousuke", "lurker"),  # роль не подтверждена
            )),
            ("The MongolZ", "APAC", "топ-8", (
                ("BLitz", "awp"),  # роль не подтверждена
                ("Techno4K", "igl"),  # роль не подтверждена
                ("910", "support"),  # роль не подтверждена
                ("Mzinho", "entry"),
                ("Senzu", "lurker"),  # роль не подтверждена
            )),
            ("MOUZ", "EU", "топ-8", (
                ("Torzsi", "awp"),
                ("XertioN", "igl"),  # роль не подтверждена
                ("Jimpphat", "entry"),
                ("Brollan", "support"),  # роль не подтверждена
                ("Spinx", "entry"),
            )),
            ("FaZe Clan", "EU", "финалист", (
                ("Rain", "entry"),
                ("100 Thieves", "awp"),  # роль не подтверждена
                ("Broky", "support"),  # роль не подтверждена
                ("Karrigan", "igl"),
                ("Frozen", "lurker"),
            )),
        ),
    },
    {
        "event": "IEM Cologne 2026",
        "year": 2026,
        "era": "modern",
        "teams": (
            ("Astralis", "EU", "группа", (
                ("Staehr", "entry"),  # роль не подтверждена
                ("Jabbi", "support"),  # роль не подтверждена
                ("HooXi", "igl"),
                ("Phzy", "awp"),
                ("Ryu", "lurker"),  # роль не подтверждена
            )),
            ("PaiN Gaming", "SA", "группа", (
                ("Biguzera", "igl"),  # роль не подтверждена
                ("Nqz", "awp"),
                ("Snow", "entry"),  # роль не подтверждена
                ("Piriajr", "support"),  # роль не подтверждена
                ("V$m", "lurker"),  # роль не подтверждена
            )),
            ("GamerLegion", "EU", "группа", (
                ("Tauson", "awp"),  # роль не подтверждена
                ("PR", "igl"),  # роль не подтверждена
                ("REZ", "entry"),
                ("Hypex", "support"),  # роль не подтверждена
                ("Snax", "entry"),
            )),
            ("HEROIC", "EU", "группа", (
                ("Yxngstxr", "awp"),  # роль не подтверждена
                ("Xfl0ud", "igl"),  # роль не подтверждена
                ("Nilo", "entry"),  # роль не подтверждена
                ("Chr1zN", "support"),  # роль не подтверждена
                ("Susp", "lurker"),  # роль не подтверждена
            )),
            ("BIG", "EU", "группа", (
                ("TabseN", "awp"),  # роль не подтверждена
                ("JDC", "igl"),  # роль не подтверждена
                ("Gr1ks", "entry"),  # роль не подтверждена
                ("BlameF", "support"),  # роль не подтверждена
                ("FaveN", "lurker"),  # роль не подтверждена
            )),
            ("M80", "NA", "группа", (
                ("Swisher", "awp"),  # роль не подтверждена
                ("Slaxz-", "igl"),  # роль не подтверждена
                ("S1n", "entry"),  # роль не подтверждена
                ("Lake", "support"),  # роль не подтверждена
                ("JBa", "lurker"),  # роль не подтверждена
            )),
            ("MIBR", "SA", "группа", (
                ("Brnz4n", "awp"),  # роль не подтверждена
                ("Insani", "igl"),  # роль не подтверждена
                ("Kl1m", "entry"),  # роль не подтверждена
                ("LNZ", "support"),  # роль не подтверждена
                ("Venomzera", "lurker"),  # роль не подтверждена
            )),
            ("SINNERS Esports", "EU", "группа", (
                ("Beastik", "awp"),  # роль не подтверждена
                ("SHOCK", "igl"),  # роль не подтверждена
                ("Kisserek", "entry"),  # роль не подтверждена
                ("StressarN", "support"),  # роль не подтверждена
                ("MoDo", "lurker"),  # роль не подтверждена
            )),
            ("NRG", "NA", "группа", (
                ("OSee", "awp"),
                ("Nitr0", "igl"),
                ("Br0", "support"),
                ("Sonic", "lurker"),  # роль не подтверждена
                ("Grim", "entry"),
            )),
            ("TYLOO", "CN", "группа", (
                ("JamYoung", "awp"),  # роль не подтверждена
                ("Moseyuh", "igl"),  # роль не подтверждена
                ("Mercury", "entry"),  # роль не подтверждена
                ("Jee", "support"),  # роль не подтверждена
                ("Zero", "lurker"),  # роль не подтверждена
            )),
            ("Sharks Esports", "EU", "группа", (
                ("Gafolo", "awp"),  # роль не подтверждена
                ("Rdnzao", "igl"),  # роль не подтверждена
                ("Doc", "entry"),  # роль не подтверждена
                ("Koala", "support"),  # роль не подтверждена
                ("Maxxkor", "lurker"),  # роль не подтверждена
            )),
            ("Gaimin Gladiators", "EU", "группа", (
                ("JOTA", "awp"),  # роль не подтверждена
                ("NEKIZ", "igl"),  # роль не подтверждена
                ("Felps", "entry"),  # роль не подтверждена
                ("HEN1", "support"),  # роль не подтверждена
                ("Luken", "lurker"),  # роль не подтверждена
            )),
            ("Team Liquid", "NA", "группа", (
                ("NAF", "lurker"),
                ("Ultimate", "awp"),  # роль не подтверждена
                ("Siuhy", "igl"),  # роль не подтверждена
                ("EliGE", "lurker"),
                ("MalbsMd", "entry"),
            )),
            ("Lynn Vision Gaming", "EU", "группа", (
                ("Westmelon", "awp"),  # роль не подтверждена
                ("Z4kr", "igl"),  # роль не подтверждена
                ("EmiliaQAQ", "entry"),  # роль не подтверждена
                ("Starry", "support"),  # роль не подтверждена
                ("C4LLM3SU3", "lurker"),  # роль не подтверждена
            )),
            ("THUNDERdOWNUNDER", "EU", "группа", (
                ("Asap", "awp"),  # роль не подтверждена
                ("TjP", "igl"),  # роль не подтверждена
                ("AliStair", "entry"),  # роль не подтверждена
                ("Dexter", "lurker"),  # роль не подтверждена
                ("Liazz", "support"),
            )),
            ("FlyQuest", "EU", "группа", (
                ("INS", "awp"),  # роль не подтверждена
                ("Vexite", "igl"),  # роль не подтверждена
                ("Nettik", "entry"),  # роль не подтверждена
                ("Jks", "lurker"),
                ("Story", "support"),  # роль не подтверждена
            )),
            ("Team Falcons", "APAC", "победитель", (
                ("NiKo", "awp"),  # роль не подтверждена
                ("TeSeS", "igl"),  # роль не подтверждена
                ("Kyxsan", "support"),
                ("M0NESY", "entry"),  # роль не подтверждена
                ("Kyousuke", "lurker"),  # роль не подтверждена
            )),
            ("Natus Vincere", "EEU", "топ-12", (
                ("B1t", "igl"),  # роль не подтверждена
                ("Aleksib", "support"),  # роль не подтверждена
                ("IM", "entry"),
                ("W0nderful", "awp"),
                ("Makazze", "lurker"),  # роль не подтверждена
            )),
            ("The MongolZ", "APAC", "топ-12", (
                ("BLitz", "awp"),  # роль не подтверждена
                ("Techno4K", "igl"),  # роль не подтверждена
                ("910", "support"),  # роль не подтверждена
                ("Mzinho", "entry"),
                ("Cobrazera", "lurker"),  # роль не подтверждена
            )),
            ("MOUZ", "EU", "топ-12", (
                ("Torzsi", "awp"),
                ("XertioN", "igl"),  # роль не подтверждена
                ("Jimpphat", "entry"),
                ("Brollan", "support"),  # роль не подтверждена
                ("Spinx", "entry"),
            )),
            ("FUT Esports", "EU", "топ-12", (
                ("Dem0n", "awp"),  # роль не подтверждена
                ("Krabeni", "igl"),  # роль не подтверждена
                ("Cmtry", "entry"),  # роль не подтверждена
                ("Dziugss", "support"),  # роль не подтверждена
                ("LauNX", "lurker"),  # роль не подтверждена
            )),
            ("Legacy", "EU", "топ-12", (
                ("Latto", "awp"),  # роль не подтверждена
                ("Dumau", "entry"),
                ("Saadzin", "support"),  # роль не подтверждена
                ("N1ssim", "lurker"),  # роль не подтверждена
                ("ArT", "igl"),
            )),
            ("Monte", "EU", "топ-12", (
                ("Gizmy", "awp"),  # роль не подтверждена
                ("Afro", "igl"),  # роль не подтверждена
                ("AZUWU", "entry"),  # роль не подтверждена
                ("Bymas", "support"),  # роль не подтверждена
                ("Rainwaker", "lurker"),  # роль не подтверждена
            )),
            ("PARIVISION", "EU", "топ-16", (
                ("BELCHONOKK", "igl"),  # роль не подтверждена
                ("Jame", "awp"),
                ("Nota", "entry"),  # роль не подтверждена
                ("XiELO", "support"),  # роль не подтверждена
                ("Zweih", "lurker"),  # роль не подтверждена
            )),
            ("B8", "EU", "топ-16", (
                ("Npl", "awp"),  # роль не подтверждена
                ("Esenthial", "igl"),  # роль не подтверждена
                ("Alex666", "entry"),  # роль не подтверждена
                ("Kensizor", "support"),  # роль не подтверждена
                ("S1zzi", "lurker"),  # роль не подтверждена
            )),
            ("Aurora Gaming", "EU", "топ-4", (
                ("XANTARES", "entry"),
                ("MAJ3R", "igl"),  # роль не подтверждена
                ("Wicadia", "support"),  # роль не подтверждена
                ("Woxic", "awp"),
                ("Soulfly", "lurker"),  # роль не подтверждена
            )),
            ("Team Spirit", "EEU", "топ-4", (
                ("Magixx", "lurker"),
                ("Zont1x", "lurker"),
                ("Donk", "entry"),
                ("Sh1ro", "awp"),
                ("TN1R", "igl"),  # роль не подтверждена
            )),
            ("Team Vitality", "EU", "топ-8", (
                ("ApEX", "igl"),
                ("ZywOo", "awp"),
                ("FlameZ", "entry"),
                ("Mezii", "support"),  # роль не подтверждена
                ("Ropz", "lurker"),
            )),
            ("G2 Esports", "EU", "топ-8", (
                ("HuNter-", "lurker"),
                ("HeavyGod", "entry"),
                ("SunPayus", "awp"),  # роль не подтверждена
                ("Matys", "igl"),  # роль не подтверждена
                ("NertZ", "support"),  # роль не подтверждена
            )),
            ("9z Team", "SA", "топ-8", (
                ("Max", "awp"),  # роль не подтверждена
                ("HUASOPEEK", "igl"),  # роль не подтверждена
                ("Luchov", "entry"),  # роль не подтверждена
                ("Meyern", "support"),  # роль не подтверждена
                ("Dgt", "lurker"),  # роль не подтверждена
            )),
            ("BetBoom Team", "EU", "топ-8", (
                ("S1ren", "igl"),  # роль не подтверждена
                ("Zorte", "awp"),
                ("Magnojez", "entry"),  # роль не подтверждена
                ("Boombl4", "support"),  # роль не подтверждена
                ("FL4MUS", "lurker"),  # роль не подтверждена
            )),
            ("FURIA", "SA", "финалист", (
                ("Yuurih", "igl"),  # роль не подтверждена
                ("KSCERATO", "support"),  # роль не подтверждена
                ("FalleN", "awp"),
                ("Molodoy", "lurker"),  # роль не подтверждена
                ("YEKINDAR", "entry"),
            )),
        ),
    },
)

__all__ = ["EVENTS"]
