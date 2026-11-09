# -*- coding: utf-8 -*-
"""Собирает составы участников мейджоров из Liquipedia.

Скрипт разработческий: сам он в работу сайта не входит, а обновляет
`backend/csdraft_majors_rosters.py`, который уже импортируется игрой «87-0».

Что делает:

    * читает HTML страниц турниров через API Liquipedia: в нём есть и карточки
      участников с составами, и таблица призовых с занятыми местами;
    * собирает по каждой команде пятёрку игроков и место на турнире;
    * подставляет роли: для игроков из словаря ниже — известные, для
      остальных — по правилу (в модуле такие роли помечены «роль не
      подтверждена»);
    * пишет готовый модуль данных.

Запуск (из корня проекта):

    .\\.venv\\Scripts\\python.exe _fetch_major_rosters.py

Источник данных: Liquipedia (CC-BY-SA 3.0). Ответы кэшируются в служебной
папке, поэтому повторный запуск не дёргает сайт заново.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Dict, List, Optional, Sequence, Tuple

UA = "GreenhouseCraft/1.0 (personal non-commercial project; contact: site owner)"
API = "https://liquipedia.net/counterstrike/api.php"
CACHE_DIR = os.path.join(os.environ.get("TEMP") or os.environ.get("TMP") or ".", "liqcache")
OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "backend", "csdraft_majors_rosters.py")
PAUSE = 15.0  # вежливая пауза между запросами к API

# Страницы турниров: (страница, название для игры, год).
EVENTS: Sequence[Tuple[str, str, int]] = (
    ("DreamHack/2013/Winter", "DreamHack Winter 2013, Jönköping", 2013),
    ("ESL/Major Series One/2014/Katowice", "EMS One Katowice 2014", 2014),
    ("ESL/One/2014/Cologne", "ESL One Cologne 2014", 2014),
    ("DreamHack/2014/Winter", "DreamHack Winter 2014, Jönköping", 2014),
    ("ESL/One/2015/Katowice", "ESL One Katowice 2015", 2015),
    ("ESL/One/2015/Cologne", "ESL One Cologne 2015", 2015),
    ("DreamHack/2015/Cluj-Napoca", "DreamHack Open Cluj-Napoca 2015", 2015),
    ("MLG/2016/Columbus", "MLG Columbus 2016", 2016),
    ("ESL/One/2016/Cologne", "ESL One Cologne 2016", 2016),
    ("ELEAGUE/2017/Major", "ELEAGUE Atlanta 2017", 2017),
    ("PGL/2017/Krakow", "PGL Kraków 2017", 2017),
    ("ELEAGUE/2018/Major", "ELEAGUE Boston 2018", 2018),
    ("FACEIT/2018/Major", "FACEIT London 2018", 2018),
    ("Intel Extreme Masters/Season XIII/World Championship", "IEM Katowice 2019", 2019),
    ("StarLadder/2019/Major", "StarLadder Berlin 2019", 2019),
    ("PGL/2021/Stockholm", "PGL Major Stockholm 2021", 2021),
    ("PGL/2022/Antwerp", "PGL Major Antwerp 2022", 2022),
    ("Intel Extreme Masters/2022/Rio", "IEM Rio 2022", 2022),
    ("BLAST/Major/2023/Paris", "BLAST.tv Paris Major 2023", 2023),
    ("PGL/2024/Copenhagen", "PGL Major Copenhagen 2024", 2024),
    ("Perfect World/Major/2024/Shanghai", "Perfect World Shanghai 2024", 2024),
    ("BLAST/Major/2025/Austin", "BLAST.tv Austin Major 2025", 2025),
    ("StarLadder/2025/Major", "StarLadder Budapest 2025", 2025),
    ("Intel Extreme Masters/2026/Cologne", "IEM Cologne 2026", 2026),
    ("PGL/2026/Singapore", "PGL Major Singapore 2026", 2026),
)

# Место на турнире -> сила состава (та же шкала, что в csdraft_majors).
PLACE_BY_POSITION = ((1, "победитель"), (2, "финалист"), (4, "топ-4"),
                     (8, "топ-8"), (12, "топ-12"), (16, "топ-16"))

# Амплуа, которые раздаются игрокам без известной роли.
ROLE_ORDER = ("awp", "igl", "entry", "support", "lurker")

# Роли известных игроков (ник в нижнем регистре -> роль). Роль — та, в которой
# игрок выступал большую часть карьеры; в конкретном составе она может
# отличаться, поэтому роли всегда считаются ориентиром, а не фактом.
KNOWN_ROLES: Dict[str, str] = {
    "adren": "igl", "ange1": "igl", "apex": "igl", "alex": "igl",
    "amanek": "support", "arch": "awp", "art": "igl", "attacker": "entry",
    "b1ad3": "igl", "bald": "lurker", "bondik": "entry", "bntet": "entry",
    "boros": "lurker", "br0": "support", "buster": "entry", "byali": "lurker",
    "cadian": "igl", "cajunb": "awp", "calyx": "entry", "cerq": "awp",
    "chrisj": "awp", "chopper": "igl", "coldzera": "lurker", "cromen": "support",
    "cypher": "entry", "daps": "igl", "dav1d": "lurker", "dazed": "igl",
    "delpan": "lurker", "denis": "entry", "dennis": "entry", "depi": "support",
    "dev1ce": "awp", "device": "awp", "devilwalk": "support", "donk": "entry",
    "dosia": "lurker", "dpg": "entry", "draken": "awp", "dumau": "entry",
    "dupreeh": "entry", "dycha": "support", "ecl9pse": "lurker",
    "edward": "support", "element": "support", "elige": "lurker", "el1an": "awp",
    "emo": "entry", "ethan": "lurker", "ex6tenz": "igl", "f0rest": "entry",
    "fallen": "awp", "fame": "support", "fashr": "awp", "fetish": "igl",
    "fifflaren": "awp", "fitch": "entry", "fl1t": "support", "flamez": "entry",
    "flamie": "lurker", "flusha": "support", "fns": "igl", "forester": "entry",
    "frozen": "lurker", "gade": "lurker", "getright": "lurker", "gla1ve": "igl",
    "gob b": "igl", "golden": "igl", "grim": "entry", "guardian": "awp",
    "hades": "entry", "hallzerk": "awp", "hally": "lurker", "hampus": "igl",
    "happy": "igl", "hazed": "support", "heavygod": "entry", "hext": "entry",
    "hiko": "lurker", "hobbit": "lurker", "hooxi": "igl", "hunter-": "lurker",
    "hutji": "entry", "im": "entry", "interz": "support", "issaa": "support",
    "jame": "awp", "jdm64": "awp", "jimpphat": "entry", "jkaem": "entry",
    "jks": "lurker", "juanflatroo": "entry", "jw": "awp", "k1to": "entry",
    "karrigan": "igl", "kennys": "awp", "kioshima": "support", "krimz": "support",
    "kuben": "igl", "kucher": "support", "kyxsan": "support", "lacazette": "entry",
    "lekr0": "entry", "liazz": "support", "lucas1": "entry", "magixx": "lurker",
    "malbsmd": "entry", "mantuu": "awp", "markeloff": "awp", "michu": "entry",
    "mir": "entry", "misutaaa": "entry", "moddii": "entry", "mou": "lurker",
    "msl": "igl", "mzinho": "entry", "n0thing": "lurker", "naf": "lurker",
    "nafany": "igl", "naito": "entry", "nbk-": "support", "neo": "lurker",
    "nicoodoz": "awp", "nikolarn": "lurker", "nitr0": "igl", "nqz": "awp",
    "nukkye": "lurker", "olofmeister": "entry", "osee": "awp", "oskar": "awp",
    "ottond": "awp", "oxit": "entry", "pasha": "awp", "pashabiceps": "awp",
    "perfecto": "support", "phzy": "awp", "pimp": "lurker", "pita": "support",
    "plessen": "entry", "plopski": "support", "polly": "entry", "pronax": "igl",
    "ptr": "awp", "qikert": "support", "raalz": "support", "rain": "entry",
    "rallen": "entry", "reatz": "support", "rez": "entry", "rpk": "support",
    "ropz": "lurker", "russ": "entry", "s1mple": "awp", "saffee": "awp",
    "sag": "entry", "schneider": "entry", "scream": "entry", "seized": "lurker",
    "semphis": "igl", "sdy": "entry", "sergej": "entry", "sh1ro": "awp",
    "shahzam": "awp", "shara": "igl", "shox": "lurker", "skadoodle": "awp",
    "skullz": "entry", "smooya": "awp", "snappi": "igl", "snax": "entry",
    "somebody": "support", "spinx": "entry", "spiidi": "entry",
    "stanislaw": "igl", "starix": "igl", "stavn": "entry", "stewie2k": "lurker",
    "styko": "support", "summer": "lurker", "sunny": "entry", "sycrone": "support",
    "taco": "support", "tarik": "igl", "taz": "support", "tecn9": "lurker",
    "thomas": "lurker", "timber": "entry", "tizian": "entry", "tony": "entry",
    "torzsi": "awp", "toxic": "entry", "tropical": "support", "twist": "awp",
    "twistzz": "lurker", "tysen": "entry", "valde": "lurker", "vini": "support",
    "w0nderful": "awp", "wardell": "awp", "waterfallz": "entry",
    "waylander": "entry", "winter": "entry", "woxic": "awp", "xantares": "entry",
    "xelos": "support", "xizt": "igl", "xotic": "entry", "xsepower": "awp",
    "xseven": "entry", "xyp9x": "support", "yekindar": "entry", "ytb": "entry",
    "zacharee": "entry", "zews": "support", "zont1x": "lurker", "zorte": "awp",
    "zywoo": "awp", "3k2": "lurker", "9pasha": "entry",
}

# Регион команды (название в нижнем регистре -> регион). Нужен игре для бонуса
# за «своих»: у команд одного региона он срабатывает.
TEAM_REGIONS: Dict[str, str] = {
    "astralis": "EU", "fnatic": "EU", "natus vincere": "EEU", "navi": "EEU",
    "ninjas in pyjamas": "EU", "faze clan": "EU", "g2 esports": "EU",
    "team vitality": "EU", "mouz": "EU", "mousesports": "EU", "north": "EU",
    "heroic": "EU", "og": "EU", "team spirit": "EEU", "virtus.pro": "EEU",
    "gambit esports": "EEU", "vici gaming": "CN", "tyloo": "CN",
    "rare atom": "CN", "lynn vision": "CN", "the mongolz": "APAC",
    "cloud9": "NA", "complexity": "NA", "complexity gaming": "NA",
    "team liquid": "NA", "nrg": "NA", "evil geniuses": "NA", "eg": "NA",
    "100 thieves": "NA", "immortals": "SA", "mibr": "SA", "sk gaming": "SA",
    "pain gaming": "SA", "furia": "SA", "imperial": "SA", "nouns": "NA",
    "wildcard": "NA", "m80": "NA", "big": "EU", "sprout": "EU",
    "godsent": "EU", "copenhagen flames": "EU", "renaissance": "APAC",
    "abyssal": "APAC", "k23": "APAC", "avangar": "EEU", "forze": "EEU",
    "nemiga": "EEU", "winstrike": "EEU", "vega squadron": "EEU",
    "eternal fire": "EEU", "team one": "NA", "singularity": "NA",
    "anonymo": "EU", "sangal": "EU", "endpoint": "EU", "movistar riders": "EU",
    "giants": "EU", "mad lions": "EU", "saw": "EU", "splyce": "EU",
    "hellraisers": "EEU", "quantum bellator": "EEU", "ence": "EU",
    "havu": "EU", "team dignitas": "EU", "dignitas": "EU", "optic gaming": "NA",
    "luminosity": "SA", "tempo storm": "SA", "red reserve": "EU",
    "misfits": "NA", "flipsid3 tactics": "EEU", "counter logic gaming": "NA",
    "selfless": "NA", "elevate": "APAC", "sharks": "SA", "9z team": "SA",
    "keyd stars": "SA", "team secret": "EU", "bleed": "APAC",
    "team falcons": "APAC", "aurora": "EEU", "mouz nxt": "EU",
    "falcons": "APAC", "virtus pro": "EEU", "sk gaming 2": "SA",
    "team liquid brazil": "SA", "nrg esports": "NA", "big clan": "EU",
}

# Названия из таблицы призовых, которые не совпадают с составами напрямую:
# ник/название в составе (norm) -> название в таблице (norm).
TEAM_ALIASES: Dict[str, str] = {}


def norm(text: str) -> str:
    """Ключ для сопоставления названий команд."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def cache_path(page: str, kind: str) -> str:
    digest = hashlib.sha1(f"{kind}|{page}".encode("utf-8")).hexdigest()[:16]
    return os.path.join(CACHE_DIR, f"{kind}-{digest}.txt")


