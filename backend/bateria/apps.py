"""Configuración de la aplicación de batería."""

from django.apps import AppConfig


class BateriaConfig(AppConfig):
    """Registra los datos de monitoreo de batería."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bateria'
