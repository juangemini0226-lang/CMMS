
from django.core.management.base import BaseCommand, CommandError

from activos.utils.iso14224_seed import cargar_catalogo_iso_basico


class Command(BaseCommand):
    help = "Carga un catálogo ISO 14224 básico (niveles 6–9) para habilitar los menús desplegables."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Crea los códigos base aun si ya existe catálogo cargado.",
        )

    def handle(self, *args, **options):
        force = options.get("force", False)

        try:
            creadas = cargar_catalogo_iso_basico(force=force)
        except Exception as exc:  # pragma: no cover - para trazas explícitas en CLI
            raise CommandError(f"No se pudo cargar el catálogo básico ISO 14224: {exc}") from exc

        if creadas == 0:
            self.stdout.write(self.style.WARNING("No se crearon registros: el catálogo ya tiene datos. Usa --force si quieres intentar recrearlos."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Catálogo ISO 14224 básico cargado ({creadas} clases creadas/actualizadas)."))