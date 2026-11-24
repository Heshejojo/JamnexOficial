"""Configuración de la aplicación de almacenamiento."""

from django.apps import AppConfig


class AlmacenamientoConfig(AppConfig):
    """Registra los componentes de almacenamiento en Django."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'almacenamiento'
