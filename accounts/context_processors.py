from typing import Any, Dict

from personal.models import TecnicoOperativo

# Grupos que identifican a un técnico aunque no exista aún el perfil extendido.
GRUPOS_TECNICO = {
    "tecnico",
    "técnico",
    "tecnico_actual",
    "Tecnico",
    "Tecnico_Taller",
    "tecnico_taller",
}


def tecnico_flags(request) -> Dict[str, Any]:
    """Expone banderas de técnico para limitar navegación y vistas."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {
            "tecnico_en_sesion": None,
            "solo_tarjetas_tecnico": False,
            "es_tecnico": False,
            "rol_portal": "visitante",
        }

    try:
        tecnico = user.tecnico_operativo
    except TecnicoOperativo.DoesNotExist:
        tecnico = None

    pertenece_grupo_tecnico = user.groups.filter(name__in=GRUPOS_TECNICO).exists()
    es_tecnico = bool(tecnico or pertenece_grupo_tecnico)
    es_admin = bool(user.is_staff or user.is_superuser)
    solo_tarjetas = es_tecnico and not es_admin
    rol_portal = "tecnico" if solo_tarjetas else ("admin" if es_admin else "usuario")

    return {
        "tecnico_en_sesion": tecnico,
        "solo_tarjetas_tecnico": solo_tarjetas,
        "es_tecnico": es_tecnico,
        "rol_portal": rol_portal,
    }