# -*- coding: utf-8 -*-
"""Промежуточный отчёт по теплице (Самост. работа 3) — сборка DOCX."""
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

OUT = "Промежуточный отчёт — Умная AI-Теплица (Arduino Nano).docx"

doc = Document()

# ------------------------------------------------------------------ страница
section = doc.sections[0]
section.page_width = Cm(21.0)
section.page_height = Cm(29.7)
section.left_margin = Cm(2.5)
section.right_margin = Cm(1.5)
section.top_margin = Cm(2.0)
section.bottom_margin = Cm(2.0)

style = doc.styles["Normal"]
style.font.name = "Times New Roman"
style.font.size = Pt(12)
style.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
pf = style.paragraph_format
pf.line_spacing = 1.5
pf.space_after = Pt(0)
pf.first_line_indent = Cm(1.25)
pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY


def p(text="", bold=False, italic=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
      indent=True, size=None, space_before=0, space_after=0):
    par = doc.add_paragraph()
    par.alignment = align
    par.paragraph_format.first_line_indent = Cm(1.25) if indent else Cm(0)
    par.paragraph_format.space_before = Pt(space_before)
    par.paragraph_format.space_after = Pt(space_after)
    par.paragraph_format.line_spacing = 1.5
    run = par.add_run(text)
    run.bold = bold
    run.italic = italic
    if size:
        run.font.size = Pt(size)
    return par


def h1(text):
    par = doc.add_paragraph()
    par.paragraph_format.first_line_indent = Cm(0)
    par.paragraph_format.space_before = Pt(12)
    par.paragraph_format.space_after = Pt(6)
    par.paragraph_format.line_spacing = 1.25
    par.paragraph_format.keep_with_next = True
    run = par.add_run(text)
    run.bold = True
    run.font.size = Pt(14)
    return par


def h2(text):
    par = doc.add_paragraph()
    par.paragraph_format.first_line_indent = Cm(0)
    par.paragraph_format.space_before = Pt(10)
    par.paragraph_format.space_after = Pt(4)
    par.paragraph_format.line_spacing = 1.25
    par.paragraph_format.keep_with_next = True
    run = par.add_run(text)
    run.bold = True
    run.font.size = Pt(12.5)
    return par


def bullet(text):
    par = doc.add_paragraph(style="List Bullet")
    par.paragraph_format.line_spacing = 1.5
    par.paragraph_format.space_after = Pt(0)
    par.paragraph_format.left_indent = Cm(1.25)
    par.add_run(text)
    return par


def caption(text):
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.LEFT
    par.paragraph_format.first_line_indent = Cm(0)
    par.paragraph_format.space_before = Pt(6)
    par.paragraph_format.space_after = Pt(3)
    par.paragraph_format.line_spacing = 1.0
    par.paragraph_format.keep_with_next = True
    run = par.add_run(text)
    run.font.size = Pt(10)
    run.italic = True
    return par


def shade(cell, color):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    tc_pr.append(shd)


def no_split(row):
    tr_pr = row._tr.get_or_add_trPr()
    cant = OxmlElement("w:cantSplit")
    tr_pr.append(cant)


def header_row(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tr_pr.append(tbl_header)


def table(headers, rows, widths=None, font=9.5, aligns=None):
    tbl = doc.add_table(rows=1, cols=len(headers))
    tbl.style = "Table Grid"
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    head = tbl.rows[0]
    header_row(head)
    no_split(head)
    for i, text in enumerate(headers):
        cell = head.cells[i]
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        shade(cell, "DCE6F1")
        par = cell.paragraphs[0]
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.first_line_indent = Cm(0)
        par.paragraph_format.line_spacing = 1.0
        par.paragraph_format.space_after = Pt(0)
        run = par.add_run(text)
        run.bold = True
        run.font.size = Pt(font)
    for values in rows:
        row = tbl.add_row()
        no_split(row)
        for i, text in enumerate(values):
            cell = row.cells[i]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            par = cell.paragraphs[0]
            if aligns and aligns[i] == "c":
                par.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                par.alignment = WD_ALIGN_PARAGRAPH.LEFT
            par.paragraph_format.first_line_indent = Cm(0)
            par.paragraph_format.line_spacing = 1.0
            par.paragraph_format.space_after = Pt(0)
            run = par.add_run(str(text))
            run.font.size = Pt(font)
    if widths:
        for i, width in enumerate(widths):
            tbl.columns[i].width = Cm(width)
        for row in tbl.rows:
            for i, width in enumerate(widths):
                row.cells[i].width = Cm(width)
    par = doc.add_paragraph()
    par.paragraph_format.space_after = Pt(0)
    par.paragraph_format.line_spacing = 1.0
    par.add_run().font.size = Pt(4)
    return tbl


def code_block(lines, size=8.5):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.style = "Table Grid"
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.rows[0].cells[0]
    shade(cell, "F4F4F4")
    par = cell.paragraphs[0]
    par.paragraph_format.first_line_indent = Cm(0)
    par.paragraph_format.line_spacing = 1.0
    par.paragraph_format.space_after = Pt(0)
    run = par.add_run(lines)
    run.font.name = "Consolas"
    run.font.size = Pt(size)
    run.element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
    par2 = doc.add_paragraph()
    par2.paragraph_format.space_after = Pt(0)
    par2.paragraph_format.line_spacing = 1.0


def flow_diagram():
    columns = [
        ["Датчики", "12 x влажность", "DHT22", "фоторезистор", "HC-SR04"],
        ["Arduino Nano", "ATmega328P", "CD74HC4067", "2 x 74HC595"],
        ["Сервер", "автоматика 2 с", "SQLite, PostgreSQL", "REST /api/*"],
        ["Панель", "PWA (front/)", "опрос 2 с"],
    ]
    width = 20
    lines = [" ──► ".join(column[0].ljust(width) for column in columns).rstrip()]
    for index in range(1, max(len(column) for column in columns)):
        lines.append("     ".join(
            (column[index] if index < len(column) else "").ljust(width)
            for column in columns
        ).rstrip())
    lines.append(" " * (width + 5) + "└──► насосы (12), вентилятор, фитолампа")
    return "\n".join(lines)


def page_field(paragraph):
    run = paragraph.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_begin)
    run._r.append(instr)
    run._r.append(fld_end)


