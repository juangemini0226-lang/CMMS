from django.urls import path
from .views import carga_interactiva_view, seleccionar_reporte_view

app_name = 'reportes'

urlpatterns = [
    path('seleccionar/', seleccionar_reporte_view, name='seleccionar_reporte'),
    path('cargas/', carga_interactiva_view, name='carga_interactiva'),
]