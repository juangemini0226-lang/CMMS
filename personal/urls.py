from django.urls import path

from . import views

app_name = "personal"

urlpatterns = [
    path("tecnicos/", views.TecnicoOperativoListView.as_view(), name="tecnico_list"),
    path("tecnicos/nuevo/", views.TecnicoOperativoCreateView.as_view(), name="tecnico_create"),
    path("tecnicos/<int:pk>/editar/", views.TecnicoOperativoUpdateView.as_view(), name="tecnico_update"),
    path("tecnicos/<int:pk>/eliminar/", views.TecnicoOperativoDeleteView.as_view(), name="tecnico_delete"),
    path("turnos/", views.TurnoListView.as_view(), name="turno_list"),
    path("turnos/nuevo/", views.TurnoCreateView.as_view(), name="turno_create"),
    path("turnos/<int:pk>/editar/", views.TurnoUpdateView.as_view(), name="turno_update"),
    path("turnos/<int:pk>/eliminar/", views.TurnoDeleteView.as_view(), name="turno_delete"),
    path("ausencias/", views.AusenciaListView.as_view(), name="ausencia_list"),
    path("ausencias/nueva/", views.AusenciaCreateView.as_view(), name="ausencia_create"),
    path("ausencias/<int:pk>/editar/", views.AusenciaUpdateView.as_view(), name="ausencia_update"),
    path("ausencias/<int:pk>/eliminar/", views.AusenciaDeleteView.as_view(), name="ausencia_delete"),
    path("agenda/resumen/", views.AgendaResumenView.as_view(), name="agenda_resumen"),
]