from rest_framework import serializers

from areas.models import Area
from areas.serializers import AreaSerializer
from .models import Trabajador


class TrabajadorSerializer(serializers.ModelSerializer):
    area = AreaSerializer(read_only=True)
    area_id = serializers.PrimaryKeyRelatedField(
        source='area',
        queryset=Area.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Trabajador
        fields = [
            'id', 'numero_empleado', 'nombre', 'apellido_paterno', 'apellido_materno',
            'area', 'area_id', 'activo', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, attrs):
        if attrs.get('area') is None:
            area, _ = Area.objects.get_or_create(
                nombre='General',
                defaults={'descripcion': 'Área por defecto del sistema', 'activo': True},
            )
            attrs['area'] = area
        return attrs
