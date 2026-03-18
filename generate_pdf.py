"""
generate_pdf.py
───────────────
Converts the raw HTML notes content into a polished, branded PDF
matching the Anuj Jindal design reference.

Brand colours:
  Blue  #1B71AC
  Green #2AB573

Header logo : https://anujjindal.in/wp-content/uploads/2022/05/LOGO-FULL-01.png
Watermark   : https://anujjindal.in/wp-content/uploads/2023/02/LOGO-CROP.png
              550 × 550 px, 20 % opacity

Usage:
    python generate_pdf.py [--input <html_file>] [--output <pdf_file>]

"""

import io
import os
import sys
import argparse
import textwrap
import urllib.request
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, Image, PageBreak
)
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Brand constants ──────────────────────────────────────────────────────────
BLUE  = colors.HexColor("#1B71AC")
GREEN = colors.HexColor("#2AB573")
LIGHT_BLUE  = colors.HexColor("#E8F4FD")
LIGHT_GREEN = colors.HexColor("#E8F9F1")
LIGHT_YELLOW = colors.HexColor("#FFFBEA")
WHITE = colors.white
DARK_TEXT = colors.HexColor("#1A1A2E")
GREY_TEXT = colors.HexColor("#555555")
PAGE_BG   = colors.HexColor("#F9FAFB")

HEADER_LOGO_URL    = "https://anujjindal.in/wp-content/uploads/2022/05/LOGO-FULL-01.png"
WATERMARK_LOGO_URL = "https://anujjindal.in/wp-content/uploads/2023/02/LOGO-CROP.png"

SUBJECT  = "Economic and Social Issues"
CHAPTER  = "Economic Growth and Development"
PHONE    = "+91 9999466225"
WEBSITE  = "www.anujjindal.in"

PAGE_W, PAGE_H = A4          # 595.27 × 841.89 pt
MARGIN_H = 1.5 * cm
MARGIN_V = 1.5 * cm

# ── Image cache ──────────────────────────────────────────────────────────────
_IMAGE_CACHE: dict[str, bytes] = {}

def _fetch_image(url: str) -> bytes | None:
    if url in _IMAGE_CACHE:
        return _IMAGE_CACHE[url]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = r.read()
        _IMAGE_CACHE[url] = data
        return data
    except Exception as e:
        print(f"[WARN] Could not fetch {url}: {e}", file=sys.stderr)
        return None


def _pil_image(url: str):
    """Return a PIL Image or None."""
    from PIL import Image as PILImage
    data = _fetch_image(url)
    if data is None:
        return None
    return PILImage.open(io.BytesIO(data)).convert("RGBA")


