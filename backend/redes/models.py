from django.db import models

from dispositivos.models import Dispositivo
from operadores.models import Operador
from sims.models import Sim


class RegistroRed(models.Model):
    TIPO_CONEXION_CHOICES = [
        ('WIFI', 'WiFi'),
        ('DATOS_MOVILES', 'Datos Móviles'),
        ('SIN_CONEXION', 'Sin conexión'),
    ]

    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE, related_name='registros_red')
    sim = models.ForeignKey(Sim, on_delete=models.SET_NULL, null=True, blank=True, related_name='registros_red')
    tipo_conexion = models.CharField(max_length=30, choices=TIPO_CONEXION_CHOICES, default='WIFI')
    ssid = models.CharField(max_length=255, null=True, blank=True)
    rssi = models.IntegerField(null=True, blank=True)
    frecuencia = models.IntegerField(null=True, blank=True)
    velocidad = models.FloatField(null=True, blank=True)
    tipo_red_movil = models.CharField(max_length=80, null=True, blank=True)
    operador = models.ForeignKey(Operador, on_delete=models.SET_NULL, null=True, blank=True, related_name='registros_red')
    ip_local = models.CharField(max_length=100, null=True, blank=True)
    ip_publica = models.CharField(max_length=100, null=True, blank=True)
    fecha_hora = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.dispositivo} - {self.tipo_conexion}'
