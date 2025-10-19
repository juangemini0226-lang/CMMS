from django.contrib import admin
from tree_queries.admin import TreeAdmin
from .models import (
    Organizacion, NivelJerarquia, CampoPersonalizado,
    NodoActivo, ClaseEquipoISO14224, PlantillaActivo,
    DocumentoActivo
)

# ========================================
# CONFIGURACIÓN
# ========================================

@admin.register(Organizacion)
class OrganizacionAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'codigo', 'creado_por', 'creado_el']
    search_fields = ['nombre', 'codigo']
    list_filter = ['creado_el']
    readonly_fields = ['creado_el', 'actualizado_el']


class CampoPersonalizadoInline(admin.TabularInline):
    model = CampoPersonalizado
    extra = 1
    fields = ['nombre_campo', 'tipo_campo', 'es_requerido', 'orden']


@admin.register(NivelJerarquia)
class NivelJerarquiaAdmin(admin.ModelAdmin):
    list_display = [
        'organizacion', 'numero_nivel', 'nombre_nivel', 
        'es_nivel_equipo', 'requiere_tag', 'corresponde_iso_14224'
    ]
    list_filter = ['organizacion', 'es_nivel_equipo', 'requiere_tag']
    search_fields = ['nombre_nivel', 'descripcion']
    ordering = ['organizacion', 'numero_nivel']
    inlines = [CampoPersonalizadoInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('organizacion', 'numero_nivel', 'nombre_nivel', 'descripcion')
        }),
        ('Configuración', {
            'fields': ('es_nivel_equipo', 'requiere_tag', 'corresponde_iso_14224')
        }),
        ('Configuración de TAG', {
            'fields': ('prefijo_tag', 'formato_tag'),
            'classes': ('collapse',),
            'description': 'Configura cómo se generarán los TAGs automáticamente para este nivel.'
        }),
    )


@admin.register(CampoPersonalizado)
class CampoPersonalizadoAdmin(admin.ModelAdmin):
    list_display = ['nivel_jerarquia', 'nombre_campo', 'tipo_campo', 'es_requerido', 'orden']
    list_filter = ['nivel_jerarquia__organizacion', 'tipo_campo', 'es_requerido']
    search_fields = ['nombre_campo']
    ordering = ['nivel_jerarquia', 'orden']


# ========================================
# ACTIVOS
# ========================================

class DocumentoActivoInline(admin.TabularInline):
    model = DocumentoActivo
    extra = 0
    fields = ['tipo_documento', 'nombre', 'archivo', 'descripcion']
    readonly_fields = ['subido_por', 'subido_el']
    
    def has_add_permission(self, request, obj=None):
        return True


