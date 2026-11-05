from django.db import models

from areas.models import Area


class Trabajador(models.Model):
    numero_empleado = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=100)
    apellido_paterno = models.CharField(max_length=100)
    apellido_materno = models.CharField(max_length=100, blank=True)
    area = models.ForeignKey(Area, on_delete=models.PROTECT, related_name='trabajadores')
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.nombre} {self.apellido_paterno}'
