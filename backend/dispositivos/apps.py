"""Configuración de la aplicación de dispositivos."""

from django.apps import AppConfig


class DispositivosConfig(AppConfig):
    """Registra los modelos y servicios de dispositivos móviles."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dispositivos'
