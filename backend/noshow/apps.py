from django.apps import AppConfig


class NoshowConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "noshow"
    verbose_name = "predicción de inasistencia"
