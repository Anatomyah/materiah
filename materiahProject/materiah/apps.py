from django.apps import AppConfig


class MateriahConfig(AppConfig):
    """

    MateriahConfig

    This class is a subclass of AppConfig in the Django framework. It is used to configure the 'materiah' app in a Django project.

    Attributes:
        default_auto_field (str): The default auto field for models in this app.
        name (str): The name of the app.

    Methods:
        ready(): An override method called when the Django project is initialized. It imports signals module, starts the scheduler, and sets the 'scheduler_started' attribute.

    Example usage:

    ```python
    class MateriahConfig(AppConfig):
        default_auto_field = 'django.db.models.BigAutoField'
        name = 'materiah'

        def ready(self):
            import materiah.signals
            from . import apscheduler_config
            if not hasattr(self, 'scheduler_started'):
                apscheduler_config.start_scheduler()
                self.scheduler_started = True
    ```

    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'materiah'

    def ready(self):
        import materiah.signals
        from . import apscheduler_config
        if not hasattr(self, 'scheduler_started'):
            apscheduler_config.start_scheduler()
            self.scheduler_started = True
