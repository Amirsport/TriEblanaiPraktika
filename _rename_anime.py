#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Приводит названия аниме в «Аниме-сонглессе» к русскому виду.

Латинские названия (как в animethemes) заменяются общепринятыми русскими;
там, где русское название уже было, треки объединяются под него.
"""
from __future__ import annotations

import pathlib
import re
import sys

sys.path.insert(0, "/opt/greenhouse")

from backend.db import open_database  # noqa: E402

MAPPING = {
    "Aikatsu!": "Айкацу!",
    "Akame ga Kill!": "Убийца Акамэ!",
    "Akatsuki no Yona": "Ёна на заре",
    "Another": "Иная",
    "Bakuman.": "Бакуман",
    "BanG Dream!": "Банг Дрим!",
    "Beelzebub": "Вельзевул",
    "Black Clover (TV)": "Чёрный клевер",
    "Blue Lock": "Синяя тюрьма",
    "Bocchi the Rock!": "Ботти — рокерша!",
    "Boku dake ga Inai Machi": "Город, в котором меня нет",
    "Boku no Hero Academia 2nd Season": "Моя геройская академия",
    "Boruto: Naruto Next Generations": "Боруто: Новое поколение Наруто",
    "Bungou Stray Dogs 2nd Season": "Великий из бродячих псов",
    "Captain Tsubasa": "Капитан Цубаса",
    "Cardcaptor Sakura": "Сакура — собирательница карт",
    "Cardfight!! Vanguard": "Кардфайт!! Авангард",
    "Charlotte": "Шарлотта",
    "D.Gray-man": "Ди Грей-мен",
    "Darling in the FranXX": "Милый во Франксе",
    "Detective Conan": "Детектив Конан",
    "Diamond no Ace": "Алмазный Эйс",
    "Dr. Stone: Stone Wars": "Доктор Стоун",
    "Dragon Ball Super": "Драконий жемчуг Супер",
    "Duel Masters": "Дуэльные мастера",
    "Dungeon Meshi": "Трапеза в подземелье",
    "Enen no Shouboutai": "Пламенная бригада пожарных",
    "Eyeshield 21": "Айшилд 21",
    "Free!": "Вольный!",
    "Fruits Basket": "Корзина фруктов",
    "Future Card Buddyfight": "Баддифайт",
    "Gintama": "Гинтама",
    "Gintama'": "Гинтама",
    "Gotoubun no Hanayome": "Пять невест",
    "Guilty Crown": "Корона грешника",
    "Inazuma Eleven": "Одиннадцать молний",
    "Jigokuraku": "Адский рай",
    "Kaguya-sama wa Kokurasetai?: Tensai-tachi no Renai Zunousen": "Кагуя: в любви как на войне",
    "Kaijuu 8-gou 2nd Season": "Кайдзю №8",
    "Kanojo, Okarishimasu": "Девушка на час",
    "Katekyo Hitman Reborn!": "Учитель-киллер Реборн!",
    "Kill la Kill": "Килл ла Килл",
    "Kimetsu no Yaiba: Yuukaku-hen": "Клинок, рассекающий демонов",
    "Komi-san wa, Comyushou desu.": "Коми-сан не умеет общаться",
    "Kono Subarashii Sekai ni Shukufuku wo!": "Этот замечательный мир!",
    "Kuroshitsuji": "Тёмный дворецкий",
    "Kusuriya no Hitorigoto": "Монолог фармацевта",
    "Log Horizon": "Лог Горизонт",
    "Love Live! School Idol Project": "Лов Лайв!",
    "Made in Abyss": "Созданный в Бездне",
    "Mahou Shoujo Madoka★Magica: Hangyaku no Monogatari": "Девочка-волшебница Мадока",
    "Mashle": "Мэшл",
    "Medaka Box": "Ящик Медаки",
    "Mob Psycho 100 II": "Моб Психо 100",
    "Mushoku Tensei III: Isekai Ittara Honki Dasu": "Реинкарнация безработного",
    "Nanatsu no Taizai": "Семь смертных грехов",
    "Nisekoi": "Фальшивая любовь",
    "No Game No Life": "Нет игры — нет жизни",
    "Nurarihyon no Mago": "Внук Нурарихёна",
    "One Punch Man 2nd Season": "Ванпанчмен",
    "Ore dake Level Up na Ken": "Поднятие уровня в одиночку",
    "Ouran Koukou Host Club": "Хост-клуб Оранской школы",
    "Overlord": "Оверлорд",
    "PriPara": "ПриПара",
    "Sakamoto Days": "Дни Сакамото",
    "Shingeki no Kyojin: The Final Season - Kanketsu-hen Kouhen": "Атака титанов",
    "Shokugeki no Souma: Food Wars": "Кулинарные поединки",
    "Shokugeki no Souma: San no Sara - Toutsuki Ressha-hen": "Кулинарные поединки",
    "Sono Bisque Doll wa Koi wo Suru": "Моя девушка — кукла",
    "Sousou no Frieren": "Провожающая в последний путь Фрирен",
    "Spy x Family": "Семья шпиона",
    "Sword Art Online II": "Мастера меча онлайн",
    "Tate no Yuusha no Nariagari": "Восхождение Героя Щита",
    "Tensei shitara Slime Datta Ken": "О моём перерождении в слизь",
    "Tokyo Ghoul:re": "Токийский гуль:re",
    "Toriko": "Торико",
    "Uma Musume: Pretty Derby": "Ума Мусумэ: Прекрасное дерби",
    "Vinland Saga": "Сага о Винланде",
    "Yakusoku no Neverland": "Обещанный Неверленд",
    "Youjo Senki": "Сага о злой Тане",
    "Yowamushi Pedal": "Трусливый велосипедист",
    "Yu☆Gi☆Oh! 5D's": "Ю-Ги-О! 5D's",
    "Zombieland Saga": "Сага о зомби-землях",
}


def dsn() -> str:
    env = pathlib.Path("/etc/greenhouse.env").read_text(encoding="utf-8")
    match = re.search(r"^GREENHOUSE_DSN=(.+)$", env, re.M)
    return match.group(1).strip().strip('"').strip("'") if match else ""


db = open_database(None, dsn())
changed = 0
with db.connect() as conn:
    for old, new in MAPPING.items():
        cursor = conn.execute(
            "UPDATE songless_tracks SET anime = %s, updated_at = now() WHERE anime = %s",
            (new, old))
        if cursor.rowcount:
            changed += cursor.rowcount
            print(f"{old} -> {new} ({cursor.rowcount})")

print("переименовано строк:", changed)
tracks = db.songless_tracks()
latin = sorted({t["anime"] for t in tracks if not re.search(r"[А-Яа-яЁё]", t["anime"])})
print("уникальных названий:", len({t["anime"] for t in tracks}))
print("осталось без кириллицы:", len(latin))
for name in latin:
    print("  ", name)