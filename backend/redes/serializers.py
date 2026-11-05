from rest_framework import serializers

from .models import RegistroRed


class RegistroRedSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroRed
        fields = ['id', 'dispositivo', 'sim', 'tipo_conexion', 'fecha_hora']
