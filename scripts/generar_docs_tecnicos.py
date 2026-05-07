"""Genera PDFs de la documentación técnica del proyecto.

Convierte los Markdown de docs/ y los del raíz (CHANGELOG, CONTRIBUTING,
Manual_Policia) a PDF con el mismo aspecto visual que los manuales
producidos por scripts/generar_manuales.py.

Salida (junto a cada Markdown):
  - docs/ARQUITECTURA.pdf
  - docs/API.pdf
  - docs/BASE_DE_DATOS.pdf
  - docs/DESPLIEGUE.pdf
  - docs/DESARROLLO.pdf
  - docs/SEGURIDAD.pdf
  - CHANGELOG.pdf
  - CONTRIBUTING.pdf
  - Manual_Policia.pdf (sobrescribe el del script de manuales si existe)

Uso:
  python scripts/generar_docs_tecnicos.py
"""
from __future__ import annotations

import re
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent.parent

# Paleta consistente con scripts/generar_manuales.py
PRIMARY = colors.HexColor("#1f4e79")
ACCENT = colors.HexColor("#d9a441")
LIGHT = colors.HexColor("#eef3f8")
DARK = colors.HexColor("#1b1b1b")
MUTED = colors.HexColor("#6c757d")
CODE_BG = colors.HexColor("#f4f4f6")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle("DocH1", parent=styles["Heading1"],
           textColor=PRIMARY, fontSize=22, spaceAfter=12, leading=26))
styles.add(ParagraphStyle("DocH2", parent=styles["Heading2"],
           textColor=PRIMARY, fontSize=15, spaceBefore=14, spaceAfter=8))
styles.add(ParagraphStyle("DocH3", parent=styles["Heading3"],
           textColor=DARK, fontSize=12, spaceBefore=8, spaceAfter=4))
styles.add(ParagraphStyle("DocBody", parent=styles["BodyText"],
           fontSize=10.5, leading=15, spaceAfter=6, alignment=4))
styles.add(ParagraphStyle("DocBullet", parent=styles["BodyText"],
           fontSize=10.5, leading=14, leftIndent=14, bulletIndent=2,
           spaceAfter=2))
styles.add(ParagraphStyle("DocCode", parent=styles["Code"],
           fontSize=9, leading=11.5, textColor=DARK, backColor=CODE_BG,
           borderPadding=6, leftIndent=0, rightIndent=0,
           spaceBefore=4, spaceAfter=8))
styles.add(ParagraphStyle("DocInlineCode", parent=styles["BodyText"],
           fontName="Courier", fontSize=10, leading=14))


# ── Conversión Markdown → flowables ─────────────────────────────────

_INLINE_CODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _inline_md_to_html(text: str) -> str:
    """Convierte una línea Markdown inline a HTML compatible con Paragraph."""
    out = escape(text, quote=False)
    # Restaurar entidades para que regex de markdown opere sobre ASCII normal
    out = out.replace("&amp;", "&")  # los & los re-escapamos al final si quedan
    # Código inline
    out = _INLINE_CODE.sub(
        lambda m: f'<font face="Courier" backColor="#f4f4f6">{escape(m.group(1))}</font>',
        out,
    )
    # Negrita y cursiva
    out = _BOLD.sub(r"<b>\1</b>", out)
    out = _ITALIC.sub(r"<i>\1</i>", out)
    # Enlaces
    out = _LINK.sub(r'<link href="\2" color="#1f4e79"><u>\1</u></link>', out)
    # Re-escapar &
    out = out.replace("&", "&amp;").replace("&amp;lt;", "&lt;").replace("&amp;gt;", "&gt;")
    out = out.replace("&amp;amp;", "&amp;").replace("&amp;quot;", "&quot;")
    return out


