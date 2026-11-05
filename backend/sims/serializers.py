from rest_framework import serializers
from django.db import transaction

from operadores.models import Operador
from .models import AsignacionSim, Sim, SimTransferConflict
from .models import normalize_iccid


class SimSerializer(serializers.ModelSerializer):
    operador = serializers.PrimaryKeyRelatedField(
        queryset=Operador.objects.all(),
        required=False,
        allow_null=True,
    )
    operador_nombre = serializers.CharField(source='operador.nombre', read_only=True, allow_null=True)
    detectada = serializers.SerializerMethodField()
    ultimo_reporte = serializers.SerializerMethodField()
    dispositivos_count = serializers.SerializerMethodField()
    dispositivos_historial = serializers.SerializerMethodField()

    def get_detectada(self, obj):
        return obj.historial.filter(hasta__isnull=True).exists()

    def get_ultimo_reporte(self, obj):
        record = obj.historial.order_by('-ultimo_reporte', '-desde').first()
        return record.ultimo_reporte.isoformat() if record and record.ultimo_reporte else None

    def get_dispositivos_count(self, obj):
        return obj.historial.values('dispositivo_id').distinct().count()

    def get_dispositivos_historial(self, obj):
        records = obj.historial.values('dispositivo_id', 'hasta')
        devices = {}
        for record in records:
            device_id = record['dispositivo_id']
            if device_id is None:
                continue
            entry = devices.setdefault(device_id, {'dispositivo': device_id, 'detectada': False})
            if record['hasta'] is None:
                entry['detectada'] = True
        if obj.dispositivo_id is not None:
            current = devices.setdefault(
                obj.dispositivo_id,
                {'dispositivo': obj.dispositivo_id, 'detectada': False},
            )
            current['detectada'] = current['detectada'] or obj.historial.filter(
                dispositivo_id=obj.dispositivo_id,
                hasta__isnull=True,
            ).exists()
        return list(devices.values())

    class Meta:
        model = Sim
        fields = [
            'id', 'dispositivo', 'sim_uuid', 'iccid', 'numero_telefonico', 'operador', 'operador_nombre', 'pais', 'mcc', 'mnc',
            'slot', 'carrier_id', 'esim', 'tecnologia', 'roaming', 'estado', 'sim_datos',
            'fecha_alta', 'activo', 'detectada', 'ultimo_reporte', 'dispositivos_count',
            'dispositivos_historial',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class SimEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sim
        fields = ['iccid', 'numero_telefonico']

    @transaction.atomic
    def update(self, instance, validated_data):
        iccid = validated_data.get('iccid', instance.iccid)
        normalized = normalize_iccid(iccid)
        duplicate = (
            Sim.objects.select_for_update()
            .filter(iccid_normalized=normalized)
            .exclude(pk=instance.pk)
            .first()
            if normalized
            else None
        )

        if duplicate is not None:
            from consumos.models import Consumo, ConsumoSyncState
            from redes.models import RegistroRed

            duplicate.historial.all().update(sim=instance)
            duplicate.transfer_conflicts.all().update(sim=instance)
            duplicate.asignaciones.all().update(sim=instance)
            Consumo.objects.filter(sim=duplicate).update(sim=instance)
            ConsumoSyncState.objects.filter(sim=duplicate).update(sim=instance)
            RegistroRed.objects.filter(sim=duplicate).update(sim=instance)
            duplicate.delete()

        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


class SimTransferConflictSerializer(serializers.ModelSerializer):
    sim_id = serializers.IntegerField(read_only=True)
    iccid = serializers.CharField(source='sim.iccid', read_only=True, allow_null=True)
    numero_telefonico = serializers.CharField(source='sim.numero_telefonico', read_only=True, allow_null=True)
    source_device_name = serializers.SerializerMethodField()
    target_device_name = serializers.SerializerMethodField()

    class Meta:
        model = SimTransferConflict
        fields = [
            'id', 'sim_id', 'iccid', 'numero_telefonico',
            'source_device', 'source_device_name',
            'target_device', 'target_device_name', 'created_at',
        ]

    @staticmethod
    def _device_name(device):
        if device is None:
            return 'Dispositivo eliminado'
        return ' '.join(filter(None, [device.fabricante, device.modelo])) or device.device_uuid or str(device.pk)

    def get_source_device_name(self, conflict):
        return self._device_name(conflict.source_device)

    def get_target_device_name(self, conflict):
        return self._device_name(conflict.target_device)


class AsignacionSimSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsignacionSim
        fields = ['id', 'sim', 'dispositivo', 'trabajador', 'slot', 'fecha_asignacion', 'fecha_finalizacion', 'activo']
