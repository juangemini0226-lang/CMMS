from django.db import models
from django.utils import timezone


class CampoPadre(models.Model):
    nombre = models.CharField(max_length=150, unique=True, verbose_name="Campo padre")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Campo padre"
        verbose_name_plural = "Campos padre"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class CampoHijo(models.Model):
    padre = models.ForeignKey(
        CampoPadre,
        on_delete=models.CASCADE,
        related_name="hijos",
        verbose_name="Campo padre",
    )
    nombre = models.CharField(max_length=150, verbose_name="Campo hijo")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Campo hijo"
        verbose_name_plural = "Campos hijo"
        ordering = ["padre__nombre", "nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["padre", "nombre"], name="unique_campo_hijo_por_padre"
            )
        ]

    def __str__(self):
        return f"{self.padre}: {self.nombre}"


class SubopcionCampo(models.Model):
    campo_hijo = models.ForeignKey(
        CampoHijo,
        on_delete=models.CASCADE,
        related_name="subopciones",
        verbose_name="Campo hijo",
    )
    nombre = models.CharField(max_length=150, verbose_name="Nombre de subopción")
    codigo = models.CharField(
        max_length=50, blank=True, verbose_name="Código / referencia"
    )
    descripcion = models.TextField(blank=True, verbose_name="Descripción")

    class Meta:
        verbose_name = "Subopción"
        verbose_name_plural = "Subopciones"
        ordering = ["campo_hijo__padre__nombre", "campo_hijo__nombre", "nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["campo_hijo", "nombre"],
                name="unique_subopcion_por_campo_hijo",
            )
        ]

    def __str__(self):
        return f"{self.campo_hijo} - {self.nombre}"


class Novedad(models.Model):
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("atendida", "Atendida"),
        ("finalizada", "Finalizada"),
    ]
    fecha = models.DateField(default=timezone.now, verbose_name="Fecha de la novedad")
    actividad = models.ForeignKey(
        "ActividadNovedad",
        on_delete=models.PROTECT,
        related_name="novedades",
        null=True,
        blank=True,
        verbose_name="Actividad",
    )
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default="pendiente",
        verbose_name="Estado",
    )
    equipo = models.ForeignKey(
        "activos.NodoActivo",
        on_delete=models.PROTECT,
        related_name="novedades",
        verbose_name="Equipo o molde",
    )

    class Meta:
        verbose_name = "Novedad"
        verbose_name_plural = "Novedades"
        ordering = ["-fecha", "-id"]

    def __str__(self):
        actividad = self.actividad.nombre if self.actividad else "Sin actividad"
        return f"{self.fecha} - {actividad}"


class ActividadNovedad(models.Model):
    nombre = models.CharField(max_length=150, unique=True, verbose_name="Actividad")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Actividad de novedad"
        verbose_name_plural = "Actividades de novedades"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

class NovedadDetalle(models.Model):
    novedad = models.ForeignKey(
        Novedad,
        on_delete=models.CASCADE,
        related_name="detalles",
        verbose_name="Novedad",
    )
    campo_padre = models.ForeignKey(
        CampoPadre,
        on_delete=models.CASCADE,
        related_name="detalles",
        verbose_name="Campo padre",
    )
    campo_hijo = models.ForeignKey(
        CampoHijo,
        on_delete=models.CASCADE,
        related_name="detalles",
        verbose_name="Campo hijo",
    )
    subopcion = models.ForeignKey(
        SubopcionCampo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="detalles",
        verbose_name="Subopción seleccionada",
    )
    comentario = models.CharField(
        max_length=255, blank=True, verbose_name="Comentario o detalle"
    )
    evidencia = models.ImageField(
        upload_to="novedades/evidencias/",
        blank=True,
        null=True,
        verbose_name="Evidencia (imagen)",
    )

    class Meta:
        verbose_name = "Detalle de novedad"
        verbose_name_plural = "Detalles de novedad"
        ordering = ["novedad", "campo_padre__nombre", "campo_hijo__nombre"]

    def __str__(self):
        return f"{self.novedad} - {self.campo_padre}/{self.campo_hijo}"