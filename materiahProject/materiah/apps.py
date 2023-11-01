from django.apps import AppConfig


class MateriahConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'materiah'

    def ready(self):
        pass
