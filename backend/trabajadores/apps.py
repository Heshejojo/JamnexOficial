"""Configuración de la aplicación de trabajadores."""

from django.apps import AppConfig


class TrabajadoresConfig(AppConfig):
    """Registra los datos de trabajadores."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'trabajadores'
