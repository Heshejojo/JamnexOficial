"""Configuración de la aplicación de áreas operativas."""

from django.apps import AppConfig


class AreasConfig(AppConfig):
    """Registra los catálogos de organización territorial."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'areas'
