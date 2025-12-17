from django.contrib import admin

from .models import DocumentoCargado


@admin.register(DocumentoCargado)
class DocumentoCargadoAdmin(admin.ModelAdmin):
    list_display = ('nombre_original', 'tipo', 'fecha_subida')
    list_filter = ('tipo', 'fecha_subida')
    search_fields = ('nombre_original', 'descripcion')
    ordering = ('-fecha_subida',)