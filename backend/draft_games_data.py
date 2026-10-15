# -*- coding: utf-8 -*-
"""Составы для драфтов по Valorant и Rocket League.

Пак — это реальный состав команды на конкретном турнире: команда, событие, год,
место, регион, эпоха, карты (арены) того пула и игроки с ролями.

Игрок: (ник, роль, AIM, CLUTCH, IMP). Оценки — **игровые**, а не официальная
статистика: они расставлены так, чтобы чемпионы и звёзды были сильнее, а у
игроков разных ролей был смысл в драфте. Ники, команды и турниры — исторические
факты и принадлежат их владельцам. Роли указаны по основной роли игрока в этом
составе: кто-то совмещал позиции, тогда выбрана главная.
"""
from __future__ import annotations

from typing import Any, Dict, Tuple

# Карты Valorant: пул турниров VCT.
VALORANT_MAPS: Tuple[str, ...] = (
    "Ascent", "Bind", "Haven", "Split", "Icebox", "Breeze", "Fracture", "Pearl",
    "Lotus", "Sunset",
)

# Арены Rocket League.
RL_ARENAS: Tuple[str, ...] = (
    "DFH Stadium", "Mannfield", "Champions Field", "Urban Central", "Wasteland",
    "Neo Tokyo", "Beckwith Park", "Utopia Coliseum",
)