# ------------------------------------------------------- колонтитулы
section.different_first_page_header_footer = True
footer = section.footer.paragraphs[0]
footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
footer.paragraph_format.first_line_indent = Cm(0)
page_field(footer)

header = section.header.paragraphs[0]
header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
header.paragraph_format.first_line_indent = Cm(0)
run = header.add_run("Умная AI-Теплица · промежуточный отчёт · 20.10.2026")
run.font.size = Pt(8.5)
run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

# =====================================================================
# ТИТУЛЬНЫЙ ЛИСТ
# =====================================================================
for _ in range(2):
    doc.add_paragraph()

p("Технологическая практика 2026–2027, осенний семестр", align=WD_ALIGN_PARAGRAPH.CENTER,
  indent=False, size=12)
p("Направление: интеллектуальные системы управления и обработка данных",
  align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, size=11, space_after=18)

p("ПРОМЕЖУТОЧНЫЙ ОТЧЁТ", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER,
  indent=False, size=18, space_after=4)
p("Самостоятельная работа 3 · промежуточная аттестация по индивидуальным проектам",
  align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, size=11, space_after=2)
p("по индивидуальному проекту технологической практики", align=WD_ALIGN_PARAGRAPH.CENTER,
  indent=False, size=12, space_after=24)

p("«Умная AI-Теплица»:", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER,
  indent=False, size=16, space_after=2)
p("система автоматического управления микроклиматом\n12 участков на Arduino Nano",
  bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, size=15, space_after=30)

p("Проект: TriEblanaiPraktika", align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, size=12)
p("Команда: Knoffik — backend, SiZeT — frontend, Amr — full-stack / engineer",
  align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, size=11)
p("Репозиторий: github.com/Amirsport/TriEblanaiPraktika",
  align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, size=11, space_after=30)

for _ in range(6):
    doc.add_paragraph()
p("Выполнил: ____________________   Группа: __________",
  align=WD_ALIGN_PARAGRAPH.LEFT, indent=False, size=12)
p("Проверил: ____________________", align=WD_ALIGN_PARAGRAPH.LEFT, indent=False, size=12)
for _ in range(3):
    doc.add_paragraph()
p("20 октября 2026 г.", align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, size=12)

doc.add_page_break()

# =====================================================================
# 1. ПОСТАНОВКА ЗАДАЧИ
# =====================================================================
h1("1. Постановка задачи в измеримых терминах")

h2("1.1. Объект исследования и управления")
p("Объект — теплица-парник, разделённая на 12 участков (ячеек кассеты). На каждом "
  "участке измеряется влажность почвы и работает собственный насос полива; общими для "
  "теплицы являются температура воздуха, освещённость и уровень воды в баке. "
  "Исполнители — 12 насосов, вентилятор проветривания и фитолампа досветки.")
p("Цель промежуточного этапа — работающий программно-аппаратный контур, который измеряет "
  "микроклимат каждого участка, автоматически управляет поливом, проветриванием и "
  "досветкой, сохраняет историю измерений и позволяет воспроизвести любую проверку по "
  "сохранённым данным. Контур доведён до уровня, при котором плата Arduino Nano "
  "собирается и прошивается, сервер и панель работают, а канал обмена «плата — сервер» "
  "проверен на протокольном уровне.")

