from rest_framework import serializers

from .models import Consumo


class ConsumoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consumo
        fields = ['id', 'dispositivo', 'sim', 'consumo_datos_movil', 'consumo_total', 'fecha', 'periodo', 'fuente']
