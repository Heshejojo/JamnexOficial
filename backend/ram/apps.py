"""Configuración de la aplicación de monitoreo de memoria RAM."""

from django.apps import AppConfig


class RamConfig(AppConfig):
    """Registra los datos de uso de memoria RAM."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ram'
