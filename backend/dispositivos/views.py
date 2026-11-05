import hashlib
import secrets
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import authentication, generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from consumos.models import Consumo, ConsumoSyncState
from bateria.models import RegistroBateria
from ram.models import RegistroRam
from almacenamiento.models import RegistroAlmacenamiento
from redes.models import RegistroRed
from sims.history import close_missing, register_presence
from sims.models import Sim, SimTransferConflict, normalize_iccid
from operadores.models import Operador

from .models import CredencialDispositivo, Dispositivo
from .serializers import DeviceConsumptionSerializer, DeviceNetworkSerializer, DeviceRegisterSerializer, DeviceSimSerializer, DeviceSimStatusSerializer, DeviceStatusSerializer, DispositivoEditSerializer, DispositivoSerializer
from usuarios.permissions import RolePermission
from auditoria.services import record_action


DEVICE_MODEL_FIELDS = {
    'fabricante', 'modelo', 'version_android', 'android_sdk',
    'imei_2', 'ram_total', 'almacenamiento_total',
}


class DeviceAuthentication(authentication.BaseAuthentication):
    keyword = 'Device'

    def authenticate(self, request):
        header = request.headers.get('Authorization', '')
        if not header.startswith(f'{self.keyword} '):
            return None

        raw_token = header[len(self.keyword) + 1:].strip()
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        credential = CredencialDispositivo.objects.select_related('dispositivo').filter(
            token_hash=token_hash, revocado=False, dispositivo__activo=True
        ).first()
        if not credential:
            return None

        credential.ultimo_uso = timezone.now()
        credential.save(update_fields=['ultimo_uso'])
        return credential.dispositivo, credential


class DeviceRegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = DeviceRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        device_defaults = {
            key: value
            for key, value in data.items()
            if key in DEVICE_MODEL_FIELDS
        }
        device, created = Dispositivo.objects.get_or_create(
            device_uuid=data['device_uuid'],
            defaults={
                **device_defaults,
                'serial': data.get('serial'),
                'imei_1': data.get('imei_1'),
            },
        )
        if not created:
            for field, value in device_defaults.items():
                setattr(device, field, value)
            update_fields = [*device_defaults, 'updated_at']
            for field in ('serial', 'imei_1'):
                current_value = getattr(device, field)
                generic_serial = field == 'serial' and (
                    not current_value
                    or current_value.strip().lower() in {'unknown', 'null'}
                    or current_value == device.device_uuid
                )
                if (generic_serial or not current_value) and data.get(field):
                    setattr(device, field, data[field])
                    update_fields.append(field)
            device.save(update_fields=update_fields)
        raw_token = secrets.token_urlsafe(32)
        CredencialDispositivo.objects.update_or_create(
            dispositivo=device,
            defaults={'token_hash': hashlib.sha256(raw_token.encode()).hexdigest(), 'revocado': False},
        )
        return Response({'device_id': device.id, 'device_uuid': device.device_uuid, 'token': raw_token}, status=status.HTTP_201_CREATED)