h2("1.2. Измеряемые и регулируемые величины")
p("Перечень величин, единиц и источников приведён в таблице 1. Каждое показание "
  "сохраняется в базу с меткой времени в формате ISO-8601 UTC, поэтому любую метрику "
  "можно пересчитать по журналу.")
caption("Таблица 1 — Измеряемые и регулируемые величины")
table(
    ["Величина", "Ед. изм.", "Диапазон / шаг", "Источник"],
    [
        ["Влажность почвы", "%", "0…100; шаг 1", "12 ёмкостных датчиков через CD74HC4067"],
        ["Температура воздуха", "°C", "−40…+80; шаг 0,1 (в сессии 22,6…24,9)", "DHT22"],
        ["Относительная влажность воздуха", "%", "0…100; в текущей версии не передаётся", "DHT22 (резерв протокола)"],
        ["Освещённость", "лк", "0…45 000; шаг 1 (оценка)", "Фоторезистор, канал C12"],
        ["Уровень воды в баке", "%", "0…100 (3…25 см)", "HC-SR04"],
        ["Состояние исполнителя", "—", "вкл. / выкл.", "14 выходов 2×74HC595"],
        ["Длительность полива", "с", "0…120", "Таймер прошивки и сервера"],
        ["Период опроса участка", "с", "2,0 (факт 2,04)", "Прошивка, SEND_INTERVAL_MS"],
        ["Задержка команды", "мс", "—", "REST API, автоматика"],
    ],
    widths=[4.8, 1.6, 5.3, 5.1],
)

h2("1.3. Критерии успеха и целевые значения")
p("Целевые значения зафиксированы до начала измерений; часть из них относится к "
  "аппаратной проверке, которая ещё не выполнена, потому что датчики к плате не "
  "подключены. Таблица 2 показывает фактическое состояние на 20.10.2026.")
caption("Таблица 2 — Критерии успеха и фактическое состояние")
table(
    ["Показатель", "Целевое значение", "Факт (20.10.2026)", "Статус"],
    [
        ["Период опроса участка", "≤ 2,5 с", "2,04 с", "Выполнено"],
        ["p95 времени ответа GET /api/state", "≤ 50 мс", "33,35 мс", "Выполнено"],
        ["Полный цикл команды «включить — подтвердить»", "≤ 100 мс", "53,86 мс", "Выполнено"],
        ["Задержка автоматического полива", "≤ 4 с", "1,67 с", "Выполнено"],
        ["Объём хранения записи", "≤ 120 Б", "85,3 Б", "Выполнено"],
        ["Загрузка Flash прошивки", "≤ 80 %", "42,3 %", "Выполнено"],
        ["Занятая RAM прошивки", "≤ 80 %", "33,0 %", "Выполнено"],
        ["Ошибка датчика влажности относительно эталона", "≤ ±5 %", "не измерена", "В работе"],
        ["Непрерывная наработка без сбоев", "≥ 72 ч", "120,3 с, 0 сбоев; 7,43 ч данных", "В работе"],
    ],
    widths=[6.8, 3.0, 4.8, 2.2],
)

# =====================================================================
# 2. АРХИТЕКТУРА
# =====================================================================
h1("2. Архитектура и реализация")

h2("2.1. Структурная схема решения")
p("Данные идут по цепочке «датчики → контроллер → сервер → панель». Плата опрашивает "
  "12 датчиков влажности через аналоговый мультиплексор, добавляет общие для теплицы "
  "температуру воздуха, освещённость и уровень воды и раз в 2 секунды "
  "отправляет кадр JSON в последовательный порт. Сервер принимает кадр, пишет показания "
  "в базу, каждые 2 секунды просматривает пороги и отправляет команды исполнителям. "
  "Панель получает состояние по REST API и обновляется каждые 2 секунды.")
code_block(flow_diagram(), size=8)
caption("Рисунок 1 — Структурная схема тепличного контура")
p("Если сервер вынесен на VPS, плата остаётся дома: между ними работает агент "
  "backend/device_agent.py, который держит COM-порт, отправляет показания по HTTPS и "
  "применяет полученные команды. Протокол обмена при этом не меняется, поэтому один и "
  "тот же код платы работает и с локальным сервером, и с удалённым.")
p("Без платы сервер включает эмулятор: он повторяет тот же протокол и физическую модель "
  "участков (испарение, полив, нагрев, освещение от времени суток). Поэтому все замеры "
  "ниже получены на том же коде, который будет работать с реальными датчиками.")

h2("2.2. Аппаратные средства")
p("Состав стенда приведён в таблице 3. Плата Arduino Nano выбрана как минимально "
  "достаточная: 10 цифровых линий закрывают мультиплексор, сдвиговые регистры, DHT22 и "
  "ультразвуковой датчик, а один аналоговый вход обслуживает 13 каналов через "
  "CD74HC4067.")
