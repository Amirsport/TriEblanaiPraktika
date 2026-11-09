# -*- coding: utf-8 -*-
"""DOCX -> PDF для отчёта: рендер документа python-docx через reportlab."""
import sys
from xml.sax.saxutils import escape

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, PageBreak,
                                PageTemplate, Paragraph as RParagraph, Preformatted,
                                Spacer, Table as RTable, TableStyle)

FONTS = r"C:\Windows\Fonts"
pdfmetrics.registerFont(TTFont("TNR", FONTS + r"\times.ttf"))
pdfmetrics.registerFont(TTFont("TNR-Bold", FONTS + r"\timesbd.ttf"))
pdfmetrics.registerFont(TTFont("TNR-Italic", FONTS + r"\timesi.ttf"))
pdfmetrics.registerFont(TTFont("TNR-BoldItalic", FONTS + r"\timesbi.ttf"))
pdfmetrics.registerFontFamily("TNR", normal="TNR", bold="TNR-Bold",
                              italic="TNR-Italic", boldItalic="TNR-BoldItalic")
pdfmetrics.registerFont(TTFont("Mono", FONTS + r"\consola.ttf"))
pdfmetrics.registerFont(TTFont("Mono-Bold", FONTS + r"\consolab.ttf"))
pdfmetrics.registerFontFamily("Mono", normal="Mono", bold="Mono-Bold",
                              italic="Mono", boldItalic="Mono-Bold")

PAGE_W, PAGE_H = A4
LEFT, RIGHT = 2.5 * cm, 1.5 * cm
TOP, BOTTOM = 2.0 * cm, 2.0 * cm
CONTENT_W = PAGE_W - LEFT - RIGHT

_docx = Document(sys.argv[1])
OUT = sys.argv[2]

_styles = {}


def style(key, size, align=TA_JUSTIFY, indent=1.25 * cm, before=0, after=0,
          keep=0, bullet=0):
    key = (key, round(size, 1), align, round(indent, 1), round(before, 1),
           round(after, 1), keep, bullet)
    if key not in _styles:
        _styles[key] = ParagraphStyle(
            "s%d" % len(_styles), fontName="TNR", fontSize=size,
            leading=size * 1.45, alignment=align, firstLineIndent=indent,
            spaceBefore=before, spaceAfter=after, keepWithNext=keep,
            bulletFontName="TNR", bulletFontSize=size, bulletIndent=0,
            leftIndent=indent if not bullet else 1.25 * cm,
        )
    return _styles[key]


def run_markup(paragraph):
    parts = []
    for run in paragraph.runs:
        text = escape(run.text).replace("\n", "<br/>")
        if not text:
            continue
        name = run.font.name
        if name == "Consolas":
            text = '<font name="Mono">%s</font>' % text
        if run.bold:
            text = "<b>%s</b>" % text
        if run.italic:
            text = "<i>%s</i>" % text
        parts.append(text)
    return "".join(parts)


def para_size(paragraph, default=12):
    sizes = [run.font.size.pt for run in paragraph.runs if run.font.size]
    return max(sizes) if sizes else default


def has_page_break(paragraph):
    return bool(paragraph._p.xpath('.//w:br[@w:type="page"]'))


def render_paragraph(paragraph):
    if has_page_break(paragraph):
        return [PageBreak()]
    text = run_markup(paragraph)
    if not text.strip():
        return [Spacer(1, para_size(paragraph) * 1.5)]

    size = para_size(paragraph)
    fmt = paragraph.paragraph_format
    align = fmt.alignment
    if align == WD_ALIGN_PARAGRAPH.CENTER:
        ralign = TA_CENTER
    elif align == WD_ALIGN_PARAGRAPH.JUSTIFY:
        ralign = TA_JUSTIFY
    else:
        ralign = TA_LEFT

    indent = fmt.first_line_indent.pt if fmt.first_line_indent is not None else 0
    if paragraph.style.name == "List Bullet":
        st = style("bullet", size, TA_JUSTIFY, 0, 0, 0, 0, 1)
        return [RParagraph(text, st, bulletText="\u2022")]
    heading = bool(paragraph.runs) and all(r.bold for r in paragraph.runs if r.text.strip())
    keep = 1 if (heading or paragraph.runs and paragraph.runs[0].italic) else 0
    st = style("p", size, ralign, indent, 0, 0, keep, 0)
    return [RParagraph(text, st)]


