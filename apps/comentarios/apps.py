from django.apps import AppConfig


class ComentariosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.comentarios'
    verbose_name = 'Comentários e Participação'

    def ready(self):
        # Conecta os signals de alerta de movimentação (proposição seguida).
        from . import alertas  # noqa: F401
