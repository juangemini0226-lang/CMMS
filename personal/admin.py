from django.contrib import admin

from .models import Ausencia, TecnicoOperativo, Turno


@admin.register(TecnicoOperativo)
class TecnicoOperativoAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "perfil",
        "numero_identificacion",
        "especialidad",
        "estado",
        "fecha_ingreso",
    )
    search_fields = ("user__username", "user__first_name", "user__last_name", "numero_identificacion", "especialidad")
    list_filter = ("estado", "perfil__organizacion")


@admin.register(Turno)
class TurnoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "fecha_inicio", "fecha_fin", "creado_por")
    list_filter = ("fecha_inicio",)
    search_fields = ("nombre", "descripcion")
    filter_horizontal = ("tecnicos",)


@admin.register(Ausencia)
class AusenciaAdmin(admin.ModelAdmin):
    list_display = ("tecnico", "tipo", "fecha_inicio", "fecha_fin", "estado")
    list_filter = ("tipo", "estado", "fecha_inicio")
    search_fields = ("tecnico__user__first_name", "tecnico__user__last_name", "motivo")