def _table_from_md(lines: list[str]) -> Table:
    """Construye una Table reportlab desde líneas Markdown |a|b|c| con
    fila de separación |---|---|---|. La primera línea es la cabecera."""
    rows: list[list[str]] = []
    for ln in lines:
        s = ln.strip().strip("|")
        if re.fullmatch(r"\s*:?-+:?\s*(\|\s*:?-+:?\s*)*", s):
            continue
        cells = [c.strip() for c in s.split("|")]
        rows.append([Paragraph(_inline_md_to_html(c), styles["DocBody"]) for c in cells])
    if not rows:
        return Spacer(0, 0)
    ncols = max(len(r) for r in rows)
    for r in rows:
        while len(r) < ncols:
            r.append(Paragraph("", styles["DocBody"]))
    # Anchuras simples: reparte el ancho útil entre columnas
    avail = (A4[0] - 4 * cm)
    col_widths = [avail / ncols] * ncols
    t = Table(rows, hAlign="LEFT", colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("BOX", (0, 0), (-1, -1), 0.3, MUTED),
        ("INNERGRID", (0, 0), (-1, -1), 0.2, MUTED),
    ]))
    return t


def md_to_flowables(md: str) -> list:
    """Conversor Markdown → flowables. Soporta:
    - # / ## / ### encabezados
    - párrafos
    - listas - / *
    - bloques de código ``` ... ```
    - tablas pipe-separated con fila de separación
    - código inline, **negrita**, *cursiva*, [enlace](url)
    """
    lines = md.splitlines()
    out: list = []
    i = 0
    paragraph_buf: list[str] = []
    list_buf: list[str] = []

    def flush_paragraph():
        if paragraph_buf:
            text = " ".join(paragraph_buf).strip()
            if text:
                out.append(Paragraph(_inline_md_to_html(text), styles["DocBody"]))
            paragraph_buf.clear()

    def flush_list():
        if list_buf:
            for item in list_buf:
                out.append(Paragraph(
                    f"• {_inline_md_to_html(item)}",
                    styles["DocBullet"],
                ))
            list_buf.clear()
            out.append(Spacer(1, 4))

    while i < len(lines):
        ln = lines[i]
        # Bloque de código
        if ln.strip().startswith("```"):
            flush_paragraph(); flush_list()
            i += 1
            code_lines: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # saltar cierre ```
            out.append(Preformatted("\n".join(code_lines), styles["DocCode"]))
            continue
        # Tabla: detecta línea con | y siguiente línea de separadores
        if "|" in ln and (i + 1) < len(lines) and re.match(
            r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$", lines[i + 1]
        ):
            flush_paragraph(); flush_list()
            tbl_lines = [ln]
            j = i + 1
            while j < len(lines) and "|" in lines[j]:
                tbl_lines.append(lines[j])
                j += 1
            out.append(_table_from_md(tbl_lines))
            out.append(Spacer(1, 6))
            i = j
            continue
        # Encabezados
        m = re.match(r"^(#{1,6})\s+(.*)$", ln)
        if m:
            flush_paragraph(); flush_list()
            level = len(m.group(1))
            txt = _inline_md_to_html(m.group(2).strip())
            style = styles["DocH1"] if level == 1 else (
                styles["DocH2"] if level == 2 else styles["DocH3"])
            out.append(Paragraph(txt, style))
            i += 1
            continue
        # Listas
        m = re.match(r"^\s*[-*+]\s+(.*)$", ln)
        if m:
            flush_paragraph()
            list_buf.append(m.group(1).strip())
            i += 1
            continue
        # Línea vacía → flush
        if ln.strip() == "":
            flush_paragraph(); flush_list()
            i += 1
            continue
        # Texto normal: acumula
        flush_list()
        paragraph_buf.append(ln.strip())
        i += 1

    flush_paragraph(); flush_list()
    return out


# ── Plantilla de documento (portada + cuerpo) ───────────────────────


