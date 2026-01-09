from django.conf import settings
from django.db import models
from django.utils import timezone

from activos.models import PerfilUsuario

class TecnicoOperativo(models.Model):
    """Perfil extendido para técnicos operativos vinculados a un usuario."""

    ESTADOS = [
        ("activo", "Activo"),
        ("inactivo", "Inactivo"),
        ("licencia", "En licencia"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tecnico_operativo",
        verbose_name="Usuario",
        null=True,
        blank=True,
        help_text="Asocia un usuario del sistema si el técnico inicia sesión.",
    )
    nombre = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Nombre del técnico",
        help_text="Usa este campo si el técnico no tiene usuario.",
    )
    perfil = models.ForeignKey(
        PerfilUsuario,
        on_delete=models.PROTECT,
        related_name="tecnicos",
        verbose_name="Perfil organizacional",
    )
    numero_identificacion = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="N.° identificación",
    )
    especialidad = models.CharField(max_length=150, verbose_name="Especialidad")
    telefono_contacto = models.CharField(
        max_length=30,
        verbose_name="Teléfono de contacto",
    )
    correo_corporativo = models.EmailField(
        blank=True,
        verbose_name="Correo corporativo",
    )
    fecha_ingreso = models.DateField(default=timezone.now, verbose_name="Fecha de ingreso")
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default="activo",
        verbose_name="Estado",
    )
    notas = models.TextField(blank=True, verbose_name="Notas internas")

    class Meta:
        verbose_name = "Técnico operativo"
        verbose_name_plural = "Técnicos operativos"
        ordering = ["user__last_name", "user__first_name", "nombre"]

    def __str__(self) -> str:
        return f"{self.nombre_display} ({self.especialidad})"

    @property
    def nombre_display(self) -> str:
        if self.user_id:
            return self.user.get_full_name() or self.user.username
        return self.nombre or "Sin nombre"
    @property
    def organizacion(self):
        return self.perfil.organizacion


class Turno(models.Model):
    """Define turnos o guardias asignables a técnicos operativos."""

    nombre = models.CharField(max_length=120, verbose_name="Nombre del turno")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    fecha_inicio = models.DateTimeField(verbose_name="Inicio del turno")
    fecha_fin = models.DateTimeField(verbose_name="Fin del turno")
    color = models.CharField(
        max_length=9,
        default="#2563eb",
        help_text="Color en formato HEX para calendarios",
        verbose_name="Color",
    )
    tecnicos = models.ManyToManyField(
        TecnicoOperativo,
        related_name="turnos",
        blank=True,
        verbose_name="Técnicos asignados",
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="turnos_creados",
        verbose_name="Creado por",
    )
    actualizado_el = models.DateTimeField(auto_now=True, verbose_name="Actualizado el")

    class Meta:
        verbose_name = "Turno"
        verbose_name_plural = "Turnos"
        ordering = ["-fecha_inicio"]

    def __str__(self) -> str:
        return f"{self.nombre} ({self.fecha_inicio:%d/%m/%Y %H:%M} - {self.fecha_fin:%H:%M})"


class Ausencia(models.Model):
    """Ausencias programadas o imprevistas de técnicos operativos."""

    TIPOS_AUSENCIA = [
        ("vacaciones", "Vacaciones"),
        ("enfermedad", "Enfermedad"),
        ("permiso", "Permiso"),
        ("otro", "Otro"),
    ]

    ESTADOS = [
        ("pendiente", "Pendiente de aprobación"),
        ("aprobada", "Aprobada"),
        ("rechazada", "Rechazada"),
    ]

    tecnico = models.ForeignKey(
        TecnicoOperativo,
        on_delete=models.CASCADE,
        related_name="ausencias",
        verbose_name="Técnico",
    )
    tipo = models.CharField(max_length=20, choices=TIPOS_AUSENCIA, verbose_name="Tipo")
    fecha_inicio = models.DateField(verbose_name="Fecha de inicio")
    fecha_fin = models.DateField(verbose_name="Fecha de finalización")
    motivo = models.TextField(verbose_name="Motivo o detalle")
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default="pendiente",
        verbose_name="Estado",
    )
    turno_relacionado = models.ForeignKey(
        Turno,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ausencias",
        verbose_name="Turno relacionado",
    )
    aprobado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="ausencias_aprobadas",
        null=True,
        blank=True,
        verbose_name="Aprobado por",
    )
    creado_el = models.DateTimeField(auto_now_add=True, verbose_name="Creado el")

    class Meta:
        verbose_name = "Ausencia"
        verbose_name_plural = "Ausencias"
        ordering = ["-fecha_inicio"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(fecha_fin__gte=models.F("fecha_inicio")),
                name="ausencia_fecha_fin_gte_inicio",
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_tipo_display()} - {self.tecnico} ({self.fecha_inicio:%d/%m/%Y})"

    @property
    def duracion_dias(self) -> int:
        return (self.fecha_fin - self.fecha_inicio).days + 1