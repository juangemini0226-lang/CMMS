from django.urls import path
from . import views

urlpatterns = [
    path('activos/pdf/', views.reporte_activos_pdf, name='reporte_activos_pdf'),
    # Aquí puedes agregar más reportes en el futuro
]