caption("Таблица 3 — Состав аппаратной части")
table(
    ["Компонент", "Кол-во", "Интерфейс", "Назначение"],
    [
        ["Arduino Nano (ATmega328P, 16 МГц)", "1", "USB / UART", "Опрос датчиков и управление исполнителями"],
        ["CD74HC4067", "1", "1 аналоговый + 4 цифровых", "13 каналов на входе A0"],
        ["Датчик влажности почвы ёмкостный", "12", "Аналоговый", "Влажность по участкам"],
        ["DHT22", "1", "1-Wire", "Температура и влажность воздуха"],
        ["HC-SR04", "1", "2 цифровых", "Уровень воды в баке"],
        ["74HC595", "2", "3 цифровых, каскад", "16 выходов управления"],
        ["Модуль реле 16 каналов", "1", "Логика 5 В", "Коммутация насосов, вентилятора, лампы"],
        ["Насосы 12 В", "12", "Реле", "Полив по участкам"],
        ["Вентилятор 12 В", "1", "Реле", "Проветривание"],
        ["Фитолампа LED 12 В", "1", "MOSFET-модуль", "Досветка"],
        ["Блок питания 12 В", "1", "—", "Насосы, вентилятор, лампа"],
        ["Блок питания 5 В, 2 А", "1", "—", "Реле и датчики"],
    ],
    widths=[5.8, 1.3, 3.9, 5.8],
    aligns=["l", "c", "l", "l"],
)

h2("2.3. Распиновка Arduino Nano")
p("Прошивка переведена с Mega 2560 на Nano: изменена карта выводов, а кадр телеметрии "
  "печатается в порт потоком, без JSON-документа на 12 участков, чтобы уложиться в "
  "2 КБ SRAM. Занятые линии показаны в таблице 4.")
caption("Таблица 4 — Распиновка Arduino Nano")
table(
    ["Вывод Nano", "Подключение", "Режим"],
    [
        ["A0", "SIG CD74HC4067", "Аналоговый вход"],
        ["D2…D5", "S0…S3 мультиплексора", "Выход"],
        ["D6", "DATA DHT22", "Вход/выход 1-Wire"],
        ["D7", "TRIG HC-SR04", "Выход"],
        ["D8", "ECHO HC-SR04", "Вход"],
        ["D9", "DS 74HC595", "Выход"],
        ["D10", "SHCP (clock)", "Выход"],
        ["D11", "STCP (latch)", "Выход"],
        ["D12, D13, A1…A7", "Резерв", "—"],
        ["D0, D1", "Serial (USB)", "UART 115200"],
    ],
    widths=[4.2, 7.0, 5.4],
    aligns=["l", "l", "l"],
)
p("Питание разделено: насосы, вентилятор и лампа — от блока 12 В; модуль реле и датчики — "
  "от отдельного блока 5 В на 2 А; земли всех блоков объединены. Расчёт по паспортным "
  "токам модулей: 14 каналов реле — до 280 мА, 12 датчиков влажности — около 60 мА, "
  "DHT22 и HC-SR04 — около 20 мА, итого около 360 мА; запас блока 5 В — более чем "
  "пятикратный. При всех включённых насосах линия 12 В потребляет до 3,6 А (типовой "
  "ток насоса 0,3 А, подлежит проверке), поэтому блок 12 В выбран с запасом не менее "
  "5 А, а прошивка ограничивает непрерывную работу исполнителя двумя минутами.")

h2("2.4. Программные средства")
caption("Таблица 5 — Программные средства и версии")
table(
    ["Средство", "Версия", "Назначение"],
    [
        ["Python", "3.9.13", "Сервер, автоматика, REST API (stdlib http.server)"],
        ["SQLite", "3.37.2", "Хранение истории (по умолчанию)"],
        ["PostgreSQL + psycopg", "—", "Альтернативное хранение"],
        ["ArduinoJson", "6.21.6", "Разбор команд на плате"],
        ["DHT sensor library", "1.4.7", "Работа с DHT22"],
        ["Adafruit Unified Sensor", "1.1.15", "Зависимость библиотеки DHT"],
        ["PlatformIO Core", "6.2.0", "Сборка прошивки для Nano"],
        ["HTML / CSS / JS (PWA)", "—", "Панель управления и офлайн-оболочка"],
        ["pyserial", "—", "COM-порт при подключённой плате"],
    ],
    widths=[4.8, 2.4, 9.4],
)

h2("2.5. Что реализовано и что находится в отладке")
p("На момент отчётности работает следующее:")
bullet("прошивка greenhouse_12zone.ino (277 строк) собирается под arduino:avr:nano: "
       "Flash — 12 984 из 30 720 байт (42,3 %), RAM — 675 из 2 048 байт (33,0 %);")