def fetch(page: str, prop: str) -> str:
    """Забирает страницу турнира через API (с кэшем на диске)."""
    path = cache_path(page, prop)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    query = urllib.parse.urlencode({"action": "parse", "page": page,
                                    "format": "json", "prop": prop})
    request = urllib.request.Request(f"{API}?{query}", headers={
        "User-Agent": UA, "Accept": "application/json", "Accept-Encoding": "gzip"})
    payload = b""
    for attempt in range(8):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                payload = response.read()
                if response.headers.get("Content-Encoding") == "gzip":
                    payload = gzip.decompress(payload)
            break
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == 7:
                raise
            wait = 60 * (attempt + 1)
            print(f"лимит запросов, пауза {wait} с", flush=True)
            time.sleep(wait)
    text = json.loads(payload.decode("utf-8"))["parse"][prop]["*"]
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    time.sleep(PAUSE)
    return text





def parse_participants(html: str) -> "List[Tuple[str, List[str]]]":
    """Составы из карточек участников в HTML: [(команда, [игроки]), ...].

    В карточке название команды повторяется несколько раз, затем идут игроки,
    а ниже — запасные и тренер, поэтому берётся первая пятёрка чужих ссылок.
    """
    found: "Dict[str, Tuple[str, List[str]]]" = {}
    order: List[str] = []
    marker = 'class="team-participant-card&#95;&#95;header"'
    for chunk in participants_html(html).split(marker)[1:]:
        links = re.findall(r'href="/counterstrike/([^"/]+)"\s+title="([^"]+)"', chunk)
        titles = [re.sub(r"\s*\([^)]*\)$", "", title) for _, title in links]
        if len(titles) < 6:
            continue
        team = titles[0]
        players: List[str] = []
        for title in titles:
            if title != team and title not in players:
                players.append(title)
            if len(players) == 5:
                break
        if len(players) < 5:
            continue
        key = norm(team)
        if key not in found:
            order.append(key)
        found[key] = (team, players)
    return [(found[key][0], found[key][1]) for key in order]


