from rest_framework import serializers

from dispositivos.models import Dispositivo

from .models import Area, Proceso, Subproceso


class ProcesoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proceso
        fields = ['id', 'nombre', 'descripcion', 'activo']


class SubprocesoSerializer(serializers.ModelSerializer):
    proceso_id = serializers.PrimaryKeyRelatedField(
        source='proceso',
        queryset=Proceso.objects.filter(activo=True),
    )
    proceso_nombre = serializers.CharField(source='proceso.nombre', read_only=True)

    class Meta:
        model = Subproceso
        fields = ['id', 'proceso_id', 'proceso_nombre', 'nombre', 'descripcion', 'activo']


class AreaSerializer(serializers.ModelSerializer):
    subproceso_id = serializers.PrimaryKeyRelatedField(
        source='subproceso',
        queryset=Subproceso.objects.filter(activo=True, proceso__activo=True),
        required=False,
        allow_null=True,
    )
    subproceso_nombre = serializers.CharField(
        source='subproceso.nombre',
        read_only=True,
        allow_null=True,
    )
    proceso_nombre = serializers.CharField(
        source='subproceso.proceso.nombre',
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Area
        fields = [
            'id', 'nombre', 'descripcion', 'activo', 'subproceso_id',
            'subproceso_nombre', 'proceso_nombre',
        ]

    def validate(self, attrs):
        subproceso = attrs.get('subproceso', getattr(self.instance, 'subproceso', None))
        if subproceso is None:
            raise serializers.ValidationError({
                'subproceso_id': 'Selecciona la división a la que pertenece esta zona.'
            })
        return attrs


class DispositivoZonaSerializer(serializers.ModelSerializer):
    area_id = serializers.PrimaryKeyRelatedField(
        source='area',
        queryset=Area.objects.filter(activo=True, subproceso__activo=True, subproceso__proceso__activo=True),
        required=False,
        allow_null=True,
    )
    zona_nombre = serializers.CharField(source='area.nombre', read_only=True, allow_null=True)
    division_nombre = serializers.CharField(
        source='area.subproceso.nombre',
        read_only=True,
        allow_null=True,
    )
    distribucion_nombre = serializers.CharField(
        source='area.subproceso.proceso.nombre',
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Dispositivo
        fields = [
            'id', 'device_uuid', 'fabricante', 'modelo', 'area_id',
            'zona_nombre', 'division_nombre', 'distribucion_nombre',
        ]
