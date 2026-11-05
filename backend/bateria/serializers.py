from rest_framework import serializers

from .models import RegistroBateria


class RegistroBateriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroBateria
        fields = ['id', 'dispositivo', 'porcentaje', 'estado', 'temperatura', 'fecha_hora']
        read_only_fields = ['fecha_hora']