def participants_html(html: str) -> str:
    """Вырезает раздел участников из HTML страницы."""
    marker = re.search(r'id="Participants"', html)
    if not marker:
        return ""
    rest = html[marker.end():]
    stop = re.search(r"<h2[\s>]", rest)
    return rest[:stop.start()] if stop else rest


# Слова, по которым видно, что в карточке не команда, а заглушка слота.
PLACEHOLDER_WORDS = ("slot", "tbd", "tba", "placeholder", "winner of", "qualified for")


def is_placeholder(team: str) -> bool:
    lowered = team.lower()
    return any(word in lowered for word in PLACEHOLDER_WORDS)


def match_place(team: str, places: "Dict[str, str]") -> str:
    """Место команды из таблицы призовых.

    Названия в составах и в таблице иногда расходятся, поэтому после точного
    совпадения проверяются известные синонимы, а затем — вхождение названия,
    но только если такое совпадение единственное.
    """
    key = norm(team)
    if key in places:
        return places[key]
    alias = TEAM_ALIASES.get(key)
    if alias and alias in places:
        return places[alias]
    if len(key) >= 5:
        near = [value for name, value in places.items()
                if len(name) >= 5 and (name in key or key in name)]
        if len(set(near)) == 1:
            return near[0]
    return ""


def place_for(position: str) -> str:
    try:
        number = int(re.split(r"[^0-9]", position.strip())[0])
    except (ValueError, IndexError):
        return "группа"
    for limit, name in PLACE_BY_POSITION:
        if number <= limit:
            return name
    return "группа"


