from django.db import models
from django.db.models import Q

from dispositivos.models import Dispositivo
from operadores.models import Operador
from trabajadores.models import Trabajador


def normalize_iccid(value):
    normalized = ''.join(character for character in str(value or '').upper() if character.isalnum())
    if normalized.startswith('S') and normalized[1:].isdigit():
        normalized = normalized[1:]
    normalized = normalized.rstrip('F')
    if normalized.isdigit() and len(normalized) == 20:
        normalized = normalized[:19]
    return normalized


class Sim(models.Model):
    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.SET_NULL, null=True, blank=True, related_name='sims')
    sim_uuid = models.CharField(max_length=255, unique=True, null=True, blank=True)
    iccid = models.CharField(max_length=255, null=True, blank=True)
    iccid_normalized = models.CharField(max_length=255, blank=True, db_index=True)
    numero_telefonico = models.CharField(max_length=50, null=True, blank=True)
    operador = models.ForeignKey(Operador, on_delete=models.PROTECT, related_name='sims', null=True, blank=True)
    pais = models.CharField(max_length=100, blank=True)
    mcc = models.CharField(max_length=10, blank=True)
    mnc = models.CharField(max_length=10, blank=True)
    slot = models.IntegerField(null=True, blank=True)
    carrier_id = models.IntegerField(null=True, blank=True)
    esim = models.BooleanField(default=False)
    tecnologia = models.CharField(max_length=30, blank=True)
    roaming = models.BooleanField(default=False)
    estado = models.CharField(max_length=50, default='activo')
    sim_datos = models.BooleanField(default=False)
    fecha_alta = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.sim_uuid or self.iccid or f'SIM {self.pk}'

    def save(self, *args, **kwargs):
        self.iccid_normalized = normalize_iccid(self.iccid)
        update_fields = kwargs.get('update_fields')
        if update_fields is not None and 'iccid_normalized' not in update_fields:
            kwargs['update_fields'] = [*update_fields, 'iccid_normalized']
        super().save(*args, **kwargs)


class HistorialSim(models.Model):
    sim = models.ForeignKey(Sim, on_delete=models.CASCADE, related_name='historial')
    dispositivo = models.ForeignKey(
        Dispositivo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historial_sims',
    )
    slot = models.IntegerField(null=True, blank=True)
    desde = models.DateTimeField(auto_now_add=True)
    hasta = models.DateTimeField(null=True, blank=True)
    consumo_mb = models.FloatField(default=0)
    ultimo_reporte = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-desde']

    def __str__(self):
        return f'{self.sim} en {self.dispositivo or "dispositivo eliminado"}'


class SimTransferConflict(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pendiente'
        TRANSFERRED = 'TRANSFERRED', 'Transferida'
        STALE = 'STALE', 'Desactualizada'
        DISMISSED = 'DISMISSED', 'Conservada'
        ACKNOWLEDGED = 'ACKNOWLEDGED', 'Aviso visto'

    sim = models.ForeignKey(Sim, on_delete=models.CASCADE, related_name='transfer_conflicts')
    source_device = models.ForeignKey(
        Dispositivo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='outgoing_sim_transfer_conflicts',
    )
    target_device = models.ForeignKey(
        Dispositivo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incoming_sim_transfer_conflicts',
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['sim', 'target_device'],
                condition=Q(status='PENDING'),
                name='unique_pending_sim_transfer_target',
            ),
        ]

    def __str__(self):
        return f'{self.sim} transfer request ({self.status})'


class AsignacionSim(models.Model):
    sim = models.ForeignKey(Sim, on_delete=models.CASCADE, related_name='asignaciones')
    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE, related_name='sims_asignadas')
    trabajador = models.ForeignKey(Trabajador, on_delete=models.CASCADE, related_name='sims_asignadas')
    slot = models.IntegerField(null=True, blank=True)
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    fecha_finalizacion = models.DateTimeField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.sim} -> {self.dispositivo}'
