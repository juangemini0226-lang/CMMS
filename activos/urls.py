from django.urls import path
from . import views

app_name = 'activos'

urlpatterns = [
    # Dashboard
    path('', views.dashboard_activos, name='dashboard_activos'),
    
    # Configuración de jerarquía
    path('configurar-jerarquia/', views.configurar_jerarquia, name='configurar_jerarquia'),
    
    # Gestión de activos
    path('arbol/', views.vista_arbol_activos, name='vista_arbol_activos'),
    path('crear/', views.crear_activo, name='crear_activo'),
    path('crear/<int:padre_id>/', views.crear_activo, name='crear_activo_hijo'),
    path('<int:activo_id>/', views.detalle_activo, name='detalle_activo'),
    path('<int:activo_id>/editar/', views.editar_activo, name='editar_activo'),
    path('<int:activo_id>/eliminar/', views.eliminar_activo, name='eliminar_activo'),
    
    # Importación/Exportación Excel
    path('importar-excel/', views.importar_excel, name='importar_excel'),
    path('exportar-excel/', views.exportar_excel, name='exportar_excel'),
    path('plantilla-excel/', views.descargar_plantilla_excel, name='descargar_plantilla_excel'),
    
    # API JSON
    path('api/arbol/', views.api_arbol_activos, name='api_arbol_activos'),
    path('api/generar-tag/', views.api_generar_tag, name='api_generar_tag'),

    path('seleccionar-familia/', views.seleccionar_familia, name='seleccionar_familia'),
    path('seleccionar-activo/<int:familia_id>/', views.seleccionar_activo, name='seleccionar_activo'),
    path('dependencias/<int:activo_id>/', views.lista_dependencias, name='lista_dependencias'),
    
]
