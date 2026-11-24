"""Configuración de la aplicación de operadores móviles."""

from django.apps import AppConfig


class OperadoresConfig(AppConfig):
    """Registra el catálogo de operadores."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'operadores'