# ── Styles ────────────────────────────────────────────────────────────────────
def _build_styles():
    base = getSampleStyleSheet()

    def s(name, **kw):
        return ParagraphStyle(name=name, **kw)

    return {
        # ── Body / headings ─────────────────────────────────
        "body": s("body",
            fontName="Helvetica", fontSize=9.5, leading=15,
            textColor=DARK_TEXT, spaceAfter=4, alignment=TA_JUSTIFY),

        "body_bullet": s("body_bullet",
            fontName="Helvetica", fontSize=9.5, leading=15,
            textColor=DARK_TEXT, leftIndent=14, firstLineIndent=-10,
            spaceAfter=3, alignment=TA_LEFT),

        "h1": s("h1",
            fontName="Helvetica-Bold", fontSize=16, leading=20,
            textColor=WHITE, alignment=TA_CENTER,
            spaceAfter=4, spaceBefore=6),

        "h2": s("h2",
            fontName="Helvetica-Bold", fontSize=12.5, leading=16,
            textColor=WHITE, alignment=TA_LEFT, spaceAfter=3),

        "h3": s("h3",
            fontName="Helvetica-Bold", fontSize=10.5, leading=14,
            textColor=BLUE, spaceAfter=3, spaceBefore=5),

        "h4": s("h4",
            fontName="Helvetica-Bold", fontSize=9.5, leading=13,
            textColor=GREEN, spaceAfter=2, spaceBefore=4),

        # ── Callout / knowledge nugget ───────────────────────
        "nugget_title": s("nugget_title",
            fontName="Helvetica-Bold", fontSize=10, leading=14,
            textColor=GREEN, spaceAfter=2),

        "nugget_body": s("nugget_body",
            fontName="Helvetica", fontSize=9, leading=13,
            textColor=DARK_TEXT, leftIndent=10, firstLineIndent=-8,
            spaceAfter=2, alignment=TA_LEFT),

        # ── Table cell ───────────────────────────────────────
        "cell": s("cell",
            fontName="Helvetica", fontSize=9, leading=13,
            textColor=DARK_TEXT, alignment=TA_LEFT),

        "cell_bold": s("cell_bold",
            fontName="Helvetica-Bold", fontSize=9, leading=13,
            textColor=DARK_TEXT, alignment=TA_LEFT),

        "cell_hdr": s("cell_hdr",
            fontName="Helvetica-Bold", fontSize=9.5, leading=13,
            textColor=WHITE, alignment=TA_CENTER),

        # ── Header / footer ──────────────────────────────────
        "header_subject": s("header_subject",
            fontName="Helvetica-Bold", fontSize=8, leading=11,
            textColor=WHITE, alignment=TA_RIGHT),

        "footer_txt": s("footer_txt",
            fontName="Helvetica", fontSize=8, leading=10,
            textColor=GREY_TEXT, alignment=TA_CENTER),
    }


# ── Page canvas decorator ─────────────────────────────────────────────────────
class _PageDecor:
    """Draws header, footer, background, and watermark on every page."""

    def __init__(self, header_logo_data: bytes | None,
                 watermark_data: bytes | None):
        self._hlogo = header_logo_data
        self._wm    = watermark_data

    def __call__(self, cv: pdfcanvas.Canvas, doc):
        cv.saveState()
        w, h = PAGE_W, PAGE_H

        # ── Subtle page background ──────────────────────────
        cv.setFillColor(PAGE_BG)
        cv.rect(0, 0, w, h, fill=1, stroke=0)

        # ── Header strip ────────────────────────────────────
        header_h = 1.35 * cm
        cv.setFillColor(BLUE)
        cv.rect(0, h - header_h, w, header_h, fill=1, stroke=0)

        # Green accent line below header
        cv.setFillColor(GREEN)
        cv.rect(0, h - header_h - 3, w, 3, fill=1, stroke=0)

        # Logo in header
        if self._hlogo:
            try:
                img = Image(io.BytesIO(self._hlogo))
                logo_h = header_h * 0.72
                logo_w = logo_h * 3.5   # approximate aspect
                img.drawWidth  = logo_w
                img.drawHeight = logo_h
                img.drawOn(cv, MARGIN_H, h - header_h + (header_h - logo_h) / 2)
            except Exception:
                pass

        # Subject / chapter text on the right of header
        from reportlab.platypus import Paragraph as P
        st = _build_styles()
        lines = f"<b>{SUBJECT}</b><br/>{CHAPTER}"
        p = P(lines, st["header_subject"])
        p.wrapOn(cv, 10 * cm, header_h)
        p.drawOn(cv, w - MARGIN_H - 10 * cm,
                 h - header_h + (header_h - p.height) / 2)

        # ── Footer strip ────────────────────────────────────
        footer_h = 0.9 * cm
        cv.setFillColor(BLUE)
        cv.rect(0, 0, w, footer_h, fill=1, stroke=0)
        cv.setFillColor(GREEN)
        cv.rect(0, footer_h, w, 2, fill=1, stroke=0)

        # Footer text
        cv.setFont("Helvetica", 8)
        cv.setFillColor(WHITE)
        cv.drawString(MARGIN_H, footer_h / 2 - 3,
                      f"{PHONE}   {WEBSITE}")
        cv.drawRightString(w - MARGIN_H, footer_h / 2 - 3,
                           f"Page {doc.page}")

        # ── Watermark ───────────────────────────────────────
        if self._wm:
            try:
                from PIL import Image as PILImage
                wm_img = PILImage.open(io.BytesIO(self._wm)).convert("RGBA")
                r, g, b, a = wm_img.split()
                a = a.point(lambda x: int(x * 0.20))  # 20 % opacity
                wm_img.putalpha(a)
                wm_buf = io.BytesIO()
                wm_img.save(wm_buf, format="PNG")
                wm_buf.seek(0)

                wm_size = 5 * cm     # drawn size on page
                cx = (w - wm_size) / 2
                cy = (h - wm_size) / 2
                cv.drawImage(
                    pdfcanvas.ImageReader(wm_buf),
                    cx, cy, width=wm_size, height=wm_size,
                    mask="auto"
                )
            except Exception as e:
                print(f"[WARN] Watermark error: {e}", file=sys.stderr)

        cv.restoreState()


