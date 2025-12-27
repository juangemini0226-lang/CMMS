# activos/models.py

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User

from tree_queries.models import TreeNode
from tree_queries.query import TreeQuerySet


# ============================
# Helpers multi-tenant
# ============================

class TenantAwareQuerySet(models.QuerySet):
    """QuerySet con helpers para aislamiento multi-tenant."""

    def for_user(self, user):
        organizacion = getattr(getattr(user, "perfil", None), "organizacion", None)
        if not organizacion:
            return self.none()

        # Si el modelo TIENE FK "organizacion", filtra normal
        if any(f.name == "organizacion" for f in self.model._meta.fields):
            return self.filter(organizacion=organizacion)

        # Caso especial: el modelo Organizacion NO tiene FK "organizacion"
        # pero igual queremos devolver solo la org del usuario.
        if self.model.__name__ == "Organizacion":
            return self.filter(pk=organizacion.pk)

        # Si no aplica, por seguridad no devolvemos nada
        return self.none()


class TenantAwareManager(models.Manager.from_queryset(TenantAwareQuerySet)):
    """Manager que expone atajo para filtrar por organización del usuario autenticado."""

    def for_user(self, user):
        return self.get_queryset().for_user(user)


class TenantAwareTreeQuerySet(TreeQuerySet):
    """QuerySet con capacidades de árbol y filtrado multi-tenant."""

    def for_user(self, user):
        organizacion = getattr(getattr(user, "perfil", None), "organizacion", None)
        if organizacion:
            return self.filter(organizacion=organizacion)
        return self.none()


# ========================================
# MÓDULO 1: CONFIGURACIÓN ORGANIZACIONAL
# ========================================

