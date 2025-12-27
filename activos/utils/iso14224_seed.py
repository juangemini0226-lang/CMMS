from typing import Iterable, Mapping, Optional

from activos.models import ClaseEquipoISO14224

CatalogNode = Mapping[str, object]


CATALOGO_BASE: Iterable[CatalogNode] = [
    {
        "codigo": "SYS_ALIM",
        "nombre": "Sistema de alimentación",
        "descripcion": "Cadena base de alimentación/energía para equipos.",
        "nivel_taxonomico": 6,
        "children": [
            {
                "codigo": "SUB_BOMBA",
                "nombre": "Subunidad de bombeo",
                "descripcion": "Conjunto de bombas y accesorios principales.",
                "nivel_taxonomico": 7,
                "children": [
                    {
                        "codigo": "ITEM_FILTRO",
                        "nombre": "Filtro principal",
                        "descripcion": "Elemento filtrante previo al suministro.",
                        "nivel_taxonomico": 8,
                        "children": [
                            {
                                "codigo": "COMP_JUNTA",
                                "nombre": "Junta tórica",
                                "descripcion": "Junta de sellado del filtro.",
                                "nivel_taxonomico": 9,
                            },
                            {
                                "codigo": "COMP_SENSOR_PRES",
                                "nombre": "Sensor de presión",
                                "descripcion": "Sensor para monitoreo de presión en la línea.",
                                "nivel_taxonomico": 9,
                            },
                        ],
                    },
                    {
                        "codigo": "ITEM_MOTOR",
                        "nombre": "Motor de accionamiento",
                        "descripcion": "Motor que impulsa la bomba de alimentación.",
                        "nivel_taxonomico": 8,
                        "children": [
                            {
                                "codigo": "COMP_ACOPLE",
                                "nombre": "Acople flexible",
                                "descripcion": "Acople entre motor y bomba.",
                                "nivel_taxonomico": 9,
                            },
                        ],
                    },
                ],
            },
            {
                "codigo": "SUB_CONTROL_ALIM",
                "nombre": "Subunidad de control",
                "descripcion": "Controladores, válvulas y monitoreo del sistema de alimentación.",
                "nivel_taxonomico": 7,
                "children": [
                    {
                        "codigo": "ITEM_VALVULA",
                        "nombre": "Válvula de control",
                        "descripcion": "Válvula de control principal.",
                        "nivel_taxonomico": 8,
                        "children": [
                            {
                                "codigo": "COMP_ACTUADOR",
                                "nombre": "Actuador neumático",
                                "descripcion": "Actuador para apertura/cierre de la válvula.",
                                "nivel_taxonomico": 9,
                            },
                        ],
                    },
                ],
            },
        ],
    },
    {
        "codigo": "SYS_MOV",
        "nombre": "Sistema de movimiento",
        "descripcion": "Estructura base para mecanismos de desplazamiento.",
        "nivel_taxonomico": 6,
        "children": [
            {
                "codigo": "SUB_GUIAS",
                "nombre": "Subunidad de guías",
                "descripcion": "Guías lineales o patines del sistema.",
                "nivel_taxonomico": 7,
                "children": [
                    {
                        "codigo": "ITEM_CARRO",
                        "nombre": "Carro de guía",
                        "descripcion": "Carro o patín sobre la guía.",
                        "nivel_taxonomico": 8,
                        "children": [
                            {
                                "codigo": "COMP_RODAMIENTO",
                                "nombre": "Rodamiento",
                                "descripcion": "Rodamiento interno del carro.",
                                "nivel_taxonomico": 9,
                            },
                        ],
                    },
                ],
            },
            {
                "codigo": "SUB_CONTROL_MOV",
                "nombre": "Subunidad de control de movimiento",
                "descripcion": "Controladores y sensores asociados al movimiento.",
                "nivel_taxonomico": 7,
                "children": [
                    {
                        "codigo": "ITEM_SENSOR_POS",
                        "nombre": "Sensor de posición",
                        "descripcion": "Sensor para retroalimentación de posición.",
                        "nivel_taxonomico": 8,
                        "children": [
                            {
                                "codigo": "COMP_CABLE",
                                "nombre": "Cableado de señal",
                                "descripcion": "Cable de señal del sensor de posición.",
                                "nivel_taxonomico": 9,
                            },
                        ],
                    },
                ],
            },
        ],
    },
]


def _crear_clase(data: CatalogNode, padre: Optional[ClaseEquipoISO14224] = None) -> ClaseEquipoISO14224:
    clase, _ = ClaseEquipoISO14224.objects.get_or_create(
        codigo=data["codigo"],
        defaults={
            "nombre": data["nombre"],
            "descripcion": data["descripcion"],
            "nivel_taxonomico": data["nivel_taxonomico"],
            "padre": padre,
        },
    )

    for child in data.get("children", []):
        _crear_clase(child, clase)

    return clase


def cargar_catalogo_iso_basico(force: bool = False) -> int:
    """
    Carga un catálogo ISO 14224 mínimo para los niveles 6–9.

    Args:
        force: si es True, intenta crear los códigos aunque existan otros registros.

    Returns:
        Cantidad de clases creadas o actualizadas.
    """

    if not force and ClaseEquipoISO14224.objects.exists():
        return 0

    creadas = 0
    for nodo in CATALOGO_BASE:
        antes = ClaseEquipoISO14224.objects.count()
        _crear_clase(nodo)
        creadas += ClaseEquipoISO14224.objects.count() - antes

    return creadas
