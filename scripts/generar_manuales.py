"""Genera manuales PDF ilustrados para cada rol del Censo Municipal de Animales.

Salida:
  - Manual_Administrador.pdf
  - Manual_Empleado.pdf
  - Manual_Policia.pdf
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent.parent

# ---------- Paleta / estilos ----------

PRIMARY = colors.HexColor("#1f4e79")
ACCENT = colors.HexColor("#d9a441")
LIGHT = colors.HexColor("#eef3f8")
DARK = colors.HexColor("#1b1b1b")
MUTED = colors.HexColor("#6c757d")
OK = colors.HexColor("#2e7d32")
WARN = colors.HexColor("#c62828")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle("H1", parent=styles["Heading1"],
           textColor=PRIMARY, fontSize=22, spaceAfter=12, leading=26))
styles.add(ParagraphStyle("H2", parent=styles["Heading2"],
           textColor=PRIMARY, fontSize=15, spaceBefore=14, spaceAfter=8))
styles.add(ParagraphStyle("H3", parent=styles["Heading3"],
           textColor=DARK, fontSize=12, spaceBefore=8, spaceAfter=4))
styles.add(ParagraphStyle("Body", parent=styles["BodyText"],
           fontSize=10.5, leading=15, spaceAfter=6, alignment=4))
styles.add(ParagraphStyle("Callout", parent=styles["BodyText"],
           fontSize=10, leading=14, textColor=DARK,
           backColor=LIGHT, borderColor=PRIMARY, borderWidth=0.5,
           borderPadding=8, spaceBefore=6, spaceAfter=10))
styles.add(ParagraphStyle("Cover", parent=styles["Title"],
           textColor=colors.white, fontSize=32, leading=38))
styles.add(ParagraphStyle("CoverSub", parent=styles["Normal"],
           textColor=colors.white, fontSize=14, leading=18))
styles.add(ParagraphStyle("Caption", parent=styles["Italic"],
           fontSize=9, textColor=MUTED, alignment=1, spaceAfter=8))

# ---------- Ilustraciones (Flowables con dibujo vectorial) ----------


class Illustration(Flowable):
    """Flowable base que dibuja sobre el canvas con un tamaño dado."""

    def __init__(self, width, height, caption=""):
        super().__init__()
        self.width = width
        self.height = height
        self.caption = caption

    def wrap(self, *_):
        return self.width, self.height

    def draw(self):
        raise NotImplementedError


def _box(c, x, y, w, h, title, fill=LIGHT, stroke=PRIMARY, text_color=DARK, font_size=9):
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(0.8)
    c.roundRect(x, y, w, h, 4, stroke=1, fill=1)
    c.setFillColor(text_color)
    c.setFont("Helvetica-Bold", font_size)
    c.drawCentredString(x + w / 2, y + h / 2 - font_size / 3, title)


def _arrow(c, x1, y1, x2, y2, color=PRIMARY):
    from reportlab.lib.colors import toColor  # noqa: F401
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(1.2)
    c.line(x1, y1, x2, y2)
    # punta
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    size = 5
    c.setLineJoin(1)
    p = c.beginPath()
    p.moveTo(x2, y2)
    p.lineTo(x2 - size * math.cos(ang - math.pi / 7),
             y2 - size * math.sin(ang - math.pi / 7))
    p.lineTo(x2 - size * math.cos(ang + math.pi / 7),
             y2 - size * math.sin(ang + math.pi / 7))
    p.close()
    c.drawPath(p, stroke=0, fill=1)


class LoginFlow(Illustration):
    """Diagrama del flujo de inicio de sesión."""

    def __init__(self, rol="empleado"):
        super().__init__(16 * cm, 6 * cm, f"Fig. Flujo de inicio de sesión ({rol})")
        self.rol = rol

    def draw(self):
        c = self.canv
        y = 3.2 * cm
        w, h = 3.2 * cm, 1.4 * cm
        gap = 0.4 * cm
        x = 0
        labels = ["Abrir URL", "Login", "Contraseña OK", "Panel"]
        colors_ = [LIGHT, LIGHT, colors.HexColor("#fff4d6"), LIGHT]
        for i, (lbl, fl) in enumerate(zip(labels, colors_)):
            _box(c, x, y, w, h, lbl, fill=fl)
            if i < len(labels) - 1:
                _arrow(c, x + w + 1, y + h / 2, x + w + gap - 1, y + h / 2)
            x += w + gap
        # Ramas inferiores
        _box(c, 3.6 * cm, 0.4 * cm, 3.2 * cm, 1.2 * cm,
             "Fallo 5 veces → bloqueo", fill=colors.HexColor("#fde8e8"), stroke=WARN)
        _box(c, 7.2 * cm, 0.4 * cm, 3.2 * cm, 1.2 * cm,
             "1er login → cambiar clave", fill=colors.HexColor("#fff4d6"), stroke=ACCENT)
        _arrow(c, 5 * cm, y, 5 * cm, 1.6 * cm, color=WARN)
        _arrow(c, 8.6 * cm, y, 8.6 * cm, 1.6 * cm, color=ACCENT)


class ScreenWireframe(Illustration):
    """Mockup de una pantalla con cabecera, menú lateral y contenido."""

    def __init__(self, title, tabs, active_tab=0, content_blocks=None, caption=""):
        super().__init__(16 * cm, 9 * cm, caption or f"Fig. Pantalla: {title}")
        self.title = title
        self.tabs = tabs
        self.active = active_tab
        self.blocks = content_blocks or ["Filtros", "Tabla / listado", "Acciones"]

    def draw(self):
        c = self.canv
        W, H = self.width, self.height
        # Marco ventana
        c.setStrokeColor(MUTED)
        c.setLineWidth(0.6)
        c.setFillColor(colors.white)
        c.roundRect(0, 0, W, H, 6, stroke=1, fill=1)
        # Barra superior
        c.setFillColor(PRIMARY)
        c.rect(0, H - 0.9 * cm, W, 0.9 * cm, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(0.3 * cm, H - 0.6 * cm, "Censo Municipal de Animales")
        c.setFont("Helvetica", 8)
        c.drawRightString(W - 0.3 * cm, H - 0.6 * cm, "usuario ▾   Salir")
        # Menú lateral
        menu_w = 3.6 * cm
        c.setFillColor(LIGHT)
        c.rect(0, 0, menu_w, H - 0.9 * cm, stroke=0, fill=1)
        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColor(DARK)
        for i, t in enumerate(self.tabs):
            ty = H - 1.4 * cm - i * 0.55 * cm
            if i == self.active:
                c.setFillColor(ACCENT)
                c.rect(0, ty - 0.18 * cm, menu_w, 0.5 * cm, stroke=0, fill=1)
                c.setFillColor(colors.white)
            else:
                c.setFillColor(DARK)
            c.drawString(0.35 * cm, ty, f"• {t}")
        # Título del contenido
        c.setFillColor(PRIMARY)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(menu_w + 0.4 * cm, H - 1.5 * cm, self.title)
        # Bloques de contenido
        by = H - 2.3 * cm
        for i, blk in enumerate(self.blocks):
            bh = 1.4 * cm if i > 0 else 0.9 * cm
            _box(c, menu_w + 0.4 * cm, by - bh, W - menu_w - 0.8 * cm, bh,
                 blk, fill=colors.HexColor("#fafbfc"), stroke=MUTED, font_size=9)
            by -= bh + 0.25 * cm
            if by < 0.4 * cm:
                break


class Architecture(Illustration):
    """Diagrama: navegador → nginx → api → mariadb, con volúmenes."""

    def __init__(self):
        super().__init__(16 * cm, 6.5 * cm, "Fig. Arquitectura de servicios")

    def draw(self):
        c = self.canv
        y = 3.5 * cm
        _box(c, 0, y, 2.8 * cm, 1.4 * cm, "Navegador", fill=LIGHT)
        _arrow(c, 2.8 * cm, y + 0.7 * cm, 3.6 * cm, y + 0.7 * cm)
        _box(c, 3.6 * cm, y, 2.8 * cm, 1.4 * cm, "nginx\n(80 / 8181)", fill=LIGHT)
        _arrow(c, 6.4 * cm, y + 0.7 * cm, 7.2 * cm, y + 0.7 * cm)
        _box(c, 7.2 * cm, y, 2.8 * cm, 1.4 * cm, "API Flask", fill=colors.HexColor("#fff4d6"), stroke=ACCENT)
        _arrow(c, 10 * cm, y + 0.7 * cm, 10.8 * cm, y + 0.7 * cm)
        _box(c, 10.8 * cm, y, 3 * cm, 1.4 * cm, "MariaDB", fill=LIGHT)
        # volúmenes
        _box(c, 7.2 * cm, 0.4 * cm, 2.8 * cm, 1.2 * cm, "logs/", fill=colors.HexColor("#eef7ee"), stroke=OK)
        _box(c, 10.8 * cm, 0.4 * cm, 3 * cm, 1.2 * cm, "db/backups/", fill=colors.HexColor("#eef7ee"), stroke=OK)
        _arrow(c, 8.6 * cm, y, 8.6 * cm, 1.6 * cm, color=OK)
        _arrow(c, 12.3 * cm, y, 12.3 * cm, 1.6 * cm, color=OK)
        # etiqueta
        c.setFillColor(MUTED)
        c.setFont("Helvetica-Oblique", 8)
        c.drawString(0, y + 1.7 * cm, "Puerto 80 = empleado/policía     Puerto 8181 = administrador (solo localhost)")


class MobileMock(Illustration):
    """Mockup de teléfono con panel de policía."""

    def __init__(self):
        super().__init__(16 * cm, 8 * cm, "Fig. Panel de policía en móvil (PWA)")

    def draw(self):
        c = self.canv
        # Teléfono
        phx, phy, phw, phh = 1 * cm, 0.3 * cm, 5 * cm, 7.4 * cm
        c.setStrokeColor(DARK)
        c.setFillColor(colors.HexColor("#222"))
        c.setLineWidth(1.2)
        c.roundRect(phx, phy, phw, phh, 10, stroke=1, fill=1)
        # pantalla
        sx, sy, sw, sh = phx + 0.25 * cm, phy + 0.7 * cm, phw - 0.5 * cm, phh - 1.4 * cm
        c.setFillColor(colors.white)
        c.rect(sx, sy, sw, sh, stroke=0, fill=1)
        # barra
        c.setFillColor(PRIMARY)
        c.rect(sx, sy + sh - 0.7 * cm, sw, 0.7 * cm, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(sx + 0.15 * cm, sy + sh - 0.5 * cm, "Policía Municipal")
        # caja chip
        c.setFillColor(LIGHT)
        c.rect(sx + 0.2 * cm, sy + sh - 1.6 * cm, sw - 0.4 * cm, 0.7 * cm, stroke=0, fill=1)
        c.setFillColor(DARK)
        c.setFont("Helvetica", 7)
        c.drawString(sx + 0.3 * cm, sy + sh - 1.35 * cm, "Buscar por chip…")
        # resultado simulado
        c.setFillColor(colors.HexColor("#eef7ee"))
        c.rect(sx + 0.2 * cm, sy + 0.6 * cm, sw - 0.4 * cm, sh - 2.6 * cm, stroke=0, fill=1)
        c.setFillColor(OK)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(sx + 0.3 * cm, sy + sh - 2.4 * cm, "Animal encontrado")
        c.setFillColor(DARK)
        c.setFont("Helvetica", 7)
        lines = ["Chip: 941000023456789", "Propietario: García López", "Especie: Perro  Raza: Labrador",
                 "Vacuna: 2025-11-04 OK", "Seguro: Vigente", " ", "[ Registrar incidencia ]"]
        for i, ln in enumerate(lines):
            c.drawString(sx + 0.3 * cm, sy + sh - 2.8 * cm - i * 0.3 * cm, ln)
        # Texto lateral explicativo
        tx = 7 * cm
        c.setFillColor(PRIMARY)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(tx, 6.8 * cm, "La app es instalable (PWA)")
        c.setFillColor(DARK)
        c.setFont("Helvetica", 9)
        bullets = [
            "• Chrome/Edge (Android) → menú → \"Instalar aplicación\"",
            "• Safari (iOS) → Compartir → \"Añadir a pantalla de inicio\"",
            "• Icono directo al panel de policía",
            "• Consultas recientes disponibles sin conexión",
            "• Registrar incidencias requiere red",
        ]
        for i, b in enumerate(bullets):
            c.drawString(tx, 5.9 * cm - i * 0.55 * cm, b)


class RoleMatrix(Illustration):
    """Matriz de permisos por rol."""

    def __init__(self, highlight):
        super().__init__(16 * cm, 7.5 * cm, "Fig. Matriz de permisos por rol")
        self.highlight = highlight

    def draw(self):
        c = self.canv
        roles = ["Admin", "Empleado", "Policía"]
        funcs = [
            ("Alta / modificación de propietarios", [1, 1, 0]),
            ("Alta / modificación de animales", [1, 1, 0]),
            ("Baja de animal", [1, 1, 0]),
            ("Seguros (pólizas)", [1, 1, 0]),
            ("Consulta por chip / DNI", [1, 1, 1]),
            ("Registro de incidencias", [1, 0, 1]),
            ("Gestión de cuentas y backups", [1, 0, 0]),
            ("Auditoría y logs", [1, 0, 0]),
        ]
        col_w = [8 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm]
        row_h = 0.7 * cm
        x0, y0 = 0, self.height - row_h
        # cabecera
        c.setFillColor(PRIMARY)
        c.rect(0, y0, sum(col_w), row_h, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x0 + 0.2 * cm, y0 + 0.22 * cm, "Funcionalidad")
        for i, r in enumerate(roles):
            cx = col_w[0] + sum(col_w[1:i + 1]) + col_w[i + 1] / 2
            c.drawCentredString(cx, y0 + 0.22 * cm, r)
        # filas
        c.setFont("Helvetica", 9.5)
        for idx, (fname, perms) in enumerate(funcs):
            y = y0 - (idx + 1) * row_h
            c.setFillColor(LIGHT if idx % 2 == 0 else colors.white)
            c.rect(0, y, sum(col_w), row_h, stroke=0, fill=1)
            c.setFillColor(DARK)
            c.drawString(x0 + 0.2 * cm, y + 0.22 * cm, fname)
            for i, p in enumerate(perms):
                cx = col_w[0] + sum(col_w[1:i + 1]) + col_w[i + 1] / 2
                is_hl = roles[i].lower().startswith(self.highlight.lower())
                if p:
                    c.setFillColor(OK if is_hl else DARK)
                    c.setFont("Helvetica-Bold", 11)
                    c.drawCentredString(cx, y + 0.22 * cm, "✓")
                else:
                    c.setFillColor(MUTED)
                    c.setFont("Helvetica", 10)
                    c.drawCentredString(cx, y + 0.22 * cm, "—")
                c.setFont("Helvetica", 9.5)
        # bordes
        c.setStrokeColor(MUTED)
        c.setLineWidth(0.4)
        total_h = row_h * (len(funcs) + 1)
        c.rect(0, y0 + row_h - total_h, sum(col_w), total_h, stroke=1, fill=0)


class BackupTimeline(Illustration):
    def __init__(self):
        super().__init__(16 * cm, 5 * cm, "Fig. Ciclo de backups automáticos")

    def draw(self):
        c = self.canv
        # línea de tiempo
        c.setStrokeColor(PRIMARY)
        c.setLineWidth(1.2)
        y = 2.5 * cm
        c.line(0.5 * cm, y, 15.5 * cm, y)
        # marcas
        marks = [("04:00", "Backup"),
                 ("+1 día", "Backup"),
                 ("+30 días", "Borrado auto"),
                 ("Restaurar", "Crea pre-restore")]
        xs = [1 * cm, 5 * cm, 10 * cm, 14 * cm]
        for (t, lbl), x in zip(marks, xs):
            c.setFillColor(PRIMARY)
            c.circle(x, y, 0.15 * cm, stroke=0, fill=1)
            c.setFont("Helvetica-Bold", 9)
            c.setFillColor(DARK)
            c.drawCentredString(x, y + 0.5 * cm, t)
            c.setFont("Helvetica", 8.5)
            c.setFillColor(MUTED)
            c.drawCentredString(x, y - 0.6 * cm, lbl)
        c.setFillColor(DARK)
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(0, 0.3 * cm, "Formato: backup_YYYY-MM-DD_HHMMSS.sql.gz  ·  Retención: 30 días  ·  Ubicación: db/backups/")


class IncidentFlow(Illustration):
    def __init__(self):
        super().__init__(16 * cm, 5 * cm, "Fig. Registro de una incidencia")

    def draw(self):
        c = self.canv
        steps = ["Buscar chip", "Ver ficha", "Registrar\nincidencia", "Tipo +\ndescripción", "Guardado\n(auditoría)"]
        w, h = 2.8 * cm, 1.8 * cm
        gap = 0.25 * cm
        x = 0
        y = 1.6 * cm
        for i, s in enumerate(steps):
            _box(c, x, y, w, h, "", fill=LIGHT)
            c.setFillColor(DARK)
            c.setFont("Helvetica-Bold", 9)
            for j, line in enumerate(s.split("\n")):
                c.drawCentredString(x + w / 2, y + h / 2 + 0.25 * cm - j * 0.35 * cm, line)
            if i < len(steps) - 1:
                _arrow(c, x + w, y + h / 2, x + w + gap - 0.05 * cm, y + h / 2)
            x += w + gap
        c.setFillColor(MUTED)
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(0, 0.4 * cm,
                     "Cada incidencia queda asociada al chip y al animal, y se registra en la auditoría.")


# ---------- Construcción del documento ----------


def _cover_page(canvas, doc, title, subtitle, rol):
    canvas.saveState()
    W, H = A4
    canvas.setFillColor(PRIMARY)
    canvas.rect(0, 0, W, H, stroke=0, fill=1)
    # Banda acento
    canvas.setFillColor(ACCENT)
    canvas.rect(0, H - 4 * cm, W, 0.4 * cm, stroke=0, fill=1)
    # Título
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 30)
    canvas.drawString(2 * cm, H - 7 * cm, title)
    canvas.setFont("Helvetica", 16)
    canvas.drawString(2 * cm, H - 8.2 * cm, subtitle)
    # Badge rol
    canvas.setFillColor(ACCENT)
    canvas.roundRect(2 * cm, H - 10.2 * cm, 6 * cm, 1.3 * cm, 6, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawCentredString(5 * cm, H - 9.45 * cm, f"Rol: {rol}")
    # Pie
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica", 10)
    canvas.drawString(2 * cm, 2 * cm, "Ayuntamiento de Navalcarnero")
    canvas.drawString(2 * cm, 1.5 * cm, "Censo Municipal de Animales")
    canvas.restoreState()


def _page_frame(canvas, doc):
    canvas.saveState()
    W, H = A4
    # Cabecera
    canvas.setFillColor(PRIMARY)
    canvas.rect(0, H - 1.4 * cm, W, 1.4 * cm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(2 * cm, H - 0.9 * cm, "Censo Municipal de Animales · Navalcarnero")
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(W - 2 * cm, H - 0.9 * cm, doc.title)
    # Pie
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8.5)
    canvas.drawString(2 * cm, 1.2 * cm, "Documento interno — uso exclusivo del personal municipal")
    canvas.drawRightString(W - 2 * cm, 1.2 * cm, f"Página {doc.page}")
    canvas.setStrokeColor(MUTED)
    canvas.setLineWidth(0.3)
    canvas.line(2 * cm, 1.45 * cm, W - 2 * cm, 1.45 * cm)
    canvas.restoreState()


def build_doc(path, title, subtitle, rol, story_fn):
    doc = BaseDocTemplate(
        str(path), pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title=title, author="Ayuntamiento de Navalcarnero",
    )
    W, H = A4
    cover_frame = Frame(0, 0, W, H, id="cover",
                        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    body_frame = Frame(2 * cm, 2 * cm, W - 4 * cm, H - 4 * cm, id="body")
    doc.addPageTemplates([
        PageTemplate(id="Cover", frames=[cover_frame],
                     onPage=lambda c, d: _cover_page(c, d, title, subtitle, rol)),
        PageTemplate(id="Body", frames=[body_frame], onPage=_page_frame),
    ])
    story = [Spacer(1, 1), PageBreak()]  # salto tras portada
    # cambio a plantilla Body
    from reportlab.platypus import NextPageTemplate
    story = [NextPageTemplate("Body"), PageBreak()]
    story.extend(story_fn())
    doc.build(story)


def P(t, style="Body"):
    return Paragraph(t, styles[style])


def section(title, level=2):
    return P(title, f"H{level}")


def callout(text):
    return Paragraph(f"<b>ℹ</b> {text}", styles["Callout"])


def caption(fig):
    return Paragraph(fig.caption, styles["Caption"])


def bullets(items):
    html = "".join(f"• {it}<br/>" for it in items)
    return Paragraph(html, styles["Body"])


def pretty_table(data, header=True):
    t = Table(data, hAlign="LEFT", colWidths=[5 * cm, 10 * cm])
    ts = TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9.5),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("BOX", (0, 0), (-1, -1), 0.3, MUTED),
        ("INNERGRID", (0, 0), (-1, -1), 0.2, MUTED),
    ])
    t.setStyle(ts)
    return t


# ---------- Contenidos por rol ----------


ADMIN_TABS = ["Inicio", "Propietarios", "Animales", "Seguros", "Baja animal",
              "Estadísticas", "Logs", "Auditoría", "Agentes", "Empleados",
              "Backups", "Consulta"]
EMPLEADO_TABS = ["Inicio", "Propietarios", "Animales", "Seguros",
                 "Baja animal", "Consulta", "Estadísticas"]
POLICIA_TABS = ["Panel policía", "Consulta chip", "Incidencias"]


def story_admin():
    s = []
    s += [section("Manual del Administrador", 1),
          P("Este manual describe el uso completo del Censo Municipal de Animales "
            "para el rol <b>administrador</b>: acceso, gestión de cuentas, auditoría, "
            "backups y mantenimiento. Incluye ilustraciones de cada pantalla y flujo.")]
    s += [section("1. Acceso"),
          P("El panel de administrador se sirve en <b>http://localhost:8181</b>, "
            "accesible <b>solo desde el propio equipo servidor</b> (nginx lo escucha "
            "en 127.0.0.1). El resto de usuarios entra por el puerto 80."),
          Architecture(), caption(Architecture()),
          section("1.1 Primer arranque", 3),
          P("Si no hay contraseña configurada, al entrar aparece el modal "
            "<b>\"Crear contraseña de administrador\"</b> (mínimo 6 caracteres)."),
          section("1.2 Inicio de sesión y bloqueos", 3),
          bullets([
              "Casilla <b>\"Recordar sesión\"</b> → dura 1 año en ese navegador.",
              "5 intentos fallidos en 5 minutos → bloqueo temporal.",
              "20 intentos fallidos por IP → bloqueo de esa IP.",
          ]),
          LoginFlow("admin"), caption(LoginFlow("admin"))]

    s += [PageBreak(), section("2. Estructura del panel"),
          P("El menú lateral izquierdo da acceso a cada pestaña. La cabecera muestra "
            "el usuario y el botón <b>Salir</b>."),
          ScreenWireframe("Auditoría", ADMIN_TABS, active_tab=7,
                          content_blocks=["Filtros: fecha, rol, acción, usuario, IP",
                                          "Tabla cronológica de eventos",
                                          "Acciones: Ver JSON · Descargar auditoria.jsonl"],
                          caption="Fig. Pantalla Auditoría (menú lateral completo del administrador)"),
          caption(ScreenWireframe("Auditoría", ADMIN_TABS))]

    s += [section("2.1 Resumen de pestañas", 3),
          pretty_table([
              ["Pestaña", "Uso"],
              ["Inicio", "Resumen y alertas del sistema"],
              ["Propietarios", "Alta, consulta, gestión de direcciones"],
              ["Animales", "Alta, modificación, vacunas, esterilizado, seguro"],
              ["Seguros", "Pólizas asociadas a chip"],
              ["Baja de animal", "Bajas por motivo, muerte o traslado"],
              ["Estadísticas", "Gráficos agregados"],
              ["Logs", "Ficheros de log del servidor"],
              ["Auditoría", "Eventos con diff antes/después"],
              ["Agentes", "Cuentas de policía"],
              ["Empleados", "Cuentas nominales de empleado"],
              ["Backups", "Copias de seguridad de la BD"],
              ["Consulta", "Buscador transversal por DNI, chip o nombre"],
          ])]

    s += [PageBreak(), section("3. Gestión de usuarios"),
          P("El administrador es el <b>único</b> que puede crear, restablecer o "
            "desactivar cuentas. Empleados y policías solo se autogestionan la "
            "contraseña."),
          RoleMatrix("admin"), caption(RoleMatrix("admin")),
          section("3.1 Empleados", 3),
          bullets([
              "Crear cuenta: usuario, nombre, contraseña inicial temporal.",
              "El empleado <b>debe</b> cambiar la contraseña al primer inicio de sesión.",
              "Restablecer contraseña → vuelve a forzar cambio.",
              "Activar/desactivar → una cuenta desactivada no puede entrar.",
              "Tras 6 meses sin iniciar sesión, bloqueo automático por inactividad.",
          ]),
          section("3.2 Agentes de policía", 3),
          P("Misma gestión que empleados. Los agentes acceden por el puerto público "
            "pulsando <b>\"Acceso de Policía Municipal\"</b> en la pantalla de login."),
          section("3.3 Recuperación de contraseña", 3),
          P("Cuando un usuario pulsa <b>\"¿Olvidaste tu contraseña?\"</b>, la "
            "solicitud se registra (acción <b>solicitud_recuperacion</b>). El "
            "administrador debe restablecer la contraseña manualmente desde la "
            "pestaña correspondiente.")]

    s += [PageBreak(), section("4. Auditoría"),
          P("La pestaña <b>Auditoría</b> registra todas las acciones que alteran "
            "datos o cuentas, con diff antes/después para modificaciones de animal."),
          bullets([
              "Creación, modificación y baja de propietarios y animales.",
              "Gestión de cuentas (crear, modificar, eliminar, bloquear).",
              "Backups (manual, automático, restauración, eliminación).",
              "Solicitudes de recuperación de contraseña.",
              "Bloqueos por inactividad o intentos fallidos.",
          ]),
          callout("Filtros disponibles: fecha, rol, acción, usuario, IP. "
                  "Botón <b>Ver</b> muestra el JSON completo; <b>Descargar</b> "
                  "exporta el fichero <i>auditoria.jsonl</i>.")]

    s += [section("5. Backups"),
          BackupTimeline(), caption(BackupTimeline()),
          P("Copia automática diaria a las <b>04:00</b>, retención <b>30 días</b>, "
            "formato <b>backup_YYYY-MM-DD_HHMMSS.sql.gz</b>."),
          pretty_table([
              ["Botón", "Efecto"],
              ["Crear ahora", "Ejecuta un backup inmediato."],
              ["Actualizar", "Refresca el listado."],
              ["Descargar", "Descarga el .sql.gz al equipo."],
              ["Restaurar", "Sobrescribe la BD con el backup elegido."],
              ["Eliminar", "Borra el archivo del servidor."],
          ]),
          callout("Antes de restaurar, el sistema crea automáticamente un "
                  "<b>backup pre-restore</b>. La confirmación exige escribir "
                  "literalmente la palabra <b>RESTAURAR</b>.")]

    s += [PageBreak(), section("6. Logs y estadísticas"),
          P("Los logs del servidor se rotan diariamente (<b>log_YYYY-MM-DD.txt</b>, "
            "retención 90 días). La auditoría se guarda aparte en "
            "<b>auditoria.jsonl</b>."),
          P("La pestaña <b>Estadísticas</b> muestra gráficos agregados (razas, "
            "edad, estado vivo/baja, esterilizados, cobertura de seguro, "
            "nacimientos por año) con filtros opcionales.")]

    s += [section("7. Mantenimiento"),
          pretty_table([
              ["Comando", "Descripción"],
              ["docker compose up -d --build", "Arrancar / reconstruir"],
              ["docker compose down", "Parar"],
              ["docker compose logs -f api", "Seguir logs del backend"],
              ["docker compose restart api", "Reiniciar solo el backend"],
              ["python -m pytest", "Ejecutar tests"],
          ]),
          callout("Al actualizar el backend: <b>docker compose up -d --build api</b>.")]

    s += [section("8. Seguridad"),
          bullets([
              "Hashing <b>bcrypt</b> (rounds=12). SHA-256 antiguos migran al primer login.",
              "Rate limit: 5 fallos por usuario y 20 por IP en 5 minutos.",
              "Bloqueo por inactividad (6 meses) e intentos fallidos consecutivos.",
              "Tokens: 8 h sin \"recordar\", 1 año con \"recordar\". Revocables reiniciando la API.",
              "Path traversal y nombres inválidos rechazados en endpoints de archivos.",
              "Separación por puertos: 8181 solo localhost; 80 para resto.",
          ])]
    return s


def story_empleado():
    s = []
    s += [section("Manual del Empleado", 1),
          P("Esta guía explica, paso a paso y con ilustraciones, cómo usar el "
            "Censo Municipal de Animales con el rol <b>empleado</b>: alta y "
            "modificación de propietarios, animales, seguros y bajas, además de "
            "consultas y estadísticas.")]

    s += [section("1. Acceso"),
          P("Desde cualquier equipo de la red municipal, abre "
            "<b>http://&lt;IP-del-servidor&gt;</b>. En la pantalla de login: "
            "usuario + contraseña. No uses el enlace de Policía Municipal."),
          LoginFlow("empleado"), caption(LoginFlow("empleado")),
          section("1.1 Primer inicio y cambio de contraseña", 3),
          bullets([
              "Al primer acceso <b>debes cambiar</b> la contraseña temporal.",
              "Mínimo 8 caracteres, con mayúscula, minúscula, número y carácter especial.",
              "Caduca cada 365 días; se te pedirá cambiarla al iniciar sesión.",
          ]),
          callout("Marcando <b>\"Recordar sesión\"</b> la sesión dura hasta un año "
                  "en ese dispositivo. Sin marcar, se cierra al cerrar el navegador."),
          section("1.2 Bloqueos automáticos", 3),
          bullets([
              "5 intentos fallidos en 5 minutos → bloqueo temporal.",
              "6 meses sin iniciar sesión → bloqueo por inactividad.",
              "En ambos casos contacta con el administrador.",
          ])]

    s += [PageBreak(), section("2. Estructura del panel"),
          P("La cabecera tiene un <b>buscador global</b> (DNI, chip o nombre) y "
            "el menú de usuario con <b>Cambiar contraseña</b> y <b>Salir</b>. "
            "El menú lateral da acceso a cada pestaña."),
          ScreenWireframe("Propietarios", EMPLEADO_TABS, active_tab=1,
                          content_blocks=["Formulario: DNI/NIE, apellidos, nombre, teléfonos",
                                          "Direcciones asociadas (varias por propietario)",
                                          "Botones: Guardar · Consultar"],
                          caption="Fig. Pantalla Propietarios"),
          caption(ScreenWireframe("Propietarios", EMPLEADO_TABS)),
          RoleMatrix("empleado"), caption(RoleMatrix("empleado"))]

    s += [PageBreak(), section("3. Propietarios"),
          bullets([
              "<b>Alta</b>: DNI/NIE, apellidos, nombre, teléfonos, direcciones.",
              "<b>Consulta</b>: requiere criterio previo (DNI, chip o nombre). "
              "No se listan datos completos sin búsqueda, por protección de datos.",
              "<b>Direcciones</b>: un propietario puede tener varias asociadas.",
          ])]

    s += [section("4. Animales"),
          ScreenWireframe("Animales", EMPLEADO_TABS, active_tab=2,
                          content_blocks=["Datos: chip, especie, raza, sexo, año de nacimiento",
                                          "Estado: esterilizado, vacuna antirrábica",
                                          "Vínculos: propietario (DNI), nº censo, póliza"],
                          caption="Fig. Alta / modificación de animal"),
          caption(ScreenWireframe("Animales", EMPLEADO_TABS)),
          bullets([
              "<b>Alta</b>: chip, especie, raza, sexo, año de nacimiento, "
              "esterilizado, vacuna antirrábica, propietario (DNI), nº de censo, "
              "póliza opcional.",
              "<b>Modificación</b>: propietario, fecha de última vacuna, "
              "esterilizado, póliza. Cada cambio queda en auditoría con valor "
              "anterior y nuevo.",
              "<b>Consulta</b>: por chip o desde la ficha del propietario.",
          ])]

    s += [PageBreak(), section("5. Seguros"),
          P("Pestaña <b>Seguros</b>: alta y consulta de pólizas (compañía, "
            "número de póliza, vigencia). Las pólizas se enlazan al chip del "
            "animal en la pestaña <b>Animales</b>.")]

    s += [section("6. Baja de animal"),
          bullets([
              "Motivos: fallecimiento, traslado, pérdida, etc.",
              "Numeración automática: <b>BAJA-AAAA-####</b>.",
              "Queda registrada en auditoría.",
              "Las bajas <b>por edad avanzada</b> se ejecutan cada noche automáticamente.",
          ])]

    s += [section("7. Consulta global y estadísticas"),
          P("En la cabecera, escribe chip, DNI o nombre y selecciona el "
            "resultado para abrir la ficha correspondiente."),
          P("La pestaña <b>Estadísticas</b> ofrece gráficos agregados con filtros."),]

    s += [PageBreak(), section("8. Buenas prácticas"),
          bullets([
              "No compartas usuario ni contraseña: todas las acciones quedan a tu nombre.",
              "Pulsa <b>Salir</b> al terminar, sobre todo en equipos compartidos.",
              "Si sospechas un acceso indebido, avisa al administrador.",
              "Si ves <b>\"API sin conexión\"</b> en la cabecera, revisa la red o "
              "avisa al administrador.",
          ])]

    s += [section("9. Preguntas frecuentes"),
          pretty_table([
              ["Pregunta", "Respuesta"],
              ["¿Puedo cambiar mi contraseña cuando quiera?",
               "Sí, desde el menú de usuario (arriba derecha) → Cambiar contraseña."],
              ["¿Por qué me pide cambiarla otra vez?",
               "Han pasado 365 días o el administrador la ha restablecido."],
              ["¿Por qué no veo listados sin buscar?",
               "Los empleados solo acceden a datos tras un criterio de búsqueda, "
               "por protección de datos."],
              ["¿Qué hago si no recuerdo mi contraseña?",
               "Pulsa \"¿Olvidaste tu contraseña?\" e indica un motivo. El "
               "administrador la restablecerá."],
          ])]
    return s


def story_policia():
    s = []
    s += [section("Manual del Agente de Policía Municipal", 1),
          P("Guía del Censo Municipal de Animales para agentes de la Policía "
            "Municipal. Explica cómo consultar un animal por chip, registrar "
            "incidencias y usar la aplicación instalada en el móvil (PWA).")]

    s += [section("1. Acceso"),
          P("Desde un equipo o móvil de la red municipal, abre "
            "<b>http://&lt;IP-del-servidor&gt;</b>. En la pantalla de login pulsa "
            "el enlace inferior <b>\"Acceso de Policía Municipal\"</b> e introduce "
            "usuario + contraseña de agente."),
          LoginFlow("policía"), caption(LoginFlow("policía")),
          section("1.1 Primer inicio de sesión", 3),
          bullets([
              "Debes cambiar la contraseña temporal que te dio el administrador.",
              "Mínimo 8 caracteres: mayúscula, minúscula, número y carácter especial.",
              "Caduca cada 365 días.",
          ]),
          callout("<b>\"Recordar sesión\"</b> mantiene el acceso hasta un año en "
                  "ese dispositivo. Útil en un móvil personal de servicio; "
                  "<b>no la marques</b> en equipos compartidos."),
          section("1.2 Bloqueos", 3),
          bullets([
              "5 intentos fallidos en 5 minutos → bloqueo temporal.",
              "6 meses sin iniciar sesión → bloqueo por inactividad.",
              "Avisa al administrador para desbloquear o restablecer contraseña.",
          ])]

    s += [PageBreak(), section("2. Panel de policía"),
          P("Al iniciar sesión accedes <b>directamente</b> al panel. No tienes "
            "acceso a propietarios, animales, seguros ni bajas. Tus funciones son "
            "consulta y registro de incidencias."),
          ScreenWireframe("Panel policía", POLICIA_TABS, active_tab=0,
                          content_blocks=["Buscador por chip",
                                          "Ficha: propietario, vacunas, seguro",
                                          "Botón: Registrar incidencia"],
                          caption="Fig. Panel de policía en navegador"),
          caption(ScreenWireframe("Panel policía", POLICIA_TABS)),
          RoleMatrix("policía"), caption(RoleMatrix("policía"))]

    s += [PageBreak(), section("3. Consulta rápida por chip"),
          P("Escribe el chip del animal en el buscador del panel. El sistema "
            "muestra la <b>ficha pública</b> del animal: propietario, vacuna "
            "antirrábica, estado de esterilización y cobertura de seguro."),
          callout("Si el chip no existe o el animal está de baja, el panel lo "
                  "indica claramente. En ese caso, usa el botón de registrar "
                  "incidencia para dejar constancia de lo ocurrido.")]

    s += [section("4. Registro de incidencias"),
          IncidentFlow(), caption(IncidentFlow()),
          P("Desde la ficha del animal, pulsa <b>Registrar incidencia</b>. "
            "Rellena:"),
          bullets([
              "<b>Tipo</b> (mordedura, abandono, sin correa, otro…).",
              "<b>Descripción</b> del hecho.",
              "<b>Fecha y hora</b> (por defecto, la actual).",
              "<b>Agente</b> (se rellena con tu usuario automáticamente).",
          ]),
          P("Al guardar, la incidencia queda asociada al chip y al animal, y el "
            "evento se registra en la auditoría del sistema.")]

    s += [PageBreak(), section("5. Uso en el móvil — PWA"),
          MobileMock(), caption(MobileMock()),
          P("La aplicación se puede <b>instalar</b> como app nativa en Android o "
            "iOS. Ventajas: icono directo en pantalla de inicio y consultas "
            "recientes disponibles sin conexión."),
          pretty_table([
              ["Sistema", "Cómo instalar"],
              ["Android (Chrome/Edge)",
               "Abre la URL → menú del navegador → \"Instalar aplicación\"."],
              ["iOS (Safari)",
               "Abre la URL → Compartir → \"Añadir a pantalla de inicio\"."],
          ]),
          callout("Sin conexión funcionan las <b>consultas recientes</b> "
                  "(chips, propietarios, incidencias ya vistos). El <b>registro "
                  "de nuevas incidencias requiere conexión</b> al servidor.")]

    s += [section("6. Buenas prácticas"),
          bullets([
              "Cierra sesión (<b>Salir</b>) al terminar el turno si el terminal "
              "no es personal.",
              "No compartas tus credenciales: las incidencias quedan firmadas con tu usuario.",
              "Si pierdes el dispositivo donde está instalada la PWA, avisa al "
              "administrador para revocar la sesión.",
              "Si ves <b>\"API sin conexión\"</b> puedes seguir consultando lo "
              "reciente, pero no podrás registrar incidencias hasta recuperar la red.",
          ])]

    s += [section("7. Preguntas frecuentes"),
          pretty_table([
              ["Pregunta", "Respuesta"],
              ["¿Puedo dar de alta o modificar animales?",
               "No. Eso corresponde a los empleados. Tú solo consultas y registras incidencias."],
              ["¿Qué datos veo del propietario?",
               "Los estrictamente necesarios para la identificación del animal."],
              ["¿Puedo registrar una incidencia sin conexión?",
               "No; requiere conectividad. Consulta sí funciona offline si viste "
               "ese chip recientemente."],
              ["¿Cómo cambio mi contraseña?",
               "Menú de usuario → Cambiar contraseña. Cumple los requisitos de "
               "fortaleza."],
          ])]
    return s


def main():
    outputs = [
        ("Manual_Administrador.pdf", "Manual del Administrador",
         "Censo Municipal de Animales · Navalcarnero", "Administrador", story_admin),
        ("Manual_Empleado.pdf", "Manual del Empleado",
         "Censo Municipal de Animales · Navalcarnero", "Empleado", story_empleado),
        ("Manual_Policia.pdf", "Manual del Agente de Policía",
         "Censo Municipal de Animales · Navalcarnero", "Policía Municipal", story_policia),
    ]
    for fname, title, subtitle, rol, fn in outputs:
        out = ROOT / fname
        build_doc(out, title, subtitle, rol, fn)
        print(f"[ok] {out}")


if __name__ == "__main__":
    main()
