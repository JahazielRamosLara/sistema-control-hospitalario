"""Generación del expediente clínico integral en PDF (macro CrearExpedientePacienteIntegral)."""
from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .config import settings
from .schemas import PacienteDetalle

COLOR_SEMAFORO = {
    "Verde": colors.HexColor("#2e7d32"),
    "Amarillo": colors.HexColor("#c79100"),
    "Naranja": colors.HexColor("#e65100"),
    "Rojo": colors.HexColor("#c62828"),
    "Vino": colors.HexColor("#6d1b2b"),
}
AZUL = colors.HexColor("#1f4e79")
CRITICO = colors.HexColor("#fde2e2")


def _f(fecha) -> str:
    return fecha.strftime("%d/%m/%Y") if fecha else "—"


def expediente_pdf(p: PacienteDetalle) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(letter),
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.3 * cm,
        bottomMargin=1.3 * cm,
        title=f"Expediente {p.expediente}",
        author=settings.nombre_hospital,
    )
    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle("t", parent=estilos["Title"], textColor=AZUL, fontSize=17, spaceAfter=2)
    sub = ParagraphStyle("s", parent=estilos["Normal"], fontSize=8.5, textColor=colors.grey, alignment=1)
    seccion = ParagraphStyle("sec", parent=estilos["Heading3"], textColor=colors.white, fontSize=10.5)
    celda = ParagraphStyle("c", parent=estilos["Normal"], fontSize=8, leading=10)
    celda_b = ParagraphStyle("cb", parent=celda, fontName="Helvetica-Bold", textColor=colors.white)

    def barra(texto: str):
        t = Table([[Paragraph(texto, seccion)]], colWidths=[doc.width])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), AZUL), ("LEFTPADDING", (0, 0), (-1, -1), 6)]))
        return t

    def pares(filas):
        data = [[Paragraph(f"<b>{a}</b>", celda), Paragraph(str(b), celda),
                 Paragraph(f"<b>{c}</b>", celda), Paragraph(str(d), celda)] for a, b, c, d in filas]
        t = Table(data, colWidths=[3.5 * cm, doc.width / 2 - 3.5 * cm, 3.5 * cm, doc.width / 2 - 3.5 * cm])
        t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                               ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        return t

    color_riesgo = COLOR_SEMAFORO.get(p.riesgo.semaforo, colors.black).hexval()[2:]
    historia = [
        Paragraph("EXPEDIENTE CLÍNICO INTEGRAL DEL PACIENTE", titulo),
        Paragraph(
            f"{settings.nombre_hospital} · Generado el {datetime.now():%d/%m/%Y %H:%M} · "
            "Documento confidencial — NOM-004-SSA3-2012",
            sub,
        ),
        Spacer(1, 10),
        barra("FICHA DE IDENTIFICACIÓN"),
        pares([
            ("Expediente:", p.expediente, "Edad:", f"{p.edad} años" if p.edad is not None else "—"),
            ("Paciente:", p.nombre, "Sexo:", p.sexo or "—"),
            ("Servicio:", p.servicio or "—", "Tipo de sangre:", p.tipo_sangre or "—"),
            ("Médico tratante:", p.medico_tratante or "—", "Alergias:", p.alergias or "—"),
            ("Contacto:", p.contacto_emergencia or "—", "Teléfono:", p.telefono or "—"),
        ]),
        Spacer(1, 8),
        barra("RESUMEN CLÍNICO"),
        pares([
            ("Total de atenciones:", len(p.atenciones), "Nivel de riesgo:",
             f'<font color="#{color_riesgo}"><b>{p.riesgo.nivel}</b></font>'),
            ("Eventos críticos:", p.riesgo.eventos_criticos, "Última atención:", _f(p.ultima_atencion)),
            ("Acción requerida:", p.riesgo.accion or "—", "Estado:", p.estado),
        ]),
        Spacer(1, 8),
        barra("HISTORIAL DE ATENCIONES"),
    ]

    encabezado = ["FECHA", "TIPO DE ATENCIÓN", "MÉDICO", "TURNO", "TRIAGE", "NOTA CLÍNICA / HALLAZGOS",
                  "PLAN DE MANEJO", "E.C."]
    anchos = [1.9, 3.3, 3.6, 2.0, 2.9, 6.6, 4.9, 0.9]
    escala = doc.width / (sum(anchos) * cm)
    filas = [[Paragraph(h, celda_b) for h in encabezado]]
    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    for i, a in enumerate(p.atenciones, start=1):
        filas.append([Paragraph(x or "", celda) for x in (
            _f(a.fecha), a.tipo_atencion, a.medico, a.turno, a.triage, a.nota_clinica, a.plan_manejo,
            "SÍ" if a.evento_critico else "")])
        if a.evento_critico:
            estilo.append(("BACKGROUND", (0, i), (-1, i), CRITICO))
    if not p.atenciones:
        filas.append([Paragraph("Sin atenciones registradas", celda)] + [""] * 7)
        estilo.append(("SPAN", (0, 1), (-1, 1)))
    tabla = Table(filas, colWidths=[w * cm * escala for w in anchos], repeatRows=1)
    tabla.setStyle(TableStyle(estilo))
    historia += [tabla, Spacer(1, 36),
                 Paragraph("_______________________________", celda),
                 Paragraph(f"Médico tratante: {p.medico_tratante or '—'}", celda)]

    def pie(canvas, d):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.grey)
        canvas.drawString(d.leftMargin, 0.7 * cm, f"Expediente {p.expediente} · {p.nombre}")
        canvas.drawRightString(d.pagesize[0] - d.rightMargin, 0.7 * cm, f"Página {d.page}")
        canvas.restoreState()

    doc.build(historia, onFirstPage=pie, onLaterPages=pie)
    return buf.getvalue()
