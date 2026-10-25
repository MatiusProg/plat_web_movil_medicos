"""US-26 — La receta en PDF, con los datos de la organización y del médico.

Es un documento que sale del sistema —se imprime, se lleva a la farmacia, se
manda por WhatsApp—, así que lleva lo que lo hace verificable y nada más:

- **Quién la emite:** la organización (razón social, NIT, sucursal) y el
  médico con su matrícula.
- **Para quién:** nombre, documento y edad del paciente.
- **Qué:** los medicamentos, las órdenes y las indicaciones de la atención.
- **Cuándo y con qué firma:** la firma electrónica del encuentro (US-24), con
  fecha y hora. Lo que se imprime es lo firmado; por eso no hay PDF de un
  borrador.

**No lleva el diagnóstico.** La receta la lee el farmacéutico y cualquiera a
quien el paciente se la pase; el diagnóstico es de la historia clínica y se
queda ahí.

Las enmiendas a la receta o a las órdenes (US-24) **sí van**, al final y con
su autor: una receta corregida que se imprime sin la corrección dice algo que
el médico ya rectificó.

``reportlab`` se importa dentro de la función, por la misma razón que en
``reporting/exporters.py``.
"""

import datetime as dt
import io
from html import escape
from zoneinfo import ZoneInfo

from reporting.exporters import slugify


def _local(encounter, momento):
    tz = ZoneInfo(encounter.branch.timezone or "America/La_Paz")
    return momento.astimezone(tz)


def _edad(nacimiento, dia):
    if nacimiento is None:
        return None
    return dia.year - nacimiento.year - (
        (dia.month, dia.day) < (nacimiento.month, nacimiento.day)
    )


def filename(encounter) -> str:
    fecha = _local(encounter, encounter.appointment.starts_at).strftime("%Y-%m-%d")
    return f"receta-{fecha}-{slugify(encounter.patient.last_name or 'paciente')}.pdf"


def render(encounter) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )

    org = encounter.organization
    paciente = encounter.patient
    medico = encounter.practitioner
    sucursal = encounter.branch
    atendido = _local(encounter, encounter.appointment.starts_at)
    firmado = _local(encounter, encounter.signed_at)

    salida = io.BytesIO()
    documento = SimpleDocTemplate(
        salida, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=18 * mm,
        title=f"Receta · {paciente.full_name}", author=org.name,
    )

    estilos = getSampleStyleSheet()
    color_marca = colors.HexColor(org.primary_color or "#0F766E")
    gris = colors.HexColor("#6B7280")
    normal = ParagraphStyle("normal", parent=estilos["Normal"], fontSize=9.5, leading=13)
    pequeno = ParagraphStyle("pequeno", parent=normal, fontSize=8, leading=10.5, textColor=gris)
    titulo = ParagraphStyle("titulo", parent=estilos["Title"], fontSize=16,
                            leading=20, alignment=0, spaceAfter=2, textColor=color_marca)
    seccion = ParagraphStyle("seccion", parent=normal, fontName="Helvetica-Bold",
                             fontSize=10.5, spaceBefore=10, spaceAfter=4,
                             textColor=color_marca)
    celda = ParagraphStyle("celda", parent=normal, fontSize=9, leading=11.5)
    celda_titulo = ParagraphStyle("celda_titulo", parent=celda,
                                  fontName="Helvetica-Bold", textColor=colors.white)

    def p(texto, estilo=normal):
        return Paragraph(escape(str(texto)).replace("\n", "<br/>"), estilo)

    def tabla(encabezados, filas, anchos):
        datos = [[p(h, celda_titulo) for h in encabezados]]
        datos += [[p(v, celda) for v in fila] for fila in filas]
        t = Table(datos, colWidths=[documento.width * a for a in anchos], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), color_marca),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#F9FAFB")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return t

    emisor = " · ".join(filter(None, [
        org.legal_name, f"NIT {org.tax_id}" if org.tax_id else "",
    ]))
    sede = " · ".join(filter(None, [sucursal.name, sucursal.address, sucursal.phone]))
    historia = [
        p(org.name, ParagraphStyle("org", parent=normal, fontName="Helvetica-Bold",
                                   fontSize=12, leading=15)),
        p(emisor, pequeno),
        p(sede, pequeno),
        Spacer(1, 6 * mm),
        p("Receta médica", titulo),
        p(f"Atención del {atendido.strftime('%d/%m/%Y %H:%M')}", pequeno),
        Spacer(1, 4 * mm),
    ]

    edad = _edad(paciente.birth_date, atendido.date())
    datos_paciente = [
        ["Paciente", paciente.full_name],
        ["Documento", paciente.document_number or "—"],
        ["Edad", f"{edad} años" if edad is not None else "—"],
        ["Médico", f"{medico.full_name} · Matrícula {medico.license_number}"
         if medico.license_number else medico.full_name],
    ]
    cabecera = Table(
        [[p(k, pequeno), p(v)] for k, v in datos_paciente],
        colWidths=[documento.width * 0.18, documento.width * 0.82],
    )
    cabecera.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    historia.append(cabecera)

    medicamentos = list(encounter.prescription_items.all())
    if medicamentos:
        historia.append(p("Rp/ Medicamentos", seccion))
        historia.append(tabla(
            ["Medicamento", "Dosis", "Frecuencia", "Duración", "Indicaciones"],
            [[m.medication, m.dose, m.frequency, m.duration, m.instructions or "—"]
             for m in medicamentos],
            [0.28, 0.14, 0.18, 0.14, 0.26],
        ))

    ordenes = list(encounter.orders.all())
    if ordenes:
        historia.append(p("Órdenes de laboratorio y estudios", seccion))
        historia.append(tabla(
            ["Tipo", "Estudio", "Observaciones"],
            [[o.get_kind_display(), o.description, o.notes or "—"] for o in ordenes],
            [0.2, 0.45, 0.35],
        ))

    if encounter.indications.strip():
        historia.append(p("Indicaciones", seccion))
        historia.append(p(encounter.indications.strip()))

    enmiendas = [a for a in encounter.amendments.all()
                 if a.section in ("prescription", "orders", "indications")]
    if enmiendas:
        historia.append(p("Correcciones posteriores a la firma", seccion))
        for a in enmiendas:
            cuando = _local(encounter, a.created_at).strftime("%d/%m/%Y %H:%M")
            historia.append(p(f"{a.get_section_display()} — {a.author.full_name}, {cuando}", pequeno))
            historia.append(p(a.text))
            historia.append(Spacer(1, 2 * mm))

    historia += [
        Spacer(1, 14 * mm),
        p(f"Firmado electrónicamente por {encounter.signed_by.full_name} "
          f"el {firmado.strftime('%d/%m/%Y a las %H:%M')}.", normal),
        p(f"Código de la atención: {encounter.id}", pequeno),
    ]

    generado = dt.datetime.now(ZoneInfo(sucursal.timezone or "America/La_Paz"))
    pie = f"{org.name} · generado el {generado.strftime('%d/%m/%Y %H:%M')}"

    def dibujar_pie(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(gris)
        canvas.drawString(18 * mm, 10 * mm, pie[:150])
        canvas.drawRightString(doc.pagesize[0] - 18 * mm, 10 * mm,
                               f"Página {canvas.getPageNumber()}")
        canvas.restoreState()

    documento.build(historia, onFirstPage=dibujar_pie, onLaterPages=dibujar_pie)
    return salida.getvalue()
