from django.contrib import admin

from .models import (
    ActividadNovedad,
    CampoHijo,
    CampoPadre,
    Novedad,
    NovedadDetalle,
    SubopcionCampo,
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