@admin.register(NodoActivo)
class NodoActivoAdmin(TreeAdmin):
    # Configuración básica del TreeAdmin
    list_display = [
        'codigo', 'nombre', 'tag', 'nivel_jerarquia', 
        'estado', 'criticidad'
    ]
    list_display_links = ['nombre']
    list_filter = [
        'organizacion', 'nivel_jerarquia', 'estado', 'criticidad'
    ]
    search_fields = ['nombre', 'codigo', 'tag', 'descripcion']
    readonly_fields = ['tag', 'creado_por', 'creado_el', 'actualizado_el']
    autocomplete_fields = ['parent']  # Autocompletado para el padre
    inlines = [DocumentoActivoInline]
    
    # Configuración para TreeAdmin (vista jerárquica)
    # TreeAdmin automáticamente maneja la visualización del árbol
    
    fieldsets = (
        ('Jerarquía', {
            'fields': ('organizacion', 'nivel_jerarquia', 'parent'),
            'description': 'Define la ubicación del activo en la jerarquía organizacional.'
        }),
        ('Identificación', {
            'fields': ('nombre', 'codigo', 'tag'),
            'description': 'TAG se genera automáticamente según la configuración del nivel.'
        }),
        ('Descripción', {
            'fields': ('descripcion', 'ubicacion_fisica')
        }),
        ('Datos Técnicos', {
            'fields': ('clase_equipo_iso', 'fabricante', 'modelo', 'numero_serie'),
            'classes': ('collapse',)
        }),
        ('Estado y Criticidad', {
            'fields': ('estado', 'criticidad', 'fecha_instalacion')
        }),
        ('Imagen', {
            'fields': ('imagen',),
            'classes': ('collapse',)
        }),
        ('Datos Personalizados', {
            'fields': ('datos_personalizados',),
            'classes': ('collapse',),
            'description': 'Campos adicionales configurables en formato JSON.'
        }),
        ('Metadatos', {
            'fields': ('creado_por', 'creado_el', 'actualizado_el'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimiza las consultas incluyendo relaciones"""
        qs = super().get_queryset(request)
        return qs.select_related('organizacion', 'nivel_jerarquia', 'parent', 'creado_por')
    
    def save_model(self, request, obj, form, change):
        """Asigna automáticamente el usuario que crea el activo"""
        if not change:  # Si es nuevo
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filtra las opciones según la organización"""
        if db_field.name == "nivel_jerarquia":
            # Si hay un parámetro de organización, filtrar niveles
            if request.GET.get('organizacion'):
                kwargs["queryset"] = NivelJerarquia.objects.filter(
                    organizacion_id=request.GET.get('organizacion')
                )
        if db_field.name == "parent":
            # Solo mostrar activos de la misma organización como posibles padres
            if request.GET.get('organizacion'):
                kwargs["queryset"] = NodoActivo.objects.filter(
                    organizacion_id=request.GET.get('organizacion')
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# ========================================
# CATÁLOGOS ISO 14224
# ========================================

@admin.register(ClaseEquipoISO14224)
class ClaseEquipoISO14224Admin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'nivel_taxonomico', 'padre']
    list_filter = ['nivel_taxonomico']
    search_fields = ['codigo', 'nombre', 'descripcion']
    ordering = ['codigo']
    autocomplete_fields = ['padre']
    
    fieldsets = (
        ('Identificación', {
            'fields': ('codigo', 'nombre')
        }),
        ('Clasificación', {
            'fields': ('nivel_taxonomico', 'padre')
        }),
        ('Descripción', {
            'fields': ('descripcion',)
        }),
    )


# ========================================
# PLANTILLAS
# ========================================

@admin.register(PlantillaActivo)
class PlantillaActivoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'organizacion', 'nivel_jerarquia', 'es_activa', 'creado_el']
    list_filter = ['organizacion', 'nivel_jerarquia', 'es_activa', 'creado_el']
    search_fields = ['nombre']
    ordering = ['-creado_el']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'organizacion', 'nivel_jerarquia')
        }),
        ('Configuración', {
            'fields': ('clase_equipo_iso', 'es_activa')
        }),
        ('Datos Predeterminados', {
            'fields': ('datos_predeterminados',),
            'description': 'Valores por defecto en formato JSON que se aplicarán al crear activos con esta plantilla.'
        }),
    )


# ========================================
# DOCUMENTOS
# ========================================

@admin.register(DocumentoActivo)
class DocumentoActivoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'activo', 'tipo_documento', 'subido_por', 'subido_el']
    list_filter = ['tipo_documento', 'subido_el']
    search_fields = ['nombre', 'descripcion', 'activo__nombre', 'activo__codigo']
    readonly_fields = ['subido_por', 'subido_el']
    autocomplete_fields = ['activo']
    ordering = ['-subido_el']
    
    fieldsets = (
        ('Información del Documento', {
            'fields': ('activo', 'tipo_documento', 'nombre')
        }),
        ('Archivo y Descripción', {
            'fields': ('archivo', 'descripcion')
        }),
        ('Metadatos', {
            'fields': ('subido_por', 'subido_el'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Asigna automáticamente el usuario que sube el documento"""
        if not change:
            obj.subido_por = request.user
        super().save_model(request, obj, form, change)


# ========================================
# CONFIGURACIONES ADICIONALES
# ========================================

# Personalización del sitio admin
admin.site.site_header = "CMMS ESTRA - Administración"
admin.site.site_title = "CMMS ESTRA"
admin.site.index_title = "Panel de Administración"
