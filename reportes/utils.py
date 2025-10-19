import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, black
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from activos.models import NodoActivo, ClaseEquipoISO14224
from django.contrib.staticfiles import finders


def dibujar_membrete(c, doc):
    c.saveState()
    ancho, alto = letter
    ruta_logo = "reportes/static/reportes/Logo.png"  # Ajustar ruta al logo en static

    color_gris_oscuro = HexColor('#363435')
    color_gris_claro = HexColor('#F0F0F0')
    color_rojo = HexColor('#E30613')

    c.setFillColor(color_gris_claro)
    c.rect(0, alto - 1*cm, ancho, 1*cm, fill=1, stroke=0)
    c.setFillColor(color_gris_oscuro)
    p = c.beginPath()
    p.moveTo(ancho, alto)
    p.lineTo(ancho, alto - 1.5*cm)
    p.lineTo(ancho - 11*cm, alto - 1.5*cm)
    p.curveTo(ancho - 11.3*cm, alto - 1.5*cm, ancho - 11.5*cm, alto - 1.4*cm, ancho - 11.6*cm, alto - 1.2*cm)
    p.lineTo(ancho - 12*cm, alto)
    p.close()
    c.drawPath(p, fill=1, stroke=0)

    color_gris = HexColor('#636363')
    c.setFillColor(color_gris_oscuro)
    c.rect(0, 0, ancho, 0.5*cm, fill=1, stroke=0)
    c.setFillColor(color_gris_claro)
    c.rect(0, 0.5*cm, ancho, 0.8*cm, fill=1, stroke=0)
    c.setFillColor(color_rojo)
    p_rojo = c.beginPath()
    p_rojo.moveTo(0, 0.5*cm)
    p_rojo.lineTo(0, 2*cm)
    p_rojo.lineTo(11.2*cm, 2*cm)
    p_rojo.curveTo(11.9*cm, 2*cm, 12.3*cm, 1.2*cm, 12.5*cm, 1.05*cm)
    p_rojo.lineTo(13.0*cm, 0.5*cm)
    p_rojo.close()
    c.drawPath(p_rojo, fill=1, stroke=0)

    try:
        c.drawImage(ruta_logo, 8.5*cm, 0.5*cm, width=3.5*cm, preserveAspectRatio=True, mask='auto')
    except:
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(black)
        c.drawCentredString(10.25*cm, 0.9*cm, "LOGO")

    c.setFont("Helvetica", 8)
    c.setFillColor(color_gris)
    c.drawString(13 * cm, 1*cm, "✆ 60 (4) 604 41 00   ⚲ Calle 30 No. 55-72 - Medellín, Colombia")

    c.setFont("Helvetica", 8)
    c.setFillColor(color_gris)
    c.drawRightString(ancho - 0.5*cm, 0.7*cm, f"Página {c.getPageNumber()}")

    c.restoreState()


def generar_reporte_activos():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=1.5*cm, bottomMargin=2.5*cm)
    elementos = []
    estilos = getSampleStyleSheet()

    titulo = Paragraph("Reporte de Activos", estilos['Title'])
    elementos.append(titulo)
    elementos.append(Spacer(1, 12))

    activos = NodoActivo.objects.all()[:50]

    data = [['Código', 'Nombre', 'Estado', 'Criticidad', 'Ubicación']]
    for a in activos:
        data.append([a.codigo, a.nombre, a.estado, a.criticidad, a.ubicacion_fisica])
    
    tabla = Table(data, colWidths=[70, 130, 70, 70, 130])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#d3d3d3')),
        ('GRID', (0, 0), (-1, -1), 0.5, black),
    ]))
    elementos.append(tabla)
    doc.build(elementos, onFirstPage=dibujar_membrete, onLaterPages=dibujar_membrete)

    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def generar_reporte_taxonomia():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=1.5*cm, bottomMargin=2.5*cm)
    elementos = []
    estilos = getSampleStyleSheet()

    titulo = Paragraph("Reporte de Taxonomía ISO 14224", estilos['Title'])
    elementos.append(titulo)
    elementos.append(Spacer(1, 12))

    clases = ClaseEquipoISO14224.objects.all()[:50]

    data = [['Código', 'Nombre', 'Nivel Taxonómico']]
    for c in clases:
        data.append([c.codigo, c.nombre, c.nivel_taxonomico])
    
    tabla = Table(data, colWidths=[100, 200, 100])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#d3d3d3')),
        ('GRID', (0, 0), (-1, -1), 0.5, black),
    ]))
    elementos.append(tabla)
    doc.build(elementos, onFirstPage=dibujar_membrete, onLaterPages=dibujar_membrete)

    pdf = buffer.getvalue()
    buffer.close()
    return pdf
