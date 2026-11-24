"""Configuración de la aplicación de reportes."""

from django.apps import AppConfig


class ReportesConfig(AppConfig):
    """Registra las vistas de reportes y resumen operativo."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reportes'
