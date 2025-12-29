from django.urls import path
from . import views

# Validar presencia de vistas críticas para evitar errores de carga en runtime
eliminar_activo_view = getattr(views, 'eliminar_activo', None)
if eliminar_activo_view is None:
    raise ImportError('La vista "eliminar_activo" no está definida en activos.views')

app_name = 'activos'

urlpatterns = [
    # Dashboard
    path('', views.dashboard_activos, name='dashboard_activos'),

   # Configuración de jerarquía
    path('configurar-jerarquia/', views.configurar_jerarquia, name='configurar_jerarquia'),
    path('configurar-jerarquia/datos/', views.niveles_jerarquia_datos, name='niveles_jerarquia_datos'),
    path('plantillas/', views.gestionar_plantillas, name='gestionar_plantillas'),
    path('taxonomia-iso/', views.gestionar_taxonomia_iso, name='gestionar_taxonomia_iso'),
    # Gestión de activos
    path('arbol/', views.vista_arbol_activos, name='vista_arbol_activos'),
    path('crear/', views.crear_activo, name='crear_activo'),
    path('crear/<int:padre_id>/', views.crear_activo, name='crear_activo_hijo'),
    path('<int:activo_id>/', views.detalle_activo, name='detalle_activo'),
    path('<int:activo_id>/editar/', views.editar_activo, name='editar_activo'),
    path('<int:activo_id>/eliminar/', eliminar_activo_view, name='eliminar_activo'),

    # Familias y dependencias
    path('familias/', views.gestionar_familias, name='gestionar_familias'),
    path('seleccionar-familia/', views.seleccionar_familia, name='seleccionar_familia'),
    path('seleccionar-activo/<int:familia_id>/', views.seleccionar_activo, name='seleccionar_activo'),
    path('dependencias/<int:activo_id>/', views.lista_dependencias, name='lista_dependencias'),

    # Importación/Exportación Excel
    path('importar-excel/', views.importar_excel, name='importar_excel'),
    path('exportar-excel/', views.exportar_excel, name='exportar_excel'),
    path('plantilla-excel/', views.descargar_plantilla_excel, name='descargar_plantilla_excel'),

    # API JSON
    path('api/arbol/', views.api_arbol_activos, name='api_arbol_activos'),
    path('api/generar-tag/', views.api_generar_tag, name='api_generar_tag'),

]