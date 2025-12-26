from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from activos.models import (
    FamiliaActivo,
    NivelJerarquia,
    NodoActivo,
    Organizacion,
)


class Command(BaseCommand):
    help = (
        "Crea una serie completa de activos siguiendo el plan de trabajo "
        "de la aplicación (niveles ISO 14224 del 1 al 9)."
    )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("╔══════════════════════════════════════════════╗"))
        self.stdout.write(self.style.SUCCESS("║  CREACIÓN GUIADA DE ACTIVOS (PLAN DE TRABAJO) ║"))
        self.stdout.write(self.style.SUCCESS("╚══════════════════════════════════════════════╝"))

        admin_user = self._obtener_o_crear_usuario_admin()
        organizacion = self._obtener_o_crear_organizacion(admin_user)
        niveles = self._obtener_o_crear_niveles(organizacion)
        familias = self._obtener_o_crear_familias(organizacion)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("🚀 Iniciando carga de activos según la jerarquía ISO 14224"))

        activos_plan = [
            {
                "codigo": "IND-ESTRA",
                "nombre": "Gestión Integral de Residuos",
                "nivel": 1,
                "descripcion": "Industria principal de manejo y valorización de residuos",
                "familia": "Infraestructura",
                "datos_personalizados": {
                    "linea_base": "ISO 14224",
                    "enfoque": "Industria",
                },
                "children": [
                    {
                        "codigo": "NEG-COLECTA",
                        "nombre": "Recolección y Transporte",
                        "nivel": 2,
                        "descripcion": "Línea de negocio enfocada en recolección y transferencia",
                        "familia": "Infraestructura",
                        "children": [
                            {
                                "codigo": "INS-MED",
                                "nombre": "Centro Operativo Medellín",
                                "nivel": 3,
                                "descripcion": "Base operativa urbana para rutas de recolección",
                                "familia": "Infraestructura",
                                "datos_personalizados": {
                                    "coordenadas": "6.2442, -75.5812",
                                    "turnos": "24/7",
                                },
                                "children": [
                                    {
                                        "codigo": "PLA-PTAR",
                                        "nombre": "Planta de Tratamiento Norte",
                                        "nivel": 4,
                                        "familia": "Infraestructura",
                                        "descripcion": "Planta principal con líneas de tratamiento y aire comprimido",
                                        "children": [
                                            {
                                                "codigo": "SIS-BOM",
                                                "nombre": "Sistema de Bombeo de Lodos",
                                                "nivel": 5,
                                                "familia": "Sistema de bombeo",
                                                "descripcion": "Red de bombeo hacia digestores y espesadores",
                                                "datos_personalizados": {
                                                    "fluido": "Lodos",
                                                    "presion_diseno_bar": 8,
                                                },
                                                "children": [
                                                    {
                                                        "codigo": "EQ-BP1",
                                                        "nombre": "Bomba Progresiva Principal",
                                                        "nivel": 6,
                                                        "familia": "Equipos rotativos",
                                                        "descripcion": "Bomba progresiva para transferencia de lodo",
                                                        "fabricante": "Seepex",
                                                        "modelo": "MD 012-24",
                                                        "numero_serie": "BP1-2023-ESTRA",
                                                        "criticidad": "alta",
                                                        "datos_personalizados": {
                                                            "flujo_m3h": 12,
                                                            "rpm_operacion": 480,
                                                        },
                                                        "children": [
                                                            {
                                                                "codigo": "SU-HID",
                                                                "nombre": "Tren Hidráulico",
                                                                "nivel": 7,
                                                                "familia": "Subcomponentes",
                                                                "descripcion": "Elementos hidráulicos de potencia y control",
                                                                "children": [
                                                                    {
                                                                        "codigo": "IM-MOT",
                                                                        "nombre": "Motor Principal",
                                                                        "nivel": 8,
                                                                        "familia": "Subcomponentes",
                                                                        "descripcion": "Motor eléctrico 25 HP",
                                                                        "fabricante": "WEG",
                                                                        "modelo": "W22",
                                                                        "numero_serie": "MOT-25HP-W22",
                                                                        "criticidad": "media",
                                                                        "children": [
                                                                            {
                                                                                "codigo": "P-ROD-A",
                                                                                "nombre": "Rodamiento Lado Conducción",
                                                                                "nivel": 9,
                                                                                "familia": "Subcomponentes",
                                                                                "descripcion": "Rodamiento 6314 C3",
                                                                                "criticidad": "media",
                                                                                "datos_personalizados": {
                                                                                    "proveedor": "SKF",
                                                                                    "inventario_min": 2,
                                                                                },
                                                                            }
                                                                        ],
                                                                    }
                                                                ],
                                                            }
                                                        ],
                                                    },
                                                    {
                                                        "codigo": "EQ-BP2",
                                                        "nombre": "Bomba de Reserva",
                                                        "nivel": 6,
                                                        "familia": "Equipos rotativos",
                                                        "descripcion": "Equipo redundante para continuidad operativa",
                                                        "fabricante": "Seepex",
                                                        "modelo": "MD 012-24",
                                                        "numero_serie": "BP2-2023-ESTRA",
                                                        "criticidad": "media",
                                                    },
                                                ],
                                            },
                                            {
                                                "codigo": "SIS-AIRE",
                                                "nombre": "Sistema de Aire Comprimido",
                                                "nivel": 5,
                                                "familia": "Sistema de aire",
                                                "descripcion": "Distribución de aire para instrumentación y actuadores",
                                                "children": [
                                                    {
                                                        "codigo": "EQ-COMP1",
                                                        "nombre": "Compresor Tornillo",
                                                        "nivel": 6,
                                                        "familia": "Equipos rotativos",
                                                        "descripcion": "Compresor principal de 45 kW",
                                                        "fabricante": "Atlas Copco",
                                                        "modelo": "GA 45",
                                                        "numero_serie": "AC-GA45-001",
                                                        "criticidad": "alta",
                                                        "datos_personalizados": {
                                                            "presion_bar": 7.5,
                                                            "caudal_lmin": 7800,
                                                        },
                                                    }
                                                ],
                                            },
                                        ],
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ]

        creados, actualizados = self._crear_activos_recursivos(
            activos_plan, niveles, familias, organizacion, admin_user
        )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("📊 Resumen"))
        self.stdout.write(self.style.SUCCESS(f"   ✓ Activos creados: {creados}"))
        self.stdout.write(self.style.SUCCESS(f"   ↻ Activos actualizados: {actualizados}"))
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("✅ Plan de trabajo aplicado correctamente"))

    def _obtener_o_crear_usuario_admin(self):
        admin_user, creado = User.objects.get_or_create(
            username="admin",
            defaults={"email": "admin@estra.com"},
        )
        if creado:
            admin_user.set_password("admin123")
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("✓ Usuario administrador creado (admin / admin123)"))
        else:
            self.stdout.write(self.style.WARNING("⚠ Usuario administrador existente reutilizado"))
        return admin_user

    def _obtener_o_crear_organizacion(self, admin_user):
        organizacion, creada = Organizacion.objects.get_or_create(
            codigo="ESTRA",
            defaults={
                "nombre": "Estra Soluciones",
                "descripcion": "Organización base para la carga de activos",
                "creado_por": admin_user,
            },
        )
        if creada:
            self.stdout.write(self.style.SUCCESS("✓ Organización 'Estra Soluciones' creada"))
        else:
            self.stdout.write(self.style.WARNING("⚠ Organización 'Estra Soluciones' ya existía"))
        return organizacion

    def _obtener_o_crear_niveles(self, organizacion):
        niveles = NivelJerarquia.objects.filter(organizacion=organizacion)
        if niveles.exists():
            self.stdout.write(self.style.WARNING("⚠ Niveles ISO 14224 ya configurados: se reutilizarán"))
            return {nivel.numero_nivel: nivel for nivel in niveles}

        self.stdout.write(self.style.SUCCESS("🧭 Creando niveles ISO 14224 (1-9)"))
        niveles_config = [
            (1, "Industria", False, False, "", ""),
            (2, "Negocio", False, False, "", ""),
            (3, "Instalación", False, True, "I", "{PREFIJO}-{CODIGO}"),
            (4, "Planta/Unidad", False, True, "P", "{PADRE}-{PREFIJO}-{CODIGO}"),
            (5, "Sección/Sistema", False, True, "S", "{PADRE}-{PREFIJO}-{CODIGO}"),
            (6, "Equipo", True, True, "EQ", "{PADRE}-{PREFIJO}-{SECUENCIA}"),
            (7, "Subunidad", False, True, "SU", "{PADRE}-{PREFIJO}-{SECUENCIA}"),
            (8, "Item Mantenible", False, True, "IM", "{PADRE}-{PREFIJO}-{SECUENCIA}"),
            (9, "Parte/Pieza", False, True, "P", "{PADRE}-{PREFIJO}-{SECUENCIA}"),
        ]

        niveles_creados = {}
        for numero, nombre, es_equipo, requiere_tag, prefijo, formato in niveles_config:
            niveles_creados[numero] = NivelJerarquia.objects.create(
                organizacion=organizacion,
                numero_nivel=numero,
                nombre_nivel=nombre,
                descripcion=f"Nivel {numero} - {nombre}",
                corresponde_iso_14224=numero,
                es_nivel_equipo=es_equipo,
                requiere_tag=requiere_tag,
                prefijo_tag=prefijo,
                formato_tag=formato,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"   ✓ Nivel {numero}: {nombre} (TAG automático: {requiere_tag})"
                )
            )
        return niveles_creados

    def _obtener_o_crear_familias(self, organizacion):
        familias_config = {
            "Infraestructura": "Elementos de soporte físico y ubicación",
            "Sistema de bombeo": "Sistemas hidráulicos y de transferencia",
            "Equipos rotativos": "Bombas, compresores y rotativos",
            "Subcomponentes": "Subconjuntos y partes mantenibles",
            "Sistema de aire": "Redes y equipos de aire comprimido",
        }

        familias = {}
        for nombre, descripcion in familias_config.items():
            familia, _ = FamiliaActivo.objects.get_or_create(
                organizacion=organizacion, nombre=nombre, defaults={"descripcion": descripcion}
            )
            familias[nombre] = familia
            self.stdout.write(self.style.SUCCESS(f"✓ Familia preparada: {nombre}"))
        return familias

    def _crear_activos_recursivos(self, activos, niveles, familias, organizacion, usuario, parent=None):
        creados = 0
        actualizados = 0

        for activo in activos:
            nivel = niveles[activo["nivel"]]
            familia = familias.get(activo.get("familia"))

            objeto, creado = NodoActivo.objects.update_or_create(
                organizacion=organizacion,
                codigo=activo["codigo"],
                defaults={
                    "nivel_jerarquia": nivel,
                    "nombre": activo["nombre"],
                    "descripcion": activo.get("descripcion", ""),
                    "familia": familia,
                    "parent": parent,
                    "fabricante": activo.get("fabricante", ""),
                    "modelo": activo.get("modelo", ""),
                    "numero_serie": activo.get("numero_serie", ""),
                    "criticidad": activo.get("criticidad", ""),
                    "datos_personalizados": activo.get("datos_personalizados", {}),
                    "creado_por": usuario,
                },
            )

            if creado:
                creados += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"   [+] {objeto.obtener_ruta_completa()} (Nivel {nivel.numero_nivel})"
                    )
                )
            else:
                actualizados += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"   [↻] {objeto.obtener_ruta_completa()} actualizado (Nivel {nivel.numero_nivel})"
                    )
                )

            hijos = activo.get("children", [])
            sub_creados, sub_actualizados = self._crear_activos_recursivos(
                hijos, niveles, familias, organizacion, usuario, parent=objeto
            )
            creados += sub_creados
            actualizados += sub_actualizados

        return creados, actualizados