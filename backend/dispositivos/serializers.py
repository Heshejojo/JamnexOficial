from rest_framework import serializers

from .models import AsignacionDispositivo, Dispositivo


class DispositivoSerializer(serializers.ModelSerializer):
    en_linea = serializers.BooleanField(source='esta_activo', read_only=True)
    sims_distintas_30d = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Dispositivo
        fields = [
            'id', 'device_uuid', 'fabricante', 'modelo', 'version_android', 'android_sdk',
            'serial', 'imei_1', 'imei_2', 'ram_total', 'almacenamiento_total',
            'activo', 'en_linea', 'ultimo_contacto', 'sim_count_reported',
            'sims_reported_at', 'sims_distintas_30d', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'sim_count_reported', 'sims_reported_at', 'created_at', 'updated_at',
        ]


class DispositivoEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dispositivo
        fields = ['serial', 'imei_1']


class DeviceRegisterSerializer(serializers.Serializer):
    device_uuid = serializers.CharField(max_length=255)
    fabricante = serializers.CharField(max_length=120, allow_blank=True, required=False)
    modelo = serializers.CharField(max_length=120, allow_blank=True, required=False)
    version_android = serializers.CharField(max_length=50, allow_blank=True, required=False)
    imei_1 = serializers.CharField(max_length=255, allow_blank=True, required=False, allow_null=True)
    imei_2 = serializers.CharField(max_length=255, allow_blank=True, required=False, allow_null=True)
    serial = serializers.CharField(max_length=255, allow_blank=True, required=False, allow_null=True)
    android_sdk = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    ram_total = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    almacenamiento_total = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    ram_usada = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    ram_disponible = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    almacenamiento_usado = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    almacenamiento_disponible = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    battery_temperature = serializers.FloatField(required=False, allow_null=True)


class DeviceStatusSerializer(serializers.Serializer):
    device_uuid = serializers.CharField(max_length=255)
    activo = serializers.BooleanField(required=False)
    battery_percent = serializers.IntegerField(min_value=0, max_value=100, required=False, allow_null=True)
    battery_status = serializers.CharField(max_length=30, required=False, allow_blank=True)
    connected = serializers.BooleanField(required=False)
    ram_total = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    almacenamiento_total = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    ram_usada = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    ram_disponible = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    almacenamiento_usado = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    almacenamiento_disponible = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    battery_temperature = serializers.FloatField(required=False, allow_null=True)
    timestamp = serializers.DateTimeField(required=False)


class DeviceConsumptionSerializer(serializers.Serializer):
    consumo_datos_movil = serializers.FloatField(min_value=0, default=0)
    consumo_total = serializers.FloatField(min_value=0, required=False)
    periodo = serializers.ChoiceField(choices=['diario', 'semanal', 'mensual', 'personalizado'], default='diario')
    fecha = serializers.DateTimeField(required=False)
    sim = serializers.IntegerField(required=False, allow_null=True)
    sim_slot = serializers.IntegerField(required=False, allow_null=True)


class DeviceNetworkSerializer(serializers.Serializer):
    tipo_conexion = serializers.ChoiceField(choices=['WIFI', 'DATOS_MOVILES', 'SIN_CONEXION'])


class DeviceSimSerializer(serializers.Serializer):
    sim_uuid = serializers.CharField(max_length=255)
    iccid = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    slot = serializers.IntegerField(min_value=-1, required=False, allow_null=True)
    operador_nombre = serializers.CharField(max_length=120, required=False, allow_blank=True, allow_null=True)
    pais = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    mcc = serializers.CharField(max_length=10, required=False, allow_blank=True, allow_null=True)
    mnc = serializers.CharField(max_length=10, required=False, allow_blank=True, allow_null=True)
    numero_telefonico = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    carrier_id = serializers.IntegerField(required=False, allow_null=True)
    esim = serializers.BooleanField(required=False, allow_null=True)
    tecnologia = serializers.CharField(max_length=30, required=False, allow_blank=True, allow_null=True)
    roaming = serializers.BooleanField(required=False, allow_null=True)


class DeviceSimStatusSerializer(serializers.Serializer):
    sim_count = serializers.IntegerField(min_value=0, max_value=10)
    sim_slots = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=10),
        required=False,
        allow_empty=True,
    )


class AsignacionDispositivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsignacionDispositivo
        fields = ['id', 'dispositivo', 'trabajador', 'fecha_asignacion', 'fecha_finalizacion', 'activo']
