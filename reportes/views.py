from django.shortcuts import render
from django.http import HttpResponse

from .forms import CargaDocumentoForm, SeleccionReporteForm
from .models import DocumentoCargado
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


def carga_interactiva_view(request):
    cargados = []
    if request.method == 'POST':
        form = CargaDocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            tipo = form.cleaned_data['tipo']
            descripcion = form.cleaned_data['descripcion']
            archivos = request.FILES.getlist('archivos')

            for archivo in archivos:
                DocumentoCargado.objects.create(
                    archivo=archivo,
                    tipo=tipo,
                    descripcion=descripcion,
                    nombre_original=archivo.name,
                )
                cargados.append(archivo.name)

            form = CargaDocumentoForm()
    else:
        form = CargaDocumentoForm()

    recientes = DocumentoCargado.objects.all()[:6]
    context = {
        'form': form,
        'cargados': cargados,
        'recientes': recientes,
    }
    return render(request, 'reportes/carga_interactiva.html', context)