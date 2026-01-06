
from typing import Any, Dict

from personal.models import TecnicoOperativo


def tecnico_flags(request) -> Dict[str, Any]:
    """Expone banderas de técnico para limitar navegación y vistas."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {
            "tecnico_en_sesion": None,
            "solo_tarjetas_tecnico": False,
        }

    try:
        tecnico = user.tecnico_operativo
    except TecnicoOperativo.DoesNotExist:
        tecnico = None

    tiene_grupo_tecnico = user.groups.filter(name="tecnico_actual").exists()
    solo_tarjetas = bool(
        tecnico
        and not user.is_staff
        and not user.is_superuser
        and (tiene_grupo_tecnico or True)
    )

    return {
        "tecnico_en_sesion": tecnico,
        "solo_tarjetas_tecnico": solo_tarjetas,
    }