# ── Content builders ──────────────────────────────────────────────────────────
def _section_heading(title: str, styles) -> list:
    """Blue full-width heading bar."""
    bg = Table(
        [[Paragraph(title, styles["h2"])]],
        colWidths=[PAGE_W - 2 * MARGIN_H],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BLUE),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
            ("ROUNDEDCORNERS", [4]),
        ])
    )
    return [Spacer(1, 6), bg, Spacer(1, 5)]


def _sub_heading(title: str, styles) -> list:
    return [Paragraph(title, styles["h3"]), Spacer(1, 2)]


def _bullet(text: str, styles, indent=0) -> Paragraph:
    prefix = "•  " if indent == 0 else "    ◦  "
    return Paragraph(f"{prefix}{text}", styles["body_bullet"])


def _nugget_box(title: str, items: list[str], styles) -> list:
    """Green-accented 'Knowledge Nugget' callout box."""
    content = [Paragraph(f"📌 {title}", styles["nugget_title"])]
    for item in items:
        content.append(Paragraph(f"•  {item}", styles["nugget_body"]))

    inner = Table(
        [[c] for c in content],
        colWidths=[PAGE_W - 2 * MARGIN_H - 22],
        style=TableStyle([
            ("TOPPADDING",    (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING",   (0, 0), (-1, -1), 4),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
        ])
    )

    outer = Table(
        [[inner]],
        colWidths=[PAGE_W - 2 * MARGIN_H],
        style=TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), LIGHT_GREEN),
            ("BOX",           (0, 0), (-1, -1), 1.5, GREEN),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("ROUNDEDCORNERS", [6]),
        ])
    )
    return [Spacer(1, 6), outer, Spacer(1, 6)]


def _comparison_table(headers: list[str], rows: list[list[str]], styles) -> list:
    """Styled comparison table with branded header row."""
    col_count = len(headers)
    col_w = (PAGE_W - 2 * MARGIN_H) / col_count

    data = [[Paragraph(h, styles["cell_hdr"]) for h in headers]]
    for row in rows:
        data.append([Paragraph(cell, styles["cell"]) for cell in row])

    tbl = Table(data, colWidths=[col_w] * col_count,
                repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  BLUE),
        ("BACKGROUND",    (0, 1), (-1, -1), WHITE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT_BLUE]),
        ("BOX",           (0, 0), (-1, -1), 0.8, BLUE),
        ("INNERGRID",     (0, 0), (-1, -1), 0.4, colors.HexColor("#C5DCF0")),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return [Spacer(1, 6), tbl, Spacer(1, 8)]


def _world_bank_table(styles) -> list:
    headers = ["Category", "GNI Per Capita Income (in US $)"]
    rows = [
        ["Low income", "$1,135 or less in 2022"],
        ["Low middle income", "$1,136 and $4,465"],
        ["Upper middle income", "$4,466 and $13,845"],
        ["High income", "$13,846 or more"],
    ]
    return _comparison_table(headers, rows, styles)