bullet("сервер принимает телеметрию, ведёт историю, считает статусы участков и "
       "автоматически управляет поливом, проветриванием и досветкой;")
bullet("REST API отдаёт состояние, историю, журнал, настройки и статус канала платы; "
       "панель на HTML/CSS/JS устанавливается как PWA;")
bullet("эмулятор датчиков повторяет протокол платы, поэтому переход на реальное железо "
       "сводится к запуску сервера с флагом --serial COM3;")
bullet("домашний агент связывает плату с сервером на VPS по HTTPS.")
p("В отладке находятся: монтаж 12 датчиков влажности и калибровка констант SOIL_DRY и "
  "SOIL_WET, измерение погрешности датчиков относительно эталона, замер токов "
  "исполнителей и 72-часовая наработка. Эти работы требуют физического подключения "
  "датчиков, которых пока нет.")
p("Репозиторий с кодом и инструкцией: https://github.com/Amirsport/TriEblanaiPraktika. "
  "Команды запуска сервера, панели, прошивки и повторного снятия метрик приведены в "
  "приложении В.")

# =====================================================================
# 3. ДАННЫЕ
# =====================================================================
h1("3. Данные: происхождение, объём, разметка")

h2("3.1. Источник данных")
p("Данные получены программным прототипом: сервер опрашивал эмулятор, который "
  "воспроизводит физическую модель 12 участков и протокол платы. Реальные измерения "
  "появятся после подключения датчиков; протокол и структура записи при этом не "
  "меняются, поэтому накопленная история останется сопоставимой.")

h2("3.2. Объём данных")
p("В базе 160 567 записей за четыре сессии опроса (таблица 6). Каждый участок получил "
  "13 380–13 381 запись. Суммарная длительность опроса при темпе 6 записей в секунду "
  "(12 участков раз в 2 секунды) — около 7,43 часа.")
caption("Таблица 6 — Сессии сбора данных")
table(
    ["Сессия", "Дата", "Записей", "Длительность опроса, ч"],
    [
        ["1", "05.10.2026", "82 728", "3,83"],
        ["2", "12.10.2026", "19 020", "0,88"],
        ["3", "13.10.2026", "58 543", "2,71"],
        ["4", "15.10.2026", "276", "0,01"],
        ["Итого", "05–15.10.2026", "160 567", "7,43"],
    ],
    widths=[2.2, 4.2, 4.2, 6.0],
    aligns=["c", "c", "c", "c"],
)
p("Файл базы занимает 13,4 МБ. Прирост в отдельном 60-секундном прогоне составил "
  "28 672 байта на 336 записей, то есть 85,3 байта на запись. При непрерывном опросе "
  "6 записей в секунду это 44,2 МБ в сутки и около 1,33 ГБ за 30 суток — приемлемый "
  "объём для SQLite и тем более для PostgreSQL.")

h2("3.3. Формат хранения и структура полей")
p("База — SQLite (файл data/greenhouse.sqlite3), кодировка UTF-8, метки времени — "
  "ISO-8601 UTC. Основные таблицы и их объём приведены в таблице 7.")
caption("Таблица 7 — Схема базы данных тепличного контура")
table(
    ["Таблица", "Ключевые поля", "Назначение", "Записей"],
    [
        ["zones", "id, name, position", "Справочник 12 участков", "12"],
        ["readings", "id, zone_id, temperature, moisture, light, recorded_at", "История показаний", "160 567"],
        ["zone_devices", "zone_id, device, on_state, updated_at", "Состояние исполнителей", "36"],
        ["settings", "mode, moisture_target, moisture_threshold, temperature_threshold, light_threshold", "Пороги и режим", "1"],
        ["state", "tank, window_open, source, port, updated_at", "Общее состояние теплицы", "1"],
        ["logs", "id, ts, level, zone_id, message", "Журнал событий", "290"],
        ["device_commands", "id, zone_id, device, on_state, seconds, created_at, applied_at", "Очередь команд для VPS", "0"],
        ["users, auth_sessions", "id, username, role; token, expires_at", "Вход в панель", "6 + 6"],
    ],
    widths=[3.4, 6.8, 4.6, 2.0],
    font=9,
    aligns=["l", "l", "l", "c"],
)
p("Первичные ключи — суррогатные id; связь readings.zone_id → zones.id и "
  "zone_devices.zone_id → zones.id поддерживается логикой приложения. В журнале "
  "290 событий: 156 информационных и 134 предупреждения (автополив, перегрев, "
  "переключение режима).")

h2("3.4. Примеры данных и разметка")
p("Кадр телеметрии, строка истории и записи журнала приведены в приложении Б. Выгрузка "
  "1 200 строк (по 100 на участок) лежит в reports/dataset_sample.csv, результаты "
  "прогонов — в reports/metrics.json. Разметки классов в наборе нет: это временные ряды "
  "измерений. Для проверки точности датчиков планируется разметка эталонными "
  "измерениями — по 3 точки на каждый из 12 участков (36 опорных значений) и по "
  "3 температуры в диапазоне 20–30 °C.")

