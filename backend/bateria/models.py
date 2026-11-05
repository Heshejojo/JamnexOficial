from django.db import models

from dispositivos.models import Dispositivo


class RegistroBateria(models.Model):
    ESTADO_CHOICES = [
        ('CARGANDO', 'Cargando'),
        ('DESCARGANDO', 'Descargando'),
        ('CARGADA', 'Cargada'),
        ('DESCONOCIDO', 'Desconocido'),
    ]

    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE, related_name='registros_bateria')
    porcentaje = models.IntegerField(default=0)
    estado = models.CharField(max_length=30, choices=ESTADO_CHOICES, default='DESCONOCIDO')
    temperatura = models.FloatField(null=True, blank=True)
    fecha_hora = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.dispositivo} - {self.porcentaje}%'