VALORANT_PACKS: Tuple[Dict[str, Any], ...] = (
    # ------------------------------------------------- Первый VCT: 2021–2022
    {
        "id": "acend-ch2021", "team": "Acend", "event": "VCT Champions 2021",
        "year": 2021, "place": "победитель", "major": True, "region": "EMEA", "era": "legacy",
        "maps": ["Ascent", "Bind", "Haven"],
        "players": [
            ("cNed", "duelist", 90, 84, 88),
            ("starxo", "initiator", 82, 80, 84),
            ("Kiles", "sentinel", 78, 82, 79),
            ("zeek", "flex", 80, 78, 82),
            ("BONECOLD", "controller", 76, 86, 80),
        ],
    },
    {
        "id": "gambit-ch2021", "team": "Gambit Esports", "event": "VCT Champions 2021",
        "year": 2021, "place": "финалист", "major": True, "region": "EMEA", "era": "legacy",
        "maps": ["Icebox", "Bind", "Ascent"],
        "players": [
            ("nAts", "sentinel", 88, 92, 90),
            ("Chronicle", "initiator", 84, 86, 85),
            ("Redgar", "controller", 78, 84, 82),
            ("Sheydos", "flex", 82, 80, 83),
            ("d3ffo", "duelist", 84, 78, 82),
        ],
    },
    {
        "id": "sentinels-reykjavik2021", "team": "Sentinels", "event": "VCT Masters Reykjavík 2021",
        "year": 2021, "place": "победитель", "major": True, "region": "NA", "era": "legacy",
        "maps": ["Haven", "Ascent", "Bind"],
        "players": [
            ("TenZ", "duelist", 92, 84, 90),
            ("dapr", "sentinel", 82, 84, 83),
            ("SicK", "initiator", 82, 82, 83),
            ("zombs", "controller", 78, 84, 81),
            ("ShahZaM", "flex", 80, 86, 84),
        ],
    },
    {
        "id": "gambit-berlin2021", "team": "Gambit Esports", "event": "VCT Masters Berlin 2021",
        "year": 2021, "place": "победитель", "major": True, "region": "EMEA", "era": "legacy",
        "maps": ["Split", "Icebox", "Haven"],
        "players": [
            ("nAts", "sentinel", 88, 92, 90),
            ("Chronicle", "initiator", 84, 86, 85),
            ("Redgar", "controller", 78, 84, 82),
            ("Sheydos", "flex", 82, 80, 83),
            ("d3ffo", "duelist", 84, 78, 82),
        ],
    },
    {
        "id": "loud-ch2022", "team": "LOUD", "event": "VCT Champions 2022",
        "year": 2022, "place": "победитель", "major": True, "region": "SA", "era": "legacy",
        "maps": ["Haven", "Fracture", "Ascent"],
        "players": [
            ("aspas", "duelist", 94, 86, 92),
            ("Less", "sentinel", 88, 88, 88),
            ("Sacy", "initiator", 84, 86, 86),
            ("saadhak", "flex", 82, 90, 86),
            ("pANcada", "controller", 84, 84, 85),
        ],
    },
    {
        "id": "optic-ch2022", "team": "OpTic Gaming", "event": "VCT Champions 2022",
        "year": 2022, "place": "финалист", "major": True, "region": "NA", "era": "legacy",
        "maps": ["Ascent", "Bind", "Breeze"],
        "players": [
            ("yay", "duelist", 93, 88, 92),
            ("crashies", "initiator", 84, 84, 85),
            ("FNS", "controller", 78, 88, 84),
            ("Marved", "flex", 86, 84, 86),
            ("Victor", "sentinel", 82, 84, 84),
        ],
    },
    {
        "id": "fpx-copenhagen2022", "team": "FunPlus Phoenix", "event": "VCT Masters Copenhagen 2022",
        "year": 2022, "place": "победитель", "major": True, "region": "EMEA", "era": "legacy",
        "maps": ["Split", "Pearl", "Icebox"],
        "players": [
            ("ardiis", "duelist", 88, 82, 87),
            ("Zyppan", "initiator", 86, 84, 86),
            ("ANGE1", "controller", 80, 88, 84),
            ("Suygetsu", "sentinel", 86, 88, 87),
            ("Shao", "flex", 84, 86, 86),
        ],
    },
    {
        "id": "prx-copenhagen2022", "team": "Paper Rex", "event": "VCT Masters Copenhagen 2022",
        "year": 2022, "place": "финалист", "major": True, "region": "APAC", "era": "legacy",
        "maps": ["Bind", "Haven", "Icebox"],
        "players": [
            ("Jinggg", "duelist", 90, 84, 89),
            ("f0rsakeN", "flex", 88, 86, 88),
            ("d4v41", "sentinel", 84, 86, 85),
            ("mindfreak", "controller", 80, 84, 82),
            ("Benkai", "initiator", 80, 84, 83),
        ],
    },
    # ---------------------------------------------------- Франшиза: 2023–2024
    {
        "id": "eg-ch2023", "team": "Evil Geniuses", "event": "VCT Champions 2023",
        "year": 2023, "place": "победитель", "major": True, "region": "NA", "era": "modern",
        "maps": ["Lotus", "Ascent", "Haven"],
        "players": [
            ("Demon1", "duelist", 92, 86, 91),
            ("Ethan", "initiator", 86, 88, 87),
            ("Boostio", "controller", 82, 90, 86),
            ("C0M", "sentinel", 84, 84, 85),
            ("Jawgemo", "flex", 86, 84, 86),
        ],
    },
    {
        "id": "prx-ch2023", "team": "Paper Rex", "event": "VCT Champions 2023",
        "year": 2023, "place": "финалист", "major": True, "region": "APAC", "era": "modern",
        "maps": ["Sunset", "Lotus", "Ascent"],
        "players": [
            ("Jinggg", "duelist", 91, 86, 90),
            ("something", "initiator", 88, 84, 87),
            ("f0rsakeN", "flex", 88, 86, 88),
            ("d4v41", "sentinel", 84, 86, 85),
            ("mindfreak", "controller", 80, 86, 83),
        ],
    },
    {
        "id": "fnatic-tokyo2023", "team": "Fnatic", "event": "VCT Masters Tokyo 2023",
        "year": 2023, "place": "победитель", "major": True, "region": "EMEA", "era": "modern",
        "maps": ["Lotus", "Split", "Ascent"],
        "players": [
            ("Derke", "duelist", 92, 86, 91),
            ("Leo", "flex", 88, 86, 88),
            ("Alfajer", "sentinel", 88, 88, 89),
            ("Chronicle", "initiator", 86, 88, 87),
            ("Boaster", "controller", 82, 90, 86),
        ],
    },
    {
        "id": "edg-ch2024", "team": "EDward Gaming", "event": "VCT Champions 2024",
        "year": 2024, "place": "победитель", "major": True, "region": "CN", "era": "modern",
        "maps": ["Haven", "Sunset", "Lotus"],
        "players": [
            ("ZmjjKK", "duelist", 92, 88, 91),
            ("CHICHOO", "sentinel", 86, 88, 87),
            ("nobody", "controller", 82, 88, 85),
            ("Smoggy", "flex", 86, 84, 86),
            ("Haodong", "initiator", 84, 84, 84),
        ],
    },
    {
        "id": "heretics-ch2024", "team": "Team Heretics", "event": "VCT Champions 2024",
        "year": 2024, "place": "финалист", "major": True, "region": "EMEA", "era": "modern",
        "maps": ["Sunset", "Ascent", "Lotus"],
        "players": [
            ("MiniBoo", "duelist", 88, 84, 87),
            ("Wo0t", "flex", 86, 84, 86),
            ("benjyfishy", "sentinel", 86, 88, 87),
            ("RieNs", "initiator", 84, 86, 85),
            ("Boo", "controller", 80, 90, 85),
        ],
    },
    {
        "id": "sentinels-madrid2024", "team": "Sentinels", "event": "VCT Masters Madrid 2024",
        "year": 2024, "place": "победитель", "major": True, "region": "NA", "era": "modern",
        "maps": ["Sunset", "Icebox", "Ascent"],
        "players": [
            ("TenZ", "duelist", 90, 84, 88),
            ("zekken", "flex", 88, 86, 88),
            ("Sacy", "initiator", 84, 88, 86),
            ("Zellsis", "sentinel", 84, 86, 85),
            ("johnqt", "controller", 84, 88, 86),
        ],
    },
    {
        "id": "geng-shanghai2024", "team": "Gen.G", "event": "VCT Masters Shanghai 2024",
        "year": 2024, "place": "победитель", "major": True, "region": "APAC", "era": "modern",
        "maps": ["Icebox", "Sunset", "Lotus"],
        "players": [
            ("t3xture", "duelist", 90, 86, 89),
            ("Karon", "sentinel", 86, 88, 87),
            ("Meteor", "flex", 86, 88, 87),
            ("Lakia", "initiator", 82, 84, 83),
            ("Munchkin", "controller", 84, 88, 86),
        ],
    },
    {
        "id": "heretics-madrid2024", "team": "Team Heretics", "event": "VCT Masters Madrid 2024",
        "year": 2024, "place": "финалист", "major": True, "region": "EMEA", "era": "modern",
        "maps": ["Icebox", "Ascent", "Sunset"],
        "players": [
            ("MiniBoo", "duelist", 88, 84, 87),
            ("Wo0t", "flex", 86, 84, 86),
            ("benjyfishy", "sentinel", 86, 88, 87),
            ("RieNs", "initiator", 84, 86, 85),
            ("Boo", "controller", 80, 90, 85),
        ],
    },
)