def _growth_vs_dev_table(styles) -> list:
    headers = ["Basis", "Economic Growth", "Economic Development"]
    rows = [
        ["Meaning",
         "Increase in output level sustained over time.",
         "Quantitative AND qualitative changes in the economy."],
        ["Parameters",
         "Rise in GDP or market productivity.",
         "Health, education, employment, gender, environment, etc."],
        ["Nature",
         "Quantitative changes only.",
         "Both quantitative and qualitative."],
        ["Scope", "Narrow.", "Broad."],
        ["Measurement",
         "GDP, GNP, etc.",
         "HDI, Gender Inequality Index, GDI, etc."],
    ]
    return _comparison_table(headers, rows, styles)


# ── Main content builder ──────────────────────────────────────────────────────
def _build_story(styles: dict, img_dir: Path) -> list:
    story = []
    add = story.append
    addl = story.extend

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 1 – Economic Growth
    # ════════════════════════════════════════════════════════════════════════
    addl(_section_heading("1.0  Economic Growth", styles))

    # 1.1 Meaning
    addl(_sub_heading("1.1  Meaning and Importance", styles))
    add(Paragraph(
        "Economic growth is an increase in the level of output of goods and "
        "services sustained over a long period of time, measured in terms of "
        "value added.", styles["body"]))
    add(Paragraph(
        "<b>Economic growth rate</b> = (Change in GDP) / (Last Year's GDP) × 100",
        styles["body"]))
    for pt in [
        "In economics, growth theory typically refers to growth of <b>potential output</b> "
        "(i.e., production at full employment).",
        "Economic growth is essentially a <b>dynamic concept</b> — a continuous expansion "
        "in the level of output.",
        "<b>Commodity Market:</b> Growth leads to increased output and newer, better products.",
        "<b>Factor Market:</b> Growth brings improvements in workforce skills and more "
        "efficient machinery.",
        "<b>Structural Shift:</b> Growth moves an economy from rural/agriculture-based to "
        "urban/industry-dominated.",
    ]:
        add(_bullet(pt, styles))
    add(Spacer(1, 4))

    # Types of growth – image
    img_path = img_dir / "Untitled.png"
    if img_path.exists():
        addl(_section_heading("Types of Economic Growth", styles))
        img = Image(str(img_path), width=PAGE_W - 2 * MARGIN_H - 40,
                    height=8 * cm, kind="proportional")
        add(img)
        add(Spacer(1, 6))

    # 1.2 Importance
    addl(_sub_heading("1.2  Importance of Economic Growth", styles))
    for pt in ["Poverty alleviation", "Wider availability for human choices and economic activities",
               "Resolves social issues", "Improves standard of living", "Better technology"]:
        add(_bullet(pt, styles))
    add(Spacer(1, 4))

    # 1.3 Factors
    addl(_sub_heading("1.3  Factors Affecting Economic Growth", styles))
    factors = [
        ("<b>Capital Formation (Investment)</b>",
         "More capital investment → more production → more economic growth."),
        ("<b>Capital-Output Ratio</b>",
         "Units of capital required to produce one unit of output. A <i>lower</i> ratio "
         "indicates higher efficiency, potentially freeing capital for further investment "
         "and spurring innovation."),
        ("<b>Occupational Structure</b>",
         "Efficient utilisation of labour boosts the overall productivity of the economy."),
        ("<b>Technological Progress</b>",
         "Technology enables more output from the same quantity of resources, boosting "
         "potential output."),
    ]
    for title, desc in factors:
        add(Paragraph(f"{title} — {desc}", styles["body"]))
    add(Spacer(1, 4))

    # 1.4 Limitations
    addl(_sub_heading("1.4  Limitations of Economic Growth", styles))
    for pt in [
        "<b>Inequality of Income</b> — In early development stages, growth tends to "
        "worsen income distribution.",
        "<b>Pollution and Negative Externalities</b> — Increased output pressures the "
        "environment, causing pollution and degradation.",
        "<b>Loss of Non-Renewable Resources</b> — More production demands more resources, "
        "depleting non-renewables.",
    ]:
        add(_bullet(pt, styles))

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 2 – Economic Development
    # ════════════════════════════════════════════════════════════════════════
    addl(_section_heading("2.0  Economic Development", styles))

    addl(_sub_heading("2.1  Meaning and Importance", styles))
    add(Paragraph(
        "Economic development refers to a sustained, long-term increase in the economic "
        "well-being, standard of living, and overall prosperity of a country or region. "
        "It is a <b>broader concept</b> that includes economic growth — without growth, "
        "development cannot happen.", styles["body"]))
    add(Paragraph(
        "It encompasses improvements beyond mere GDP growth: quality of life, poverty "
        "and inequality reduction, technology, infrastructure, education, healthcare, "
        "and social institutions.", styles["body"]))
    add(Spacer(1, 3))

    addl(_nugget_box("Importance of Economic Development", [
        "Improved Quality of Life",
        "Poverty Reduction",
        "Enhanced Human Capital",
        "Increased Employment",
        "Stimulated Innovation and Technological Advancement",
        "Infrastructure Development",
        "Social Stability and Equity",
        "Environmental Sustainability",
        "Institutional and Political Stability",
    ], styles))

    addl(_sub_heading("2.2  Evolution of Economic Development", styles))
    add(Paragraph(
        "Till the 1960s, economic development was often used as a synonym of economic "
        "growth. Over time, two different approaches emerged:", styles["body"]))
    for pt in [
        "<b>Traditional Approach</b> — Economic growth converts into economic development; "
        "believed in sustained annual GDP growth of 5–7%; structural transformation from "
        "agrarian to industrial economy.",
        "<b>Modern Approach</b> — Measures development on a broader, multidimensional level "
        "beyond GDP growth.",
    ]:
        add(_bullet(pt, styles))
    add(Spacer(1, 4))

    # Traditional approach image
    img_path = img_dir / "Untitled_1.png"
    if img_path.exists():
        addl(_sub_heading("2.3  Traditional Approach – Key Features", styles))
        img = Image(str(img_path), width=PAGE_W - 2 * MARGIN_H - 10,
                    height=6 * cm, kind="proportional")
        add(img)
        add(Spacer(1, 6))

    # Modern approach image
    for fname in ["Untitled_2.png", "Untitled_3.png"]:
        img_path = img_dir / fname
        if img_path.exists():
            img = Image(str(img_path), width=PAGE_W - 2 * MARGIN_H - 10,
                        height=6 * cm, kind="proportional")
            add(img)
            add(Spacer(1, 4))

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 3 – Growth vs Development
    # ════════════════════════════════════════════════════════════════════════
    addl(_section_heading("3.0  Economic Growth vs Economic Development", styles))
    addl(_growth_vs_dev_table(styles))

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 4 – Structural Changes
    # ════════════════════════════════════════════════════════════════════════
    addl(_section_heading("4.0  Economic Development and Structural Changes", styles))
    add(Paragraph(
        "Econometricians have attempted to measure structural changes in economies as "
        "development proceeds. Pioneering work was done by <b>Prof. Simon Kuznets</b> "
        "(historical data). <b>Hollis Chenery</b> extended and refined the study using "
        "current data.", styles["body"]))

    # Structural changes image
    for fname in ["Untitled_4.png", "Untitled_5.png"]:
        img_path = img_dir / fname
        if img_path.exists():
            img = Image(str(img_path), width=PAGE_W - 2 * MARGIN_H - 10,
                        height=5.5 * cm, kind="proportional")
            add(img)
            add(Spacer(1, 4))

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 5 – Indices
    # ════════════════════════════════════════════════════════════════════════
    addl(_section_heading("5.0  Indices to Measure Economic Development", styles))

    # ── 5.1 HDR ────────────────────────────────────────────────────────────
    addl(_sub_heading("5.1  Human Development Report & Its Components", styles))

    # HDI
    addl(_sub_heading("5.1.1  Human Development Index (HDI)", styles))
    hdi_data = [
        ("Origin", "1990"),
        ("Released by", "United Nations Development Programme (UNDP)"),
        ("Purpose", "Emphasise that people and their capabilities — not economic "
                    "growth alone — should be the ultimate criteria for assessing "
                    "a country's development."),
        ("Coverage", "191 countries (subject to change)"),
        ("Index range", "0 (lowest) to 1 (highest human development)"),
    ]
    for k, v in hdi_data:
        add(Paragraph(f"<b>{k}:</b>  {v}", styles["body"]))
    add(Spacer(1, 3))

    # HDI image
    for fname in ["Untitled_6.png"]:
        img_path = img_dir / fname
        if img_path.exists():
            img = Image(str(img_path), width=PAGE_W - 2 * MARGIN_H - 10,
                        height=6 * cm, kind="proportional")
            add(img)
            add(Spacer(1, 4))

    # IHDI
    addl(_sub_heading("5.1.2  Inequality-adjusted HDI (IHDI)", styles))
    for pt in [
        "<b>Origin:</b> 2010  |  <b>Released by:</b> UNDP",
        "Incorporates a <b>correction factor for inequality</b> within a country.",
        "While HDI measures average achievements, IHDI assesses the <i>distribution</i> "
        "of those achievements.",
        "Coverage is broadly the same as HDI, subject to data availability.",
    ]:
        add(_bullet(pt, styles))
    add(Spacer(1, 4))

    # GDI
    addl(_sub_heading("5.1.3  Gender Development Index (GDI)", styles))
    add(Paragraph("<b>Origin:</b> 1990  |  <b>Released by:</b> UNDP", styles["body"]))
    add(Paragraph("<b>Purpose:</b> Measure achievements across health, education, and "
                  "standard of living by gender.", styles["body"]))
    gdi_dims = [
        ["Dimension", "Female", "Male"],
        ["Health", "Life expectancy at birth", "Life expectancy at birth"],
        ["Education",
         "Expected & mean years of schooling",
         "Expected & mean years of schooling"],
        ["Economic Resources",
         "Estimated earned income",
         "Estimated earned income"],
    ]

    # GDI image
    img_path = img_dir / "Screenshot_20231211_153014.png"
    if img_path.exists():
        img = Image(str(img_path), width=PAGE_W - 2 * MARGIN_H - 10,
                    height=5.5 * cm, kind="proportional")
        add(img)
        add(Spacer(1, 4))

    # GII
    addl(_sub_heading("5.1.4  Gender Inequality Index (GII)", styles))
    add(Paragraph("<b>Origin:</b> 1990  |  <b>Released by:</b> UNDP", styles["body"]))
    add(Paragraph(
        "Reflects gender-based disadvantage in three dimensions: <b>reproductive "
        "health</b>, <b>empowerment</b>, and the <b>labour market</b>. Ranges from "
        "0 (equality) to 1 (maximum inequality). A lower value = better performance.",
        styles["body"]))
    for fname in ["Untitled_7.png", "Untitled_8.png"]:
        img_path = img_dir / fname
        if img_path.exists():
            img = Image(str(img_path), width=PAGE_W - 2 * MARGIN_H - 10,
                        height=5.5 * cm, kind="proportional")
            add(img)
            add(Spacer(1, 4))

    # GSNI
    addl(_sub_heading("5.1.5  Gender Social Norms Index (GSNI)", styles))
    for pt in [
        "<b>Origin:</b> 2019  |  <b>Released by:</b> UNDP",
        "Quantifies biases against women across four dimensions: political, "
        "educational, economic, and physical integrity.",
        "Coverage: 91 countries (subject to change).",
    ]:
        add(_bullet(pt, styles))
    add(Spacer(1, 4))

    # MPI
    addl(_sub_heading("5.1.6  Multidimensional Poverty Index (MPI)", styles))
    for pt in [
        "<b>Origin:</b> 2010  |  <b>Released by:</b> OPHI and UNDP",
        "Published annually in the Human Development Report.",
        "Shows <i>how</i> people are poor (not just who is poor) — "
        "covering all deprivations, identifying the poorest, and tracking "
        "policy effectiveness.",
        "Coverage: ~100 countries (subject to change).",
    ]:
        add(_bullet(pt, styles))

    for fname in ["Untitled_9.png", "Untitled_10.png"]:
        img_path = img_dir / fname
        if img_path.exists():
            img = Image(str(img_path), width=PAGE_W - 2 * MARGIN_H - 10,
                        height=5.5 * cm, kind="proportional")
            add(img)
            add(Spacer(1, 4))

    # ── 5.2 Other Indices ───────────────────────────────────────────────────
    addl(_sub_heading("5.2  Other Indices to Measure Economic Development", styles))

    other_indices = [
        ("5.2.1  Genuine Progress Indicator (GPI)",
         "Alternative to GDP; accounts for income distribution, environmental "
         "degradation, household/volunteer work, and social factors. No single "
         "central authority — calculated by independent research institutions."),
        ("5.2.2  World Happiness Index (WHI)",
         "Origin: 2012 | Released by: UN Sustainable Development Solutions Network. "
         "Judges country success by the happiness of people."),
        ("5.2.3  OECD Better Life Index",
         "Broader perspective beyond GDP. Doesn't provide a single ranking — "
         "users customise weights for 11 dimensions on the OECD website."),
        ("5.2.4  Physical Quality of Life Index (PQLI)",
         "Developed by economist Morris David Morris in the 1970s. Components: "
         "Basic Literacy Rate, Life Expectancy at Age 1, Infant Mortality Rate. "
         "Scores 0–100 (higher = better)."),
    ]
    for title, desc in other_indices:
        add(Paragraph(f"<b>{title}:</b>  {desc}", styles["body"]))
        add(Spacer(1, 3))

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 6 – Developed vs Developing
    # ════════════════════════════════════════════════════════════════════════
    addl(_section_heading("6.0  Developed vs Developing Economies", styles))

    addl(_sub_heading("6.1  Introduction", styles))
    add(Paragraph(
        "World Bank's World Development Report categorises economies into three "
        "groups: <b>high income</b>, <b>middle income</b>, and <b>low income</b>. "
        "High income = developed/advanced; low income = underdeveloped. Developing "
        "economies are underdeveloped but show high growth potential.",
        styles["body"]))
    add(Spacer(1, 3))

    addl(_sub_heading("6.2  Income-based Classification (World Bank 2024)", styles))
    addl(_world_bank_table(styles))

    addl(_sub_heading("6.2.2  Development-based Classification", styles))
    for pt in [
        "<b>Developed Country (MEDC)</b> — Sovereign state with developed economy and "
        "advanced technological infrastructure. Example: USA.",
        "<b>Developing Country</b> — Less industrialised, based on primary activities but "
        "thriving toward services/mass production. Examples: China, India.",
        "<b>Least Developed Countries (LDCs)</b> — Low-income with severe structural "
        "impediments and high vulnerability. Examples: Somalia, Sudan.",
    ]:
        add(_bullet(pt, styles))
    add(Spacer(1, 4))

    addl(_sub_heading("6.3  Common Characteristics of Developing Countries", styles))
    chars = [
        "Low GNP Per Capita", "Scarcity of Capital",
        "Rapid population growth and high dependency burden",
        "Low Levels of Productivity", "Technological Backwardness",
        "High Levels of Unemployment", "Low Human Wellbeing",
        "Wide Income Inequality", "High Poverty",
        "Agrarian Economy", "Low Participation in Foreign Trade",
    ]
    for c in chars:
        add(_bullet(c, styles))

    for fname in ["Untitled_11.png", "Untitled_12.png"]:
        img_path = img_dir / fname
        if img_path.exists():
            img = Image(str(img_path), width=PAGE_W - 2 * MARGIN_H - 10,
                        height=6 * cm, kind="proportional")
            add(img)
            add(Spacer(1, 4))

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 7 – Composite Development Index
    # ════════════════════════════════════════════════════════════════════════
    addl(_section_heading("7.0  Composite Development Index", styles))
    add(Paragraph(
        "The <b>Raghuram Rajan Committee</b> (2013) submitted its report on a new "
        "<b>Underdevelopment Index</b> called the Composite Development Index, designed "
        "to determine the underdevelopment of Indian states.",
        styles["body"]))
    add(Paragraph(
        "The index has <b>10 sub-components</b>, each carrying equal weightage:",
        styles["body"]))
    sub_comps = [
        "Monthly per-capita consumption expenditure",
        "Education",
        "Health",
        "Household amenities",
        "Poverty rate",
        "Female literacy",
        "Percentage of SC/ST population",
        "Urbanisation rate",
        "Financial inclusion",
        "Connectivity",
    ]
    for i, sc in enumerate(sub_comps, 1):
        add(Paragraph(f"  {i}.  {sc}", styles["body_bullet"]))

    addl(_nugget_box("Remember", [
        "Economic Growth is a subset of Economic Development.",
        "HDI = Health + Education + Standard of Living.",
        "A lower GII value indicates better gender equality.",
        "PQLI was the first composite alternative to GDP.",
        "Raghuram Rajan Committee (2013) → Composite Development Index for Indian states.",
    ], styles))

    add(Spacer(1, 10))
    add(HRFlowable(width="100%", thickness=1.5, color=GREEN))
    add(Spacer(1, 4))
    add(Paragraph(
        f"<i>Subject: {SUBJECT}  |  Chapter: {CHAPTER}</i>",
        ParagraphStyle("footer_note", fontName="Helvetica-Oblique",
                       fontSize=8, textColor=GREY_TEXT, alignment=TA_CENTER)))

    return story


