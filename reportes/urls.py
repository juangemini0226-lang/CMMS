from django.urls import path
from .views import seleccionar_reporte_view

app_name = 'reportes'

urlpatterns = [
    path('seleccionar/', seleccionar_reporte_view, name='seleccionar_reporte'),
]
