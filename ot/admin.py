from django.contrib import admin

from .models import WorkOrder, WorkOrderAdjunto, WorkOrderEvento, WorkOrderEventoFoto


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ("codigo", "titulo", "estado", "prioridad", "equipo", "responsable")
    list_filter = ("estado", "prioridad")
    search_fields = ("titulo", "descripcion", "consecutivo")
    readonly_fields = ("consecutivo", "fecha_creacion", "fecha_actualizacion")


@admin.register(WorkOrderEvento)
class WorkOrderEventoAdmin(admin.ModelAdmin):
    list_display = ("orden", "estado", "creado_por", "creado_el")
    list_filter = ("estado",)
    search_fields = ("orden__titulo", "descripcion")


@admin.register(WorkOrderEventoFoto)
class WorkOrderEventoFotoAdmin(admin.ModelAdmin):
    list_display = ("evento", "creado_por", "creado_el")
    search_fields = ("evento__orden__titulo",)


@admin.register(WorkOrderAdjunto)
class WorkOrderAdjuntoAdmin(admin.ModelAdmin):
    list_display = ("orden", "creado_por", "creado_el")
    search_fields = ("orden__titulo",)