from django.apps import AppConfig


class LegislativoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.legislativo'
    verbose_name = 'Legislativo FNP'

    def ready(self):
        from . import signals  # noqa: F401