def _cover_page(canvas, doc, title, subtitle):
    canvas.saveState()
    W, H = A4
    canvas.setFillColor(PRIMARY)
    canvas.rect(0, 0, W, H, stroke=0, fill=1)
    canvas.setFillColor(ACCENT)
    canvas.rect(0, H - 4 * cm, W, 0.4 * cm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 28)
    canvas.drawString(2 * cm, H - 7 * cm, title)
    canvas.setFont("Helvetica", 14)
    canvas.drawString(2 * cm, H - 8.2 * cm, subtitle)
    canvas.setFont("Helvetica", 10)
    canvas.drawString(2 * cm, 2 * cm, "Ayuntamiento de Navalcarnero")
    canvas.drawString(2 * cm, 1.5 * cm, "Censo Municipal de Animales")
    canvas.restoreState()


def _page_frame(canvas, doc):
    canvas.saveState()
    W, H = A4
    canvas.setFillColor(PRIMARY)
    canvas.rect(0, H - 1.4 * cm, W, 1.4 * cm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(2 * cm, H - 0.9 * cm,
                      "Censo Municipal de Animales · Navalcarnero")
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(W - 2 * cm, H - 0.9 * cm, doc.title)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8.5)
    canvas.drawString(2 * cm, 1.2 * cm,
                      "Documento técnico — uso interno del Ayuntamiento")
    canvas.drawRightString(W - 2 * cm, 1.2 * cm, f"Página {doc.page}")
    canvas.setStrokeColor(MUTED)
    canvas.setLineWidth(0.3)
    canvas.line(2 * cm, 1.45 * cm, W - 2 * cm, 1.45 * cm)
    canvas.restoreState()


def build_pdf(md_path: Path, pdf_path: Path, title: str, subtitle: str):
    md = md_path.read_text(encoding="utf-8")
    flow = md_to_flowables(md)
    doc = BaseDocTemplate(
        str(pdf_path), pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title=title, author="Ayuntamiento de Navalcarnero",
    )
    W, H = A4
    cover_frame = Frame(0, 0, W, H, id="cover",
                        leftPadding=0, rightPadding=0,
                        topPadding=0, bottomPadding=0)
    body_frame = Frame(2 * cm, 2 * cm, W - 4 * cm, H - 4 * cm, id="body")
    doc.addPageTemplates([
        PageTemplate(id="Cover", frames=[cover_frame],
                     onPage=lambda c, d: _cover_page(c, d, title, subtitle)),
        PageTemplate(id="Body", frames=[body_frame], onPage=_page_frame),
    ])
    story = [NextPageTemplate("Body"), PageBreak()]
    story.extend(flow)
    doc.build(story)


def main() -> None:
    SUB = "Censo Municipal de Animales · Navalcarnero"
    items = [
        # (md, pdf, título)
        (ROOT / "docs" / "ARQUITECTURA.md",     ROOT / "docs" / "ARQUITECTURA.pdf",     "Arquitectura del sistema"),
        (ROOT / "docs" / "API.md",              ROOT / "docs" / "API.pdf",              "Referencia de la API"),
        (ROOT / "docs" / "BASE_DE_DATOS.md",    ROOT / "docs" / "BASE_DE_DATOS.pdf",    "Base de datos"),
        (ROOT / "docs" / "DESPLIEGUE.md",       ROOT / "docs" / "DESPLIEGUE.pdf",       "Despliegue"),
        (ROOT / "docs" / "DESARROLLO.md",       ROOT / "docs" / "DESARROLLO.pdf",       "Guía de desarrollo"),
        (ROOT / "docs" / "SEGURIDAD.md",        ROOT / "docs" / "SEGURIDAD.pdf",        "Seguridad y privacidad"),
        (ROOT / "CHANGELOG.md",                 ROOT / "CHANGELOG.pdf",                 "Changelog"),
        (ROOT / "CONTRIBUTING.md",              ROOT / "CONTRIBUTING.pdf",              "Guía de contribución"),
        (ROOT / "Manual_Policia.md",            ROOT / "Manual_Policia.pdf",            "Manual del Agente de Policía"),
    ]
    for md, pdf, title in items:
        if not md.is_file():
            print(f"[skip] {md} no existe")
            continue
        build_pdf(md, pdf, title, SUB)
        print(f"[ok]   {pdf}")


if __name__ == "__main__":
    main()
