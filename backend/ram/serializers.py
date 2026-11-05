from rest_framework import serializers

from .models import RegistroRam


class RegistroRamSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroRam
        fields = ['id', 'dispositivo', 'ram_total', 'ram_usada', 'ram_disponible', 'porcentaje', 'fecha_hora']
        read_only_fields = ['fecha_hora']
