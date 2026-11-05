from rest_framework import serializers

from .models import RegistroAlmacenamiento


class RegistroAlmacenamientoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroAlmacenamiento
        fields = ['id', 'dispositivo', 'almacenamiento_total', 'usado', 'disponible', 'porcentaje', 'fecha_hora']
        read_only_fields = ['fecha_hora']