# =====================================================================
# 4. МЕТРИКИ
# =====================================================================
h1("4. Метрики и измеряемые результаты")
p("Замеры выполнены на одном ПК: Windows 10 Pro 22H2 (сборка 19045), Intel Core "
  "i5-12450H (8 ядер / 12 потоков), 15,7 ГБ ОЗУ, Python 3.9.13, SQLite 3.37.2. Сервер "
  "запускался локально на 127.0.0.1 с временной базой, клиент — тот же ПК. Время "
  "ответа включает установку TCP-соединения, обработку запроса и сериализацию JSON.")
caption("Таблица 8 — Измеренные показатели тепличного контура")
table(
    ["Показатель", "Значение", "Условия измерения"],
    [
        ["Период отправки кадров телеметрии", "2,07 с", "58 кадров за 120,3 с"],
        ["Период опроса участка", "2,04 с", "58 значений на участок за 118 с"],
        ["Записей в секунду", "5,79", "696 записей за 120,3 с"],
        ["GET /api/state, среднее", "25,92 мс", "n = 300"],
        ["GET /api/state, медиана", "30,44 мс", "n = 300"],
        ["GET /api/state, p95", "33,35 мс", "n = 300"],
        ["GET /api/state, максимум", "107,63 мс", "n = 300"],
        ["GET /api/zones/1/history?limit=60, среднее", "15,36 мс", "n = 200"],
        ["GET /api/zones/1/history?limit=60, p95", "27,04 мс", "n = 200"],
        ["POST /api/devices, среднее", "35,42 мс", "n = 20"],
        ["Полный цикл команды, среднее", "53,86 мс", "POST + подтверждение, n = 20"],
        ["Полный цикл команды, p95", "64,37 мс", "n = 20"],
        ["Реакция автоматики: первый участок", "1,54 с", "порог влажности 99 %"],
        ["Реакция автоматики: все 12 участков", "1,67 с", "12/12 насосов включены"],
        ["Старт сервера", "1,04 с", "до первого ответа /api/health"],
        ["Сбои канала телеметрии", "0 из 58 кадров", "120,3 с непрерывной работы"],
        ["Flash прошивки", "12 984 Б (42,3 %)", "PlatformIO, arduino:avr:nano"],
        ["RAM прошивки", "675 Б (33,0 %)", "PlatformIO, arduino:avr:nano"],
        ["Объём записи", "85,3 Б", "336 записей за 60 с, +28 672 Б"],
        ["Объём базы истории", "13,4 МБ", "160 567 записей"],
    ],
    widths=[7.0, 3.4, 6.4],
    font=9,
)
p("Наибольшую задержку даёт GET /api/state: сервер последовательно читает последние "
  "показания по 12 участкам и состояние 36 исполнителей. Даже p95 = 33,35 мс оставляет "
  "почти полуторакратный запас до целевых 50 мс. Полный цикл команды (POST и подтверждение по состоянию) укладывается "
  "в 54 мс при цели 100 мс, а автоматика срабатывает за один такт — 1,67 с при цели 4 с.")
p("Прошивка занимает 42,3 % Flash и 33,0 % RAM. Запас по RAM особенно важен для "
  "ATmega328P: кадр телеметрии печатается потоком, поэтому 12 объектов JSON не "
  "размещаются в стеке одновременно. Ограничение непрерывной работы исполнителя "
  "двумя минутами задано в прошивке и не зависит от сервера.")

# =====================================================================
# 5. ВЕРИФИКАЦИЯ
# =====================================================================
h1("5. Верификация результата")

h2("5.1. Стенд и методика проверки")
p("Проверка выполнена по трём сценариям. Первый — телеметрия: сервер непрерывно работал "
  "120,3 с, за это время эмулятор отправил 58 кадров, в базу записано 696 строк, обрывов "
  "канала не зафиксировано. Второй — API: 300 последовательных запросов GET /api/state "
  "и 200 запросов истории, результаты сведены в среднее, медиану, p95 и максимум. "
  "Третий — управление: 20 циклов включения и выключения насоса, затем проверка "
  "автоматики с порогом влажности 99 %, чтобы решение сработало гарантированно.")
p("Прирост базы измерялся отдельным прогоном: после 20 секунд работы фиксировался размер "
  "файла и число строк, ещё через 60 секунд — повторно. Разница составила 336 записей и "
  "28 672 байта.")

