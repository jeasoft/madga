from django.apps import AppConfig


class MadgaConfig(AppConfig):
    name = "madga"
    verbose_name = "MADGA"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from madga import signals  # noqa: F401
