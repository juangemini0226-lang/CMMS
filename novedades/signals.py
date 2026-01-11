import unicodedata

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import AtencionPlantaDetalle, Novedad, NovedadDetalle


def _normalizar_texto(valor: str) -> str:
    if not valor:
        return ""
    normalizado = unicodedata.normalize("NFKD", valor)
    sin_tildes = "".join(
        caracter for caracter in normalizado if not unicodedata.combining(caracter)
    )
    return sin_tildes.lower().strip()


def _es_atencion_planta(novedad: Novedad) -> bool:
    actividad = novedad.actividad.nombre if novedad.actividad else ""
    return _normalizar_texto(actividad) == "atencion planta"


def _replicar_detalle(detalle: NovedadDetalle) -> None:
    novedad = detalle.novedad
    if not _es_atencion_planta(novedad):
        (
            AtencionPlantaDetalle.objects.filter(novedad_detalle_id=detalle.pk)
            .delete()
        )
        return

    subopcion = detalle.subopcion.nombre if detalle.subopcion else ""
    AtencionPlantaDetalle.objects.update_or_create(
        novedad_detalle_id=detalle.pk,
        defaults={
            "novedad": novedad,
            "fecha_novedad": novedad.fecha,
            "equipo": novedad.equipo,
            "campo_padre": detalle.campo_padre.nombre,
            "campo_hijo": detalle.campo_hijo.nombre,
            "subopcion": subopcion,
            "comentario": detalle.comentario,
        },
    )


@receiver(post_save, sender=NovedadDetalle)
def replicar_detalle_atencion_planta(sender, instance, **kwargs):
    _replicar_detalle(instance)


@receiver(post_delete, sender=NovedadDetalle)
def eliminar_detalle_atencion_planta(sender, instance, **kwargs):
    AtencionPlantaDetalle.objects.filter(novedad_detalle_id=instance.pk).delete()


@receiver(post_save, sender=Novedad)
def sincronizar_novedad_atencion_planta(sender, instance, **kwargs):
    detalles = instance.detalles.select_related(
        "campo_padre", "campo_hijo", "subopcion"
    )
    if not _es_atencion_planta(instance):
        AtencionPlantaDetalle.objects.filter(novedad=instance).delete()
        return
    for detalle in detalles:
        _replicar_detalle(detalle)


@receiver(post_delete, sender=Novedad)
def eliminar_novedad_atencion_planta(sender, instance, **kwargs):
    AtencionPlantaDetalle.objects.filter(novedad=instance).delete()