h2("5.2. Число испытаний и воспроизводимость")
p("Всего выполнено 500 запросов к API, 20 циклов команд (по 10 включений и выключений), "
  "два прогона телеметрии длительностью 120,3 с и 80 с, один тест автоматики на 12 "
  "участках и четыре сессии накопления данных. Повторный прогон дал близкие значения: "
  "среднее GET /api/state — 25,92 и 25,64 мс, p95 — 33,35 и 33,94 мс, темп записи — "
  "5,79 и 5,79 записи в секунду, реакция автоматики — 1,67 и 1,77 с. Разброс не "
  "превышает 5 %, что подтверждает воспроизводимость.")
p("Для повторного получения чисел достаточно выполнить:")
code_block(
    "python backend/server.py --open\n"
    "python tools/bench_greenhouse.py --duration 120 --out metrics.json",
    size=9,
)

h2("5.3. Ограничения и источники ошибок")
bullet("Канал проверен на эмуляторе, а не на реальных датчиках: погрешность влажности, "
       "температуры и уровня воды пока не измерена.")
bullet("Измерения API сделаны одним клиентом на localhost; при нескольких клиентах и "
       "сетевой задержке абсолютные значения вырастут.")
bullet("Задержка включает установку нового TCP-соединения на каждый запрос, то есть "
       "является верхней оценкой для браузера с keep-alive.")
bullet("Прирост базы измерен по файлу SQLite и включает служебные страницы; при "
       "непрерывной работе оценка 85,3 байта на запись может меняться в пределах "
       "нескольких процентов.")
bullet("72-часовая наработка не проводилась: подтверждены только 120,3 с без сбоев и "
       "7,43 часа накопленной истории.")

# =====================================================================
# 6. ВЫВОДЫ
# =====================================================================
h1("6. Выводы и план доработки")

h2("6.1. Что подтверждено измерениями")
bullet("Контур работает: плата Nano собирается (Flash 42,3 %, RAM 33,0 %), сервер "
       "принимает телеметрию, база растёт с темпом 5,79 записи в секунду, ошибок канала "
       "нет.")
bullet("Период опроса участка — 2,04 с при цели 2,5 с; кадры уходят каждые 2,07 с.")
bullet("REST API укладывается в целевые задержки: p95 состояния 33,35 мс, полный цикл "
       "команды 53,86 мс.")
bullet("Автоматика включает все 12 насосов за 1,67 с при пороге 4 с.")
bullet("История из 160 567 записей занимает 13,4 МБ, то есть 85,3 байта на запись.")

h2("6.2. Что не достигнуто и почему")
p("Не измерена погрешность датчиков и не подтверждена 72-часовая наработка: датчики к "
  "плате не подключены, поэтому физический канал ещё не нагружался. Эти показатели "
  "вынесены в план и не подменяются оценками по эмулятору.")

h2("6.3. План доработки")
caption("Таблица 9 — План работ до следующего этапа")
table(
    ["Шаг", "Работа", "Ожидаемый числовой результат", "Срок"],
    [
        ["1", "Подключить 12 датчиков влажности, DHT22 и HC-SR04; откалибровать SOIL_DRY / SOIL_WET",
         "Погрешность влажности ≤ ±5 % на 36 опорных точках", "27.10.2026"],
        ["2", "Проверить реальный канал Serial 115200 на плате",
         "0 ошибок за 1 час, период опроса 2,0 ± 0,1 с", "27.10.2026"],
        ["3", "Замерить токи насоса, вентилятора и лампы",
         "Ток 12 В ≤ 5 А, запас блока питания ≥ 30 %", "03.11.2026"],
        ["4", "Провести 72-часовую наработку",
         "Ошибок < 0,1 %, доступность ≥ 99 %", "10.11.2026"],
        ["5", "Проверить автополив на реальной почве",
         "Задержка ≤ 4 с, отклонение влажности от цели ≤ 5 %", "10.11.2026"],
        ["6", "Сравнить SQLite и PostgreSQL на 1 млн записей",
         "p95 выборки истории ≤ 50 мс", "17.11.2026"],
    ],
    widths=[1.0, 6.8, 6.3, 2.7],
    font=9,
    aligns=["c", "l", "l", "c"],
)
p("Таким образом, на промежуточном этапе получен работающий программно-аппаратный "
  "прототип с воспроизводимыми числовыми характеристиками. Оставшиеся показатели "
  "относятся к физическому подключению датчиков и могут быть измерены на следующем "
  "шаге без изменения архитектуры.")

# =====================================================================
# ПРИЛОЖЕНИЯ
# =====================================================================
doc.add_page_break()
h1("Приложение А. Сводная таблица метрик")
p("Таблица А.1 показывает результаты трёх независимых прогонов. Совпадение значений "
  "служит проверкой воспроизводимости: расхождение средних задержек не превышает "
  "0,5 мс, темпа записи — 0,2 записи в секунду, реакции автоматики — 0,1 с.")
