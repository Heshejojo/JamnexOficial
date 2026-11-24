"""Identidad, credenciales y asignaciones de dispositivos móviles."""

from datetime import timedelta

from django.db import models
from django.utils import timezone

from areas.models import Area
from trabajadores.models import Trabajador


class Dispositivo(models.Model):
    """Equipo registrado con su actividad reciente y SIM reportadas."""

    device_uuid = models.CharField(max_length=255, unique=True, null=True, blank=True)
    fabricante = models.CharField(max_length=120, null=True, blank=True)
    modelo = models.CharField(max_length=120, null=True, blank=True)
    version_android = models.CharField(max_length=50, null=True, blank=True)
    android_sdk = models.IntegerField(null=True, blank=True)
    serial = models.CharField(max_length=255, null=True, blank=True)
    imei_1 = models.CharField(max_length=255, null=True, blank=True)
    imei_2 = models.CharField(max_length=255, null=True, blank=True)
    ram_total = models.BigIntegerField(null=True, blank=True)
    almacenamiento_total = models.BigIntegerField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    ultimo_contacto = models.DateTimeField(null=True, blank=True)
    sim_count_reported = models.PositiveSmallIntegerField(null=True, blank=True)
    sims_reported_at = models.DateTimeField(null=True, blank=True)
    area = models.ForeignKey(
        Area,
        on_delete=models.SET_NULL,
        related_name='dispositivos',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.modelo or self.device_uuid or f'Dispositivo {self.pk}'

    @property
    def esta_activo(self):
        """Indica si el equipo está habilitado y tuvo contacto en las últimas 72 h."""
        return bool(
            self.activo
            and self.ultimo_contacto
            and self.ultimo_contacto >= timezone.now() - timedelta(hours=72)
        )

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False


class CredencialDispositivo(models.Model):
    """Token del equipo almacenado como hash para autenticar sincronizaciones."""

    dispositivo = models.OneToOneField(Dispositivo, on_delete=models.CASCADE, related_name='credencial')
    token_hash = models.CharField(max_length=128, unique=True)
    creado_at = models.DateTimeField(auto_now_add=True)
    ultimo_uso = models.DateTimeField(null=True, blank=True)
    revocado = models.BooleanField(default=False)

    def __str__(self):
        return f'Credencial de {self.dispositivo}'


class AsignacionDispositivo(models.Model):
    """Relación de asignación entre un dispositivo y un trabajador."""

    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE, related_name='asignaciones')
    trabajador = models.ForeignKey(Trabajador, on_delete=models.CASCADE, related_name='dispositivos_asignados')
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    fecha_finalizacion = models.DateTimeField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.dispositivo} -> {self.trabajador}'
