from django.db import models

from dispositivos.models import Dispositivo


class RegistroRam(models.Model):
    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE, related_name='registros_ram')
    ram_total = models.BigIntegerField(default=0)
    ram_usada = models.BigIntegerField(default=0)
    ram_disponible = models.BigIntegerField(default=0)
    porcentaje = models.FloatField(default=0)
    fecha_hora = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.dispositivo} - {self.porcentaje}%'
