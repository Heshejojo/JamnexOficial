from django.db import models

from dispositivos.models import Dispositivo


class RegistroAlmacenamiento(models.Model):
    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE, related_name='registros_almacenamiento')
    almacenamiento_total = models.BigIntegerField(default=0)
    usado = models.BigIntegerField(default=0)
    disponible = models.BigIntegerField(default=0)
    porcentaje = models.FloatField(default=0)
    fecha_hora = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.dispositivo} - {self.porcentaje}%'
