from django.shortcuts import render
from django.http import HttpResponse
from .forms import SeleccionReporteForm
from .utils import generar_reporte_activos, generar_reporte_taxonomia

def seleccionar_reporte_view(request):
    if request.method == 'POST':
        form = SeleccionReporteForm(request.POST)
        if form.is_valid():
            tipo = form.cleaned_data['tipo_reporte']
            if tipo == 'activos':
                pdf = generar_reporte_activos()
                nombre = 'reporte_activos.pdf'
            else:
                pdf = generar_reporte_taxonomia()
                nombre = 'reporte_taxonomia.pdf'

            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{nombre}"'
            return response
    else:
        form = SeleccionReporteForm()
    return render(request, 'reportes/seleccionar_reporte.html', {'form': form})
