# -*- coding: utf-8 -*-
"""Данные для дуэли «Narutodle»: персонажи, графы сравнения и цвета аватаров.

Этот файл — исходный набор для первичного заполнения базы: при запуске сервер
проверяет таблицу `narutodle_characters` и, если она пуста, заливает данные
отсюда (см. backend/seed_narutodle.py). Дальше источник правды — база:
персонажей можно править и добавлять прямо в ней, а изображения — привязывать
к строкам.

Таблица персонажей читается сверху вниз по FIELDS; неизвестные или спорные
значения помечаются UNKNOWN и по этой графе догадка считается несовпавшей
(кроме случая, когда неизвестно у обоих). Тексты не переписывались ни из каких
источников — это короткие справочные значения: деревня, клан, стихии и так далее.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

UNKNOWN = "неизвестно"

# Графы сравнения: подпись показывается в шапке таблицы попыток.
ATTRIBUTES: List[Dict[str, Any]] = [
    {"key": "gender", "label": "Пол"},
    {"key": "village", "label": "Деревня"},
    {"key": "clan", "label": "Клан"},
    {"key": "nature", "label": "Стихии", "multi": True},
    {"key": "kekkei", "label": "Кеккей генкай"},
    {"key": "jinchuriki", "label": "Джинчурики"},
    {"key": "debut", "label": "Первая арка"},
]

MALE = "мужской"
FEMALE = "женский"

KONOHA = "Коноха"
SUNA = "Суна"
KIRI = "Кири"
KUMO = "Кумо"
IWA = "Ива"
OTO = "Ото"
AME = "Аме"
TAKI = "Таки"
KUSA = "Куса"
UZUSHIO = "Узушио"
NO_VILLAGE = "нет деревни"
YU = "Ю"
IRON = "Страна Железа"

# Арки сюжета по порядку. «Первая арка» — это место персонажа в истории, а не
# серия («Классика»/«Шиппуден»): границы взяты по манге — Naruto главы 1–699 и
# Boruto: Naruto Next Generations. Список задаёт порядок для подсказки «раньше
# или позже»: арки вне него подсказку не дают.
WAVES = "Страна Волн"
CHUNIN = "Экзамен на чунина"
KONOHA_CRUSH = "Вторжение в Коноху"
TSUNADE = "Поиск Цунаде"
RETRIEVAL = "Погоня за Саске"
KAZEKAGE = "Спасение Гаары"
REUNION = "Воссоединение с Саске"
AKATSUKI = "Хидан и Какудзу"
ITACHI = "Погоня за Итачи"
# Рассказ Джирайи о Нагато и Яхико идёт в начале арки Пейна, а бой братьев
# Учиха (Саске против Итачи) — сразу после него, до нападения Пейна на Коноху.
JIRAIYA = "История о Джирайе"
BROTHERS = "Битва братьев"
PAIN = "Вторжение Пейна"
KAGE = "Совет пяти Каге"
WAR = "Четвёртая мировая война"
KAGUYA = "Финал: Кагуя"
BORUTO = "Боруто"

ARCS: List[str] = [
    WAVES, CHUNIN, KONOHA_CRUSH, TSUNADE, RETRIEVAL, KAZEKAGE, REUNION,
    AKATSUKI, ITACHI, JIRAIYA, BROTHERS, PAIN, KAGE, WAR, KAGUYA, BORUTO,
]

NO_CLAN = "нет клана"
NO_KEKKEI = "нет"
NO_BEAST = "нет"

# Цвет аватара — по родной деревне. Аватар рисует страница игры: инициалы
# на цветном квадрате; свою картинку можно подставить в поле image.
VILLAGE_COLORS: Dict[str, str] = {
    KONOHA: "#3f7d3a",
    SUNA: "#c2912c",
    KIRI: "#2f7fa8",
    KUMO: "#b0661f",
    IWA: "#6b6f74",
    OTO: "#7a4b9a",
    AME: "#4b6b8a",
    TAKI: "#2f8f7a",
    KUSA: "#6f8f2f",
    UZUSHIO: "#b8455f",
    NO_VILLAGE: "#6d5a8f",
    YU: "#7a6a5f",
    IRON: "#5c6b7a",
    UNKNOWN: "#7a6a5f",
}
DEFAULT_COLOR = "#8a5a3c"

FIELDS = ("name", "gender", "village", "clan", "nature", "kekkei",
          "jinchuriki", "debut")

# Портрет персонажа отдаётся отдельным адресом: в каталоге — только ссылка.
PORTRAIT_PATH = "/api/games/narutodle/portrait/%s"

# name, gender, village, clan, nature, kekkei, jinchuriki, debut (арка)
ROWS: List[tuple] = [
    # Набор из выгрузки narutochars_fixed.csv (148 персонажей, id по
    # возрастанию). Кеккей генкай Наруто оставлен прежним — «нет».
    ("Наруто Узумаки", MALE, KONOHA, "Узумаки", ["Ветер", "Молния", "Земля", "Вода", "Огонь"], NO_KEKKEI, "Девятихвостый", WAVES),
    ("Саске Учиха", MALE, KONOHA, "Учиха", ["Огонь", "Молния", "Ветер", "Земля", "Вода"], "Шаринган, Риннеган", NO_BEAST, WAVES),
    ("Сакура Харуно", FEMALE, KONOHA, NO_CLAN, ["Земля", "Вода"], NO_KEKKEI, NO_BEAST, WAVES),
    ("Какаши Хатаке", MALE, KONOHA, NO_CLAN, ["Молния", "Земля", "Вода", "Огонь"], "Шаринган", NO_BEAST, WAVES),
    ("Ямато", MALE, KONOHA, NO_CLAN, ["Земля", "Вода"], "Деревянный выпуск", NO_BEAST, REUNION),
    ("Сай", MALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KAZEKAGE),
    ("Кабуто Якуши", MALE, KONOHA, NO_CLAN, ["Земля", "Вода", "Ветер", "Огонь", "Молния"], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Хината Хьюга", FEMALE, KONOHA, "Хьюга", ["Огонь", "Молния"], "Бьякуган", NO_BEAST, WAVES),
    ("Неджи Хьюга", MALE, KONOHA, "Хьюга", ["Огонь", "Земля", "Вода"], "Бьякуган", NO_BEAST, CHUNIN),
    ("Ханаби Хьюга", FEMALE, KONOHA, "Хьюга", [UNKNOWN], "Бьякуган", NO_BEAST, CHUNIN),
    ("Хиаши Хьюга", MALE, KONOHA, "Хьюга", [UNKNOWN], "Бьякуган", NO_BEAST, CHUNIN),
    ("Рок Ли", MALE, KONOHA, NO_CLAN, ["нет"], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Тентен", FEMALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Майто Гай", MALE, KONOHA, NO_CLAN, ["Огонь", "Молния"], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Шикамару Нара", MALE, KONOHA, "Нара", ["Огонь", "Земля"], NO_KEKKEI, NO_BEAST, WAVES),
    ("Чоджи Акимичи", MALE, KONOHA, "Акимичи", ["Огонь", "Земля"], NO_KEKKEI, NO_BEAST, WAVES),
    ("Ино Яманака", FEMALE, KONOHA, "Яманака", ["Земля", "Вода"], NO_KEKKEI, NO_BEAST, WAVES),
    ("Киба Инузука", MALE, KONOHA, "Инузука", [UNKNOWN], NO_KEKKEI, NO_BEAST, WAVES),
    ("Шино Абураме", MALE, KONOHA, "Абураме", [UNKNOWN], NO_KEKKEI, NO_BEAST, WAVES),
    ("Шикаку Нара", MALE, KONOHA, "Нара", [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Чоза Акимичи", MALE, KONOHA, "Акимичи", [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Иноичи Яманака", MALE, KONOHA, "Яманака", [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Цуме Инузука", FEMALE, KONOHA, "Инузука", [UNKNOWN], NO_KEKKEI, NO_BEAST, KONOHA_CRUSH),
    ("Шиби Абураме", MALE, KONOHA, "Абураме", [UNKNOWN], NO_KEKKEI, NO_BEAST, KONOHA_CRUSH),
    ("Хирузен Сарутоби", MALE, KONOHA, "Сарутоби", ["Огонь", "Ветер", "Молния", "Земля", "Вода"], NO_KEKKEI, NO_BEAST, WAVES),
    ("Асума Сарутоби", MALE, KONOHA, "Сарутоби", ["Ветер", "Огонь"], NO_KEKKEI, NO_BEAST, WAVES),
    ("Конохамару Сарутоби", MALE, KONOHA, "Сарутоби", ["Огонь", "Ветер"], NO_KEKKEI, NO_BEAST, WAVES),
    ("Куренай Юхи", FEMALE, KONOHA, NO_CLAN, ["Огонь"], NO_KEKKEI, NO_BEAST, WAVES),
    ("Шизуне", FEMALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, TSUNADE),
    ("Анко Митараши", FEMALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Ирука Умино", MALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, WAVES),
    ("Джирайя", MALE, KONOHA, NO_CLAN, ["Огонь", "Земля", "Вода", "Ветер"], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Цунаде", FEMALE, KONOHA, "Сенджу", ["Молния", "Земля", "Вода", "Огонь"], NO_KEKKEI, NO_BEAST, TSUNADE),
    ("Орочимару", MALE, KONOHA, NO_CLAN, ["Огонь", "Ветер", "Молния", "Земля", "Вода"], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Минато Намиказе", MALE, KONOHA, NO_CLAN, ["Огонь", "Ветер", "Молния"], NO_KEKKEI, "Девятихвостый (половина Инь)", WAVES),
    ("Сакумо Хатаке", MALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, PAIN),
    ("Хаяте Гекко", MALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Дан Като", MALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, TSUNADE),
    ("Рин Нохара", FEMALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, "Трёххвостый", ITACHI),
    ("Данзо Шимура", MALE, KONOHA, NO_CLAN, ["Ветер", "Огонь", "Земля", "Вода"], "Шаринган, Деревянный выпуск", NO_BEAST, KAZEKAGE),
    ("Хаширама Сенджу", MALE, KONOHA, "Сенджу", ["Земля", "Вода", "Огонь"], "Деревянный выпуск", NO_BEAST, KONOHA_CRUSH),
    ("Тобирама Сенджу", MALE, KONOHA, "Сенджу", ["Вода", "Земля", "Огонь", "Молния"], NO_KEKKEI, NO_BEAST, KONOHA_CRUSH),
    ("Итачи Учиха", MALE, KONOHA, "Учиха", ["Огонь", "Вода", "Ветер"], "Шаринган", NO_BEAST, KONOHA_CRUSH),
    ("Мадара Учиха", MALE, KONOHA, "Учиха", ["Огонь", "Ветер", "Молния", "Земля", "Вода"], "Шаринган, Риннеган, Деревянный выпуск", NO_BEAST, "История о Джирайе"),
    ("Изуна Учиха", MALE, KONOHA, "Учиха", ["Огонь"], "Шаринган", NO_BEAST, "Битва братьев"),
    ("Обито Учиха", MALE, KONOHA, "Учиха", ["Огонь"], "Шаринган, Риннеган, Деревянный выпуск", NO_BEAST, KAZEKAGE),
    ("Шисуи Учиха", MALE, KONOHA, "Учиха", ["Огонь"], "Шаринган", NO_BEAST, KAGE),
    ("Фугаку Учиха", MALE, KONOHA, "Учиха", ["Огонь"], "Шаринган", NO_BEAST, TSUNADE),
    ("Микото Учиха", FEMALE, KONOHA, "Учиха", [UNKNOWN], "Шаринган", NO_BEAST, TSUNADE),
    ("Кушина Узумаки", FEMALE, UZUSHIO, "Узумаки", [UNKNOWN], NO_KEKKEI, "Девятихвостый", "История о Джирайе"),
    ("Мито Узумаки", FEMALE, UZUSHIO, "Узумаки", [UNKNOWN], NO_KEKKEI, "Девятихвостый", WAR),
    ("Гаара", MALE, SUNA, NO_CLAN, ["Земля", "Ветер", "Молния"], "Магнитный выпуск", "Однохвостый", CHUNIN),
    ("Темари", FEMALE, SUNA, NO_CLAN, ["Ветер"], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Канкуро", MALE, SUNA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Баки", MALE, SUNA, NO_CLAN, ["Ветер"], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Раса", MALE, SUNA, NO_CLAN, ["Ветер", "Земля"], "Магнитный выпуск", NO_BEAST, CHUNIN),
    ("Карура", FEMALE, SUNA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, WAR),
    ("Чиё", FEMALE, SUNA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KAZEKAGE),
    ("Сасори", MALE, SUNA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KAZEKAGE),
    ("Забуза Момочи", MALE, KIRI, NO_CLAN, ["Вода"], NO_KEKKEI, NO_BEAST, WAVES),
    ("Хаку", MALE, KIRI, NO_CLAN, ["Вода", "Ветер"], "Ледяной выпуск", NO_BEAST, WAVES),
    ("Кисаме Хошигаки", MALE, KIRI, NO_CLAN, ["Вода"], NO_KEKKEI, NO_BEAST, KONOHA_CRUSH),
    ("Кимимаро Кагуя", MALE, OTO, "Кагуя", [UNKNOWN], "Шикоцумьяку", NO_BEAST, RETRIEVAL),
    ("Мэй Тэруми", FEMALE, KIRI, NO_CLAN, ["Вода", "Огонь", "Земля"], "Кипящий выпуск, Лавовый выпуск", NO_BEAST, KAGE),
    ("Ао", MALE, KIRI, NO_CLAN, ["Вода"], "Бьякуган", NO_BEAST, KAGE),
    ("Чоджуро", MALE, KIRI, NO_CLAN, ["Вода"], NO_KEKKEI, NO_BEAST, KAGE),
    ("Суйгецу Хозуки", MALE, KIRI, "Хозуки", ["Вода"], NO_KEKKEI, NO_BEAST, ITACHI),
    ("Мангецу Хозуки", MALE, KIRI, "Хозуки", ["Вода"], NO_KEKKEI, NO_BEAST, WAR),
    ("Ягура Каратачи", MALE, KIRI, NO_CLAN, [UNKNOWN], NO_KEKKEI, "Трёххвостый", KAGE),
    ("Утаката", MALE, KIRI, NO_CLAN, [UNKNOWN], NO_KEKKEI, "Шестихвостый", WAR),
    ("Киллер Би", MALE, KUMO, NO_CLAN, ["Молния"], NO_KEKKEI, "Восьмихвостый", "Битва братьев"),
    ("Эй (Четвёртый Райкаге)", MALE, KUMO, NO_CLAN, ["Молния"], NO_KEKKEI, NO_BEAST, PAIN),
    ("Югито Нии", FEMALE, KUMO, NO_CLAN, [UNKNOWN], NO_KEKKEI, "Двухвостый", AKATSUKI),
    ("Мабуи", FEMALE, KUMO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, PAIN),
    ("Омои", MALE, KUMO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, PAIN),
    ("Каруи", FEMALE, KUMO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, PAIN),
    ("Дейдара", MALE, IWA, NO_CLAN, ["Земля"], "Взрывной выпуск", NO_BEAST, KAZEKAGE),
    ("Ооноки", MALE, IWA, NO_CLAN, ["Земля", "Огонь", "Ветер"], "Пылевой выпуск", NO_BEAST, KAGE),
    ("Куроцучи", FEMALE, IWA, NO_CLAN, ["Земля", "Огонь", "Вода"], "Лавовый выпуск", NO_BEAST, KAGE),
    ("Роши", MALE, IWA, NO_CLAN, ["Земля", "Огонь"], "Лавовый выпуск", "Четырёххвостый", ITACHI),
    ("Хан", MALE, IWA, NO_CLAN, [UNKNOWN], NO_KEKKEI, "Пятихвостый", KAGE),
    ("Таюя", FEMALE, OTO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KONOHA_CRUSH),
    ("Джуго", MALE, OTO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, ITACHI),
    ("Карин", FEMALE, KUSA, "Узумаки", [UNKNOWN], NO_KEKKEI, NO_BEAST, ITACHI),
    ("Кидомару", MALE, OTO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KONOHA_CRUSH),
    ("Сакон", MALE, OTO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KONOHA_CRUSH),
    ("Джиробо", MALE, OTO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KONOHA_CRUSH),
    ("Заку Абуми", MALE, OTO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Досу Кинута", MALE, OTO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Нагато", MALE, AME, "Узумаки", ["Огонь", "Ветер", "Молния", "Земля", "Вода"], "Риннеган", NO_BEAST, "История о Джирайе"),
    ("Конан", FEMALE, AME, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, ITACHI),
    ("Яхико", MALE, AME, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, "История о Джирайе"),
    ("Какузу", MALE, TAKI, NO_CLAN, ["Земля", "Огонь", "Ветер", "Молния", "Вода"], NO_KEKKEI, NO_BEAST, AKATSUKI),
    ("Фу", FEMALE, TAKI, NO_CLAN, [UNKNOWN], NO_KEKKEI, "Семихвостый", KAGE),
    ("Хидан", MALE, YU, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, AKATSUKI),
    ("Зецу", MALE, NO_VILLAGE, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, RETRIEVAL),
    ("Кагуя Ооцуцуки", FEMALE, NO_VILLAGE, "Ооцуцуки", ["Огонь", "Ветер", "Молния", "Земля", "Вода"], "Бьякуган, Риннешаринган", "Десятихвостый", KAGUYA),
    ("Хагоромо Ооцуцуки", MALE, NO_VILLAGE, "Ооцуцуки", ["Огонь", "Ветер", "Молния", "Земля", "Вода"], "Риннеган", "Десятихвостый", WAR),
    ("Хамура Ооцуцуки", MALE, NO_VILLAGE, "Ооцуцуки", [UNKNOWN], "Бьякуган", NO_BEAST, WAR),
    ("Момошики Ооцуцуки", MALE, NO_VILLAGE, "Ооцуцуки", [UNKNOWN], "Бьякуган, Риннеган", NO_BEAST, BORUTO),
    ("Урашики Ооцуцуки", MALE, NO_VILLAGE, "Ооцуцуки", [UNKNOWN], "Бьякуган, Риннеган", NO_BEAST, BORUTO),
    ("Иссики Ооцуцуки", MALE, NO_VILLAGE, "Ооцуцуки", [UNKNOWN], NO_KEKKEI, NO_BEAST, BORUTO),
    ("Каваки", MALE, NO_VILLAGE, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, BORUTO),
    ("Боруто Узумаки", MALE, KONOHA, "Узумаки", ["Ветер", "Молния", "Вода"], NO_KEKKEI, NO_BEAST, BORUTO),
    ("Сарада Учиха", FEMALE, KONOHA, "Учиха", ["Огонь", "Молния"], "Шаринган", NO_BEAST, BORUTO),
    ("Мицуки", MALE, KONOHA, NO_CLAN, ["Ветер", "Молния"], NO_KEKKEI, NO_BEAST, BORUTO),
    ("Химавари Узумаки", FEMALE, KONOHA, "Узумаки", [UNKNOWN], "Бьякуган", "Девятихвостый", BORUTO),
    ("Чочо Акимичи", FEMALE, KONOHA, "Акимичи", [UNKNOWN], NO_KEKKEI, NO_BEAST, BORUTO),
    ("Шикадай Нара", MALE, KONOHA, "Нара", [UNKNOWN], NO_KEKKEI, NO_BEAST, BORUTO),
    ("Даруи", MALE, KUMO, NO_CLAN, ["Молния", "Вода", "Ветер"], "Штормовой выпуск", NO_BEAST, KAGE),
    ("Ши", MALE, KUMO, NO_CLAN, ["Молния"], NO_KEKKEI, NO_BEAST, KAGE),
    ("Самуи", FEMALE, KUMO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, PAIN),
    ("Эй (Третий Райкаге)", MALE, KUMO, NO_CLAN, ["Молния", "Огонь", "Земля"], NO_KEKKEI, NO_BEAST, WAR),
    ("Кинкаку", MALE, KUMO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, WAR),
    ("Гинкаку", MALE, KUMO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, WAR),
    ("Му", MALE, IWA, NO_CLAN, ["Огонь", "Земля", "Вода", "Ветер", "Молния"], "Пылевой выпуск", NO_BEAST, WAR),
    ("Ишикава", MALE, IWA, NO_CLAN, ["Земля"], NO_KEKKEI, NO_BEAST, WAR),
    ("Акацучи", MALE, IWA, NO_CLAN, ["Земля"], NO_KEKKEI, NO_BEAST, KAGE),
    ("Генгецу Хозуки", MALE, KIRI, "Хозуки", ["Огонь", "Земля", "Вода", "Молния"], NO_KEKKEI, NO_BEAST, WAR),
    ("Бьякурен", MALE, KIRI, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, WAR),
    ("Рето", MALE, SUNA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, WAR),
    ("Шамон", MALE, SUNA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, WAR),
    ("Пакура", FEMALE, SUNA, NO_CLAN, ["Огонь", "Ветер"], "Выпуск Жара", NO_BEAST, WAR),
    ("Яшамару", MALE, SUNA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Ханзо", MALE, AME, NO_CLAN, ["Огонь"], NO_KEKKEI, NO_BEAST, "История о Джирайе"),
    ("Мифуне", MALE, IRON, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, KAGE),
    ("Ибики Морино", MALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Хизаши Хьюга", MALE, KONOHA, "Хьюга", [UNKNOWN], "Бьякуган", NO_BEAST, CHUNIN),
    ("Мизуки", MALE, KONOHA, NO_CLAN, ["Земля"], NO_KEKKEI, NO_BEAST, WAVES),
    ("Кин Цучи", FEMALE, OTO, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Индра Ооцуцуки", MALE, NO_VILLAGE, "Ооцуцуки", ["Огонь", "Молния"], "Шаринган", NO_BEAST, KAGE),
    ("Ашура Ооцуцуки", MALE, NO_VILLAGE, "Ооцуцуки", ["Огонь", "Земля", "Вода", "Ветер", "Молния"], NO_KEKKEI, NO_BEAST, KAGE),
    ("Генма Ширануи", MALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Эбису", MALE, KONOHA, NO_CLAN, ["Огонь"], NO_KEKKEI, NO_BEAST, WAVES),
    ("Хомура Митокадо", MALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Кохару Утатане", FEMALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Торуне Абураме", MALE, KONOHA, "Абураме", [UNKNOWN], NO_KEKKEI, NO_BEAST, KAGE),
    ("Югао Узуки", FEMALE, KONOHA, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Аоба Ямаширо", MALE, KONOHA, NO_CLAN, ["Огонь"], NO_KEKKEI, NO_BEAST, CHUNIN),
    ("Наваки", MALE, KONOHA, "Сенджу", [UNKNOWN], NO_KEKKEI, NO_BEAST, TSUNADE),
    ("Кагами Учиха", MALE, KONOHA, "Учиха", [UNKNOWN], "Шаринган", NO_BEAST, KAGE),
    ("Ацуи", MALE, KUMO, NO_CLAN, ["Огонь"], NO_KEKKEI, NO_BEAST, WAR),
    ("Гари", MALE, IWA, NO_CLAN, ["Земля", "Молния"], "Взрывной выпуск", NO_BEAST, WAR),
    ("Фугуки Суйказан", MALE, KIRI, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, WAR),
    ("Амеюри Ринго", FEMALE, KIRI, NO_CLAN, ["Молния"], NO_KEKKEI, NO_BEAST, WAR),
    ("Кушимару Куриараре", MALE, KIRI, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, WAR),
    ("Джинин Акебино", MALE, KIRI, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, WAR),
    ("Джинпачи Мунаши", MALE, KIRI, NO_CLAN, [UNKNOWN], NO_KEKKEI, NO_BEAST, WAR),
]

CHARACTERS: List[Dict[str, Any]] = [dict(zip(FIELDS, row)) for row in ROWS]

# Поиск по имени: регистр и лишние пробелы не важны.
INDEX = {character["name"].casefold(): character for character in CHARACTERS}


def find_character(name: str) -> Optional[Dict[str, Any]]:
    """Возвращает персонажа по названию или None, если такого в наборе нет."""
    return INDEX.get((name or "").strip().casefold())


def character_names() -> List[str]:
    """Названия для подсказки в поле ввода — без скрытых свойств."""
    return [character["name"] for character in CHARACTERS]


def village_color(village: str) -> str:
    """Цвет аватара для деревни; для незнакомых названий — нейтральный."""
    return VILLAGE_COLORS.get(village, DEFAULT_COLOR)


def public_character(character: Dict[str, Any]) -> Dict[str, Any]:
    """Персонаж для отправки клиенту (после конца раунда)."""
    return {key: character[key] for key in FIELDS}


def portrait_ref(character: Dict[str, Any]) -> str:
    """Куда странице взять портрет персонажа.

    Картинка может лежать прямо в базе строкой `data:image/...` — тогда в ответе
    стоит ссылка на отдельный адрес API: сам base64 в каталоге весит мегабайты,
    и через туннель страница не успевала его получить. Если в базе путь или
    ссылка, отдаём как есть — файл кладёт владелец сайта.
    """
    image = str(character.get("image") or "")
    if not image:
        return ""
    if image.startswith("data:"):
        return PORTRAIT_PATH % character.get("id")
    return image


def attribute_list() -> List[Dict[str, Any]]:
    """Описание граф сравнения — страница строит по нему шапку таблицы."""
    return [dict(attribute) for attribute in ATTRIBUTES]


def seed_rows() -> List[Dict[str, Any]]:
    """Строки для первичного заполнения таблицы narutodle_characters."""
    return [
        {**character, "color": village_color(character["village"]), "image": ""}
        for character in CHARACTERS
    ]


__all__ = [
    "ARCS",
    "ATTRIBUTES",
    "CHARACTERS",
    "FIELDS",
    "PORTRAIT_PATH",
    "ROWS",
    "UNKNOWN",
    "VILLAGE_COLORS",
    "attribute_list",
    "character_names",
    "find_character",
    "portrait_ref",
    "public_character",
    "seed_rows",
    "village_color",
]
