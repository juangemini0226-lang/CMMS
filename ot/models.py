from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Max


class WorkOrder(models.Model):
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("por_iniciar", "Por iniciar"),
        ("en_ejecucion", "En ejecución"),
        ("en_espera", "En espera"),
        ("finalizada", "Finalizada"),
        ("cancelada", "Cancelada"),
    ]

    PRIORIDADES = [
        ("alta", "Alta"),
        ("media", "Media"),
        ("baja", "Baja"),
    ]

    consecutivo = models.PositiveIntegerField(unique=True, editable=False)
    titulo = models.CharField(max_length=255, verbose_name="Título de la OT")
    descripcion = models.TextField(blank=True, verbose_name="Descripción y alcance")
    estado = models.CharField(
        max_length=20, choices=ESTADOS, default="pendiente", verbose_name="Estado"
    )
    prioridad = models.CharField(
        max_length=10, choices=PRIORIDADES, default="media", verbose_name="Prioridad"
    )
    equipo = models.ForeignKey(
        "activos.NodoActivo",
        on_delete=models.PROTECT,
        related_name="ordenes_trabajo",
        verbose_name="Equipo o activo",
    )
    novedad_origen = models.ForeignKey(
        "novedades.Novedad",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ordenes_trabajo",
        verbose_name="Novedad origen",
    )
    responsable = models.ForeignKey(
        "personal.TecnicoOperativo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ordenes_trabajo",
        verbose_name="Responsable",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Creada el")
    fecha_actualizacion = models.DateTimeField(
        auto_now=True, verbose_name="Actualizada el"
    )
    fecha_programada = models.DateField(
        null=True, blank=True, verbose_name="Fecha programada"
    )
    fecha_cierre_compromiso = models.DateField(
        null=True, blank=True, verbose_name="Fecha de cierre comprometida"
    )

    class Meta:
        verbose_name = "Orden de trabajo"
        verbose_name_plural = "Órdenes de trabajo"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"{self.codigo} - {self.titulo}"

    @property
    def codigo(self):
        consecutivo = self.consecutivo or 0
        return f"OT-{consecutivo:05d}"

    def save(self, *args, **kwargs):
        if not self.consecutivo:
            ultimo = WorkOrder.objects.aggregate(max_consec=Max("consecutivo"))
            siguiente = (ultimo["max_consec"] or 0) + 1
            self.consecutivo = siguiente
        super().save(*args, **kwargs)


class WorkOrderEvento(models.Model):
    orden = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        related_name="eventos",
        verbose_name="Orden de trabajo",
    )
    estado = models.CharField(
        max_length=20, choices=WorkOrder.ESTADOS, verbose_name="Estado asociado"
    )
    descripcion = models.TextField(blank=True, verbose_name="Comentario")
    creado_el = models.DateTimeField(auto_now_add=True, verbose_name="Creado el")
    creado_por = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_ot",
        verbose_name="Registrado por",
    )

    class Meta:
        verbose_name = "Evento de OT"
        verbose_name_plural = "Eventos de OT"
        ordering = ["-creado_el"]

    def __str__(self):
        return f"{self.orden.codigo} - {self.get_estado_display()} ({self.creado_el:%Y-%m-%d %H:%M})"