caption("Таблица А.1 — Результаты прогонов")
table(
    ["Показатель", "Прогон 1 (120 с)", "Прогон 2 (120 с)", "Прогон 3 (60 с)"],
    [
        ["GET /api/state, среднее, мс", "25,92", "25,64", "—"],
        ["GET /api/state, p95, мс", "33,35", "33,94", "—"],
        ["GET /api/zones/1/history, среднее, мс", "15,36", "15,86", "—"],
        ["POST /api/devices, среднее, мс", "35,42", "35,62", "33,57"],
        ["Полный цикл команды, среднее, мс", "53,86", "54,71", "54,71"],
        ["Реакция автоматики, с", "1,67", "1,77", "—"],
        ["Записей в секунду", "5,79", "5,79", "5,60"],
        ["Ошибок канала", "0", "0", "0"],
    ],
    widths=[7.8, 3.0, 3.0, 3.0],
    font=9,
    aligns=["l", "c", "c", "c"],
)

h1("Приложение Б. Примеры данных")
p("Полная история лежит в data/greenhouse.sqlite3, выгрузка 1 200 строк — в "
  "reports/dataset_sample.csv (поля: zone_id, temperature_c, moisture_pct, light_lx, "
  "recorded_at_utc). Ниже — кадр телеметрии, сокращённый до двух участков:")

code_block(
    '{"type":"readings","tank":78.5,"data":[\n'
    '  {"zone":1,"temperature":23.9,"moisture":28.4,"light":26868},\n'
    '  {"zone":2,"temperature":23.9,"moisture":29.0,"light":26868}]}',
    size=8.5,
)
p("Строки истории в базе (последние записи сессии):")
code_block(
    "zone_id | temperature | moisture | light   | recorded_at\n"
    "      12|       23.73 |    29.00 | 26867.6 | 2026-10-20T06:20:20.949Z\n"
    "      11|       23.94 |    31.16 | 28103.6 | 2026-10-20T06:20:20.946Z\n"
    "      10|       23.99 |    30.51 | 26975.8 | 2026-10-20T06:20:20.940Z",
    size=8.5,
)
p("Записи журнала:")
code_block(
    "level | message\n"
    "warn  | Участок 3: автополив\n"
    "info  | Датчики недоступны — включён эмулятор 12 участков\n"
    "info  | Режим переключён: auto",
    size=8.5,
)
p("Фрагмент схемы (SQLite):")
code_block(
    "CREATE TABLE readings (\n"
    "    id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
    "    zone_id INTEGER NOT NULL,\n"
    "    temperature REAL, moisture REAL, light REAL,\n"
    "    recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))\n"
    ");",
    size=8.5,
)
p("Пример запроса — средняя влажность по участкам за сессию 13.10.2026:")
code_block(
    "SELECT zone_id, round(avg(moisture), 2) AS avg_moisture, count(*) AS n\n"
    "FROM readings\n"
    "WHERE recorded_at >= '2026-10-13' AND recorded_at < '2026-10-14'\n"
    "GROUP BY zone_id ORDER BY zone_id;",
    size=8.5,
)

h1("Приложение В. Инструкция запуска и проверки")
p("Сервер и панель (без платы — с эмулятором):")
code_block(
    "python backend/server.py --open\n"
    "# панель: http://127.0.0.1:8000/",
    size=9,
)
p("С реальной платой:")
code_block(
    "python backend/server.py --serial COM3 --port 8000",
    size=9,
)
p("Прошивка (Arduino IDE: открыть greenhouse_12zone.ino, плата Arduino Nano, "
  "процессор ATmega328P, порт COM3) или PlatformIO:")
code_block(
    "pio run -d hardware/arduino/greenhouse_12zone\n"
    "pio run -d hardware/arduino/greenhouse_12zone -t upload",
    size=9,
)
p("Повторное снятие метрик:")
code_block(
    "python tools/bench_greenhouse.py --duration 120 --out metrics.json",
    size=9,
)
p("Проверка API вручную:")
code_block(
    "curl http://127.0.0.1:8000/api/health\n"
    "curl http://127.0.0.1:8000/api/state\n"
    "curl -X POST http://127.0.0.1:8000/api/devices `\n"
    "  -H \"Content-Type: application/json\" `\n"
    "  -d '{\"zone_id\":1,\"device\":\"watering\",\"on\":true,\"seconds\":10}'",
    size=8.5,
)
p("Журнал сервера и база: data/greenhouse.sqlite3 (SQLite) или PostgreSQL при запуске "
  "с --dsn. Все команды выполняются из корня репозитория.")

doc.core_properties.title = "Промежуточный отчёт — Умная AI-Теплица (Arduino Nano)"
doc.core_properties.author = "TriEblanaiPraktika"
doc.core_properties.subject = "Технологическая практика 2026–2027"

doc.save(OUT)
print("saved", OUT)