def cell_text(cell):
    lines = []
    for paragraph in cell.paragraphs:
        lines.append(run_markup(paragraph) or "")
    return "<br/>".join(lines) if lines else ""


def wrap_code(text, size, width_pt):
    limit = max(40, int((width_pt - 8) / (size * 0.60)))
    out = []
    for line in text.split("\n"):
        if len(line) <= limit:
            out.append(line)
            continue
        current = ""
        for word in line.split(" "):
            if not current:
                current = word
            elif len(current) + 1 + len(word) <= limit:
                current += " " + word
            else:
                out.append(current)
                current = "  " + word
        out.append(current)
    return "\n".join(out)


def render_table(table):
    header_fill = None
    try:
        tc_pr = table.rows[0].cells[0]._tc.tcPr
        shd = tc_pr.find(qn("w:shd")) if tc_pr is not None else None
        header_fill = shd.get(qn("w:fill")) if shd is not None else None
    except Exception:
        header_fill = None

    widths = []
    for column in table.columns:
        width = column.width.pt if column.width else CONTENT_W / len(table.columns)
        widths.append(width)
    total = sum(widths)
    if total > CONTENT_W + 2:
        widths = [w * CONTENT_W / total for w in widths]

    first_cell = table.rows[0].cells[0]
    mono = any((run.font.name == "Consolas")
               for paragraph in first_cell.paragraphs for run in paragraph.runs)
    if mono and len(table.columns) == 1:
        text = "\n".join(paragraph.text for paragraph in first_cell.paragraphs)
        size = para_size(first_cell.paragraphs[0], 8.5)
        code = Preformatted(wrap_code(text, size, CONTENT_W),
                            ParagraphStyle("code", fontName="Mono", fontSize=size,
                                           leading=size * 1.25))
        box = RTable([[code]], colWidths=[CONTENT_W])
        box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4F4F4")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#BFBFBF")),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return [box, Spacer(1, 6)]

    data = []
    for row_index, row in enumerate(table.rows):
        cells = []
        for cell in row.cells:
            text = cell_text(cell)
            size = 9.5
            if cell.paragraphs and cell.paragraphs[0].runs:
                size = para_size(cell.paragraphs[0], 9.5)
            is_head = row_index == 0 and header_fill is not None
            st = ParagraphStyle(
                "cell", fontName="TNR", fontSize=size, leading=size * 1.18,
                alignment=TA_CENTER if is_head else TA_LEFT,
                firstLineIndent=0, spaceBefore=0, spaceAfter=0,
            )
            cells.append(RParagraph(text or " ", st))
        data.append(cells)

    rendered = RTable(data, colWidths=widths, repeatRows=1)
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#808080")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]
    if header_fill:
        commands.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#" + header_fill)))
    rendered.setStyle(TableStyle(commands))
    return [rendered, Spacer(1, 8)]


def build_story(document):
    story = []
    body = document.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            story.extend(render_paragraph(Paragraph(child, document)))
        elif child.tag == qn("w:tbl"):
            story.extend(render_table(Table(child, document)))
    return story


def on_page(canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setFont("TNR", 8.5)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawRightString(PAGE_W - RIGHT, PAGE_H - 1.1 * cm,
                               "Умная AI-Теплица · промежуточный отчёт · 20.10.2026")
    canvas.setFont("TNR", 10)
    canvas.setFillColor(colors.black)
    canvas.drawCentredString(PAGE_W / 2.0, 1.0 * cm, str(doc.page))
    canvas.restoreState()


doc = BaseDocTemplate(
    OUT, pagesize=A4, leftMargin=LEFT, rightMargin=RIGHT,
    topMargin=TOP, bottomMargin=BOTTOM,
    title="Промежуточный отчёт — Умная AI-Теплица (Arduino Nano)",
    author="TriEblanaiPraktika",
)
frame = Frame(LEFT, BOTTOM, CONTENT_W, PAGE_H - TOP - BOTTOM, id="main")
doc.addPageTemplates([PageTemplate(id="page", frames=[frame], onPage=on_page)])
doc.build(build_story(_docx))
print("saved", OUT)
