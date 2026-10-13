# -*- coding: utf-8 -*-
"""Данные для игры «Аниме-сонглесс»: опенинги, по которым угадывают аниме.

Этот файл — исходный набор для первичного заполнения таблицы `songless_tracks`:
сервер проверяет её при запуске и, если она пуста, заливает данные отсюда
(см. backend/seed_songless.py). Дальше источник правды — база.

Здесь **только справочные сведения** — название аниме, название опенинга,
исполнитель и год. Самих записей нет и быть не может: музыка защищена авторским
правом, поэтому аудио добавляет владелец сайта — своими файлами в
`front/games/animesongless/audio/` или ссылками на файлы (см. README и
`backend/seed_songless.py --audio` / `--url`). Пока у трека нет аудио, раунд
на нём не строится.

`clip` — сколько секунд звучит фрагмент, `start` — с какого места записи
начинать (удобно ставить на припев). Значения по умолчанию подходят почти
всем записям, но их можно поправить в базе под свою версию трека.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# Сколько вариантов ответа показывать (один верный и три «обманки»).
OPTION_COUNT = 4

FIELDS = ("anime", "song", "artist", "year", "audio", "clip_start", "clip_length")

DEFAULT_START = 0.0
DEFAULT_CLIP = 8.0

# Аниме, опенинг, исполнитель, год. Одна запись — одно аниме: ответом всегда
# служит название аниме, и варианты ответа не должны повторяться.
ROWS = (
    ("Наруто", "R★O★C★K★S", "Hound Dog", "2002"),
    ("Наруто: Ураганные хроники", "Hero's Come Back!!", "nobodyknows+", "2007"),
    ("Ван-Пис", "We Are!", "Хироси Китадани", "1999"),
    ("Блич", "*~Asterisk~", "Orange Range", "2004"),
    ("Тетрадь смерти", "the WORLD", "Nightmare", "2006"),
    ("Атака титанов", "Guren no Yumiya", "Linked Horizon", "2013"),
    ("Стальной алхимик: Братство", "Again", "Yui", "2009"),
    ("Код Гиас: Восставший Лелуш", "COLORS", "Flow", "2006"),
    ("Токийский гуль", "Unravel", "TK from Ling Tosite Sigure", "2014"),
    ("Паразит: учение о жизни", "Let Me Hear", "Fear, and Loathing in Las Vegas", "2014"),
    ("Охотник × Охотник", "departure!", "Масатоси Оно", "2011"),
    ("Хвост феи", "Snow fairy", "Funkist", "2009"),
    ("Евангелион", "Zankoku na Tenshi no Thesis", "Ёко Такахаси", "1995"),
    ("Мастера меча онлайн", "crossing field", "LiSA", "2012"),
    ("Клинок, рассекающий демонов", "Gurenge", "LiSA", "2019"),
    ("Магическая битва", "Kaikai Kitan", "Eve", "2020"),
    ("Моя геройская академия", "The Day", "Porno Graffitti", "2016"),
    ("Re:Zero. Жизнь с нуля в альтернативном мире", "Redo", "Конами Судзуки", "2016"),
    ("Врата Штейна", "Hacking to the Gate", "Канако Ито", "2011"),
    ("Девочка-волшебница Мадока", "Connect", "ClariS", "2011"),
    ("Ковбой Бибоп", "Tank!", "Seatbelts", "1998"),
    ("Самурай Чамплу", "Battlecry", "Nujabes", "2004"),
    ("Великий из бродячих псов", "Trash Candy", "Granrodeo", "2016"),
    ("Токийские мстители", "Cry Baby", "Official Hige Dandism", "2021"),
    ("Человек-бензопила", "KICK BACK", "Кэнси Ёнэдзу", "2022"),
    ("Ванпанчмен", "THE HERO!!", "JAM Project", "2015"),
    ("Гуррен-Лаганн", "Sorairo Days", "Сёко Накагава", "2007"),
    ("Сейлор Мун", "Moonlight Densetsu", "DALI", "1992"),
    ("Покемон", "Mezase Pokémon Master", "Рика Мацумото", "1997"),
    ("Драконий жемчуг Z", "CHA-LA HEAD-CHA-LA", "Хиронобу Кагеяма", "1989"),
    ("Драконий жемчуг", "Makafushigi Adventure!", "Хироки Такахаси", "1986"),
    ("Слэм-данк", "Kimi ga Suki da to Sakebitai", "BAAD", "1993"),
    ("Сейнт Сейя", "Pegasus Fantasy", "Make-Up", "1986"),
    ("Приключения Диджимонов", "Butter-Fly", "Кодзи Вада", "1999"),
    ("Ю-Ги-О!", "Kawaita Sakebi", "Field of View", "2000"),
    ("Торадора!", "Pre-Parade", "Риэ Кугимия и другие", "2008"),
    ("Кланнад", "Mag Mell", "Eufonius", "2007"),
    ("Меланхолия Харухи Судзумии", "Bouken Desho Desho?", "Ая Хирано", "2006"),
    ("Ангельские ритмы!", "My Soul, Your Beats!", "Lia", "2010"),
    ("Дневник будущего", "Kuusou Mesorogiwi", "Yousei Teikoku", "2011"),
    ("Волчица и пряности", "Tabi no Tochuu", "Нацуми Киёура", "2008"),
    ("Клеймор", "Raison d'être", "Nightmare", "2007"),
    ("Эльфийская песнь", "Lilium", "Кумико Нома", "2004"),
    ("Хеллсинг", "Logos Naki World", "Ясуси Исии", "2001"),
    ("Триган", "H.T.", "Цунэо Имахори", "1998"),
    ("Самурай Икс", "Sobakasu", "Judy and Mary", "1996"),
    ("Нана", "Rose", "Анна Цутия", "2006"),
    ("Хост-клуб Оранской школы", "Sakura Kiss", "Тиэко Кавабэ", "2006"),
    ("Дюрарара!!", "Uragiri no Yuuyake", "Theatre Brook", "2010"),
    ("Судьба/Ноль", "Oath Sign", "LiSA", "2011"),
    ("Некий магический индекс", "PSI-missing", "Мами Кавада", "2008"),
    ("К-он!", "Cagayake! GIRLS", "Сакурако К-ОН", "2009"),
    ("Лаки Стар", "Motteke! Sailor Fuku", "Ая Хирано и другие", "2007"),
    ("Моб Психо 100", "99", "Mob Choir", "2016"),
    ("Доктор Стоун", "Good Morning World!", "Burnout Syndromes", "2019"),
    ("Волейбол!!", "Imagination", "SPYAIR", "2014"),
    ("Баскетбол Куроко", "Can Do", "Granrodeo", "2012"),
    ("Крутой учитель Онидзука", "Driver's High", "L'Arc~en~Ciel", "1999"),
    ("Бездомный бог", "Goya no Machiawase", "Hello Sleepwalkers", "2014"),
    ("Эксперименты Лэйн", "Duvet", "boa", "1998"),
    ("Кагуя: в любви как на войне", "Love Dramatic", "Масаюки Судзуки", "2019"),
    ("Класс убийц", "Seishun Satsubatsuron", "3-nen E-gumi Utatan", "2015"),
    ("Синий экзорцист", "Core Pride", "Uverworld", "2011"),
    ("Берсерк", "Tell Me Why", "Penpals", "1997"),
    ("Кобаяши из дома с драконами", "Aozora no Rhapsody", "fhána", "2017"),
    ("Тебе, любимая", "Kimi ni Todoke", "Томофуми Танидзава", "2009"),
    ("Моногатари", "Staple Stable", "Тива Сайто", "2009"),
    ("Первый шаг", "Under Star", "Shocking Lemon", "2000"),
    ("Kill la Kill", "Sirius", "Eir Aoi", "2013"),
    ("Психопаспорт", "Abnormalize", "Ling Tosite Sigure", "2012"),
    ("Пожиратель душ", "Resonance", "T.M.Revolution", "2008"),
)

TRACKS: List[Dict[str, Any]] = [
    {
        "anime": anime,
        "song": song,
        "artist": artist,
        "year": year,
        "audio": "",
        "clip_start": DEFAULT_START,
        "clip_length": DEFAULT_CLIP,
    }
    for anime, song, artist, year in ROWS
]


def anime_names() -> List[str]:
    """Названия аниме в наборе — из них собираются варианты ответа."""
    return [track["anime"] for track in TRACKS]


def find_track(anime: str) -> Optional[Dict[str, Any]]:
    """Трек по названию аниме: регистр и лишние пробелы не важны."""
    wanted = (anime or "").strip().casefold()
    for track in TRACKS:
        if str(track["anime"]).casefold() == wanted:
            return track
    return None


def public_track(track: Dict[str, Any]) -> Dict[str, Any]:
    """Трек для отправки клиенту после угаданного раунда."""
    return {key: track[key] for key in FIELDS}


def playable(track: Dict[str, Any]) -> bool:
    """Играть можно только трек, у которого есть запись."""
    return bool(str(track.get("audio") or "").strip())


def seed_rows() -> List[Dict[str, Any]]:
    """Строки для первичного заполнения таблицы songless_tracks."""
    return [dict(track) for track in TRACKS]


__all__ = [
    "DEFAULT_CLIP",
    "DEFAULT_START",
    "FIELDS",
    "OPTION_COUNT",
    "ROWS",
    "TRACKS",
    "anime_names",
    "find_track",
    "playable",
    "public_track",
    "seed_rows",
]