class DeviceStatusView(APIView):
    authentication_classes = [DeviceAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = DeviceStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        device = request.user
        if data.get('activo') is not None:
            device.activo = data['activo']
        device.ultimo_contacto = timezone.now()
        device.save(update_fields=['activo', 'ultimo_contacto', 'updated_at'])
        if data.get('battery_percent') is not None:
            state = (data.get('battery_status') or 'DESCONOCIDO').upper()
            state = {'COMPLETA': 'CARGADA', 'DESCONOCIDA': 'DESCONOCIDO'}.get(state, state)
            if state not in {'CARGANDO', 'DESCARGANDO', 'CARGADA', 'DESCONOCIDO'}:
                state = 'DESCONOCIDO'
            RegistroBateria.objects.create(
                dispositivo=device,
                porcentaje=data['battery_percent'],
                estado=state,
                temperatura=data.get('battery_temperature'),
            )
        if data.get('ram_total') is not None:
            RegistroRam.objects.create(
                dispositivo=device,
                ram_total=data['ram_total'],
                ram_usada=data.get('ram_usada') or 0,
                ram_disponible=data.get('ram_disponible') or 0,
            )
        if data.get('almacenamiento_total') is not None:
            RegistroAlmacenamiento.objects.create(
                dispositivo=device,
                almacenamiento_total=data['almacenamiento_total'],
                usado=data.get('almacenamiento_usado') or 0,
                disponible=data.get('almacenamiento_disponible') or 0,
            )
        return Response({'device_id': device.id, 'received_at': timezone.now()})


class DeviceNetworkView(APIView):
    authentication_classes = [DeviceAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = DeviceNetworkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        sim = Sim.objects.filter(dispositivo=request.user).order_by('-updated_at').first()
        record = RegistroRed.objects.create(
            dispositivo=request.user,
            sim=sim,
            tipo_conexion=data['tipo_conexion'],
        )
        return Response({'id': record.id, 'received_at': timezone.now()}, status=status.HTTP_201_CREATED)


class DeviceSimView(APIView):
    authentication_classes = [DeviceAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = DeviceSimSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        incoming_iccid = data.get('iccid')
        normalized_iccid = normalize_iccid(incoming_iccid)
        operador_nombre = data.pop('operador_nombre', None)
        operador = None
        if operador_nombre:
            operador, _ = Operador.objects.get_or_create(
                nombre=operador_nombre,
                defaults={'pais': data.get('pais') or '', 'activo': True},
            )
        sim_defaults = {
            'dispositivo': request.user,
            'slot': data['slot'] if data.get('slot') is not None and data['slot'] >= 0 else None,
            'mcc': data.get('mcc') or '',
            'mnc': data.get('mnc') or '',
            'operador': operador,
            'pais': data.get('pais') or '',
            'carrier_id': data.get('carrier_id'),
            'esim': bool(data.get('esim')),
            'tecnologia': data.get('tecnologia') or '',
            'roaming': bool(data.get('roaming')),
            'activo': True,
        }

        with transaction.atomic():
            sim = None
            if normalized_iccid:
                sim = Sim.objects.select_for_update().filter(
                    iccid_normalized=normalized_iccid,
                ).order_by('pk').first()
            if sim is None:
                sim = Sim.objects.select_for_update().filter(
                    sim_uuid=data['sim_uuid'],
                ).first()
                if sim and sim.dispositivo_id not in (None, request.user.pk):
                    scoped_uuid = (
                        f"device-{request.user.pk}-"
                        f"{hashlib.sha256(data['sim_uuid'].encode()).hexdigest()}"
                    )
                    sim = Sim.objects.select_for_update().filter(sim_uuid=scoped_uuid).first()
                    data['sim_uuid'] = scoped_uuid

            transferred = bool(sim and sim.dispositivo_id not in (None, request.user.pk))
            source_device_id = sim.dispositivo_id if transferred else None
            if sim is None:
                sim = Sim.objects.create(
                    sim_uuid=data['sim_uuid'],
                    iccid=incoming_iccid,
                    numero_telefonico=data.get('numero_telefonico'),
                    **sim_defaults,
                )
            else:
                for field, value in sim_defaults.items():
                    setattr(sim, field, value)
                update_fields = list(sim_defaults)
                if sim.dispositivo_id is None or transferred:
                    sim.dispositivo = request.user
                    update_fields.append('dispositivo')
                if not sim.iccid and incoming_iccid:
                    sim.iccid = incoming_iccid
                    update_fields.append('iccid')
                if not sim.numero_telefonico and data.get('numero_telefonico'):
                    sim.numero_telefonico = data['numero_telefonico']
                    update_fields.append('numero_telefonico')
                sim.save(update_fields=[*update_fields, 'updated_at'])

            if transferred:
                resolved_at = timezone.now()
                SimTransferConflict.objects.filter(
                    sim=sim,
                    target_device=request.user,
                    status=SimTransferConflict.Status.PENDING,
                ).update(
                    status=SimTransferConflict.Status.TRANSFERRED,
                    resolved_at=resolved_at,
                )
                SimTransferConflict.objects.create(
                    sim=sim,
                    source_device_id=source_device_id,
                    target_device=request.user,
                    status=SimTransferConflict.Status.TRANSFERRED,
                    resolved_at=resolved_at,
                )

            register_presence(sim, request.user, sim.slot)
            active_sims = Sim.objects.filter(dispositivo=request.user, activo=True).count()
            if request.user.sim_count_reported is None or request.user.sim_count_reported < active_sims:
                request.user.sim_count_reported = active_sims
                request.user.sims_reported_at = timezone.now()
                request.user.save(update_fields=['sim_count_reported', 'sims_reported_at', 'updated_at'])
            Consumo.objects.filter(dispositivo=request.user, sim__isnull=True).update(sim=sim)
            response_data = {
                'id': sim.id,
                'available': True,
                'transferred': transferred,
            }
        return Response(response_data, status=status.HTTP_200_OK if transferred else status.HTTP_201_CREATED)


class DeviceSimStatusView(APIView):
    authentication_classes = [DeviceAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = DeviceSimStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reported_at = timezone.now()
        request.user.sim_count_reported = serializer.validated_data['sim_count']
        request.user.sims_reported_at = reported_at
        request.user.save(update_fields=['sim_count_reported', 'sims_reported_at', 'updated_at'])
        close_missing(
            request.user,
            request.user.sim_count_reported,
            reported_at,
            serializer.validated_data.get('sim_slots'),
        )
        return Response({
            'sim_count': request.user.sim_count_reported,
            'reported_at': reported_at,
        })


class DeviceConsumptionView(APIView):
    authentication_classes = [DeviceAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = DeviceConsumptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        mobile_data = data['consumo_datos_movil']
        total = mobile_data
        fecha = data.get('fecha', timezone.now())
        sim = None

        with transaction.atomic():
            device = type(request.user).objects.select_for_update().get(pk=request.user.pk)
            if 'sim_slot' in data:
                if data['sim_slot'] is not None and data['sim_slot'] >= 0:
                    sim = Sim.objects.filter(
                        dispositivo=device,
                        slot=data['sim_slot'],
                    ).order_by('-updated_at').first()
            elif data.get('sim'):
                sim = Sim.objects.filter(
                    pk=data['sim'],
                    dispositivo=device,
                ).first()
            else:
                sim = Sim.objects.filter(dispositivo=device).order_by('-updated_at').first()

            if sim is None and data['periodo'] == 'diario':
                active_sims = Sim.objects.filter(
                    dispositivo=device,
                    activo=True,
                )
                if active_sims.count() == 1:
                    sim = active_sims.first()

            if data['periodo'] != 'diario':
                monthly_report = data['periodo'] == 'mensual'
                local_date = timezone.localtime(fecha).date()
                consumption_period = Consumo.objects.filter(
                    dispositivo=device,
                    sim=sim,
                    periodo=data['periodo'],
                )
                if monthly_report:
                    consumption_period = consumption_period.filter(
                        fecha__year=local_date.year,
                        fecha__month=local_date.month,
                    )
                else:
                    consumption_period = consumption_period.filter(
                        fecha__date=local_date,
                    )
                consumo = consumption_period.order_by('-fecha', '-pk').first()
                if consumo:
                    consumo.consumo_datos_movil = mobile_data
                    consumo.consumo_total = total
                    consumo.fecha = fecha
                    consumo.save(update_fields=['consumo_datos_movil', 'consumo_total', 'fecha'])
                else:
                    consumo = Consumo.objects.create(
                        dispositivo=device,
                        sim=sim,
                        consumo_datos_movil=mobile_data,
                        consumo_total=total,
                        periodo=data['periodo'],
                        fecha=fecha,
                        fuente='ANDROID',
                    )
                return Response(
                    {'id': consumo.id, 'consumo_total': consumo.consumo_total},
                    status=status.HTTP_201_CREATED,
                )

            state, created = ConsumoSyncState.objects.get_or_create(
                dispositivo=device,
                fecha=fecha.date(),
                sim=sim,
                defaults={'ultimo_acumulado_mb': 0},
            )
            if created:
                previous_daily_total = Consumo.objects.filter(
                    dispositivo=device,
                    sim=sim,
                    periodo='diario',
                    fecha__date=fecha.date(),
                ).aggregate(total=Sum('consumo_datos_movil'))['total'] or 0
                state.ultimo_acumulado_mb = previous_daily_total

            delta = (
                mobile_data - state.ultimo_acumulado_mb
                if mobile_data >= state.ultimo_acumulado_mb
                else mobile_data
            )
            state.ultimo_acumulado_mb = mobile_data
            state.save(update_fields=['ultimo_acumulado_mb', 'updated_at'])

            if sim and delta > 0:
                consumo = Consumo.objects.filter(
                    dispositivo=device,
                    sim=sim,
                    periodo='diario',
                    fecha__date=fecha.date(),
                ).order_by('pk').first()
                if consumo:
                    consumo.consumo_datos_movil += delta
                    consumo.consumo_total = consumo.consumo_datos_movil
                    consumo.fecha = fecha
                    consumo.save(update_fields=['consumo_datos_movil', 'consumo_total', 'fecha'])
                else:
                    consumo = Consumo.objects.create(
                        dispositivo=device,
                        sim=sim,
                        consumo_datos_movil=delta,
                        consumo_total=delta,
                        periodo='diario',
                        fecha=fecha,
                        fuente='ANDROID',
                    )
            else:
                consumo = None

        if consumo is None:
            return Response(
                {'id': None, 'consumo_total': 0, 'delta_aplicado': 0},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {
                'id': consumo.id,
                'consumo_total': consumo.consumo_total,
                'delta_aplicado': delta,
            },
            status=status.HTTP_201_CREATED,
        )


class DeviceRevokeView(APIView):
    permission_classes = [RolePermission]

    def post(self, request, pk):
        device = Dispositivo.objects.get(pk=pk)
        credential = getattr(device, 'credencial', None)
        if credential:
            credential.revocado = True
            credential.save(update_fields=['revocado'])
        device.activo = False
        device.save(update_fields=['activo', 'updated_at'])
        record_action(request, 'REVOCAR', 'dispositivos', device.pk, 'Credencial de dispositivo revocada')
        return Response({'device_id': device.pk, 'revocado': True})


def dispositivos_queryset():
    """Dispositivos con cuantas SIM distintas han tenido en los ultimos 30 dias.

    Sirve aunque el celular no mande el ICCID: cada SIM que entra a un equipo
    queda registrada, asi que un equipo que cambia mucho de SIM se nota.
    """
    cutoff = timezone.now() - timedelta(days=30)
    return Dispositivo.objects.annotate(
        sims_distintas_30d=Count(
            'historial_sims__sim',
            filter=Q(historial_sims__hasta__isnull=True) | Q(historial_sims__hasta__gte=cutoff),
            distinct=True,
        ),
    ).order_by('id')


class DispositivoListCreateAPIView(generics.ListCreateAPIView):
    queryset = Dispositivo.objects.all()
    serializer_class = DispositivoSerializer
    permission_classes = [RolePermission]

    def get_queryset(self):
        return dispositivos_queryset()


class DispositivoDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Dispositivo.objects.all()
    serializer_class = DispositivoSerializer
    permission_classes = [RolePermission]

    def get_queryset(self):
        return dispositivos_queryset()

    def get_serializer_class(self):
        if self.request.method in {'PUT', 'PATCH'}:
            return DispositivoEditSerializer
        return DispositivoSerializer

    def perform_update(self, serializer):
        device = serializer.save()
        record_action(self.request, 'MODIFICAR', 'dispositivos', device.pk, 'Dispositivo modificado')

    def perform_destroy(self, instance):
        record_action(self.request, 'ELIMINAR', 'dispositivos', instance.pk, 'Dispositivo eliminado')
        instance.delete()
