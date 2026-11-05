from django.db import models


class Operador(models.Model):
    nombre = models.CharField(max_length=120)
    pais = models.CharField(max_length=100, blank=True)
    mcc = models.CharField(max_length=10, blank=True)
    mnc = models.CharField(max_length=10, blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre
