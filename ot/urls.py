from django.urls import path

from . import views

app_name = "ot"

urlpatterns = [
    path("", views.WorkOrderBoardView.as_view(), name="orden_list"),
    path("carga-masiva/", views.WorkOrderBulkUploadView.as_view(), name="orden_carga_masiva"),
     path("carga-masiva/plantilla/", views.descargar_plantilla_carga_masiva, name="orden_carga_masiva_plantilla",
    ),
    path("nueva/", views.WorkOrderCreateView.as_view(), name="orden_crear"),
    path(
        "desde-novedad/<int:novedad_id>/",
        views.WorkOrderCreateView.as_view(),
        name="orden_desde_novedad",
    ),
    path("<int:pk>/", views.WorkOrderDetailView.as_view(), name="orden_detalle"),
    path("<int:pk>/editar/", views.WorkOrderUpdateView.as_view(), name="orden_editar"),
    path(
        "<int:pk>/actualizar-estado/",
        views.actualizar_estado,
        name="orden_actualizar_estado",
    ),
]