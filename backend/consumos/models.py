from django.db import models

from dispositivos.models import Dispositivo
from sims.models import Sim


class Consumo(models.Model):
    PERIODICIDAD_CHOICES = [
        ('diario', 'Diario'),
        ('semanal', 'Semanal'),
        ('mensual', 'Mensual'),
        ('personalizado', 'Personalizado'),
    ]
    FUENTE_CHOICES = [
        ('ANDROID', 'Android'),
        ('OPERADOR', 'Operador'),
    ]

    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE, related_name='consumos')
    sim = models.ForeignKey(Sim, on_delete=models.SET_NULL, null=True, blank=True, related_name='consumos')
    consumo_datos_movil = models.FloatField(default=0)
    consumo_wifi = models.FloatField(default=0)
    consumo_total = models.FloatField(default=0)
    fecha = models.DateTimeField()
    periodo = models.CharField(max_length=30, choices=PERIODICIDAD_CHOICES, default='diario')
    fuente = models.CharField(max_length=20, choices=FUENTE_CHOICES, default='ANDROID')

    def __str__(self):
        return f'{self.dispositivo} {self.periodo} {self.consumo_total}'


class ConsumoSyncState(models.Model):
    dispositivo = models.ForeignKey(
        Dispositivo,
        on_delete=models.CASCADE,
        related_name='consumo_sync_states',
    )
    fecha = models.DateField()
    ultimo_acumulado_mb = models.FloatField(default=0)
    sim = models.ForeignKey(
        Sim,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consumo_sync_states',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['dispositivo', 'fecha', 'sim'],
                name='unique_consumption_sync_device_date_sim',
            ),
        ]
