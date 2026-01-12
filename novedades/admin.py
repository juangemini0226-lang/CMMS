from django.contrib import admin

from .models import (
    ActividadNovedad,
    CampoHijo,
    CampoPadre,
    Novedad,
    NovedadDetalle,
    SubopcionCampo,
    AtencionPlantaDetalle,
)

class SubopcionCampoInline(admin.TabularInline):
    model = SubopcionCampo
    extra = 0


@admin.register(CampoPadre)
class CampoPadreAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre",)


@admin.register(CampoHijo)
class CampoHijoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "padre", "activo")
    list_filter = ("activo", "padre")
    search_fields = ("nombre", "padre__nombre")
    inlines = [SubopcionCampoInline]


@admin.register(SubopcionCampo)
class SubopcionCampoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "campo_hijo", "codigo")
    list_filter = ("campo_hijo",)
    search_fields = ("nombre", "campo_hijo__nombre", "codigo")

@admin.register(ActividadNovedad)
class ActividadNovedadAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre",)



class NovedadDetalleInline(admin.TabularInline):
    model = NovedadDetalle
    extra = 0

@admin.register(Novedad)
class NovedadAdmin(admin.ModelAdmin):
    list_display = ("actividad", "fecha", "equipo")
    list_filter = ("fecha",)
    search_fields = ("actividad__nombre", "descripcion", "equipo__nombre", "equipo__tag")
    date_hierarchy = "fecha"
    inlines = [NovedadDetalleInline]


@admin.register(AtencionPlantaDetalle)
class AtencionPlantaDetalleAdmin(admin.ModelAdmin):
    list_display = (
        "novedad",
        "novedad_detalle_id",
        "fecha_novedad",
        "tipo_novedad",
        "equipo",
        "estado_atencion",
        "fecha_cierre",
        "tiempo_empleado_min",
    )
    list_filter = ("tipo_novedad", "estado_atencion", "fecha_novedad")
    search_fields = (
        "novedad__descripcion",
        "equipo__nombre",
        "equipo__tag",
        "campo_padre",
        "campo_hijo",
    )
