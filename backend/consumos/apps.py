"""Configuración de la aplicación de consumo de datos."""

from django.apps import AppConfig


class ConsumosConfig(AppConfig):
    """Registra los modelos de consumo y sincronización."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'consumos'
