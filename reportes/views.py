from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from activos.models import NodoActivo, Organizacion
from datetime import datetime

def reporte_activos_pdf(request):
    organizacion = Organizacion.objects.first()
    nivel_id = request.GET.get('nivel')
    estado = request.GET.get('estado')
    activos = NodoActivo.objects.filter(organizacion=organizacion)
    if nivel_id:
        activos = activos.filter(nivel_jerarquia_id=nivel_id)
    if estado:
        activos = activos.filter(estado=estado)
    context = {
        'activos': activos,
        'organizacion': organizacion,
        'fecha_actual': datetime.now().strftime('%d/%m/%Y'),
    }
    html_string = render_to_string("reportes/reporte_activos.html", context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_activos.pdf"'
    HTML(string=html_string).write_pdf(response)
    return response
