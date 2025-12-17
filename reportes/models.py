from django.db import models


class DocumentoCargado(models.Model):
    class TipoDocumento(models.TextChoices):
        REPORTE = 'reporte', 'Reporte'
        ORDEN_TRABAJO = 'orden', 'Orden de trabajo'

    archivo = models.FileField(upload_to='cargas_documentos/')
    tipo = models.CharField(max_length=20, choices=TipoDocumento.choices)
    descripcion = models.CharField(max_length=255, blank=True)
    nombre_original = models.CharField(max_length=255)
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_subida']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.nombre_original}"