"""Configuración de la aplicación de auditoría."""

from django.apps import AppConfig


class AuditoriaConfig(AppConfig):
    """Registra el almacenamiento de eventos de auditoría."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'auditoria'
