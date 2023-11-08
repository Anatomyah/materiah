from django.apps import AppConfig


class MateriahConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'materiah'

    def ready(self):
        # from . import apscheduler_config
        # if not hasattr(self, 'scheduler_started'):
        #     apscheduler_config.start_scheduler()
        #     self.scheduler_started = True
        pass
