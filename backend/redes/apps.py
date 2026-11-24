"""Configuración de la aplicación de redes."""

from django.apps import AppConfig


class RedesConfig(AppConfig):
    """Registra los estados de conectividad."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'redes'