# ── Entry-point ───────────────────────────────────────────────────────────────
def generate(output_path: str = "Economic_Growth_and_Development.pdf",
             img_dir: str | None = None) -> str:
    """
    Generate the PDF and return the output path.
    img_dir defaults to the directory of this script.
    """
    if img_dir is None:
        img_dir = Path(__file__).parent
    img_dir = Path(img_dir)

    print("[INFO] Fetching logo images …")
    header_logo_data  = _fetch_image(HEADER_LOGO_URL)
    watermark_data    = _fetch_image(WATERMARK_LOGO_URL)

    styles = _build_styles()
    story  = _build_story(styles, img_dir)

    decor = _PageDecor(header_logo_data, watermark_data)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN_H,
        rightMargin=MARGIN_H,
        topMargin=MARGIN_V + 1.5 * cm,   # extra for header strip
        bottomMargin=MARGIN_V + 1.0 * cm, # extra for footer strip
        title=f"{SUBJECT} – {CHAPTER}",
        author="Anuj Jindal",
        subject=CHAPTER,
    )

    print(f"[INFO] Building PDF → {output_path}")
    doc.build(story, onFirstPage=decor, onLaterPages=decor)
    print(f"[INFO] Done ✓  ({Path(output_path).stat().st_size // 1024} KB)")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate branded PDF from Economic Growth and Development notes.")
    parser.add_argument("--output", default="Economic_Growth_and_Development.pdf",
                        help="Output PDF path (default: Economic_Growth_and_Development.pdf)")
    parser.add_argument("--img-dir", default=None,
                        help="Directory containing the PNG images (default: script directory)")
    args = parser.parse_args()
    generate(args.output, args.img_dir)