class PrizeTableParser(HTMLParser):
    """Разбирает таблицу призовых: место -> команды этого места.

    Проходим только по строкам самой таблицы: у команды место берётся из
    ячейки с местом, а строкам с общей ячейкой (3-4, 5-8 и так далее) место
    достаётся по наследству — как оно и задумано в разметке.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.in_table = False
        self.cell = ""
        self.text: List[str] = []
        self.links: List[str] = []
        self.place = ""
        self.places: "Dict[str, str]" = {}

    def handle_starttag(self, tag: str, attrs) -> None:
        attributes = {name: value or "" for name, value in attrs}
        if tag == "table":
            self.depth += 1
            if "prizepooltable" in attributes.get("class", ""):
                self.in_table = True
        elif not self.in_table or self.depth != 1:
            return
        elif tag == "td":
            self.cell = attributes.get("class", "")
            self.text, self.links = [], []
        elif tag == "a" and self.cell:
            href = attributes.get("href", "")
            title = attributes.get("title", "")
            if title and href.startswith("/counterstrike/") and href.count("/") == 2:
                self.links.append(title)

    def handle_data(self, data: str) -> None:
        if self.in_table and self.cell:
            self.text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "table":
            self.depth -= 1
            if self.depth == 0:
                self.in_table = False
            return
        if not self.in_table or not self.cell:
            return
        if tag == "td":
            if "prizepooltable-place" in self.cell:
                place = "".join(self.text).strip()
                if place:
                    self.place = place_for(place)
            elif "prizepooltable-col-team" in self.cell and self.place:
                for title in self.links:
                    self.places[norm(title)] = self.place
            self.cell = ""


def parse_places(html: str) -> "Dict[str, str]":
    """Места из таблицы призовых: {название команды (norm): место}."""
    parser = PrizeTableParser()
    parser.feed(html)
    return parser.places


def assign_roles(players: Sequence[str]) -> "List[Tuple[str, bool]]":
    """Роли всей пятёрки.

    Известные роли остаются как есть, а подставленные раздаются по свободным
    амплуа — чтобы в одном составе не вышло, например, двух капитанов.
    """
    roles: "List[Tuple[str, bool]]" = []
    used = set()
    for nick in players:
        known = KNOWN_ROLES.get(nick.lower()) or KNOWN_ROLES.get(norm(nick))
        if known:
            used.add(known)
        roles.append((known, True) if known else ("", False))
    free = [role for role in ROLE_ORDER if role not in used]
    for index, (role, known) in enumerate(roles):
        if known:
            continue
        roles[index] = (free.pop(0) if free else ROLE_ORDER[index % len(ROLE_ORDER)], False)
    return roles


def region_for(team: str) -> str:
    return TEAM_REGIONS.get(team.lower()) or TEAM_REGIONS.get(norm(team)) or "EU"


def build() -> Tuple[List[Dict[str, object]], List[str]]:
    events: List[Dict[str, object]] = []
    warnings: List[str] = []
    failures = 0
    for page, title, year in EVENTS:
        try:
            html = fetch(page, "text")
        except Exception as error:  # сеть: лимит запросов, обрыв соединения
            failures += 1
            warnings.append(f"{title}: страница не получена ({error}) — пропуск")
            if failures >= 1:
                warnings.append("остановились: Liquipedia ограничивает запросы. "
                                "Повторите запуск позже: скачанное берётся из кэша")
                break
            continue
        failures = 0
        teams = parse_participants(html)
        if not teams:
            warnings.append(f"{title}: раздел участников не найден — пропуск")
            continue
        places = parse_places(html)
        if not places:
            warnings.append(f"{title}: нет таблицы призовых (турнир не сыгран?) — пропуск")
            continue
        prepared = []
        for team, players in teams:
            if is_placeholder(team):
                warnings.append(f"{title}: пропущена заглушка слота «{team}»")
                continue
            place = match_place(team, places)
            if not place:
                place = "группа"
                warnings.append(f"{title}: {team} — место не найдено, поставлена группа")
            roles = assign_roles(players)
            prepared.append((team, region_for(team), place, players, roles))
        prepared.sort(key=lambda item: item[2])
        events.append({"event": title, "year": year,
                       "era": "legacy" if year <= 2019 else "modern",
                       "teams": prepared})
        guessed = sum(1 for item in prepared for _, known in item[4] if not known)
        print(f"{title}: команд {len(prepared)}, ролей подставлено {guessed}")
    return events, warnings


def render(events: List[Dict[str, object]]) -> str:
    def quoted(value: str) -> str:
        return json.dumps(value, ensure_ascii=False)

    lines: List[str] = [
        "# -*- coding: utf-8 -*-",
        '"""Полные составы участников мейджоров 2013–2026 (сгенерировано).',
        "",
        "Файл создан скриптом `_fetch_major_rosters.py` из данных Liquipedia",
        "(CC-BY-SA 3.0) и править его вручную не нужно: правки затрутся при",
        "следующей сборке. Роли игроков в Liquipedia не публикуются: известные",
        "роли взяты из словаря в скрипте, остальные подставлены по правилу и",
        "помечены комментарием «роль не подтверждена».",
        '"""',
        "from __future__ import annotations",
        "",
        "from typing import Any, Dict, Tuple",
        "",
        "# Мейджоры: (событие, год, эпоха, команды). Команда: (название, регион,",
        "# место, игроки). Игрок: (ник, роль).",
        "EVENTS: Tuple[Dict[str, Any], ...] = (",
    ]
    for event in events:
        lines.append("    {")
        lines.append(f'        "event": {quoted(str(event["event"]))},')
        lines.append(f'        "year": {event["year"]},')
        lines.append(f'        "era": {quoted(str(event["era"]))},')
        lines.append('        "teams": (')
        for team, region, place, players, roles in event["teams"]:  # type: ignore[misc]
            lines.append(f"            ({quoted(team)}, {quoted(region)}, {quoted(place)}, (")
            for nick, (role, known) in zip(players, roles):  # type: ignore[misc]
                note = "" if known else "  # роль не подтверждена"
                lines.append(f"                ({quoted(nick)}, {quoted(role)}),{note}")
            lines.append("            )),")
        lines.append("        ),")
        lines.append("    },")
    lines.append(")")
    lines.append("")
    lines.append('__all__ = ["EVENTS"]')
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    events, warnings = build()
    if not events:
        print("нечего сохранять")
        return 1
    with open(OUT_PATH, "w", encoding="utf-8") as handle:
        handle.write(render(events))
    total = sum(len(event["teams"]) for event in events)
    print(f"\nсобытий: {len(events)} из {len(EVENTS)}, паков: {total}, файл: {OUT_PATH}")
    if warnings:
        print("\nна заметку:")
        for line in warnings:
            print(" -", line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
