from datetime import timedelta

from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from consumos.models import Consumo
from .models import AsignacionSim, HistorialSim, Sim, SimTransferConflict
from .serializers import (
    AsignacionSimSerializer,
    SimEditSerializer,
    SimSerializer,
    SimTransferConflictSerializer,
)
from usuarios.permissions import RolePermission


class SimListCreateAPIView(generics.ListCreateAPIView):
    queryset = Sim.objects.select_related('operador').order_by('-activo', '-updated_at', '-id')
    serializer_class = SimSerializer
    permission_classes = [RolePermission]


class SimDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Sim.objects.select_related('operador').all()
    serializer_class = SimSerializer
    permission_classes = [RolePermission]

    def get_serializer_class(self):
        if self.request.method in {'PUT', 'PATCH'}:
            return SimEditSerializer
        return SimSerializer


class SimStatusAPIView(APIView):
    permission_classes = [RolePermission]

    def post(self, request, pk):
        sim = get_object_or_404(Sim.objects.select_related('dispositivo'), pk=pk)
        if 'activo' not in request.data:
            activo = sim.activo
        else:
            activo = request.data['activo']
            if not isinstance(activo, bool):
                return Response(
                    {'detail': 'El campo activo debe ser verdadero o falso.'},
                    status=400,
                )
        sim.activo = activo
        sim.save(update_fields=['activo', 'updated_at'])
        return Response({'id': sim.id, 'activo': sim.activo})


class SimTransferConflictListAPIView(generics.ListAPIView):
    serializer_class = SimTransferConflictSerializer
    permission_classes = [RolePermission]

    def get_queryset(self):
        return SimTransferConflict.objects.filter(
            status=SimTransferConflict.Status.TRANSFERRED,
        ).select_related('sim', 'source_device', 'target_device').order_by('-created_at')


class SimMovimientosAPIView(APIView):
    permission_classes = [RolePermission]

    @staticmethod
    def _device_name(device):
        if device is None:
            return 'Dispositivo eliminado'
        return ' '.join(filter(None, [device.fabricante, device.modelo])) or device.device_uuid or str(device.pk)

    def get(self, request):
        dias = max(1, int(request.GET.get('dias', 30)))
        cutoff = timezone.now() - timedelta(days=dias)
        records = HistorialSim.objects.filter(
            desde__gte=cutoff,
        ).select_related('sim', 'dispositivo').order_by('-desde')[:50]

        eventos = []
        for record in records:
            previous = HistorialSim.objects.filter(
                sim=record.sim,
                desde__lt=record.desde,
            ).order_by('-desde').first()

            if previous is None:
                tipo = 'nueva'
                anterior_nombre = 'Sin historial previo'
            elif previous.dispositivo_id == record.dispositivo_id:
                tipo = 'reinsertada'
                anterior_nombre = self._device_name(previous.dispositivo)
            else:
                tipo = 'transferencia'
                anterior_nombre = self._device_name(previous.dispositivo)

            eventos.append({
                'id': record.id,
                'tipo': tipo,
                'sim_nombre': record.sim.numero_telefonico or record.sim.iccid or f'SIM #{record.sim_id}',
                'anterior_nombre': anterior_nombre,
                'dispositivo_nombre': self._device_name(record.dispositivo),
                'fecha': record.desde.isoformat(),
            })

        return Response({
            'eventos': eventos,
            'transferencias': sum(1 for event in eventos if event['tipo'] == 'transferencia'),
        })


class SimHistorialAPIView(APIView):
    permission_classes = [RolePermission]

    @staticmethod
    def _device_name(device):
        if device is None:
            return 'Dispositivo eliminado'
        return ' '.join(filter(None, [device.fabricante, device.modelo])) or device.device_uuid or str(device.pk)

    def get(self, request, pk):
        sim = get_object_or_404(Sim.objects.select_related('dispositivo'), pk=pk)
        records = HistorialSim.objects.filter(sim=sim).select_related('dispositivo').order_by('-desde')

        historial = []
        for record in records:
            consumo = Consumo.objects.filter(
                sim=sim,
                dispositivo=record.dispositivo,
                periodo='diario',
                fecha__gte=record.desde,
            )
            if record.hasta:
                consumo = consumo.filter(fecha__lt=record.hasta)
            consumo_mb = consumo.aggregate(total=Sum('consumo_datos_movil'))['total'] or 0

            historial.append({
                'id': record.id,
                'dispositivo': record.dispositivo_id,
                'dispositivo_nombre': self._device_name(record.dispositivo),
                'dispositivo_eliminado': record.dispositivo is None,
                'slot': record.slot,
                'desde': record.desde.isoformat(),
                'hasta': record.hasta.isoformat() if record.hasta else None,
                'actual': record.hasta is None,
                'consumo_mb': float(consumo_mb),
            })

        return Response({
            'historial': historial,
            'total_dispositivos': len({item['dispositivo'] for item in historial if item['dispositivo'] is not None}),
        })


class SimTransferConflictActionAPIView(APIView):
    permission_classes = [RolePermission]

    def post(self, request, pk, action):
        if action not in {'transfer', 'dismiss', 'acknowledge'}:
            return Response({'detail': 'Acción no válida.'}, status=400)
        with transaction.atomic():
            conflict = get_object_or_404(
                SimTransferConflict.objects.select_for_update().select_related('sim'),
                pk=pk,
            )
            if conflict.status != SimTransferConflict.Status.PENDING:
                if (
                    action == 'acknowledge'
                    and conflict.status == SimTransferConflict.Status.TRANSFERRED
                ):
                    conflict.status = SimTransferConflict.Status.ACKNOWLEDGED
                    conflict.resolved_at = timezone.now()
                    conflict.save(update_fields=['status', 'resolved_at'])
                    return Response({'id': conflict.id, 'status': conflict.status})
                return Response({'detail': 'Esta solicitud ya fue atendida.'}, status=409)

            if action == 'transfer':
                sim = Sim.objects.select_for_update().get(pk=conflict.sim_id)
                if not conflict.target_device_id:
                    return Response(
                        {'detail': 'El dispositivo que solicitó la SIM ya no existe.'},
                        status=409,
                    )
                if sim.dispositivo_id != conflict.source_device_id:
                    conflict.status = SimTransferConflict.Status.STALE
                    conflict.resolved_at = timezone.now()
                    conflict.save(update_fields=['status', 'resolved_at'])
                    return Response(
                        {'detail': 'La SIM ya cambió de dispositivo. Actualiza la lista.'},
                        status=409,
                    )

                sim.dispositivo_id = conflict.target_device_id
                sim.activo = True
                sim.save(update_fields=['dispositivo', 'activo', 'updated_at'])
                conflict.status = SimTransferConflict.Status.TRANSFERRED
            elif action == 'dismiss':
                conflict.status = SimTransferConflict.Status.DISMISSED
            conflict.resolved_at = timezone.now()
            conflict.save(update_fields=['status', 'resolved_at'])

        return Response({'id': conflict.id, 'status': conflict.status})


class AsignacionSimListCreateAPIView(generics.ListCreateAPIView):
    queryset = AsignacionSim.objects.select_related('sim', 'dispositivo', 'trabajador').all()
    serializer_class = AsignacionSimSerializer
    permission_classes = [RolePermission]


class AsignacionSimDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = AsignacionSim.objects.all()
    serializer_class = AsignacionSimSerializer
    permission_classes = [RolePermission]
