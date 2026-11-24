"""Apertura y cierre transaccional de intervalos de presencia de SIM."""

from django.db import transaction
from django.utils import timezone

from .models import HistorialSim


def register_presence(sim, dispositivo, slot=None):
    """Registra presencia y cierra el intervalo desplazado por equipo o ranura."""
    if sim is None or dispositivo is None:
        return None

    now = timezone.now()
    with transaction.atomic():
        if slot is not None:
            HistorialSim.objects.filter(
                dispositivo=dispositivo,
                slot=slot,
                hasta__isnull=True,
            ).exclude(sim=sim).update(hasta=now, updated_at=now)
        HistorialSim.objects.filter(sim=sim, hasta__isnull=True).exclude(
            dispositivo_id=dispositivo.pk,
        ).update(hasta=now)

        record = HistorialSim.objects.filter(
            sim=sim,
            dispositivo=dispositivo,
            hasta__isnull=True,
        ).order_by('-desde').first()

        if record is None:
            record = HistorialSim.objects.create(
                sim=sim,
                dispositivo=dispositivo,
                slot=slot,
                desde=now,
                ultimo_reporte=now,
            )
        else:
            record.slot = slot if slot is not None else record.slot
            record.ultimo_reporte = now
            record.save(update_fields=['slot', 'ultimo_reporte', 'updated_at'])

        return record


def close_missing(dispositivo, expected_count, reported_at=None, reported_slots=None):
    """Cierra presencias ausentes: prioriza ranuras reportadas y usa el conteo de respaldo.

    Si no se conoce el conteo, conserva las presencias abiertas; los intervalos cerrados
    permanecen disponibles para consultar el historial.
    """
    if dispositivo is None:
        return None

    reported_at = reported_at or timezone.now()
    with transaction.atomic():
        records = HistorialSim.objects.filter(
            dispositivo=dispositivo,
            hasta__isnull=True,
        ).order_by('desde')

        if reported_slots is not None:
            reported_slots = set(reported_slots)
            missing = records.exclude(slot__in=reported_slots)
            missing_sim_ids = list(missing.values_list('sim_id', flat=True))
            missing.update(hasta=reported_at, updated_at=reported_at)
            return missing.count()

        if expected_count is None:
            return records.count()

        if expected_count <= 0:
            records.update(hasta=reported_at)
            return 0

        for record in list(records[expected_count:]):
            record.hasta = reported_at
            record.save(update_fields=['hasta', 'updated_at'])

        return max(0, records.count() - expected_count)