RL_PACKS: Tuple[Dict[str, Any], ...] = (
    # --------------------------------------------------- Легенды RLCS: 2017–2019
    {
        "id": "galeforce-s4", "team": "Gale Force Esports", "event": "RLCS Season 4 Finals",
        "year": 2017, "place": "победитель", "major": True, "region": "EU", "era": "legacy",
        "maps": ["DFH Stadium", "Mannfield", "Champions Field"],
        "players": [
            ("Kaydop", "striker", 92, 90, 91),
            ("ViolentPanda", "midfield", 88, 90, 89),
            ("Turbopolsa", "keeper", 90, 92, 91),
        ],
    },
    {
        "id": "dignitas-s5", "team": "Dignitas", "event": "RLCS Season 5 Finals",
        "year": 2018, "place": "победитель", "major": True, "region": "EU", "era": "legacy",
        "maps": ["Mannfield", "DFH Stadium", "Wasteland"],
        "players": [
            ("Kaydop", "striker", 92, 90, 91),
            ("ViolentPanda", "midfield", 88, 90, 89),
            ("Turbopolsa", "keeper", 90, 92, 91),
        ],
    },
    {
        "id": "cloud9-s6", "team": "Cloud9", "event": "RLCS Season 6 Finals",
        "year": 2018, "place": "победитель", "major": True, "region": "NA", "era": "legacy",
        "maps": ["Champions Field", "DFH Stadium", "Urban Central"],
        "players": [
            ("SquishyMuffinz", "striker", 92, 92, 93),
            ("Gimmick", "midfield", 86, 86, 87),
            ("Torment", "keeper", 88, 90, 89),
        ],
    },
    {
        "id": "vitality-s7", "team": "Renault Vitality", "event": "RLCS Season 7 Finals",
        "year": 2019, "place": "победитель", "major": True, "region": "EU", "era": "legacy",
        "maps": ["DFH Stadium", "Utopia Coliseum", "Mannfield"],
        "players": [
            ("Fairy Peak", "striker", 90, 88, 89),
            ("Scrub Killa", "midfield", 88, 86, 87),
            ("Kaydop", "keeper", 90, 90, 90),
        ],
    },
    {
        "id": "nrg-s8", "team": "NRG Esports", "event": "RLCS Season 8 Finals",
        "year": 2019, "place": "победитель", "major": True, "region": "NA", "era": "legacy",
        "maps": ["Champions Field", "Neo Tokyo", "DFH Stadium"],
        "players": [
            ("Jstn", "striker", 92, 88, 91),
            ("GarrettG", "midfield", 90, 90, 90),
            ("Turbopolsa", "keeper", 88, 92, 90),
        ],
    },
    # ------------------------------------------------ Новое время: 2021–2025
    {
        "id": "bds-2021", "team": "Team BDS", "event": "RLCS 2021–22 World Championship",
        "year": 2022, "place": "победитель", "major": True, "region": "EU", "era": "modern",
        "maps": ["DFH Stadium", "Champions Field", "Mannfield"],
        "players": [
            ("M0nkey M00n", "striker", 92, 90, 91),
            ("Extra", "midfield", 90, 90, 90),
            ("Marc_by_8", "keeper", 88, 88, 88),
        ],
    },
    {
        "id": "g2-2022", "team": "G2 Esports", "event": "RLCS 2021–22 Winter Major",
        "year": 2022, "place": "победитель", "major": True, "region": "NA", "era": "modern",
        "maps": ["Champions Field", "DFH Stadium", "Urban Central"],
        "players": [
            ("JKnaps", "striker", 90, 88, 89),
            ("Chicago", "midfield", 88, 88, 88),
            ("Atomic", "keeper", 88, 86, 87),
        ],
    },
    {
        "id": "moist-2022", "team": "Moist Esports", "event": "RLCS 2021–22 Spring Major",
        "year": 2022, "place": "победитель", "major": True, "region": "EU", "era": "modern",
        "maps": ["DFH Stadium", "Utopia Coliseum", "Mannfield"],
        "players": [
            ("Vatira", "striker", 92, 88, 91),
            ("Joyo", "midfield", 88, 88, 88),
            ("rise.", "keeper", 88, 86, 87),
        ],
    },
    {
        "id": "vitality-2023", "team": "Team Vitality", "event": "RLCS 2022–23 World Championship",
        "year": 2023, "place": "победитель", "major": True, "region": "EU", "era": "modern",
        "maps": ["DFH Stadium", "Champions Field", "Beckwith Park"],
        "players": [
            ("zen", "striker", 94, 90, 93),
            ("Alpha54", "midfield", 90, 88, 90),
            ("Radosin", "keeper", 86, 88, 87),
        ],
    },
    {
        "id": "bds-2024", "team": "Team BDS", "event": "RLCS 2024 World Championship",
        "year": 2024, "place": "победитель", "major": True, "region": "EU", "era": "modern",
        "maps": ["Champions Field", "Mannfield", "DFH Stadium"],
        "players": [
            ("M0nkey M00n", "striker", 90, 88, 90),
            ("Extra", "midfield", 88, 88, 88),
            ("Rise", "keeper", 88, 86, 87),
        ],
    },
)

__all__ = ["VALORANT_MAPS", "RL_ARENAS", "VALORANT_PACKS", "RL_PACKS"]