class Organizacion(models.Model):
    """Organización/Cliente principal (Estra u otro cliente)"""
    nombre = models.CharField(max_length=200, verbose_name="Nombre")
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    creado_por = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="Creado por")
    creado_el = models.DateTimeField(auto_now_add=True, verbose_name="Creado el")
    actualizado_el = models.DateTimeField(auto_now=True, verbose_name="Actualizado el")

    # OJO: este manager ya no se rompe porque for_user maneja Organizacion aparte
    objects = TenantAwareManager()

    class Meta:
        verbose_name = "Organización"
        verbose_name_plural = "Organizaciones"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class PerfilUsuario(models.Model):
    """Extiende el modelo User para asociarlo con una organización"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="perfil")
    organizacion = models.ForeignKey(
        "activos.Organizacion",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    cargo = models.CharField(max_length=100, blank=True)
    telefono = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = "Perfil de usuario"
        verbose_name_plural = "Perfiles de usuarios"

    def __str__(self):
        return f"{self.user.username} - {self.organizacion}"


class NivelJerarquia(models.Model):
    """Define los niveles de jerarquía personalizables por organización"""
    organizacion = models.ForeignKey(
        Organizacion,
        on_delete=models.CASCADE,
        related_name="niveles_jerarquia",
        verbose_name="Organización",
    )
    numero_nivel = models.IntegerField(verbose_name="Número de nivel")
    nombre_nivel = models.CharField(max_length=100, verbose_name="Nombre del nivel")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    es_nivel_equipo = models.BooleanField(default=False, verbose_name="Es nivel de equipo principal")
    requiere_tag = models.BooleanField(default=False, verbose_name="Requiere generación de TAG")

    # Configuración de TAG
    prefijo_tag = models.CharField(max_length=10, blank=True, verbose_name="Prefijo TAG")
    formato_tag = models.CharField(
        max_length=100,
        blank=True,
        help_text="Ejemplo: {PREFIJO}-{CODIGO}-{SECUENCIA}",
        verbose_name="Formato TAG",
    )

    # ISO 14224
    corresponde_iso_14224 = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Nivel ISO 14224 correspondiente",
        help_text="Nivel 1-9 según ISO 14224",
    )

    objects = TenantAwareManager()

    class Meta:
        verbose_name = "Nivel de jerarquía"
        verbose_name_plural = "Niveles de jerarquía"
        ordering = ["organizacion", "numero_nivel"]
        unique_together = ["organizacion", "numero_nivel"]
        constraints = [
            models.CheckConstraint(
                check=Q(numero_nivel__gte=1) & Q(numero_nivel__lte=9),
                name="nivel_jerarquia_rango_iso",
            ),
        ]

    def __str__(self):
        return f"{self.organizacion.nombre} - Nivel {self.numero_nivel}: {self.nombre_nivel}"


class CampoPersonalizado(models.Model):
    """Campos adicionales configurables por nivel de jerarquía"""

    TIPOS_CAMPO = [
        ("texto", "Texto"),
        ("numero", "Número"),
        ("fecha", "Fecha"),
        ("seleccion", "Lista desplegable"),
        ("booleano", "Sí/No"),
        ("archivo", "Archivo"),
    ]

    nivel_jerarquia = models.ForeignKey(
        NivelJerarquia,
        on_delete=models.CASCADE,
        related_name="campos_personalizados",
        verbose_name="Nivel de jerarquía",
    )
    nombre_campo = models.CharField(max_length=100, verbose_name="Nombre del campo")
    tipo_campo = models.CharField(max_length=20, choices=TIPOS_CAMPO, verbose_name="Tipo de campo")
    es_requerido = models.BooleanField(default=False, verbose_name="Es requerido")
    opciones = models.JSONField(
        blank=True,
        null=True,
        help_text='Para selección: ["Opción 1", "Opción 2"]',
        verbose_name="Opciones",
    )
    valor_predeterminado = models.CharField(max_length=200, blank=True, verbose_name="Valor predeterminado")
    orden = models.IntegerField(default=0, verbose_name="Orden de visualización")

    objects = TenantAwareManager()

    class Meta:
        verbose_name = "Campo personalizado"
        verbose_name_plural = "Campos personalizados"
        ordering = ["nivel_jerarquia", "orden"]

    def __str__(self):
        return f"{self.nivel_jerarquia.nombre_nivel} - {self.nombre_campo}"


# ========================================
# MÓDULO 2: JERARQUÍA DE ACTIVOS
# ========================================

class FamiliaActivo(models.Model):
    organizacion = models.ForeignKey(
        Organizacion,
        on_delete=models.CASCADE,
        related_name="familias_activos",
        null=True,
        blank=True,
        verbose_name="Organización",
    )
    nombre = models.CharField(max_length=200, verbose_name="Nombre de la Familia")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")

    objects = TenantAwareManager()

    class Meta:
        verbose_name = "Familia de Activo"
        verbose_name_plural = "Familias de Activos"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(fields=["organizacion", "nombre"], name="unique_familia_por_organizacion"),
        ]
        indexes = [
            models.Index(fields=["organizacion", "nombre"]),
        ]

    def __str__(self):
        return self.nombre


class NodoActivo(TreeNode):
    """Nodo genérico que puede ser cualquier nivel de la jerarquía (Planta, Área, Sistema, Equipo, etc.)"""

    familia = models.ForeignKey(
        FamiliaActivo,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Familia del Activo",
        related_name="activos",
    )

    ESTADOS = [
        ("activo", "Activo"),
        ("inactivo", "Inactivo"),
        ("mantenimiento", "En mantenimiento"),
        ("fuera_servicio", "Fuera de servicio"),
        ("retirado", "Retirado"),
    ]

    CRITICIDADES = [
        ("alta", "Alta"),
        ("media", "Media"),
        ("baja", "Baja"),
    ]

    # Relaciones
    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE, verbose_name="Organización")
    nivel_jerarquia = models.ForeignKey(NivelJerarquia, on_delete=models.PROTECT, verbose_name="Nivel de jerarquía")

    # Información básica
    nombre = models.CharField(max_length=200, verbose_name="Nombre")
    codigo = models.CharField(max_length=100, verbose_name="Código")
    tag = models.CharField(max_length=100, unique=True, blank=True, null=True, verbose_name="TAG automático")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")

    # Datos ISO 14224
    clase_equipo_iso = models.CharField(max_length=100, blank=True, verbose_name="Clase de equipo ISO 14224")

    # Datos técnicos
    fabricante = models.CharField(max_length=200, blank=True, verbose_name="Fabricante")
    modelo = models.CharField(max_length=100, blank=True, verbose_name="Modelo")
    numero_serie = models.CharField(max_length=100, blank=True, verbose_name="Número de serie")

    # Datos operacionales
    fecha_instalacion = models.DateField(null=True, blank=True, verbose_name="Fecha de instalación")
    estado = models.CharField(max_length=50, choices=ESTADOS, default="activo", verbose_name="Estado")
    criticidad = models.CharField(max_length=20, choices=CRITICIDADES, blank=True, verbose_name="Criticidad")

    # Ubicación física
    ubicacion_fisica = models.CharField(max_length=300, blank=True, verbose_name="Ubicación física detallada")

    # Datos personalizados (JSON flexible)
    datos_personalizados = models.JSONField(default=dict, blank=True, verbose_name="Datos personalizados")

    catalogo_parte = models.ForeignKey(
        "activos.CatalogoParte",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Referencia de catálogo (nivel 9)",
        help_text="Solo aplicable para el último nivel ISO 14224 (Parte/Pieza).",
    )

    # Documentación
    imagen = models.ImageField(upload_to="activos/imagenes/", blank=True, null=True, verbose_name="Imagen")

    # Metadatos
    creado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="activos_creados",
        verbose_name="Creado por",
    )
    creado_el = models.DateTimeField(auto_now_add=True, verbose_name="Creado el")
    actualizado_el = models.DateTimeField(auto_now=True, verbose_name="Actualizado el")

    # ✅ corregido: usamos TreeQuerySet (vía TenantAwareTreeQuerySet)
    objects = TenantAwareTreeQuerySet.as_manager(with_tree_fields=True)

    class Meta:
        verbose_name = "Activo"
        verbose_name_plural = "Activos"
        ordering = ["organizacion", "codigo"]
        unique_together = ["organizacion", "codigo"]
        indexes = [
            models.Index(fields=["organizacion", "nivel_jerarquia"]),
            models.Index(fields=["tag"]),
            models.Index(fields=["estado"]),
            models.Index(fields=["organizacion", "parent"]),
        ]

    def __str__(self):
        return f"{self.tag or self.codigo} - {self.nombre}"

    def clean(self):
        errors = {}

        if self.parent:
            if self.parent.organizacion_id != self.organizacion_id:
                errors["organizacion"] = "El activo debe pertenecer a la misma organización que su padre."

            parent_level = getattr(self.parent, "nivel_jerarquia", None)
            current_level = self.nivel_jerarquia
            if parent_level and current_level:
                if current_level.numero_nivel - parent_level.numero_nivel != 1:
                    errors["nivel_jerarquia"] = "La jerarquía debe avanzar solo un nivel entre padre e hijo."

        if self.catalogo_parte and self.catalogo_parte.organizacion_id != self.organizacion_id:
            errors["catalogo_parte"] = "La parte debe pertenecer a la misma organización."

        if (
            self.nivel_jerarquia
            and self.nivel_jerarquia.corresponde_iso_14224 == 9
            and not self.catalogo_parte
        ):
            errors["catalogo_parte"] = "Los nodos de nivel 9 deben apuntar a una parte del catálogo."

        if errors:
            raise ValidationError(errors)

        super().clean()

    def save(self, *args, **kwargs):
        """Genera TAG automáticamente si no existe y está configurado"""
        if not self.tag and self.nivel_jerarquia and self.nivel_jerarquia.requiere_tag:
            self.tag = self.generar_tag()
        self.full_clean()
        super().save(*args, **kwargs)

    def generar_tag(self):
        """Genera el TAG del activo respetando el formato configurado"""
        formato = self.nivel_jerarquia.formato_tag or "{PREFIJO}-{CODIGO}-{SECUENCIA}"
        prefijo = self.nivel_jerarquia.prefijo_tag or ""

        ultimo_nodo = NodoActivo.objects.filter(
            organizacion=self.organizacion,
            nivel_jerarquia=self.nivel_jerarquia,
            tag__isnull=False,
        ).order_by("-id").first()

        secuencia = 1
        if ultimo_nodo and ultimo_nodo.tag:
            import re
            match = re.search(r"(\d+)$", ultimo_nodo.tag)
            if match:
                secuencia = int(match.group(1)) + 1

        codigos_padres = []
        actual = self.parent
        while actual:
            codigos_padres.insert(0, actual.codigo)
            actual = actual.parent

        tag = formato.format(
            PREFIJO=prefijo,
            CODIGO=self.codigo,
            SECUENCIA=str(secuencia).zfill(3),
            PADRE="-".join(codigos_padres) if codigos_padres else "",
        )
        return tag

    def obtener_ruta_completa(self):
        """Retorna la ruta completa del activo (Planta > Área > Sistema > Equipo)"""
        ruta = []
        actual = self
        while actual:
            ruta.insert(0, actual.nombre)
            actual = actual.parent
        return " > ".join(ruta)

    def obtener_nivel_nombre(self):
        """Retorna el nombre del nivel asociado al activo"""
        return self.nivel_jerarquia.nombre_nivel


class DependenciaActivo(models.Model):
    activo_padre = models.ForeignKey(
        NodoActivo,
        on_delete=models.CASCADE,
        related_name="dependencias",
        verbose_name="Activo Padre",
    )
    nombre = models.CharField(max_length=200, verbose_name="Nombre de la Dependencia")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")

    class Meta:
        verbose_name = "Dependencia de Activo"
        verbose_name_plural = "Dependencias de Activos"
        ordering = ["activo_padre", "nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["activo_padre", "nombre"],
                name="unique_dependencia_por_activo",
            ),
        ]

    def __str__(self):
        return f"{self.activo_padre} - {self.nombre}"


# ========================================
# MÓDULO 3: CATÁLOGO MAESTRO DE PARTES
# ========================================

class CatalogoParte(models.Model):
    """Catálogo maestro de piezas y repuestos (nivel 9 ISO 14224)."""

    organizacion = models.ForeignKey(
        Organizacion,
        on_delete=models.CASCADE,
        related_name="catalogo_partes",
        verbose_name="Organización",
    )
    codigo_sku = models.CharField(max_length=100, verbose_name="Código/SKU")
    nombre = models.CharField(max_length=200, verbose_name="Nombre")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    datos_tecnicos = models.JSONField(default=dict, blank=True, verbose_name="Datos técnicos")
    es_activo = models.BooleanField(default=True, verbose_name="Disponible para selección")

    objects = TenantAwareManager()

    class Meta:
        verbose_name = "Parte de catálogo"
        verbose_name_plural = "Catálogo de partes"
        ordering = ["organizacion", "codigo_sku"]
        constraints = [
            models.UniqueConstraint(fields=["organizacion", "codigo_sku"], name="unique_sku_por_organizacion"),
        ]
        indexes = [
            models.Index(fields=["organizacion", "codigo_sku"]),
            models.Index(fields=["organizacion", "es_activo"]),
        ]

    def __str__(self):
        return f"{self.codigo_sku} - {self.nombre}"


# ========================================
# MÓDULO 4: CATÁLOGO ISO 14224
# ========================================

class ClaseEquipoISO14224(models.Model):
    """Catálogo de clases de equipos según ISO 14224"""
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=200, verbose_name="Nombre")
    descripcion = models.TextField(verbose_name="Descripción")
    nivel_taxonomico = models.IntegerField(default=6, verbose_name="Nivel taxonómico ISO 14224")
    padre = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, verbose_name="Clase padre")

    class Meta:
        verbose_name = "Clase de equipo ISO 14224"
        verbose_name_plural = "Clases de equipos ISO 14224"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


# ========================================
# MÓDULO 5: PLANTILLAS DE ACTIVOS
# ========================================

class PlantillaActivo(models.Model):
    """Plantillas predefinidas para facilitar creación de activos similares"""
    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE, verbose_name="Organización")
    nombre = models.CharField(max_length=200, verbose_name="Nombre de la plantilla")
    nivel_jerarquia = models.ForeignKey(NivelJerarquia, on_delete=models.CASCADE, verbose_name="Nivel de jerarquía")
    clase_equipo_iso = models.ForeignKey(
        ClaseEquipoISO14224,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Clase de equipo ISO",
    )

    # Valores predeterminados
    datos_predeterminados = models.JSONField(default=dict, verbose_name="Datos predeterminados")

    es_activa = models.BooleanField(default=True, verbose_name="Está activa")
    creado_el = models.DateTimeField(auto_now_add=True, verbose_name="Creado el")

    objects = TenantAwareManager()

    class Meta:
        verbose_name = "Plantilla de activo"
        verbose_name_plural = "Plantillas de activos"
        ordering = ["organizacion", "nombre"]

    def __str__(self):
        return self.nombre


class PlantillaNodoISO(TreeNode):
    """Define la estructura jerárquica de una plantilla ISO 14224 profunda."""

    plantilla = models.ForeignKey(
        PlantillaActivo,
        on_delete=models.CASCADE,
        related_name="nodos_iso",
        verbose_name="Plantilla asociada",
    )
    organizacion = models.ForeignKey(
        Organizacion,
        on_delete=models.CASCADE,
        related_name="nodos_plantilla_iso",
        verbose_name="Organización",
    )
    nombre = models.CharField(max_length=200, verbose_name="Nombre del nodo")
    codigo = models.CharField(max_length=100, verbose_name="Código del nodo")
    nivel_iso = models.IntegerField(
        verbose_name="Nivel ISO 14224",
        help_text="Nivel 1-9 según jerarquía ISO 14224",
    )
    datos_predeterminados = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Datos predeterminados para instanciación",
    )
    catalogo_parte = models.ForeignKey(
        CatalogoParte,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Parte sugerida",
        help_text="Solo para nodos de nivel 9 (parte/pieza).",
    )

    objects = TenantAwareTreeQuerySet.as_manager(with_tree_fields=True)

    class Meta:
        verbose_name = "Nodo de plantilla ISO"
        verbose_name_plural = "Nodos de plantilla ISO"
        ordering = ["organizacion", "nivel_iso", "codigo"]
        constraints = [
            models.UniqueConstraint(fields=["plantilla", "codigo"], name="unique_codigo_por_plantilla"),
            models.CheckConstraint(
                check=Q(nivel_iso__gte=1) & Q(nivel_iso__lte=9),
                name="nivel_iso_rango_valido",
            ),
        ]

    def clean(self):
        errors = {}

        if self.plantilla and self.organizacion_id != self.plantilla.organizacion_id:
            errors["organizacion"] = "La organización del nodo debe coincidir con la de la plantilla."

        if self.parent and self.parent.organizacion_id != self.organizacion_id:
            errors["parent"] = "El padre pertenece a otra organización."

        if self.parent and self.parent.plantilla_id != self.plantilla_id:
            errors["parent"] = "El padre debe pertenecer a la misma plantilla."

        if self.catalogo_parte and self.catalogo_parte.organizacion_id != self.organizacion_id:
            errors["catalogo_parte"] = "La parte sugerida debe pertenecer a la misma organización."

        if self.catalogo_parte and self.nivel_iso != 9:
            errors["catalogo_parte"] = "Solo los nodos de nivel 9 pueden referenciar partes."

        if errors:
            raise ValidationError(errors)

        super().clean()


# ========================================
# MÓDULO 6: DOCUMENTOS ADJUNTOS
# ========================================

class DocumentoActivo(models.Model):
    """Documentos técnicos asociados a activos"""

    TIPOS_DOCUMENTO = [
        ("manual", "Manual"),
        ("plano", "Plano"),
        ("certificado", "Certificado"),
        ("ficha_tecnica", "Ficha técnica"),
        ("foto", "Fotografía"),
        ("otro", "Otro"),
    ]

    activo = models.ForeignKey(
        NodoActivo,
        on_delete=models.CASCADE,
        related_name="documentos",
        verbose_name="Activo",
    )
    tipo_documento = models.CharField(max_length=20, choices=TIPOS_DOCUMENTO, verbose_name="Tipo de documento")
    nombre = models.CharField(max_length=200, verbose_name="Nombre")
    archivo = models.FileField(upload_to="activos/documentos/", verbose_name="Archivo")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    subido_por = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="Subido por")
    subido_el = models.DateTimeField(auto_now_add=True, verbose_name="Subido el")

    class Meta:
        verbose_name = "Documento de activo"
        verbose_name_plural = "Documentos de activos"
        ordering = ["-subido_el"]

    def __str__(self):
        return f"{self.activo.nombre} - {self.nombre}"
