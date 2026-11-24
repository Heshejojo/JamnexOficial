"""Configuración de la aplicación de SIM."""

from django.apps import AppConfig


class SimsConfig(AppConfig):
    """Registra los modelos y utilidades de SIM."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sims'
