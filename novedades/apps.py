from django.apps import AppConfig


class NovedadesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'novedades'
    verbose_name = "Novedades"

    def ready(self):
        from . import signals  # noqa: F401