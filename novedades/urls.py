from django.urls import path

from . import views

app_name = "novedades"

urlpatterns = [
    path("", views.lista_novedades, name="novedad_list"),
    path("nuevo/", views.crear_novedad, name="novedad_crear"),
    path("detalle/<int:pk>/", views.novedad_detalle, name="novedad_detalle"),
    path("campos/", views.configuracion_campos, name="configuracion_campos"),
    path("campos/padre/<int:pk>/editar/", views.editar_campo_padre, name="editar_campo_padre"),
    path("campos/hijo/<int:pk>/editar/", views.editar_campo_hijo, name="editar_campo_hijo"),
    path("campos/subopcion/<int:pk>/editar/", views.editar_subopcion_campo, name="editar_subopcion_campo"),
]